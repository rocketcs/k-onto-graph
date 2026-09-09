import { chromium } from 'playwright';
import assert from 'node:assert/strict';
const browser = await chromium.launch();
const viewport = process.env.MOBILE ? { width: 390, height: 844 } : { width: 1440, height: 1000 };
const context = await browser.newContext({ viewport, recordVideo: { dir: process.env.RECORD_DIR || '/tmp/graph-startup-before', size: viewport } });
const page = await context.newPage();
page.on('pageerror', error => console.log('PAGE ERROR', error.message));
await page.goto('http://127.0.0.1:5173/?workspace=explore&view=graph');
for (let i = 0; i < 22; i++) {
  await page.waitForTimeout(1000);
  assert.equal(await page.evaluate(() => {
    const element = document.querySelector('[data-graph-startup-pending="true"]');
    return !element || getComputedStyle(element).visibility === 'hidden';
  }), true, 'Unsettled graph must not be exposed');
  console.log(i + 1, (await page.locator('.workspace-body').innerText()).slice(-1200));
  if ([1, 3, 7].includes(i)) await page.screenshot({ path: `${process.env.RECORD_DIR || '/tmp/graph-startup-before'}/frame-${i}.png` });
}
const scene = page.locator('[data-graph-startup-pending]');
await page.waitForFunction(() => document.querySelector('[data-graph-startup-pending]')?.getAttribute('data-graph-startup-pending') === 'false', undefined, { timeout: 30000 });
assert.equal(await scene.evaluate(element => getComputedStyle(element).visibility), 'visible');
const positions = () => page.evaluate(async () => {
  const { graph } = await import('/src/store/graphStore.ts');
  return graph.mapNodes((id, attrs) => [id, attrs.x, attrs.y]);
});
const settled = await positions();
assert.ok(settled.length > 0);
await page.waitForTimeout(1500);
assert.deepEqual(await positions(), settled, 'Node positions must remain stable after loading');
await scene.scrollIntoViewIfNeeded();
await page.screenshot({ path: `${process.env.RECORD_DIR || '/tmp/graph-startup-before'}/settled.png` });
if (!process.env.MOBILE) {
  await page.getByRole('button', { name: '运行', exact: true }).click();
  await page.getByRole('button', { name: '暂停', exact: true }).waitFor();
  assert.equal(await scene.getAttribute('data-graph-startup-pending'), 'false', 'Manual layout remains visible');
  await page.getByRole('button', { name: '暂停', exact: true }).click();
}
await context.close();
console.log('VIDEO', await page.video().path());
await browser.close();
