import assert from "node:assert/strict";
import test from "node:test";
import en from "../src/locales/en-US.json";
import zh from "../src/locales/zh-CN.json";
import { displayText, t } from "../src/i18n";
import { healthText } from '../src/workspaces/OntologyWorkspace/healthLocale';

test("English and Chinese messages have identical keys and placeholders", () => {
  assert.deepEqual(Object.keys(en).sort(), Object.keys(zh).sort());
  for (const key of Object.keys(en) as Array<keyof typeof en>) {
    const placeholders = (value: string) => [...value.matchAll(/\{\w+\}/g)].map(match => match[0]).sort();
    assert.ok(en[key].trim(), key);
    assert.ok(zh[key].trim(), key);
    assert.deepEqual(placeholders(en[key]), placeholders(zh[key]), key);
    assert.doesNotMatch(en[key], /[\u4e00-\u9fff]/, key);
  }
});

test("message interpolation keeps user content literal", () => {
  assert.equal(t("Focus: {0}", { 0: "$& {1} 用户节点" }), "聚焦：$& {1} 用户节点");
});

test('service status casing and health counts use the selected language', () => {
  assert.equal(displayText('needs_manual_review'), '需要人工审核');
  assert.equal(displayText('UserDefinedType'), 'UserDefinedType');
  assert.equal(healthText('2/3 labeled, 1/3 documented, 0/3 defined.'), '标签 2/3，文档 1/3，定义 0/3。');
  assert.equal(healthText('Graph has 2 SHACL violation(s), 1 SHACL warning(s).'), 'SHACL 违规：2；警告：1。');
});
