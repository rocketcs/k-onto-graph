import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const base = process.env.PIPELINE_BASE_URL || 'http://127.0.0.1:5180';
const output = new URL('../../output/pipeline-motion/', import.meta.url);
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 800 } });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
try {
  await page.route('**/motion-fixture*', route => route.fulfill({
    contentType: 'text/html',
    body: '<html><head></head><body style="margin:0;background:#080f19"><div id="root"></div><script type="module">import RefreshRuntime from "/@react-refresh"; RefreshRuntime.injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => type => type; window.__vite_plugin_react_preamble_installed__ = true;</script><script type="module" src="/src/workspaces/PipelineWorkspace/PipelineCanvas.tsx"></script></body></html>',
  }));
  for (const lang of ['zh-CN', 'en-US']) {
    await page.goto(`${base}/motion-fixture?lang=${lang}`);
    await page.evaluate(async () => {
      const { default: React } = await import('/node_modules/.vite/deps/react.js');
      const { default: { createRoot } } = await import('/node_modules/.vite/deps/react-dom_client.js');
      const { PipelineCanvas } = await import('/src/workspaces/PipelineWorkspace/PipelineCanvas.tsx');
      await import('/src/workspaces/PipelineWorkspace/pipeline.css');
      const root = createRoot(document.getElementById('root'));
      const names = ['parse', 'split', 'extract', 'normalize', 'statistics', 'validate', 'store'];
      window.renderSteps = statuses => root.render(React.createElement('div', { className: 'pl-workspace', style: { height: '100vh', width: '100%' } }, React.createElement(PipelineCanvas, {
        flow: { steps: names }, steps: names.map((id, i) => ({ id, status: statuses[i] })),
        selected: 'extract', editable: false, onSelect() {}, onChange() {}, onError() {},
      })));
      window.renderSteps(['completed', 'reused', 'running', 'pending', 'pending', 'pending', 'pending']);
    });
    await page.locator('.pl-node[data-status="running"]').waitFor();
    assert.equal(await page.locator('.pl-edge-active').count(), 1);
    assert.equal(await page.locator('.pl-node[data-status="running"] .pl-node-status').evaluate(el => getComputedStyle(el).color), 'rgb(97, 217, 232)');
    const scan = page.locator('.pl-node[data-status="running"] .pl-node-activity span');
    const before = await scan.evaluate(el => getComputedStyle(el).transform);
    await page.waitForTimeout(150);
    assert.notEqual(await scan.evaluate(el => getComputedStyle(el).transform), before);
    await page.screenshot({ path: new URL(`running-${lang}.png`, output).pathname });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await scan.evaluate(el => getComputedStyle(el).animationName), 'none');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.evaluate(() => window.renderSteps(['completed', 'reused', 'failed', 'blocked', 'blocked', 'blocked', 'blocked']));
    await page.locator('.pl-node[data-status="failed"]').waitFor();
    assert.equal(await page.locator('.pl-edge-active').count(), 0);
    assert.equal(await page.locator('.pl-edge-blocked').count(), 4);
    await page.screenshot({ path: new URL(`failed-${lang}.png`, output).pathname });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: new URL(`mobile-${lang}.png`, output).pathname });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
    await page.setViewportSize({ width: 1440, height: 800 });
  }
  assert.deepEqual(errors, []);
  console.log('State styling, directional animation, failure transitions, locales, reduced motion and mobile checks passed.');
} finally {
  await browser.close();
}
