# Explorer 中英文显示方案

## 显示范围

首页、公共导航与工作区标题，以及 Explore 的图谱、词表、智能体记忆视图使用同一套语言资源。图谱工具栏、加载阶段、图例、插件、节点详情、Markdown 编辑器、脚注和错误提示均随语言切换。

全部工作区使用同一语言设置，不设固定英文页面：

- 首页；探索：图谱、智能体记忆、词表。
- 分析：推理、SPARQL；决策工作区。
- 丰富：流水线、导入导出、差异合并、实体消歧、注册表。
- 管理：溯源、知识图谱概览、本体摘要。
- 本体中心：注册表、编辑器、版本、映射、健康、SHACL，以及加载、搜索、提案审核和 SKOS 子界面。

页面操作、提示、空状态和已知服务状态使用双语资源。Monaco 编辑器和 React Flow 控件也按当前语言初始化。节点内容、用户 Markdown、URI、API 字段名和业务标识保留原始数据；事实、规则和查询语法不翻译，内置类型名称仅在显示时翻译。外部文档、用户自定义本体标签及服务端原始诊断不是界面译文，不自动改写。

## 语言资源

- `explorer/src/locales/zh-CN.json`：简体中文。
- `explorer/src/locales/en-US.json`：英文。
- `explorer/src/i18n.ts`：语言选择、类型检查、占位符插值、页面语言和标题。
- `explorer/src/exploreLocale.ts`：内置数据类型的显示名称映射，不修改数据。

组件使用 `t("Message key")`，动态文案使用完整消息与占位符，例如 `t("Focus: {0}", { 0: nodeId })`。新增文案必须同时写入两个 JSON 文件；不得对 DOM 文字进行运行时替换，也不得翻译请求参数或类型枚举。

## 切换与保存

左侧导航底部提供“中文 / English”选择。默认中文，偏好保存为 `localStorage["semantica.locale"]`。URL 的 `lang=zh-CN` 或 `lang=en-US` 优先于保存的偏好；浏览器禁用存储时仍可通过 URL 切换。

切换采用页面重新加载，使模块级文案、图谱缓存、异步加载提示和第三方时间轴在同一次加载中使用一致语言。当前工作区与子视图通过 URL 保留；图谱临时选择、搜索和展开状态会重置。存在未应用 Markdown 草稿时先确认；取消则保留草稿与原语言。

## 验证

在 `explorer` 目录运行：

```sh
npm run test:graph-workspace
node --import tsx --test tests/exploreLocale.test.ts
node tests/exploreLocale.e2e.mjs
node tests/allPagesLocale.e2e.mjs
npm run build
```

双语浏览器测试使用 `http://127.0.0.1:5173` 的开发服务和模拟接口，覆盖中英文界面、工作区保留、偏好持久化、取消语言切换后的草稿保护及手机端渲染。

逐页测试使用当前本地服务，遍历 21 个入口的两套语言，检查语言标记、两套不同显示以及整行资源文案串语言。它覆盖当前服务可加载的状态；第三方编辑器需能访问其 CDN，流水线完整运行流程需对应后端接口可用。
