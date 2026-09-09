# Semantica 文档 Pipeline 落地方案

- 日期：2026-09-08
- 状态：已实施本地单进程纵向版本；完整 M0-M4 尚有未完成项，见[实际交付与验证](../../pipeline-workbench.md)。
- 依据：[完整设计 Spec](../specs/2026-09-08-document-pipeline-workbench-spec.md)
- 交付策略：先真实纵向链路，再配置与质量闭环，再发布与版本迭代。完整 v1 包含 M1-M4，不能将 M1 候选文件交付称为最终入库。

## 1. 现有资产与迁移策略

| 资产 | 用途 | 迁移方式 |
| --- | --- | --- |
| `scripts/verify_document_pipeline.py` | 已验证的真实六步链路 | 保留为可复现实验；提炼处理器进入产品模块，不从HTTP运行脚本 |
| `scripts/document_pipeline_rules.py` | 规则雏形 | 拆分校验、状态建议、规范化与审计；保留原始模型结果 |
| `scripts/pipeline_templates/hospital_intro.json` | 医院抽取模板 v1.1 | 转为版本化种子配置；升级时验证schema兼容 |
| `scripts/pipeline_templates/hospital_rules.json` | 状态/证据/方向配置 | 迁移到受限注册规则，不宣称支持任意表达式 |
| `scripts/test_document_pipeline_rules.py` | 7项规则测试 | 迁入正式tests并扩展实体局部语境、否定、数量时间、空值完整性 |
| `output/document-pipeline-validation/*` | 运行、审计与对比证据 | 本地参考；不把医院原文/完整模型输出自动加入公开仓库测试集 |
| 独立HTML原型 | 布局讨论 | 复用交互意图，基于React Flow和项目token重建，不迁入叠加脚本/CSS |

工作区存在用户已有修改；实现时以当时实际diff为准，不清理或覆盖无关变更。项目声明Python>=3.8，新增产品模块必须遵循其兼容策略，不能照搬验证脚本中的新版本类型语法。

## 2. 建议文件归属

以下为拟新增或修改的模块，非现存文件清单。按阶段创建，避免提前堆叠空抽象。

```text
semantica/explorer/
  app.py                          # lifespan、路由和能力注册
  runtime.py                      # 发布后的索引/事件桥接
  session.py                      # 图谱revision、写入协调与激活边界
  routes/pipelines.py             # 文档、定义、任务、事件、结果、审核API
  pipelines/
    schemas.py                    # API与artifact schema
    repository.py                 # SQLite事务与迁移
    artifacts.py                  # 受控路径、hash、原子文件写入
    service.py                    # 创建任务、幂等、审核、重跑计划
    worker.py                     # 队列领取、租约、关闭与恢复
    compiler.py                   # 版本配置 -> 类型化串行pipeline
    registry.py                   # 处理器与规则能力注册
    handlers.py                   # 解析/分块/抽取/归一/校验协调
    rules.py                      # 受限规则evaluator与审计
    publication.py                # 候选 -> 持久快照 -> GraphSession
    seeds/                        # flow/extraction/rules默认版本
semantica/server.py                # 第二入口复用任务生命周期与路由安装
semantica/pipeline/
  execution_engine.py             # 生命周期、取消终态、重试正确性
  pipeline_templates.py           # 深拷贝与实例隔离
explorer/src/workspaces/PipelineWorkspace/
  PipelineWorkspace.tsx           # 子视图与运行上下文
  PipelineCanvas.tsx              # React Flow编排
  StepInspector.tsx               # 参数、模板和规则绑定
  DefinitionEditor.tsx            # 表单与Monaco高级编辑
  RunHistory.tsx                  # 分页任务与事件
  ResultReview.tsx                # 证据、问题、修订与发布
  RunComparison.tsx               # 新旧结果与配置差异
  api.ts / types.ts               # 鉴权请求、查询key、服务契约
tests/explorer/pipelines/          # API/存储/任务/发布故障测试
tests/pipeline/                    # 通用引擎回归
explorer/tests/                    # 交互、契约和Playwright
```

`PipelineTemplateManager` 继续负责模板到builder构建；新增 compiler 负责产品配置校验和已注册handler绑定。不要让相邻文件各自实现一套重试器、模板解释器或状态机。

## 3. 阶段与依赖

