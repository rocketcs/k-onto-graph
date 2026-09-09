# 文档 Pipeline 工作台：使用与交付说明

日期：2026-09-08。基于文档 Pipeline Spec 与落地方案实现的本地单进程版本。

## 入口与操作

进入 **Enrich → Pipeline**。这是真实 React 页面，后端使用 PipelineTemplateManager 与 ExecutionEngine，不依赖此前的 HTML 原型。

1. 选择文档、流程版本、抽取模板版本、规则版本和发布策略，点击“上传并运行”。上传和创建后台任务由一次操作完成。
2. 六个必需阶段自动执行：文档解析 → 文本分块 → 知识抽取 → 实体归一 → 规则校验 → 候选结果。节点显示服务端持久状态，事件按序号读取。刷新页面可以恢复运行。
3. “校验通过自动发布”只在没有质量问题时发布。存在问题则停在“待审核”，不会将候选写进当前图谱。“审核后发布”始终等待用户发布。
4. 在“结果审核”查看关系、实体、问题和原文段落。点击记录编辑，或补充遗漏的实体／关系；必须填写原因。排除、恢复、补充和修改都会重新校验并记录审计。
5. 发布目标可以选择本地独立图谱或 Neo4j。本地发布生成可下载的 JSON 快照；Neo4j 发布需要完成实体对齐审核，详见 [Neo4j 发布说明](pipeline-neo4j-publication.md)。
6. 已激活图谱如经过手动编辑，本版会阻止再次切换，以免丢失编辑；导出编辑结果后重新启动 Explorer 再打开另一快照。活跃视图选择不跨重启恢复，已发布快照和任务会保留。

## 结果不满意时在哪里调整

| 情况 | 入口 | 影响 |
| --- | --- | --- |
| 类型、抽取内容或证据遗漏 | 模板与规则 → 抽取模板 | 修改指令、类型和示例，发布新版本后重跑抽取及后续步骤 |
| 规划误作已运营、数量年份不规范、必须出现的项目缺失 | 模板与规则 → 规则集 | 修改受支持规则，发布新版本后重跑归一与校验；上游兼容产物可复用 |
| 分块不合适 | 流程节点参数或流程模板 | 修改分块长度与重叠，保存版本后重跑 |
| 少量记录需要纠正 | 结果审核 | 编辑、补充或排除候选，重新校验；不会改写模型原始产物 |
| 希望保留两套策略 | 模板与规则 → 另存为新配置 | 以当前编辑内容建立独立草稿，再发布版本 |

表单提供常用字段，JSON 提供完整的受支持配置。草稿和已发布版本分开保存；运行绑定不可变快照。试跑只读取已保存草稿，不能发布正式图谱。更改规则或模板不会追改历史运行。

“重跑计划”先列出可复用与需重算的节点，再创建子运行。文件、流程处理参数、抽取模板、模型或处理器版本不兼容时缓存失效。规则变更从归一阶段重算。人工修订不自动继承到新运行；比较页同时返回记录变化、配置差异和质量问题前后变化。

## 本地启动

### Excel 导入（.xlsx）

文件选择器支持 `.xlsx`，上传后沿用解析、分块、抽取、审核和发布流程。每个工作表独立分块，首个非空行作为列名，每个后续行携带列名及单元格坐标；系统保留工作表名和行号。应选择与表格业务内容匹配的抽取模板。

支持普通单行表头表格、日期、数字、文本编号及简单补零格式。空白与零区分处理。公式仅读取 Excel 已保存的计算结果，不执行公式或宏；缺失公式结果、错误单元格、合并单元格、隐藏表和图片图表都会进入覆盖问题审核。复杂多行表头、多表区域自动识别尚未支持，建议整理为每张表一个矩形数据区、第一行单行表头后导入。旧 `.xls` 和宏工作簿 `.xlsm` 不支持。

预算仍为上传 20 MiB、解压 100 MiB、解析文本 200 万字符和 2,000 个模型分块；Excel 另限制每表 256 列、10 万行、全工作簿扫描 100 万单元格。超过限制会明确失败，不会截断入库。分块结果会持久化，重跑时可复用已完成的分块。

在项目根目录安装现有项目依赖及可选扩展，然后构建前端：

```sh
python -m pip install -e '.[explorer-pipeline]'
npm --prefix explorer ci
npm --prefix explorer run build
```

