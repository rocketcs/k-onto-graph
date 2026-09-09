import { useState } from "react";
import { Database, X } from "lucide-react";
import { api, key, type Run } from "./api";

type Alignment = {
  hash: string;
  candidate_revision: number;
  database: string;
  endpoint: string;
  entities: {
    id: string;
    name: string;
    type: string;
    truncated: boolean;
    matches: {
      id: string;
      labels: string[];
      properties: Record<string, unknown>;
    }[];
  }[];
};

export function Neo4jPublish({
  run,
  disabled,
  onDone,
}: {
  run: Run;
  disabled: boolean;
  onDone: () => void;
}) {
  const [plan, setPlan] = useState<Alignment | null>(null);
  const [decisions, setDecisions] = useState<Record<string, string>>({});
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [checked, setChecked] = useState<Set<string>>(new Set());
  async function prepare() {
    setBusy(true);
    setError("");
    try {
      const status = await api<{ published: boolean }>(
        `pipeline-runs/${run.id}/neo4j-reconcile`,
        {},
      );
      if (status.published) {
        onDone();
        return;
      }
      setPlan(
        await api<Alignment>(`pipeline-runs/${run.id}/neo4j-plan`, {
          candidate_revision: run.candidate_revision,
        }),
      );
      setDecisions({});
      setChecked(new Set());
      setReason("");
    } catch (error) {
      setError(String(error));
    } finally {
      setBusy(false);
    }
  }
  async function publish() {
    if (!plan) return;
    setBusy(true);
    setError("");
    const payload = {
      candidate_revision: plan.candidate_revision,
      plan_hash: plan.hash,
      decisions,
      reason,
    };
    const storageKey = `neo4j-publish:${run.id}:${plan.hash}`;
    let requestKey = sessionStorage.getItem(storageKey);
    const signature = JSON.stringify(payload);
    const stored = requestKey ? JSON.parse(requestKey) : null;
    requestKey = stored?.signature === signature ? stored.key : key();
    sessionStorage.setItem(
      storageKey,
      JSON.stringify({ signature, key: requestKey }),
    );
    try {
      await api(`pipeline-runs/${run.id}/neo4j-publish`, {
        ...payload,
        request_key: requestKey,
      });
      setPlan(null);
      onDone();
    } catch (error) {
      setError(String(error));
    } finally {
      setBusy(false);
    }
  }
  async function reconcile() {
    setBusy(true);
    try {
      const status = await api<{ published: boolean }>(
        `pipeline-runs/${run.id}/neo4j-reconcile`,
        {},
      );
      if (status.published) {
        setPlan(null);
        onDone();
      } else setError("Neo4j 暂未发现已提交记录，可按原方案重试");
    } catch (error) {
      setError(String(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button
        disabled={disabled || busy || !!run.neo4j_publication}
        onClick={() => void prepare()}
      >
        <Database size={16} />
        {run.neo4j_publication ? "已发布 Neo4j" : "发布到 Neo4j"}
      </button>
      {error && !plan && <span role="alert">{error}</span>}
      {plan && (
        <div className="pl-neo4j-overlay">
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Neo4j 实体对齐审核"
            className="pl-neo4j-dialog"
          >
            <div className="pl-section-heading">
              <h3>Neo4j 实体对齐审核 · 候选 v{plan.candidate_revision}</h3>
              <button
                aria-label="关闭对齐审核"
                disabled={busy}
                onClick={() => setPlan(null)}
              >
                <X size={16} />
              </button>
            </div>
            <div className="pl-neo4j-body">
              <p>目标：{plan.endpoint} / {plan.database}</p>
              <div className="pl-neo4j-bulk-actions">
                <button type="button" disabled={busy} onClick={() => setDecisions(Object.fromEntries(plan.entities.map((e) => [e.id, "new"]))) }>
                  全部设为新建实体
                </button>
                <button type="button" disabled={busy} onClick={() => setChecked(new Set(plan.entities.map((e) => e.id)))}>
                  全选实体
                </button>
                <button type="button" disabled={busy || checked.size === 0} onClick={() => setDecisions((old) => ({ ...old, ...Object.fromEntries([...checked].map((id) => [id, "new"])) }))}>
                  将所选设为新建
                </button>
              </div>
              {plan.entities.map((entity) => (
                <div className="pl-neo4j-entity" key={entity.id}>
                  <input type="checkbox" aria-label={`选择 ${entity.name}`} checked={checked.has(entity.id)} onChange={(e) => setChecked((old) => { const next = new Set(old); e.target.checked ? next.add(entity.id) : next.delete(entity.id); return next; })} />
                  <strong>
                    {entity.name} <small>{entity.type}</small>
                  </strong>
                  <select
                    aria-label={`对齐 ${entity.name}`}
                    value={decisions[entity.id] || ""}
                    disabled={busy}
                    onChange={(event) =>
                      setDecisions((old) => ({
                        ...old,
                        [entity.id]: event.target.value,
                      }))
                    }
                  >
                    <option value="">待确认</option>
                    <option value="new">新建独立实体</option>
                    {entity.matches.map((match) => (
                      <option key={match.id} value={match.id}>
                        关联 {String(match.properties.name || match.id)} ·{" "}
                        {match.labels.join(", ")} · {match.id}
                      </option>
                    ))}
                  </select>
                  {entity.truncated && (
                    <span role="alert">匹配超过 20 项，当前仅列出前 20 项</span>
                  )}
                  {entity.matches.map((match) => (
                    <details key={match.id}>
                      <summary>
                        {match.labels.join(", ")} · {match.id}
                      </summary>
                      <pre>{JSON.stringify(match.properties, null, 2)}</pre>
                    </details>
                  ))}
                </div>
              ))}
            </div>
            <footer>
              <label>
                审核原因
                <textarea
                  aria-label="Neo4j 审核原因"
                  value={reason}
                  disabled={busy}
                  onChange={(event) => setReason(event.target.value)}
                />
              </label>
              {error && (
                <>
                  <p role="alert">{error}</p>
                  <button disabled={busy} onClick={() => void reconcile()}>
                    核对提交结果
                  </button>
                </>
              )}
              <button
                disabled={
                  busy ||
                  !reason.trim() ||
                  plan.entities.some((entity) => !decisions[entity.id]) ||
                  plan.candidate_revision !== run.candidate_revision
                }
                onClick={() => void publish()}
              >
                {busy ? "正在提交" : "确认对齐并事务发布"}
              </button>
            </footer>
          </section>
        </div>
      )}
    </>
  );
}