| 阶段 | 可验收交付 | 依赖 | 估算工程人日 |
| --- | --- | --- | --- |
| M0 | 契约冻结、依赖审计、引擎关键回归 | 无 | 2-3 |
| M1 | DOCX上传、持久任务、真实进度、候选结果 | M0 | 5-7 |
| M2 | 模板规则编辑、审核候选、真实节点画布 | M1 | 5-7 |
| M3 | 幂等持久发布、自动门禁、Explorer可见 | M1、M2 | 5-8 |
| M4 | 版本重跑对比、串行编辑、格式扩展和完整验收 | M2、M3 | 4-6 |
| v2 | 任意DAG、并行、批量、OCR、外部存储/RAG | v1稳定后 | 单独估算 |

合计约21-31工程人日，是基于当前代码的估算，不是固定日期承诺；不含部署审批、多用户改造、OCR模型和生产数据整理。两名开发者可在契约稳定后并行前后端，关键路径仍是质量门禁和图谱发布一致性。

## 4. M0：先确定真实运行契约

### 工作包

1. 定义run/step/quality/publication状态及API schema，固定request_key、版本引用、artifact引用和错误码。
2. 审计所有GraphSession写入、两个服务入口、当前CLI加载路径与活跃图谱引用，选择M3可支持的持久目标；记录不能覆盖的写路径。
3. 补引擎测试：同名流程独立运行、停止不变成completed、失败后继不执行、默认重试预算、快速步骤事件。
4. 修复模板overrides就地修改问题，确保已发布模板与两个builder实例互不影响。
5. 验证DeepSeek调用配置透传thinking/timeout/输出schema；以可复用适配器替代验证脚本访问内部client的临时做法。
6. 建立医院文档的人工期望事实清单；不将实体数量25或边数量23设为黄金答案。

### 完成条件

- 新产品契约可编译为真实处理步骤，所有handler均有输入/输出类型。
- 通用引擎和模板相关回归通过；现有调用默认语义不被无意改变。
- 明确出版目标是托管图谱，或先新建托管图谱；不能留到发布按钮上线后再决定数据存在哪里。

## 5. M1：上传到候选结果的最小链路

### 后端

1. 创建pipeline repository及迁移、受控artifact目录，最小表覆盖documents、runs、run_steps、run_events、artifacts、幂等请求。
2. 添加能力预检、文档上传、创建run、run详情、事件和候选结果接口。
3. 两个入口复用lifespan注册组件；数据目录owner锁限定单进程，单worker事务领取queued任务；队列/模型失败持久化，重启标记interrupted。
4. 接入真实DOCXParser、分块器、模型抽取、基础归一和验证handler，记录完整事件而非轮询采样。
5. 每个步骤保存不可变产物，写入hash与schema版本；候选图谱保存并重新加载核验节点、边和来源。
6. 检测不支持的表格/图片/文本框覆盖缺口，返回明确问题而不是只读取正文就显示完整。

### 前端

1. App.tsx 的Enrich新增Pipeline页签，沿用WorkspaceShell和token。
2. 先展示不可改结构的真实默认链，参数只显示已支持项；文件上传后同一次操作创建run。
3. React Query管理服务状态，1秒事件轮询；任务ID写入可恢复URL/路由状态，记录页支持重新打开。
   终态按last_event_seq追完分页事件再停止，测试终态比最后事件先返回的情形。
4. 展示候选实体/关系及原文引用，阶段终点标为“候选已生成”，暂不显示自动发布完成。

### 完成条件

- 用户从网页运行本次DOCX，真实看到节点状态与结果；关闭/刷新页面不终止后台任务。
- 模型空正文、401、429、超时、错误JSON和中断均有可辨识状态。
- 请求重放不创建重复任务；日志不暴露key；已有JSON/CSV导入不受影响。

## 6. M2：模板、规则、证据与审核

### 工作包

1. 实现definitions/version表和表单/JSON编辑、schema校验、草稿乐观锁、发布版本与版本选择。
   增加版本详情API与草稿preview任务，冻结draft revision、记录模型用量，并禁止preview发布。