在服务端环境配置 `DEEPSEEK_API_KEY`。密钥不进入模板或运行结果，也不是页面中的 Explorer API Key。

```sh
ALLOWED_ORIGINS=http://127.0.0.1:8013,http://localhost:8013 \
SEMANTICA_PIPELINE_ENABLED=true \
SEMANTICA_PIPELINE_DATA_DIR=./output/pipeline-workbench-data \
SEMANTICA_ALLOW_ANONYMOUS=true \
python -m uvicorn semantica.explorer.app:create_app --factory --host 127.0.0.1 --port 8013
```

浏览器入口：`http://127.0.0.1:8013/?workspace=enrich&view=pipeline`。

上面的匿名设置用于本机验证。鉴权沿用 Explorer 的配置，Pipeline 请求支持页面填写 Explorer API Key；现有其他工作区的浏览器鉴权方式没有在本次统一改造。`ALLOWED_ORIGINS` 必须包含实际浏览器来源，才能接收图谱切换 WebSocket 事件。

`SEMANTICA_PIPELINE_MODEL` 可指定 DeepSeek 模型，默认 `deepseek-v4-flash`。运行目录通过文件锁限制一个服务进程，不支持 `uvicorn --workers 2`、Windows 或多实例共享目录。

SQLite WAL 保存定义、不可变版本、文档、运行、候选修订、事件、幂等记录及发布记录；artifacts 保存原文与逐步产物。备份时停止服务并复制整个数据目录。不要只复制数据库主文件而遗漏 WAL 或 artifacts。产物目前不自动清理。

## API 对照

所有接口继承 Explorer 鉴权。启用服务后也可以查看 FastAPI 的 `/docs`。

| API | 用途 |
| --- | --- |
| `GET /api/pipeline-capabilities` | 支持格式、模型可用性、处理节点与发布模式 |
| `POST /api/pipeline-documents` | multipart 文件与 request_key |
| `GET /api/pipeline-documents/{id}/content?run_id=...` | 解析后的原文段落 |
| `GET/POST /api/pipeline-definitions` | 定义列表、新建定义 |
| `GET/PUT /api/pipeline-definitions/{id}` | 读取／CAS 更新草稿 |
| `POST /api/pipeline-definitions/{id}/validate` | 校验配置 |
| `GET/POST /api/pipeline-definitions/{id}/versions` | 列出／发布不可变版本 |
| `GET /api/pipeline-definition-versions/{id}` | 读取版本快照 |
| `POST /api/pipeline-previews` | 已保存草稿试跑 |
| `GET/POST /api/pipeline-runs` | 分页历史／创建正式运行 |
| `GET /api/pipeline-runs/{id}` | 状态与 last_event_seq |
| `GET /api/pipeline-runs/{id}/events?after_seq=0` | 按序号增量读取事件 |
| `GET /api/pipeline-runs/{id}/results` | 候选、原文、质量问题与审计 |
| `PUT /api/pipeline-runs/{id}/review` | patches、additions、excluded 与修订原因 |
| `POST /api/pipeline-runs/{id}/publish` | 按 candidate_revision 幂等发布 |
| `POST /api/pipeline-runs/{id}/cancel` | 取消排队／请求运行取消 |
| `POST /api/pipeline-runs/{id}/rerun-plan` | 计算复用范围与 plan hash |
| `POST /api/pipeline-runs/{id}/reruns` | 校验 plan hash 后创建子运行 |
| `GET /api/pipeline-runs/{id}/comparison?other_run_id=...` | 比较记录、配置、质量问题 |
| `GET /api/pipeline-runs/{id}/export` | 导出运行、候选、证据与事件 |
| `GET /api/pipeline-graphs` | 发布快照及活跃视图 |
| `GET /api/pipeline-graphs/{id}/download` | 下载持久图谱 |
| `POST /api/pipeline-graphs/{id}/activate` | 显式切换活跃 Explorer 会话 |

写操作使用 request_key。重放相同 key 和请求返回原响应；同 key 不同请求返回 409。草稿和候选通过 expected revision 检测覆盖冲突。取消在处理边界生效，正在发出的模型请求须等待完成或超时；进程重启后不假装继续未完成的模型调用，而标记 interrupted 并允许重跑。

## 本次真实验证

使用用户提供的“循上介介绍-无股东版.docx”，不是测试桩输出：

