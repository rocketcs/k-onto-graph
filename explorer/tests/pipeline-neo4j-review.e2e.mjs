import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const id = process.env.PIPELINE_REVIEW_RUN;
assert.ok(id, 'Set PIPELINE_REVIEW_RUN to a clean production run');
const base = process.env.PIPELINE_BASE_URL || 'http://127.0.0.1:8013';
const output = '../output/pipeline-neo4j-e2e';
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    const page = await browser.newPage({ viewport });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/?workspace=enrich&view=pipeline&pipeline_run=${id}`);
    await page.getByRole('button', { name: '结果审核', exact: true }).click();
    const response = page.waitForResponse(r => r.url().endsWith('/neo4j-plan'));
    await page.getByRole('button', { name: '发布到 Neo4j', exact: true }).click();
    const result = await response;
    assert.equal(result.status(), 200, await result.text());
    const plan = await result.json();
    assert.ok(plan.entities.length > 0);
    const dialog = page.getByRole('dialog', { name: 'Neo4j 实体对齐审核' });
    await dialog.waitFor();
    assert.equal(await dialog.locator('select').count(), plan.entities.length);
    assert.equal(await dialog.getByRole('button', { name: '确认对齐并事务发布' }).isDisabled(), true);
    const box = await dialog.boundingBox();
    assert.ok(box.x >= 0 && box.x + box.width <= viewport.width);
    assert.ok(box.y >= 0 && box.y + box.height <= viewport.height);
    await page.screenshot({ path: `${output}/review-${viewport.width}.png`, fullPage: true });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ viewport, entities: plan.entities.length, matched: plan.entities.filter(e => e.matches.length).length, endpoint: plan.endpoint }));
    await page.close();
  }
} finally {
  await browser.close();
}