2. 用PipelineTemplateManager注册已发布流程的拷贝，绑定handler；固化抽取模板和规则快照。
3. 原文拆为稳定segment，模型返回segment引用；服务端生成证据，保留原始输出和拒绝记录。
4. quantity/year拆成原文和标准字段；条件必填：例如寿命目标需要数值及单位，不允许只有名称中出现数字就通过。
5. 状态规则按具体实体/分句判定，补否定和历史状态案例。不能沿用“同段有已运营即通过”的实验规则。
6. 维护别名字典和禁止合并名单，未确认同名或别名冲突进入审核；归一记录可追溯。
7. 结果审核支持建议修正、编辑、排除、说明和重新校验；候选版本使用expected_revision避免覆盖。
8. 画布绑定节点参数、模板与规则版本，显示规则触发数量及检查结果。

### 完成条件

- 改抽取模板后真实输出改变，改规则后能看到确定性的拒绝/建议/修正审计。
- 已启动任务不读取后来修改的草稿；发布版本被引用后不能被覆盖。
- 医院例中的全科培训项目、120岁数量缺失会被质量门禁发现，不能静默完成。
- 人工修订不篡改原始输出；修订结果再校验，旧candidate_revision不可发布。

## 7. M3：把候选结果可靠发布到Explorer

这是“一次操作完成全流程”的关键交付阶段，不能用保存JSON替代。

### 工作包

1. 实现目标graph_id/revision、托管snapshot和publication仓库；提供创建空图/注册当前快照、目标列表和激活API，首次注册持久基线。
2. 所有对目标图谱的写入口纳入共同锁/revision协议，或限定首发仅发布新托管图谱。
3. 实现prepared -> snapshot -> DB head CAS -> committed -> session activation -> visible协议；每个故障点可恢复。
4. 定义新图谱选择/打开入口；当前图谱合并遇到revision冲突回到审核，不静默覆盖外部编辑。
5. 激活时更新GraphSession、搜索、MarkdownResourceRegistry和mutation bridge；前端按revision重新加载图谱。
6. 接入auto_if_clean/manual策略，默认整批发布，待审核问题阻断发布。
7. 发布去重键和canonical/evidence ID确保重复请求无重复效果；旧来源证据不能被新任务覆盖。
8. 实现supersedes_publish_id和publication_supports；运行/重跑计划提前绑定替换范围并计入幂等hash，新版仅替换指定旧发布的贡献；保留其他文档/人工支持，展示新增、修正和撤销差异。

### 必须运行的故障注入

- 快照写入前/后失败。
- 数据库head提交前/后失败。
- GraphSession激活或搜索索引刷新失败。
- 发布已成功但HTTP响应丢失。
- 同时手工编辑目标图谱导致base revision过期。
- 用户连点确认、重复POST、进程重启后重试publication。

### 完成条件

- 合格文档一次点击自动发布，任务只有在目标图谱可见后才completed。
- 不合格结果停在awaiting_review，未被部分写入活跃图谱。
- 重启能找回发布快照，重复操作无重复实体/关系；原图谱在失败时完整或可恢复。
- 现有图谱操作、Markdown、多边、事件桥接的回归通过。

## 8. M4：重跑对比与完整v1

### 工作包

1. 依据输入hash和配置影响计算rerun-plan，明确复用/失效步骤；创建parent_run_id子任务。
2. 验证复用时无额外模型请求；强制重新抽取模式明确绕过extract缓存。
3. 新旧候选按canonical ID、关系与证据键对比，展示人工修订与规则影响，不依赖随机模型ID。
   旧审核决议不直接复制到新run；单条人工改动与通用规则发布分别记录。
4. React Flow开放类型兼容的串行节点插入、删除可选节点、连线编辑与布局保存，服务端独立校验。
5. 加入TXT/Markdown、文字PDF解析及证据定位；OCR_REQUIRED和部分内容缺失真实反映。
6. 补充上传和输出预算、取消、并发上限、数据保留与迁移维护说明。
7. 固定回归集与独立样本，评估事实准确率/召回、状态、数量、证据和方向错误；记录模型成本与延迟。
8. Playwright验证桌面/手机全流程和截图，完成Spec A01-A15追踪。

### 完成条件

- 不满意后可在网页改模板/规则，预览重跑计划，新任务复用上游，结果可对比并审核发布。
- 节点编辑有真实执行意义；不兼容连接和跳过校验无法提交运行。
- 第一份正式用户指南覆盖首次配置、自动运行、规则调整、审核、重跑、恢复和存储位置。

