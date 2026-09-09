import { t as tr } from "../../i18n";
export type Config = Record<string, unknown>;
export type Version = {
  id: string;
  definition_id?: string;
  name: string;
  kind: string;
  revision: number;
  body: Config;
  hash: string;
};
export type Definition = {
  id: string;
  kind: string;
  name: string;
  revision: number;
  body: Config;
  versions: Version[];
};
export type Step = {
  id: string;
  status: string;
  error?: string;
  duration?: number;
  metrics?: Record<string, number>;
};
export type Publication = {
  id: string;
  revision: number;
  nodes: number;
  edges: number;
  name: string;
};
export type Run = {
  publish_target?: "local" | "neo4j";
  neo4j_publication?: {
    id: string;
    nodes: number;
    facts: number;
    database: string;
  };
  id: string;
  status: string;
  purpose: string;
  document_id: string;
  document_name: string;
  steps: Step[];
  quality: string;
  candidate_revision: number;
  last_event_seq: number;
  candidate?: string;
  error?: string;
  model: string;
  parent_run_id?: string;
  created_at: number;
  publication?: Publication;
  snapshots: Record<string, Version>;
};
export type Segment = { id: string; text: string; page?: number };
export type Entity = {
  id: string;
  name: string;
  canonical_name?: string;
  type: string;
};
export type Relation = {
  id: string;
  source: string;
  target: string;
  type: string;
  status: string;
  segment_ids: string[];
  quantity_text?: string | null;
  year_text?: string | null;
  evidence?: Segment[];
};
export type Issue = {
  id: string;
  record_id: string;
  rule: string;
  message: string;
};
export type Candidate = {
  entities: Entity[];
  relationships: Relation[];
  issues: Issue[];
  audit: Config[];
  excluded: string[];
  quality: string;
};
export type Result = {
  candidate: Candidate;
  document: { segments: Segment[]; characters: number };
  usage?: Config[];
};
export type RunEvent = {
  seq: number;
  event: string;
  step_id?: string;
  timestamp: number;
};
export type Plan = {
  hash: string;
  reuse: Record<string, string>;
  recompute: string[];
};

export const key = () => crypto.randomUUID();
export async function api<T>(
  path: string,
  body?: unknown,
  method = "POST",
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = sessionStorage.getItem("semantica-api-key");
  if (token) headers["X-API-Key"] = token;
  if (body !== undefined && !(body instanceof FormData))
    headers["Content-Type"] = "application/json";
  const response = await fetch("/api/" + path, {
    method: body === undefined ? "GET" : method,
    headers,
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  if (!response.ok) {
    const value = await response.json().catch(() => ({}));
    throw new Error(
      typeof value.detail === "string"
        ? value.detail
        : value.detail?.message ||
            tr("Request failed (HTTP {0}).", { 0: response.status }),
    );
  }
  return response.json();
}
export const labels: Record<string, string> = {
  parse: tr("Document parsing"),
  split: tr("Text chunking"),
  extract: tr("Knowledge extraction"),
  normalize: tr("Entity normalization"),
  validate: tr("Rule validation"),
  store: tr("Candidate results"),
  statistics: tr("Statistics summary"),
};
export const statuses: Record<string, string> = {
  queued: tr("Queued"),
  pending: tr("Pending"),
  running: tr("Running"),
  retrying: tr("Retrying"),
  awaiting_review: tr("Awaiting review"),
  publishing: tr("Publishing"),
  completed: tr("Completed"),
  preview_completed: tr("Trial completed"),
  failed: tr("Failed"),
  blocked: tr("Blocked"),
  cancel_requested: tr("Cancelling"),
  cancelled: tr("Cancelled"),
  interrupted: tr("Interrupted"),
  reused: tr("Reused"),
};
export const terminal = new Set([
  "completed",
  "preview_completed",
  "failed",
  "cancelled",
  "interrupted",
]);
