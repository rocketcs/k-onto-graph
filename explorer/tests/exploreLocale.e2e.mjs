import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const nodes = [
    { id: 'alpha', type: 'Person', content: 'Alpha', properties: {} },
    { id: 'beta', type: 'Document', content: 'Beta', properties: {} },
  ];
  await page.routeWebSocket('**/ws/graph-updates', () => {});
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let json = {};
    if (path === '/api/info') json = { capabilities: { agent_memory: true } };
    if (path === '/api/graph/stats') json = { nodes: 2, edges: 1 };
    if (path === '/api/graph/nodes') json = { nodes, total: 2, next_cursor: null };
    if (path === '/api/graph/edges') json = { edges: [{ id: 'edge', source: 'alpha', target: 'beta', type: 'READS', weight: 1, properties: {} }], total: 1, next_cursor: null };
    if (path === '/api/temporal/bounds') json = { min: null, max: null };
    if (path === '/api/temporal/snapshot') json = { active_node_ids: ['alpha', 'beta'], active_node_count: 2 };
    if (path === '/api/graph/search') json = { results: [{ node: nodes[0], score: 1 }] };
    if (path === '/api/vocabulary/schemes') json = [];
    if (path === '/api/memories') json = { items: [], total: 0 };
    if (path.startsWith('/api/markdown/')) json = { resource: { kind: 'node', id: 'alpha' }, source: 'Original content', body: 'Original content', revision: 'r1', editable: true };
    await route.fulfill({ json });
  });
  await page.goto('http://127.0.0.1:5173/?workspace=explore');
  await page.getByRole('button', { name: '完整图谱', exact: true }).waitFor();
  assert.equal(await page.locator('html').getAttribute('lang'), 'zh-CN');
  await page.getByRole('button', { name: '效果', exact: true }).click();
  await page.getByText('场景效果', { exact: true }).waitFor();
  await page.screenshot({ path: '/tmp/explore-bilingual-zh.png' });
  await page.getByRole('combobox', { name: '界面语言' }).selectOption('en-US');
  await page.getByRole('button', { name: 'Full Graph', exact: true }).waitFor();
  assert.equal(await page.locator('html').getAttribute('lang'), 'en-US');
  assert.equal(new URL(page.url()).searchParams.get('workspace'), 'explore');
  await page.getByRole('button', { name: 'Effects', exact: true }).click();
  await page.getByText('Scene effects', { exact: true }).waitFor();
  assert.doesNotMatch((await page.locator('.workspace-shell').innerText()), /[\u4e00-\u9fff]/);
  await page.screenshot({ path: '/tmp/explore-bilingual-en.png' });
  await page.getByRole('button', { name: 'Vocabulary Browser', exact: true }).click();
  await page.getByText('Ontology & Vocabulary', { exact: true }).waitFor();
  await page.getByRole('combobox', { name: 'Language' }).selectOption('zh-CN');
  await page.getByText('本体与词表', { exact: true }).waitFor();
  assert.equal(new URL(page.url()).searchParams.get('view'), 'vocabulary');
  await page.goto('http://127.0.0.1:5173/?workspace=explore');
  await page.getByRole('button', { name: '完整图谱', exact: true }).waitFor();
  await page.getByRole('textbox', { name: '搜索图谱节点' }).fill('Alpha');
  await page.getByRole('option').filter({ hasText: 'Alpha' }).click();
  await page.getByRole('button', { name: '编辑', exact: true }).click();
  const editor = page.getByRole('textbox', { name: 'Markdown 源码' });
  await editor.fill('Unsaved content');
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('combobox', { name: '界面语言' }).selectOption('en-US');
  assert.equal(await editor.inputValue(), 'Unsaved content');
  assert.equal(await page.locator('html').getAttribute('lang'), 'zh-CN');
  await page.getByRole('button', { name: '取消', exact: true }).click();
  await editor.waitFor({ state: 'hidden' });
  page.once('dialog', dialog => { errors.push(`Unexpected dialog: ${dialog.message()}`); return dialog.dismiss(); });
  await page.getByRole('combobox', { name: '界面语言' }).selectOption('en-US');
  await page.getByRole('button', { name: 'Full Graph', exact: true }).waitFor();
  await page.goto('http://127.0.0.1:5173/?workspace=explore');
  await page.getByRole('button', { name: 'Full Graph', exact: true }).waitFor();
  assert.equal(await page.getByRole('combobox', { name: 'Language' }).inputValue(), 'en-US');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: '/tmp/explore-bilingual-en-mobile.png' });
  assert.deepEqual(errors, []);
  console.log('PASS: Chinese/English views, resource labels, persistence, workspace preservation, draft protection, mobile rendering.');
} finally {
  await browser.close();
}
