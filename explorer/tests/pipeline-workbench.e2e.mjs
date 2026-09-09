import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import assert from "node:assert/strict";

const base = process.env.PIPELINE_BASE_URL || "http://127.0.0.1:8013";
const output = path.resolve("../output/pipeline-workbench-e2e");
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
try {
  await page.goto(base + "/?workspace=enrich&view=pipeline");
  await page.getByRole("heading", { name: "文档 → 知识图谱" }).waitFor();
  await page.locator(".react-flow__node").first().waitFor();
  assert.equal(await page.locator(".react-flow__node").count(), 6);
  await page.screenshot({
    path: path.join(output, "desktop-flow.png"),
    fullPage: true,
  });
  await page.getByTitle("添加统计节点").click();
  await page
    .locator(
      '.react-flow__node-statistics, .react-flow__node[data-id="statistics"]',
    )
    .waitFor();
  assert.equal(await page.locator(".react-flow__node").count(), 7);
  await page.locator('.react-flow__node[data-id="statistics"]').click();
  await page.getByRole("button", { name: "删除统计节点", exact: true }).click();
  assert.equal(await page.locator(".react-flow__node").count(), 6);
  // Reload discards this canvas draft; the server definition was never mutated.
  await page.reload();
  await page.getByRole("heading", { name: "文档 → 知识图谱" }).waitFor();
  await page.getByRole("button", { name: "模板与规则", exact: true }).click();
  await page
    .locator(".pl-definitions > aside button")
    .filter({ has: page.locator("strong", { hasText: /^医院事实校验$/ }) })
    .click();
  await page.getByRole("checkbox", { name: "目标必须包含数量" }).waitFor();
  await page.screenshot({
    path: path.join(output, "desktop-rules.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "流程", exact: true }).click();
  if (process.env.PIPELINE_LIVE_DOCUMENT) {
    await page
      .getByLabel("选择文档", { exact: true })
      .setInputFiles(process.env.PIPELINE_LIVE_DOCUMENT);
    const responsePromise = page.waitForResponse(
      (r) =>
        r.url() === base + "/api/pipeline-runs" &&
        r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "上传并运行", exact: true }).click();
    const response = await responsePromise;
    assert.equal(response.status(), 202, await response.text());
    const { id } = await response.json();
    let run;
    for (let i = 0; i < 120; i++) {
      run = await (
        await page.request.get(`${base}/api/pipeline-runs/${id}`)
      ).json();
      if (!["queued", "running", "publishing"].includes(run.status)) break;
      await page.waitForTimeout(1000);
    }
    assert.ok(
      ["completed", "awaiting_review"].includes(run.status),
      JSON.stringify(run),
    );
    assert.ok(run.steps.every((s) => s.status === "completed"));
    await page.reload();
    await page.getByRole("heading", { name: run.document_name }).waitFor();
    await page.getByRole("button", { name: "结果审核", exact: true }).click();
    await page.locator(".pl-results table").waitFor();
    await page.screenshot({
      path: path.join(output, "desktop-results.png"),
      fullPage: true,
    });
    const result = await (
      await page.request.get(`${base}/api/pipeline-runs/${id}/results`)
    ).json();
    await fs.writeFile(
      path.join(output, "live-result.json"),
      JSON.stringify({ run, result }, null, 2),
    );
    console.log(
      JSON.stringify(
        {
          run_id: id,
          status: run.status,
          entities: result.candidate.entities.length,
          relationships: result.candidate.relationships.length,
          issues: result.candidate.issues,
        },
        null,
        2,
      ),
    );
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "流程", exact: true }).click();
  await page.screenshot({
    path: path.join(output, "mobile-flow.png"),
    fullPage: true,
  });
  const bounds = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  assert.ok(bounds.scroll <= bounds.width + 1, JSON.stringify(bounds));
  assert.deepEqual(errors, []);
  console.log(
    "Browser interaction, refresh recovery and responsive checks passed",
  );
} finally {
  await browser.close();
}