## 9. 推荐PR拆分

| PR | 内容 | 前置 |
| --- | --- | --- |
| 01 | 引擎终态/重试/事件契约、模板实例隔离测试与修复 | M0 |
| 02 | schemas、repository、artifact存储和迁移 | 01契约稳定 |
| 03 | handler registry、医院配置种子、模型适配 | 01，可与02并行 |
| 04 | 上传/任务/事件API、worker和中断恢复 | 02、03 |
| 05 | Enrich入口、真实画布、上传与运行记录 | 04契约，可提前接契约fixture开发 |
| 06 | 模板规则版本编辑、原文证据与质量门禁 | 02、03、05 |
| 07 | 审核修订、候选revision和规则审计界面 | 06 |
| 08 | 图谱持久发布与全写路径协调、故障恢复 | 02、07 |
| 09 | 自动发布、GraphSession激活、可见结果导航 | 05、08 |
| 10 | 重跑计划、缓存、比较、串行编辑 | 06、09 |
| 11 | 其他格式、回归评测、E2E、部署文档 | 10 |

PR05的契约fixture只能用于测试，正式页面必须显示后端不可用状态，不能在API失败时自动回退到模拟成功。

## 10. 测试与验收执行

| 测试层 | 关注点 | 位置 |
| --- | --- | --- |
| 单元 | 规则、字段规范化、模板隔离、失效传播、类型校验 | tests/explorer/pipelines、tests/pipeline |
| 存储 | 迁移、事务、幂等、lease、artifact hash和孤儿文件 | repository/artifact测试 |
| API | 上传限制、鉴权、409、分页、终态、重复请求 | FastAPI TestClient |
| 集成 | 真引擎 + 可控模型fixture + 实际图谱保存加载 | pipeline服务测试 |
| 发布故障 | 中断、超时、revision冲突、恢复和索引一致性 | publication集成测试 |
| 前端 | 节点稳定尺寸、查询状态、编辑版本冲突、证据定位 | 现有node测试/Testing Library |
| E2E | 上传、失败、审核、发布、重跑、刷新恢复 | 已有Playwright依赖 |
| 真实模型 | 固定本地文档与独立样本、费用、遗漏、状态/数量准确性 | 显式live评测，默认CI不调付费API |

真实文档不自动提交到公共仓库。CI使用合成医院案例，覆盖计划2000+家、两个分院不同状态、合作培训、未来年份、寿命目标及相反/否定句。实际文档作为本地验收输入，与合成和独立样本结果分别报告。

现有检查按修改范围运行：Python对应测试、前端`npm run build`、`npm run lint`，涉及图谱时跑`test:graph-store`与`test:graph-workspace`。一次通过后仅因新修改/新失败扩大或重复测试，不把重复全量测试当进度。

## 11. 部署、启用与回退

1. 能力开关默认不对不支持的目标显示发布按钮；配置数据目录、模型profile和托管图谱后才开放运行。
2. 发布前备份现有图谱及pipeline数据库，迁移先校验版本与可用空间。
3. 首次内部验收使用独立托管图谱，验证重复运行与恢复，再开放当前图谱合并。
4. 前端上线顺序与后端能力标记配套，旧后端不显示可以运行的空入口。
5. 功能回退停止接收新任务并等待/标记已有任务，不删除run/artifact/publication历史；已发布图谱按持久snapshot恢复。
6. 数据库不可降级读取时明确报错并使用备份恢复流程，不尝试以旧schema写新数据库。

## 12. v2单独设计的内容

- 任意DAG：端口到artifact映射、分支条件、合流冲突、并行输入隔离、取消传播和失败聚合，需先修订执行模型再开放UI。
- 批量文档：批任务与子任务、跨文档归一、预算、部分完成语义。
- 外部图数据库：独立发布adapter与事务/幂等协议，不能复用JSON保存成功判断。
- OCR和复杂表格：解析能力、证据定位、质量评测和额外依赖。
- 向量/RAG：Embedding模型、向量版本、索引发布和问答验收，明确失败是否影响图谱完成。
- 多用户/分布式worker：身份、授权、租户隔离、任务队列和共享存储协议。

下一步开发入口是PR01-04，先交付可用的上传与真实任务服务；完整需求以M4和Spec验收表完成为准。