- 初始运行 `ef5cc7e678cd46b6ba3a8328dca03fb3` 抽取 24 个实体、26 条关系，8 个问题阻止自动发布。
- 按原文补充健康寿命目标实体、五大学科的具体段落证据，以及 `2028年` 的原文单位。保留 8 条人工审计后通过门禁，发布 25 节点、26 关系图谱，并在 Explorer 打开验证。
- 抽取模板修订运行 `fd045ee86b4b4095a540fc4229940e97` 真实重新调用模型，仍有 5 个质量问题。没有把模板优化宣传成保证准确。
- 规则修订运行 `ad97efe6b3df463ba481419477c55918` 复用 parse/split/extract，事件中没有新模型调用；新增目标完整性规则后有 6 个问题，保持待审核。两次规则前后候选记录相同，但质量结果不同。
- 本地证据位于 `output/pipeline-workbench-e2e/`，包含真实运行 JSON、发布结果、重跑结果、桌面／手机页面截图和图谱截图。这些医院内容未加入通用测试 fixture。

## 检查与回归

```sh
.venv/bin/python -m pytest tests/explorer/test_pipeline_workbench.py tests/pipeline/test_pipeline.py tests/pipeline/test_pipeline_parallel.py tests/pipeline/test_pipeline_validator_construct.py tests/explorer/test_explorer_auth.py -q --override-ini addopts=''
npm --prefix explorer run build
cd explorer
npx eslint src/workspaces/PipelineWorkspace --max-warnings=0
npm run test:pipeline-e2e
```

后端相关检查 85 项通过。前端编译和 Pipeline ESLint 通过；Playwright 验证上传、刷新恢复、节点增删、模板表单、审核补充、发布、图谱打开、其他已打开图谱页的自动刷新及缩放交互，检查桌面与手机布局和画布像素。独立基线 HEAD `c4492091` 复现了现有 15 项失败：14 项旧 orchestration 测试期待已不匹配的链式 builder API，1 项入口测试不兼容已安装 FastAPI 的 `_IncludedRouter.path`。不能宣称仓库全量测试通过。

以下脚本需要显式环境变量，避免普通 UI 回归重复调用真实模型：

- `PIPELINE_LIVE_DOCUMENT=/absolute/path.docx node tests/pipeline-workbench.e2e.mjs`：真实上传和抽取。
- `PIPELINE_REVIEW_RUN=... node tests/pipeline-review.e2e.mjs`：本次医院 fixture 的证据修正和发布验证，无模型调用。
- `PIPELINE_RERUN_PARENT=... node tests/pipeline-rerun.live.mjs`：创建模板／规则版本，执行一次真实模型重跑，再验证规则缓存重跑。

## 与完整设计的边界

采用 Spec 允许的“新建独立托管图谱”发布路径。当前交付不是完整 M0-M4 所有工作包均已完成：

- 已支持 Neo4j 人工实体对齐和事务追加事实；尚未实现贡献替换、supersedes、全局写协调和其他外部图存储发布。
- 画布是有类型约束的串行流程，可移动节点、编辑参数、增删统计节点；六个必需阶段不可跳过，不支持任意 DAG、并行、批量和自定义代码节点。
- 支持 DOCX 正文、表格行与文本框文字、UTF-8 TXT/MD、可提取文字的 PDF。DOCX 媒体、页眉页脚或嵌入内容的覆盖缺口进入质量问题，允许文字处理但阻止自动发布；扫描 PDF 明确报 OCR_REQUIRED。尚未实现 OCR 和完整复杂文档覆盖。
- 当前规则是注册规则参数，不支持任意 DSL。别名规则较基础，复杂跨文档实体消歧、证据语义充分性和数量范围仍需人工审核或后续能力扩展。
- 文档限制 20 MiB、200 万字符、2,000 个分块；超长段落会按边界自动拆分。结果接口目前返回受限文档的完整结果，尚未实现大型候选分页、独立 artifact schema 迁移和保留期清理。
- API 主要使用受限配置校验与业务 CAS，尚未完成设计中的全部 Pydantic schema 和统一错误码细化。模型重试已有上限及退避，尚未实现 Retry-After 与 jitter。
- 运行比较显示配置、记录和问题差异；语义级别的重命名匹配和人工修订自动迁移尚未实现。

后续顺序：先补齐 schema、分页与复杂文档质量测试，再统一图谱写入协调并实现贡献替换；任意 DAG、OCR 与多用户调度仍属于后续版本。
