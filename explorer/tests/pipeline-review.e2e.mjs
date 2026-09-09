import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs/promises";

// Opt-in continuation of the hospital fixture's real model run. No model calls.
const id = process.env.PIPELINE_REVIEW_RUN;
assert.ok(id, "Set PIPELINE_REVIEW_RUN to the hospital document run ID");
const base = process.env.PIPELINE_BASE_URL || "http://127.0.0.1:8013";
const output = "../output/pipeline-workbench-e2e";
await fs.mkdir(output, { recursive: true });
async function api(route, body, method = "POST") {
  const response = await fetch(`${base}/api/${route}`, {
    method: body ? method : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  assert.ok(response.ok, await response.clone().text());
  return response.json();
}
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`${base}/?workspace=enrich&view=pipeline&pipeline_run=${id}`);
  await page.getByRole("button", { name: "结果审核", exact: true }).click();
  let run = await api(`pipeline-runs/${id}`);
  let result = await api(`pipeline-runs/${id}/results`);
  const target = "健康寿命提升至120岁";
  assert.ok(
    result.document.segments.some(
      (s) => s.id === "p16" && s.text.includes(target),
    ),
  );
  if (
    run.status === "awaiting_review" &&
    !result.candidate.entities.some((e) => e.name === target)
  ) {
    await page.getByTitle("补充实体").click();
    await page
      .getByLabel("修订记录 JSON")
      .fill(JSON.stringify({ name: target, type: "目标" }));
    await page
      .getByLabel("修订原因")
      .fill("原文 p16 明确陈述健康寿命目标，补回模型遗漏的关系端点。");
    const saved = page.waitForResponse(
      (r) => r.url().endsWith("/review") && r.request().method() === "PUT",
    );
    await page.getByRole("button", { name: "保存并校验", exact: true }).click();
    assert.equal((await saved).status(), 200);
  }
  run = await api(`pipeline-runs/${id}`);
  result = await api(`pipeline-runs/${id}/results`);
  if (run.status === "awaiting_review" && result.candidate.issues.length) {
    const paragraphs = {
      长寿医学: "p19",
      慢病逆转: "p23",
      肿瘤癌症: "p27",
      疑难重症: "p31",
      跨境救援: "p35",
    };
    const patches = [];
    for (const issue of result.candidate.issues) {
      const record = result.candidate.relationships.find(
        (r) => r.id === issue.record_id,
      );
      if (
        issue.rule === "target_evidence" &&
        record.type === "重点发展" &&
        paragraphs[record.target]
      ) {
        const segment = paragraphs[record.target];
        assert.ok(
          result.document.segments
            .find((s) => s.id === segment)
            .text.includes(record.target),
        );
        patches.push({
          record_id: record.id,
          changes: { segment_ids: ["p18", segment] },
        });
      } else if (issue.rule === "year" && record.year_text === "2028") {
        assert.ok(
          result.document.segments
            .find((s) => s.id === "p43")
            .text.includes("2028年"),
        );
        patches.push({
          record_id: record.id,
          changes: { year_text: "2028年" },
        });
      } else {
        throw new Error(
          "Unexpected issue requires human review: " + JSON.stringify(issue),
        );
      }
    }
    await api(
      `pipeline-runs/${id}/review`,
      {
        request_key: crypto.randomUUID(),
        expected_candidate_revision: run.candidate_revision,
        reason:
          "依据原文五大特色标题 p19/p23/p27/p31/p35 补齐证据；p43 年份保留原文单位。未放宽规则。",
        patches,
      },
      "PUT",
    );
  }
  result = await api(`pipeline-runs/${id}/results`);
  assert.deepEqual(result.candidate.issues, []);
  await page.reload();
  await page.getByRole("button", { name: "结果审核", exact: true }).click();
  run = await api(`pipeline-runs/${id}`);
  if (!run.publication) {
    const saved = page.waitForResponse(
      (r) => r.url().endsWith("/publish") && r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "发布独立图谱", exact: true })
      .click();
    assert.equal((await saved).status(), 200);
  }
  run = await api(`pipeline-runs/${id}`);
  assert.equal(run.status, "completed");
  assert.equal(run.publication.nodes, 25);
  assert.equal(run.publication.edges, 26);
  await page.screenshot({
    path: `${output}/review-published.png`,
    fullPage: true,
  });
  page.on("dialog", (dialog) => dialog.accept());
  const graphs = await api("pipeline-graphs");
  await api(`pipeline-graphs/${run.publication.id}/activate`, {
    revision: run.publication.revision,
    confirm_switch: true,
    expected_active_graph_id: graphs.active,
  });
  const observer = await browser.newPage();
  await observer.goto(base + "/");
  await observer.locator('.nav-button').filter({hasText: 'Knowledge Explorer'}).click();
  await observer.locator("canvas").first().waitFor();
  await observer.waitForTimeout(1000);
  const refreshed = observer.waitForResponse((r) =>
    r.url().includes("/api/graph/nodes?"),
  );
  await page.getByRole("button", { name: "查看图谱", exact: true }).click();
  assert.equal((await refreshed).status(), 200);
  await page.locator("canvas").first().waitFor();
  await page.waitForTimeout(2000);
  await page.screenshot({
    path: `${output}/published-graph.png`,
    fullPage: true,
  });
  await page
    .locator("canvas")
    .first()
    .screenshot({ path: `${output}/published-canvas.png` });
  const beforeZoom = await page.locator("canvas").first().screenshot();
  const canvasBounds = await page.locator("canvas").first().boundingBox();
  await page.mouse.move(
    canvasBounds.x + canvasBounds.width / 2,
    canvasBounds.y + canvasBounds.height / 2,
  );
  await page.mouse.wheel(0, -250);
  await page.waitForTimeout(700);
  const afterZoom = await page.locator("canvas").first().screenshot();
  assert.ok(!beforeZoom.equals(afterZoom), "Graph canvas must respond to zoom");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', {name: 'Fit view', exact: true}).click();
  await page.waitForTimeout(500);
  await page.screenshot({
    path: `${output}/published-graph-mobile.png`,
    fullPage: true,
  });
  await page
    .locator("canvas")
    .first()
    .screenshot({ path: `${output}/published-canvas-mobile.png` });
  await observer.close();
  await fs.writeFile(
    `${output}/publication-result.json`,
    JSON.stringify({ run, result }, null, 2),
  );
  assert.deepEqual(errors, []);
  console.log(
    JSON.stringify({
      id,
      status: run.status,
      nodes: run.publication.nodes,
      edges: run.publication.edges,
      audit: result.candidate.audit.length,
    }),
  );
} finally {
  await browser.close();
}
