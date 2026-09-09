import { displayText } from "../../i18n";
import { t as tr } from "../../i18n";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import {
  Play,
  Save,
  Upload,
  RefreshCw,
  ShieldCheck,
  Square,
  GitCompareArrows,
  FileText,
  Download,
  X,
  KeyRound,
  Plus,
  ExternalLink,
  Settings2,
} from "lucide-react";
import { PipelineCanvas } from "./PipelineCanvas";
import { Neo4jPublish } from "./Neo4jPublish";
import {
  api,
  key,
  labels,
  statuses,
  terminal,
  type Config,
  type Definition,
  type Entity,
  type Plan,
  type Relation,
  type Result,
  type Run,
  type RunEvent,
} from "./api";
import "./pipeline.css";

const emptyFlow: Config = {
  steps: ["parse", "split", "extract", "normalize", "validate", "store"],
  positions: {},
  chunk_size: 4000,
  overlap: 200,
};
const emptySteps: Run["steps"] = [];
const kinds: Record<string, string> = {
  flow: tr("Pipeline template"),
  extraction: tr("Extraction template"),
  rules: tr("Rule set"),
};
type Tab = "flow" | "definitions" | "runs" | "results";

export function PipelineWorkspace({
  onOpenGraph,
}: {
  onOpenGraph: () => void;
}) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("flow");
  const [runId, setRunId] = useState(
    () => new URLSearchParams(location.search).get("pipeline_run") || "",
  );
  const [versionSelection, setVersions] = useState<Record<string, string>>({});
  const [file, setFile] = useState<File | null>(null);
  const [documentId, setDocumentId] = useState("");
  const [policy, setPolicy] = useState("manual");
  const [publishTarget, setPublishTarget] = useState("neo4j");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selected, setSelected] = useState("extract");
  const [flowDraft, setFlowDraft] = useState<Config | null>(null);
  const [editing, setEditing] = useState<Definition | null>(null);
  const [draftText, setDraftText] = useState("");
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [record, setRecord] = useState<Entity | Relation | null>(null);
  const [recordText, setRecordText] = useState("");
  const [reason, setReason] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [comparison, setComparison] = useState<Config | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [token, setToken] = useState(
    () => sessionStorage.getItem("semantica-api-key") || "",
  );
  const [historyPage, setHistoryPage] = useState(0);
  const [advanced, setAdvanced] = useState(false);

  const capabilities = useQuery({
    queryKey: ["pipeline", "capabilities"],
    queryFn: () =>
      api<{
        formats: string[];
        models: { model: string; available: boolean }[];
      }>("pipeline-capabilities"),
    retry: false,
  });
  const definitions = useQuery({
    queryKey: ["pipeline", "definitions"],
    queryFn: () => api<{ items: Definition[] }>("pipeline-definitions"),
    retry: false,
  });
  const runQuery = useQuery({
    queryKey: ["pipeline", "run", runId],
    queryFn: () => api<Run>(`pipeline-runs/${runId}`),
    enabled: !!runId,
    refetchInterval: (query) => {
      const run = query.state.data;
      return run && terminal.has(run.status)
        ? false
        : run?.status === "awaiting_review"
          ? 4000
          : 1000;
    },
    retry: false,
  });
  const run = runQuery.data;
  // Candidate artifacts can remain persisted when a run is cancelled or fails.
  // Only completed runs (including review and preview states) expose results
  // to avoid presenting stale issues as actionable review work.
  const reviewable =
    !!run && ["awaiting_review", "completed", "preview_completed"].includes(run.status);
  const resultQuery = useQuery({
    queryKey: ["pipeline", "result", runId, run?.candidate_revision],
    queryFn: () => api<Result>(`pipeline-runs/${runId}/results`),
    enabled: reviewable && !!run?.candidate,
    retry: false,
  });
  const history = useQuery({
    queryKey: ["pipeline", "history", historyPage],
    queryFn: () =>
      api<{ items: Run[]; next_cursor: number | null }>(
        `pipeline-runs?cursor=${historyPage}&limit=20`,
      ),
    enabled: tab === "runs",
    refetchInterval: tab === "runs" ? 5000 : false,
  });
  const defs = definitions.data?.items || [];
  const versions: Record<string, string> = { ...versionSelection };
  const effectiveVersions: Record<string, string> = {
    ...Object.fromEntries(defs.map((d) => [d.kind, d.versions[0]?.id || ""])),
    ...versionSelection,
  };
  const config = (kind: string) =>
    defs
      .find((d) => d.versions.some((v) => v.id === versions[kind]))
      ?.versions.find((v) => v.id === (versions[kind] || effectiveVersions[kind]));
  const flow = run
    ? run.snapshots.flow.body
    : flowDraft || config("flow")?.body || emptyFlow;
  const candidate = reviewable ? resultQuery.data?.candidate : undefined;

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let after = 0;
    async function poll() {
      try {
        const [snapshot, response] = await Promise.all([
          api<Run>(`pipeline-runs/${runId}`),
          api<{
            items: RunEvent[];
            next_seq: number;
            has_more: boolean;
            snapshot_last_seq: number;
          }>(`pipeline-runs/${runId}/events?after_seq=${after}`),
        ]);
        if (cancelled) return;
        queryClient.setQueryData(["pipeline", "run", runId], snapshot);
        after = response.next_seq;
        setEvents((old) => [
          ...old,
          ...response.items.filter((e) => !old.some((x) => x.seq === e.seq)),
        ]);
        if (!terminal.has(snapshot.status) || after < snapshot.last_event_seq)
          timer = setTimeout(poll, response.has_more ? 0 : 1000);
      } catch {
        if (!cancelled) timer = setTimeout(poll, 5000);
      }
    }
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [queryClient, runId]);

  function chooseRun(id: string) {
    setEvents([]);
    setRunId(id);
    setRecord(null);
    setPlan(null);
    setComparison(null);
    const url = new URL(location.href);
    if (id) {
      url.searchParams.set("pipeline_run", id);
      url.searchParams.set("workspace", "enrich");
    } else url.searchParams.delete("pipeline_run");
    historyReplace(url);
  }
  function historyReplace(url: URL) {
    window.history.replaceState(null, "", url);
  }
  async function action(task: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await task();
      await queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  async function getDocument() {
    if (documentId) return documentId;
    if (!file) throw new Error(tr("Select a document"));
    const form = new FormData();
    form.append("file", file);
    form.append("request_key", key());
    const doc = await api<{ id: string }>("pipeline-documents", form);
    setDocumentId(doc.id);
    return doc.id;
  }
  function requestBody(docId: string) {
    return {
      document_id: docId,
      model_profile_id: "deepseek",
      ...(versions.flow ? { flow_version_id: versions.flow } : {}),
      ...(versions.extraction ? { extraction_version_id: versions.extraction } : {}),
      ...(versions.rules ? { rules_version_id: versions.rules } : {}),
      publish_policy: policy,
      publish_target: publishTarget,
      request_key: key(),
    };
  }
  async function start(preview = false) {
    const body = requestBody(await getDocument());
    if (flowDraft)
      throw new Error(tr("Publish the pipeline draft before running"));
    if (preview && editing)
      body[`${editing.kind}_version_id` as "flow_version_id"] =
        `draft:${editing.id}:${editing.revision}`;
    const cacheKey = "pipeline-pending-request";
    const signature = JSON.stringify({ ...body, request_key: "", preview });
    const pending = JSON.parse(sessionStorage.getItem(cacheKey) || "null");
    if (pending?.signature === signature)
      body.request_key = pending.request_key;
    sessionStorage.setItem(
      cacheKey,
      JSON.stringify({ signature, request_key: body.request_key }),
    );
    const next = await api<{ id: string }>(
      preview ? "pipeline-previews" : "pipeline-runs",
      body,
    );
    sessionStorage.removeItem(cacheKey);
    chooseRun(next.id);
    setTab("flow");
  }
  function editDefinition(definition: Definition) {
    setEditing(definition);
    setDraftText(JSON.stringify(definition.body, null, 2));
    setTab("definitions");
  }
  function changeField(field: string, value: unknown) {
    try {
      setDraftText(
        JSON.stringify({ ...JSON.parse(draftText), [field]: value }, null, 2),
      );
    } catch {
      setError(tr("Invalid JSON. Fix it in the advanced editor first"));
    }
  }
  async function saveDraft(publish = false) {
    if (!editing) return;
    const saved = await api<Definition>(
      `pipeline-definitions/${editing.id}`,
      { body: JSON.parse(draftText), expected_revision: editing.revision },
      "PUT",
    );
    setEditing({ ...saved, versions: editing.versions });
    if (publish) {
      const version = await api<{ id: string }>(
        `pipeline-definitions/${editing.id}/versions`,
        { expected_revision: saved.revision, request_key: key() },
      );
      setVersions((old) => ({ ...old, [editing.kind]: version.id }));
    }
    setNotice(
      publish
        ? tr("Version published; subsequent runs will use the new version")
        : tr("Draft saved"),
    );
  }
  async function saveFlow() {
    const definition = defs.find((d) => d.kind === "flow");
    if (!definition) return;
    const draft = await api<Definition>(
      `pipeline-definitions/${definition.id}`,
      {
        expected_revision: definition.revision,
        body: flowDraft || config("flow")?.body || emptyFlow,
      },
      "PUT",
    );
    const version = await api<{ id: string }>(
      `pipeline-definitions/${definition.id}/versions`,
      { expected_revision: draft.revision, request_key: key() },
    );
    setVersions((old) => ({ ...old, flow: version.id }));
    setFlowDraft(null);
    setNotice(tr("Pipeline version published"));
  }
  function selectRecord(item: Entity | Relation) {
    setRecord(item);
    setReason("");
    const editable =
      "name" in item
        ? { name: item.name, type: item.type }
        : {
            source: item.source,
            target: item.target,
            type: item.type,
            status: item.status,
            quantity_text: item.quantity_text || null,
            year_text: item.year_text || null,
            segment_ids: item.segment_ids,
          };
    setRecordText(JSON.stringify(editable, null, 2));
  }
  async function review(exclude: boolean) {
    if (!run || !record || !candidate) return;
    await api(
      `pipeline-runs/${run.id}/review`,
      {
        expected_candidate_revision: run.candidate_revision,
        request_key: key(),
        reason: reason.trim() || (exclude ? "审核时排除" : "审核时确认"),
        additions:
          record.id === "__new__"
            ? {
                ["name" in record ? "entities" : "relationships"]: [
                  JSON.parse(recordText),
                ],
              }
            : {},
        patches:
          exclude || record.id === "__new__"
            ? []
            : [{ record_id: record.id, changes: JSON.parse(recordText) }],
        excluded: exclude
          ? [...new Set([...candidate.excluded, record.id])]
          : candidate.excluded.filter((id) => id !== record.id),
      },
      "PUT",
    );
    setRecord(null);
    setNotice(tr("Revision saved and revalidated"));
  }
  async function prepareRerun() {
    if (!run) return;
    setPlan(
      await api<Plan>(
        `pipeline-runs/${run.id}/rerun-plan`,
        requestBody(run.document_id),
      ),
    );
  }
  async function rerun() {
    if (!run || !plan) return;
    const next = await api<{ id: string }>(`pipeline-runs/${run.id}/reruns`, {
      ...requestBody(run.document_id),
      plan_hash: plan.hash,
    });
    chooseRun(next.id);
    setTab("flow");
  }
  async function openGraph() {
    if (!run?.publication) return;
    if (
      !window.confirm(
        tr(
          "Opening this result switches the active graph. Export any unsaved graph changes first.",
        ),
      )
    )
      return;
    const graphs = await api<{ active: string | null }>("pipeline-graphs");
    await api(`pipeline-graphs/${run.publication.id}/activate`, {
      revision: run.publication.revision,
      request_key: key(),
      confirm_switch: true,
      expected_active_graph_id: graphs.active,
    });
    await queryClient.invalidateQueries({ queryKey: ["graph"] });
    onOpenGraph();
  }
  async function download() {
    if (!run) return;
    const value = await api(`pipeline-runs/${run.id}/export`);
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `pipeline-${run.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
  const running =
    !!run &&
    ["queued", "running", "cancel_requested", "publishing"].includes(
      run.status,
    );
  const selectedStep = run?.steps.find((s) => s.id === selected);
  const queryError =
    capabilities.error ||
    definitions.error ||
    runQuery.error ||
    resultQuery.error;

  return (
    <div className="pl-workspace">
      <div className="pl-heading">
        <div>
          <small>{tr("DOCUMENT PIPELINE")}</small>
          <h2>{run ? run.document_name : tr("Document → Knowledge Graph")}</h2>
          <span className="pl-muted">
            {run
              ? `${run.id.slice(0, 12)} · ${statuses[run.status]} · ${run.purpose === "preview" ? tr("Draft trial") : run.publish_target === "neo4j" || run.neo4j_publication ? "Neo4j" : tr("Independent graph")}`
              : tr("New run")}
          </span>
        </div>
        <div className="pl-actions">
          <button
            className="ws-btn ws-btn--ghost"
            title="API Key"
            onClick={() => setShowKey(!showKey)}
          >
            <KeyRound size={16} />
          </button>
          {run && (
            <button
              className="ws-btn ws-btn--ghost"
              onClick={() => {
                chooseRun("");
                setTab("flow");
              }}
            >
              {tr("New run")}
            </button>
          )}
          {!run && (
            <button
              className="ws-btn ws-btn--ghost"
              disabled={busy || !flowDraft}
              onClick={() => void action(saveFlow)}
            >
              <Save size={15} />
              {tr("Save pipeline version")}
            </button>
          )}
          {running ? (
            <button
              className="ws-btn ws-btn--ghost"
              disabled={busy}
              onClick={() =>
                void action(async () => {
                  await api(`pipeline-runs/${runId}/cancel`, {
                    request_key: key(),
                  });
                })
              }
            >
              <Square size={14} />
              {tr("Cancel")}
            </button>
          ) : (
            !run && (
              <button
                className="ws-btn ws-btn--primary"
                disabled={
                  busy || !file || !capabilities.data?.models[0]?.available
                }
                onClick={() => void action(() => start())}
              >
                <Play size={15} />
                {busy ? tr("Submitting…") : tr("Upload and run")}
              </button>
            )
          )}
          {run?.publication && (
            <button
              className="ws-btn ws-btn--primary"
              disabled={busy}
              onClick={() => void action(openGraph)}
            >
              <ExternalLink size={15} />
              {tr("Open graph")}
            </button>
          )}
        </div>
      </div>
      {showKey && (
        <div className="pl-key">
          <input
            type="password"
            aria-label="API Key"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="API Key"
          />
          <button
            onClick={() => {
              sessionStorage.setItem("semantica-api-key", token);
              void queryClient.invalidateQueries({ queryKey: ["pipeline"] });
              setShowKey(false);
            }}
          >
            {tr("Apply")}
          </button>
        </div>
      )}
      {(error || queryError) && (
        <div className="pl-error" role="alert">
          {displayText(String(error || queryError?.message))}
          <button title={tr("Close")} onClick={() => setError("")}>
            <X size={14} />
          </button>
        </div>
      )}
      {notice && (
        <div className="pl-notice" role="status">
          {displayText(String(notice))}
        </div>
      )}
      <nav className="pl-tabs">
        {(
          [
            ["flow", tr("Workflow")],
            ["definitions", tr("Templates and rules")],
            ["runs", tr("Run history")],
            ["results", tr("Result review")],
          ] as [Tab, string][]
        ).map(([id, name]) => (
          <button key={id} data-active={tab === id} onClick={() => setTab(id)}>
            {name}
          </button>
        ))}
      </nav>
      {tab === "flow" && (
        <>
          <div className="pl-configbar">
            <label className="pl-file">
              <Upload size={15} />
              <span>{file?.name || tr("Choose document")}</span>
              <input
                aria-label={tr("Choose document")}
                type="file"
                accept={
                  capabilities.data?.formats.join(",") || ".docx,.txt,.md"
                }
                onChange={(e) => {
                  setFile(e.target.files?.[0] || null);
                  setDocumentId("");
                }}
              />
            </label>
            {["flow", "extraction", "rules"].map((kind) => (
              <label key={kind}>
                <small>{kinds[kind]}</small>
                <select
                  aria-label={kinds[kind]}
                  disabled={
                    !defs.some((d) => d.kind === kind && d.versions.length > 0)
                  }
                  value={versions[kind] || ""}
                  onChange={(e) => {
                    setVersions((old) => ({ ...old, [kind]: e.target.value }));
                    if (kind === "flow") setFlowDraft(null);
                    setPlan(null);
                  }}
                >
                  <option value="">使用默认</option>
                  {!defs.some(
                    (d) => d.kind === kind && d.versions.length > 0,
                  ) && (
                    <option value="">
                      {definitions.isPending
                        ? tr("Loading")
                        : definitions.isError
                          ? tr("Templates failed to load")
                          : tr("No templates available")}
                    </option>
                  )}
                  {defs
                    .filter((d) => d.kind === kind)
                    .flatMap((d) =>
                      d.versions.map((v) => (
                        <option key={v.id} value={v.id}>
                          {d.name} · v{v.revision}
                        </option>
                      )),
                    )}
                </select>
                {versions[kind] && config(kind) && (
                  <span className="pl-selection-text">
                    {
                      defs.find((d) =>
                        d.versions.some((v) => v.id === versions[kind]),
                      )?.name
                    }{" "}
                    · v{config(kind)?.revision}
                  </span>
                )}
              </label>
            ))}
            <label>
              <small>发布目标</small>
              <select
                aria-label="发布目标"
                value={publishTarget}
                onChange={(event) => {
                  setPublishTarget(event.target.value);
                  if (event.target.value === "neo4j") setPolicy("manual");
                }}
              >
                <option value="local">本地独立图谱</option>
                <option value="neo4j">Neo4j 知识库</option>
              </select>
            </label>
            <label>
              <small>{tr("Publication policy")}</small>
              <select
                aria-label={tr("Publication policy")}
                value={policy}
                onChange={(e) => setPolicy(e.target.value)}
              >
                {publishTarget !== "neo4j" && (
                  <option value="auto_if_clean">
                    {tr("Publish automatically after validation")}
                  </option>
                )}
                <option value="manual">{tr("Publish after review")}</option>
              </select>
            </label>
          </div>
          <div className="pl-editor">
            <div className="pl-canvas">
              <PipelineCanvas
                key={run?.id || versions.flow}
                flow={flow}
                steps={run?.steps || emptySteps}
                editable={!run}
                selected={selected}
                onSelect={setSelected}
                onError={setError}
                onChange={setFlowDraft}
              />
              {!run && (
                <button
                  className="pl-add"
                  title={tr("Add statistics node")}
                  onClick={() => {
                    const names = flow.steps as string[];
                    if (!names.includes("statistics"))
                      setFlowDraft({
                        ...flow,
                        steps: [
                          ...names.slice(0, 4),
                          "statistics",
                          ...names.slice(4),
                        ],
                      });
                  }}
                >
                  <Plus size={16} />
                  {tr("Statistics node")}
                </button>
              )}
            </div>
            <aside className="pl-inspector">
              <h3>
                <Settings2 size={16} />
                {labels[selected]}
              </h3>
              {selectedStep && (
                <>
                  <p data-status={displayText(String(selectedStep.status))}>
                    {statuses[selectedStep.status]}
                  </p>
                  {selectedStep.error && (
                    <p className="pl-error">{selectedStep.error}</p>
                  )}
                  <dl className="pl-metrics">
                    {Object.entries(selectedStep.metrics || {})
                      .filter(([metric]) =>
                        ["extract", "split"].includes(selected)
                          ? metric === "chunks"
                          : selected !== "parse" && metric !== "chunks",
                      )
                      .map(([metric, value]) => (
                        <div key={metric}>
                          <dt>
                            {{
                              entities: tr("Entities"),
                              relationships: tr("Relationships"),
                              chunks: tr("Chunks"),
                            }[metric] || metric}
                          </dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                  </dl>
                </>
              )}
              {!run && selected === "split" && (
                <>
                  {["chunk_size", "overlap"].map((field) => (
                    <label key={field}>
                      {field === "chunk_size"
                        ? tr("Chunk length")
                        : tr("Overlap length")}
                      <input
                        aria-label={
                          field === "chunk_size"
                            ? tr("Chunk length")
                            : tr("Overlap length")
                        }
                        type="number"
                        value={Number(flow[field])}
                        onChange={(e) =>
                          setFlowDraft({
                            ...flow,
                            [field]: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                  ))}
                </>
              )}
              {["extract", "normalize", "validate"].includes(selected) && (
                <button
                  className="ws-btn ws-btn--ghost"
                  onClick={() => {
                    const d = defs.find(
                      (x) =>
                        x.kind ===
                        (selected === "extract" ? "extraction" : "rules"),
                    );
                    if (d) editDefinition(d);
                  }}
                >
                  {tr("Edit")}{" "}
                  {selected === "extract"
                    ? tr("Extraction template")
                    : tr("Rule set")}
                </button>
              )}
              {!run && selected === "statistics" && (
                <button
                  className="ws-btn ws-btn--ghost"
                  onClick={() =>
                    setFlowDraft({
                      ...flow,
                      steps: (flow.steps as string[]).filter(
                        (x) => x !== "statistics",
                      ),
                    })
                  }
                >
                  {tr("Delete statistics node")}
                </button>
              )}
              {run && (
                <>
                  <h4>{tr("Run configuration snapshot")}</h4>
                  <small>{run.model}</small>
                  {Object.entries(run.snapshots).map(([kind, value]) => (
                    <p key={kind}>
                      {kinds[kind]} · {value.name} · v{value.revision}
                    </p>
                  ))}
                  {!running && (
                    <button
                      className="ws-btn ws-btn--ghost"
                      disabled={busy}
                      onClick={() => void action(prepareRerun)}
                    >
                      <RefreshCw size={14} />
                      {tr("Calculate rerun scope")}
                    </button>
                  )}
                  {plan && (
                    <div className="pl-plan">
                      <p>
                        {tr("Reuse:")}
                        {Object.keys(plan.reuse)
                          .map((s) => labels[s])
                          .join("、") || tr("None")}
                      </p>
                      <p>
                        {tr("Rerun:")}
                        {plan.recompute.map((s) => labels[s]).join("、")}
                      </p>
                      <button
                        disabled={busy}
                        onClick={() => void action(rerun)}
                      >
                        {tr("Start new run")}
                      </button>
                    </div>
                  )}
                  {reviewable && run.candidate && (
                    <button
                      className="ws-btn ws-btn--primary"
                      onClick={() => setTab("results")}
                    >
                      {tr("View results")}
                    </button>
                  )}
                </>
              )}
            </aside>
          </div>
          {run && (
            <details className="pl-events">
              <summary>
                {tr("Execution events ·")} {events.length}
              </summary>
              <div>
                {events.map((e) => (
                  <p key={e.seq}>
                    <time>
                      {new Date(e.timestamp * 1000).toLocaleTimeString()}
                    </time>
                    <span>{e.step_id ? labels[e.step_id] : tr("Task")}</span>
                    {e.event}
                  </p>
                ))}
              </div>
            </details>
          )}
        </>
      )}
      {tab === "definitions" && (
        <div className="pl-definitions">
          <aside>
            {defs.map((d) => (
              <button
                key={d.id}
                data-active={editing?.id === d.id}
                onClick={() => editDefinition(d)}
              >
                {kinds[d.kind]}
                <strong>{d.name}</strong>
                <small>
                  {tr("Draft v")}
                  {d.revision} · {d.versions.length} {tr("published versions")}
                </small>
              </button>
            ))}
          </aside>
          <section>
            {editing ? (
              <>
                <div className="pl-section-heading">
                  <h3>
                    {editing.name} {tr("· Draft v")}
                    {editing.revision}
                  </h3>
                  <div className="pl-actions">
                    <button
                      title={tr("Copy as a new template or rule set")}
                      disabled={busy}
                      onClick={() =>
                        void action(async () => {
                          const created = await api<Definition>(
                            "pipeline-definitions",
                            {
                              kind: editing.kind,
                              name: editing.name + tr(" · Copy"),
                              body: JSON.parse(draftText),
                              request_key: key(),
                            },
                          );
                          editDefinition({ ...created, versions: [] });
                        })
                      }
                    >
                      <Plus size={14} />
                      {tr("Save as new configuration")}
                    </button>
                    <button
                      disabled={busy}
                      onClick={() =>
                        void action(async () => {
                          await api(
                            `pipeline-definitions/${editing.id}/validate`,
                            { body: JSON.parse(draftText) },
                          );
                          setNotice(tr("Configuration validated"));
                        })
                      }
                    >
                      <ShieldCheck size={14} />
                      {tr("Validation")}
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => void action(() => saveDraft())}
                    >
                      <Save size={14} />
                      {tr("Save draft")}
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => void action(() => saveDraft(true))}
                    >
                      {tr("Publish version")}
                    </button>
                    <button
                      disabled={busy || !file}
                      onClick={() => void action(() => start(true))}
                    >
                      <Play size={14} />
                      {tr("Trial saved draft")}
                    </button>
                  </div>
                </div>
                <div className="pl-mode">
                  <button
                    data-active={!advanced}
                    onClick={() => setAdvanced(false)}
                  >
                    {tr("Form")}
                  </button>
                  <button
                    data-active={advanced}
                    onClick={() => setAdvanced(true)}
                  >
                    JSON
                  </button>
                </div>
                {advanced ? (
                  <Editor
                    loading={tr("Loading editor…")}
                    height="100%"
                    language="json"
                    theme="vs-dark"
                    value={draftText}
                    onChange={(value) => setDraftText(value || "")}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 13,
                      wordWrap: "on",
                      scrollBeyondLastLine: false,
                    }}
                  />
                ) : (
                  <DefinitionForm source={draftText} onChange={changeField} />
                )}
              </>
            ) : (
              <div className="pl-empty">
                {tr("Select a template or rule set")}
              </div>
            )}
          </section>
        </div>
      )}
      {tab === "runs" && (
        <section className="pl-scroll">
          <div className="pl-section-heading">
            <h3>{tr("Run history")}</h3>
            <div className="pl-actions">
              <button className="danger" disabled={busy} onClick={() => void action(async () => {
                await api("pipeline-runs", undefined, "DELETE");
                setRunId(""); setEvents([]); setHistoryPage(0);
              })}>
                清除全部运行数据
              </button>
              <button
                disabled={!historyPage}
                onClick={() => setHistoryPage(Math.max(0, historyPage - 20))}
              >
                {tr("Previous page")}
              </button>
              <button
                disabled={!history.data?.next_cursor}
                onClick={() => setHistoryPage(history.data?.next_cursor || 0)}
              >
                {tr("Next page")}
              </button>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>{tr("Document")}</th>
                <th>{tr("Status")}</th>
                <th>{tr("Time")}</th>
                <th>{tr("Model")}</th>
                <th>{tr("Publish")}</th>
              </tr>
            </thead>
            <tbody>
              {history.data?.items.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => {
                    chooseRun(r.id);
                    setTab("flow");
                  }}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      chooseRun(r.id);
                      setTab("flow");
                    }
                  }}
                >
                  <td>
                    {r.document_name}
                    <small>{r.id.slice(0, 12)}</small>
                  </td>
                  <td data-status={displayText(String(r.status))}>
                    {statuses[r.status]}
                  </td>
                  <td>{new Date(r.created_at * 1000).toLocaleString()}</td>
                  <td>{r.model}</td>
                  <td>
                    {r.publication
                      ? tr("{0} entities / {1} relationships", {
                          0: r.publication.nodes,
                          1: r.publication.edges,
                        })
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!history.data?.items.length && (
            <div className="pl-empty">{tr("No runs yet")}</div>
          )}
        </section>
      )}
      {tab === "results" &&
        (candidate && run ? (
          <div className="pl-results">
            <section className="pl-scroll">
              <div className="pl-section-heading">
                <div>
                  <h3>
                    {candidate.entities.length} {tr("entities ·")}{" "}
                    {candidate.relationships.length} {tr("links")}
                  </h3>
                  <small>
                    {candidate.issues.length} {tr("pending issues ·")}{" "}
                    {candidate.audit.length}{" "}
                    {tr("rule or manual records · Candidate v")}
                    {run.candidate_revision}
                  </small>
                </div>
                <div className="pl-actions">
                  <button
                    disabled={busy}
                    title={tr("Export run and evidence")}
                    onClick={() => void action(download)}
                  >
                    <Download size={16} />
                  </button>
                  {run.parent_run_id && (
                    <button
                      disabled={busy}
                      title={tr("Compare with previous result")}
                      onClick={() =>
                        void action(async () =>
                          setComparison(
                            await api<Config>(
                              `pipeline-runs/${run.id}/comparison?other_run_id=${run.parent_run_id}`,
                            ),
                          ),
                        )
                      }
                    >
                      <GitCompareArrows size={16} />
                    </button>
                  )}
                  {run.purpose !== "preview" &&
                    ["awaiting_review", "completed"].includes(run.status) && (
                      <Neo4jPublish
                        key={run.id}
                        run={run}
                        disabled={busy || candidate.issues.length > 0}
                        onDone={() => {
                          void queryClient.invalidateQueries({
                            queryKey: ["pipeline"],
                          });
                          setNotice("已事务发布到 Neo4j");
                        }}
                      />
                    )}
                  {run.status === "awaiting_review" &&
                    run.publish_target !== "neo4j" && (
                      <button
                        className="ws-btn ws-btn--primary"
                        disabled={busy || candidate.issues.length > 0}
                        onClick={() =>
                          void action(async () => {
                            await api(`pipeline-runs/${run.id}/publish`, {
                              candidate_revision: run.candidate_revision,
                              request_key: key(),
                            });
                          })
                        }
                      >
                        {tr("Publish independent graph")}
                      </button>
                    )}
                </div>
              </div>
              {candidate.issues.length > 0 && (
                <div className="pl-issues">
                  {candidate.issues.map((issue) => (
                    <button
                      key={issue.id}
                      onClick={() => {
                        const item = [
                          ...candidate.entities,
                          ...candidate.relationships,
                        ].find((r) => r.id === issue.record_id);
                        if (item) selectRecord(item);
                        else {
                          setNotice(
                            issue.message +
                              tr("; adjust the extraction template and rerun"),
                          );
                        }
                      }}
                    >
                      <ShieldCheck size={14} />
                      {displayText(String(issue.message))}
                      <small>{issue.rule}</small>
                    </button>
                  ))}
                </div>
              )}
              <h4>{tr("Relationships")}</h4>
              {run.status === "awaiting_review" && (
                <button
                  title={tr("Add relationship")}
                  onClick={() =>
                    selectRecord({
                      id: "__new__",
                      source: "",
                      target: "",
                      type: "合作",
                      status: "文档陈述",
                      segment_ids: [],
                    } as Relation)
                  }
                >
                  <Plus size={16} />
                  {tr("Add relationship")}
                </button>
              )}
              <table>
                <thead>
                  <tr>
                    <th>{tr("Origin")}</th>
                    <th>{tr("Relationships")}</th>
                    <th>{tr("Target")}</th>
                    <th>{tr("Status")}</th>
                    <th>{tr("Quantity / year")}</th>
                  </tr>
                </thead>
                <tbody>
                  {candidate.relationships.map((r) => (
                    <tr
                      key={r.id}
                      className={
                        candidate.excluded.includes(r.id) ? "pl-excluded" : ""
                      }
                      onClick={() => selectRecord(r)}
                    >
                      <td>{r.source}</td>
                      <td>{displayText(String(r.type))}</td>
                      <td>{r.target}</td>
                      <td>{displayText(String(r.status))}</td>
                      <td>
                        {[r.quantity_text, r.year_text]
                          .filter(Boolean)
                          .join(" / ") || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <h4>{tr("Entities")}</h4>
              {run.status === "awaiting_review" && (
                <button
                  title={tr("Add entity")}
                  onClick={() =>
                    selectRecord({
                      id: "__new__",
                      name: "",
                      type: "机构",
                      canonical_name: "",
                    })
                  }
                >
                  <Plus size={16} />
                  {tr("Add entity")}
                </button>
              )}
              <div className="pl-entities">
                {candidate.entities.map((e) => (
                  <button
                    className={
                      candidate.excluded.includes(e.id) ? "pl-excluded" : ""
                    }
                    key={e.id}
                    onClick={() => selectRecord(e)}
                  >
                    {e.name}
                    <small>{displayText(String(e.type))}</small>
                  </button>
                ))}
              </div>
              <details>
                <summary>{tr("Rule audit")}</summary>
                <pre>{JSON.stringify(candidate.audit, null, 2)}</pre>
              </details>
              {comparison && (
                <details open>
                  <summary>{tr("Compare with parent run")}</summary>
                  <pre>{JSON.stringify(comparison, null, 2)}</pre>
                </details>
              )}
            </section>
            <aside className="pl-review">
              {record ? (
                <>
                  <div className="pl-section-heading">
                    <h3>
                      <FileText size={16} />
                      {tr("Records and evidence")}
                    </h3>
                    <button title={tr("Close")} onClick={() => setRecord(null)}>
                      <X size={14} />
                    </button>
                  </div>
                  {"source" in record &&
                    record.segment_ids.map((id) => {
                      const segment = resultQuery.data?.document.segments.find(
                        (s) => s.id === id,
                      );
                      return (
                        <blockquote key={id}>
                          <small>
                            {id}
                            {segment?.page
                              ? tr(" · Page {0}", { 0: segment.page })
                              : ""}
                          </small>
                          {segment?.text || tr("Invalid citation")}
                        </blockquote>
                      );
                    })}
                  <textarea
                    aria-label={tr("Revision records JSON")}
                    value={recordText}
                    onChange={(e) => setRecordText(e.target.value)}
                    readOnly={run.status !== "awaiting_review"}
                    rows={12}
                  />
                  {run.status === "awaiting_review" && (
                    <>
                      <input
                        aria-label={tr("Revision reason")}
                        placeholder={tr("Reason for revision or exclusion")}
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                      />
                      <div className="pl-actions">
                        <button
                          disabled={busy}
                          onClick={() => void action(() => review(false))}
                        >
                          {tr("Save and validate")}
                        </button>
                        <button
                          disabled={
                            busy || record.id === "__new__"
                          }
                          onClick={() => void action(() => review(true))}
                        >
                          {tr("Exclude this record")}
                        </button>
                      </div>
                    </>
                  )}
                </>
              ) : (
                <div className="pl-empty">
                  {tr("Select a record to view evidence")}
                </div>
              )}
              <details>
                <summary>{tr("Source paragraph")}</summary>
                {resultQuery.data?.document.segments.map((segment) => (
                  <blockquote key={segment.id}>
                    <small>
                      {segment.id}
                      {segment.page
                        ? tr(" · Page {0}", { 0: segment.page })
                        : ""}
                    </small>
                    {segment.text}
                  </blockquote>
                ))}
              </details>
            </aside>
          </div>
        ) : (
          <div className="pl-empty">{tr("No candidate results yet")}</div>
        ))}
    </div>
  );
}

const fieldLabels: Record<string, string> = {
  chunk_size: tr("Chunk length"),
  overlap: tr("Overlap length"),
  instructions: tr("Extraction requirements"),
  entity_types: tr("Entity types"),
  relation_types: tr("Relationship types"),
  statement_relations: tr("Relationships treated as document statements"),
  operational_markers: tr("Operational status evidence terms"),
  construction_markers: tr("Construction status evidence terms"),
  required_mentions: tr(
    "Items that must be covered when present in the source",
  ),
  require_target_in_evidence: tr(
    "Evidence must include the relationship target",
  ),
  require_goal_quantity: tr("Target must contain a quantity"),
  review_isolated_entities: tr("Review isolated entities"),
};
function DefinitionForm({
  source,
  onChange,
}: {
  source: string;
  onChange: (field: string, value: unknown) => void;
}) {
  let data: Config;
  try {
    data = JSON.parse(source);
  } catch {
    return (
      <div className="pl-error">
        {tr("Invalid JSON. Switch to the JSON editor to fix it.")}
      </div>
    );
  }
  return (
    <div className="pl-form">
      {Object.entries(data)
        .filter(([field]) => fieldLabels[field])
        .map(([field, value]) => (
          <label key={field}>
            {typeof value === "boolean" ? (
              <span className="pl-check">
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(e) => onChange(field, e.target.checked)}
                />
                {fieldLabels[field]}
              </span>
            ) : (
              <>
                <span>{fieldLabels[field]}</span>
                {typeof value === "number" ? (
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => onChange(field, Number(e.target.value))}
                  />
                ) : (
                  <textarea
                    rows={field === "instructions" ? 8 : 3}
                    value={
                      Array.isArray(value) ? value.join("\n") : String(value)
                    }
                    onChange={(e) =>
                      onChange(
                        field,
                        Array.isArray(value)
                          ? e.target.value.split("\n")
                          : e.target.value,
                      )
                    }
                  />
                )}
              </>
            )}
          </label>
        ))}
      <details>
        <summary>{tr("Other configuration")}</summary>
        <pre>
          {JSON.stringify(
            Object.fromEntries(
              Object.entries(data).filter(([field]) => !fieldLabels[field]),
            ),
            null,
            2,
          )}
        </pre>
      </details>
    </div>
  );
}
