import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { readFile } from 'node:fs/promises';

const en = JSON.parse(await readFile(new URL('../src/locales/en-US.json', import.meta.url)));
const zh = JSON.parse(await readFile(new URL('../src/locales/zh-CN.json', import.meta.url)));
const routes = [
  ['welcome'],
  ...['graph', 'memories', 'vocabulary'].map(view => ['explore', view]),
  ...['reasoning', 'sparql'].map(view => ['analyze', view]),
  ['decisions'],
  ...['pipeline', 'import', 'merge', 'resolve', 'registry'].map(view => ['enrich', view]),
  ...['lineage', 'kg-overview', 'ontology'].map(view => ['manage', view]),
  ...['registry', 'editor', 'versions', 'alignments', 'health', 'shacl'].map(view => ['ontology-hub', view]),
];
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  const languageLeaks = [];
  page.on('pageerror', error => errors.push(error.message));
  for (const [workspace, view] of routes) {
    const texts = [];
    for (const lang of ['zh-CN', 'en-US']) {
      const query = new URLSearchParams({ workspace, lang });
      if (view) query.set(workspace === 'ontology-hub' ? 'ontologyTab' : 'view', view);
      await page.goto(`http://127.0.0.1:5173/?${query}`);
      await page.waitForFunction(() => {
        const body = document.querySelector('.workspace-body, .landing-page');
        return body && body.textContent.trim() && !/^(Loading workspace|正在加载工作区)/.test(body.textContent.trim());
      });
      await page.waitForTimeout(600);
      assert.equal(await page.locator('html').getAttribute('lang'), lang);
      const text = await page.locator('.workspace-body, .landing-page').innerText();
      if (workspace === 'decisions') assert.match(text, lang === 'zh-CN' ? /因果链|未选择决策/ : /Causal Chain|No decision selected/);
      if (workspace === 'enrich' && view === 'resolve') assert.match(text, lang === 'zh-CN' ? /疑似重复|标记|可疑/ : /flagged pair/i);
      texts.push(text);
      const wrong = lang === 'zh-CN' ? en : zh;
      const right = lang === 'zh-CN' ? zh : en;
      const lines = text.split('\n').map(line => line.trim());
      const leaks = Object.keys(en).filter(key => wrong[key] !== right[key] && wrong[key].length > 5 && lines.includes(wrong[key]));
      // The merge preview deliberately compares original data spellings.
      const interfaceLeaks = leaks.filter(key => !(workspace === 'enrich' && view === 'merge' && key === 'Organization'));
      if (interfaceLeaks.length) languageLeaks.push({ workspace, view, lang, keys: interfaceLeaks });
      if (['pipeline', 'editor'].includes(view)) {
        await page.screenshot({ path: `/tmp/bilingual-${workspace}-${view}-${lang}.png` });
      }
    }
    assert.notEqual(texts[0], texts[1], `${workspace}/${view ?? ''} must have two displays`);
    console.log(`CHECKED ${workspace}/${view ?? ''}: Chinese and English`);
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(languageLeaks, [], 'Wrong-language interface strings');
} finally {
  await browser.close();
}
