import assert from "node:assert/strict";
import fs from "node:fs/promises";

// Explicitly opt in: this creates template versions and makes one real extraction.
const parent = process.env.PIPELINE_RERUN_PARENT;
assert.ok(parent, "Set PIPELINE_RERUN_PARENT to opt into a real model rerun");
const base = process.env.PIPELINE_BASE_URL || "http://127.0.0.1:8013";
async function api(route, body, method = "POST") {
  const response = await fetch(`${base}/api/${route}`, {
    method: body ? method : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  assert.ok(response.ok, await response.clone().text());
  return response.json();
}
async function version(kind, name, body) {
  const definition = await api("pipeline-definitions", {
    kind,
    name,
    body,
    request_key: crypto.randomUUID(),
  });
  return api(`pipeline-definitions/${definition.id}/versions`, {
    expected_revision: definition.revision,
    request_key: crypto.randomUUID(),
  });
}
async function wait(id) {
  for (let i = 0; i < 180; i++) {
    const run = await api(`pipeline-runs/${id}`);
    if (!["queued", "running", "publishing"].includes(run.status)) {
      assert.ok(
        ["awaiting_review", "completed"].includes(run.status),
        JSON.stringify(run),
      );
      return run;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error("Model run timed out");
}
const old = await api(`pipeline-runs/${parent}`);
const template = structuredClone(old.snapshots.extraction.body);
template.instructions +=
  "\n年份必须包含原文单位，如2028年。重点发展关系引用总标题及具体学科段落，不只引用总标题。发展目标的目标实体也必须列入entities，不遗漏任何关系端点。";
template.examples = [
  {
    document_segments: [{ id: "p1", text: "计划于2028年建设国际医学院。" }],
    entities: [{ name: "国际医学院", type: "机构" }],
    note: "year_text填写2028年；这是格式示例，不得把示例事实加入文档结果。",
  },
];
const extraction = await version(
  "extraction",
  "医院介绍 · 证据与年份修订",
  template,
);
const body = {
  document_id: old.document_id,
  flow_version_id: old.snapshots.flow.id,
  extraction_version_id: extraction.id,
  rules_version_id: old.snapshots.rules.id,
  publish_policy: "manual",
  model_profile_id: "deepseek",
};
const firstPlan = await api(`pipeline-runs/${parent}/rerun-plan`, body);
const first = await api(`pipeline-runs/${parent}/reruns`, {
  ...body,
  plan_hash: firstPlan.hash,
  request_key: crypto.randomUUID(),
});
console.log("Template rerun started: " + first.id);
const firstRun = await wait(first.id);
const firstResult = await api(`pipeline-runs/${first.id}/results`);
const rules = structuredClone(old.snapshots.rules.body);
rules.required_mentions = [
  ...new Set([...rules.required_mentions, "健康寿命提升至120岁"]),
];
const revisedRules = await version(
  "rules",
  "医院事实校验 · 寿命目标完整性",
  rules,
);
const secondBody = { ...body, rules_version_id: revisedRules.id };
const secondPlan = await api(
  `pipeline-runs/${first.id}/rerun-plan`,
  secondBody,
);
assert.deepEqual(Object.keys(secondPlan.reuse), ["parse", "split", "extract"]);
const second = await api(`pipeline-runs/${first.id}/reruns`, {
  ...secondBody,
  plan_hash: secondPlan.hash,
  request_key: crypto.randomUUID(),
});
const secondRun = await wait(second.id);
assert.equal(secondRun.steps.find((s) => s.id === "extract").status, "reused");
const events = await api(`pipeline-runs/${second.id}/events?limit=500`);
assert.equal(
  events.items.filter((e) => e.event === "chunk.completed").length,
  0,
);
const comparison = await api(
  `pipeline-runs/${second.id}/comparison?other_run_id=${first.id}`,
);
const secondResult = await api(`pipeline-runs/${second.id}/results`);
await fs.writeFile(
  "../output/pipeline-workbench-e2e/rerun-result.json",
  JSON.stringify(
    {
      firstPlan,
      firstRun,
      firstResult,
      secondPlan,
      secondRun,
      secondResult,
      comparison,
    },
    null,
    2,
  ),
);
console.log(
  JSON.stringify(
    {
      template_run: first.id,
      template_issues: firstResult.candidate.issues,
      rules_run: second.id,
      reused: Object.keys(secondPlan.reuse),
      rules_issues: secondResult.candidate.issues,
      comparison: {
        added: comparison.added.length,
        removed: comparison.removed.length,
        changed: comparison.changed.length,
      },
    },
    null,
    2,
  ),
);
