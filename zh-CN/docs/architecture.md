---
title: "架构"
description: "四层模块化架构，旨在支持组件的独立使用、清晰的关注点分离以及完全的可扩展性。"
icon: "building"
---

Semantica 围绕四层模块化架构构建。只导入你需要的部分：框架从不强制使用完整的全栈。每个组件都可独立替换，每一层都通过干净的接口通信，没有隐蔽的耦合。


## 四层架构

<img src="/assets/img/diagrams/architecture-overview.svg" alt="Semantica 四层架构" style={{ width: '100%', borderRadius: '12px', margin: '16px 0 24px' }} />

<Tabs>

<Tab title="第 1 层：摄取">

将来自任何来源的数据作为统一的 `SourceDocument` 加载到流水线中。

| 数据源 | 模块 | 说明 |
| :------ | :------ | :----- |
| PDF、DOCX、PPTX、HTML、JSON、CSV | `ingest.FileIngestor` | 支持归档文件、递归目录扫描 |
| Parquet | `ingest.ParquetIngestor` | PyArrow、Hive 风格分区（v0.5.0） |
| XML | `ingest.XMLIngestor` | 基于 XXE 安全的 lxml、XSD/DTD 校验（v0.5.0） |
| 网页 | `ingest.WebIngestor` | 可配置的抓取深度、链接过滤 |
| SQL / Snowflake / Databricks | `ingest.DBIngestor` / `ingest.SnowflakeIngestor` / `ingest.DatabricksIngestor` | 自定义 SQL、模式内省、Unity Catalog 血缘 |
| Kafka / 流数据 | `ingest.StreamIngestor` | 实时数据流摄取 |
| 电子邮件 | `ingest.EmailIngestor` | 支持 IMAP/SMTP，可提取附件 |
| 代码仓库 | `ingest.RepoIngestor` | Git 仓库、代码结构 |
| MCP | `ingest.MCPIngestor` | Model Context Protocol 数据源 |

</Tab>

<Tab title="第 2 层：处理">

将原始文本转换为结构化、富化的文档，为知识存储摄取做好准备。

| 步骤 | 模块 | 作用 |
| :---- | :------ | :------------ |
| 解析 | `parse.DocumentParser` / `parse.DoclingParser` | 文本与布局提取、表格检测 |
| 规范化 | `normalize` | 规范形式、日期/名称标准化、编码修复 |
| 提取 | `semantic_extract` | NER、关系提取、事件检测、三元组 |
| 构建 | `kg.GraphBuilder` | 实体合并、边构建、图谱组装 |
| 质检 | `deduplication`, `conflicts` | 重复检测、冲突消解、校验 |

</Tab>

<Tab title="第 3 层：智能">

提供持久的知识存储和嵌入基础设施，为检索与推理提供支撑。

| 组件 | 模块 | 说明 |
| :--------- | :------ | :----------- |
| 知识图谱 | `kg` | 图谱构建、时间模型、分析、Distance Intelligence（距离智能） |
| 向量存储 | `vector_store` | pgvector、Qdrant、Weaviate、Pinecone：语义相似度检索 |
| 本体 | `ontology` | OWL/RDFS 建模、SHACL 校验、本体对齐 |
| 三元组存储 | `triplet_store` | RDF 三元组存储与 SPARQL 查询 |
| 嵌入 | `embeddings` | Sentence-Transformers、FastEmbed、OpenAI、BGE |
| 时间模型 | `kg.TemporalKnowledgeGraph` | `valid_from` / `valid_until`、Allen 区间代数（v0.4.0） |

</Tab>

<Tab title="第 4 层：应用">

消费知识图谱与向量存储，服务于下游应用场景。

| 应用场景 | 模块 | 说明 |
| :-------- | :------ | :----------- |
| GraphRAG | `context.AgentContext` | 基于图谱的 LLM 检索 |
| 智能体记忆 | `context.ContextGraph` | 跨智能体运行保持持久的语义记忆 |
| 决策跟踪 | `context.AgentContext` | 记录、追踪并审计每一个智能体决策 |
| 本体中心 | `explorer` | 可视化编辑器、SHACL Studio、对齐界面（v0.5.0） |
| 多智能体 | `integrations.agno` | 共享上下文、团队级记忆、KG 工具包 |
| 可视化 | `visualization` | 交互式 HTML 图谱、嵌入图、时间视图 |
| 导出 | `export` | RDF、Parquet、ArangoDB AQL、OWL、CSV、Arrow |
| 推理 | `reasoning` | 前向链、Rete、Datalog、SPARQL、溯因推理 |

</Tab>

</Tabs>


## 数据流

每条流水线都遵循从原始数据源到交付输出的同一条线性路径：

<img src="/assets/img/diagrams/pipeline-flow.svg" alt="Semantica 8 步流水线：摄取 → 解析 → 规范化 → 提取 → 构建知识图谱 → 质检 → 存储 → 交付" style={{ width: '100%', borderRadius: '10px', margin: '16px 0 24px' }} />


## 模块总览

| 层 | 类别 | 模块 |
| :----- | :-------- | :------- |
| **第 1 层：摄取** | 数据源 | `ingest`, `split` |
| **第 2 层：处理** | 转换 | `parse`, `normalize`, `semantic_extract`, `deduplication`, `conflicts` |
| **第 3 层：智能** | 存储 | `kg`, `vector_store`, `graph_store`, `triplet_store`, `embeddings`, `ontology` |
| **第 4 层：应用** | 交付 | `context`, `reasoning`, `export`, `visualization`, `explorer`, `pipeline` |
|: | 横切关注点 | `provenance`, `change_management`, `llms`, `mcp_server`, `seed`, `evals`, `core`, `utils` |


## 扩展点

每一层都暴露一个基于注册表的扩展点。注册自定义实现后，它们即可参与完整的流水线，而无需对核心代码做任何改动。

<CodeGroup>

```python Custom Ingestor
from semantica.ingest.registry import method_registry

def custom_file_ingestor(source):
    # Return a list of document dicts with 'text', 'metadata', 'source'
    return [{"text": "...", "metadata": {}, "source": source}]

# Register under the "file" task category with a unique name
method_registry.register("file", "my_custom_format", custom_file_ingestor)

available = method_registry.list_all("file")
```

```python Custom Extractor
from semantica.semantic_extract.registry import method_registry

def custom_entity_extractor(text, config=None):
    # Return a list of entity dicts with 'text', 'type', 'confidence'
    return [{"text": "...", "type": "CUSTOM_TYPE", "confidence": 0.9}]

# Register under the "entity" extraction task
method_registry.register("entity", "my_extractor", custom_entity_extractor)
```

```python Custom Plugin
from semantica.core import PluginRegistry

class MyPlugin:
    def process(self, graph, config):
        # Modify the graph in place and return it
        return graph

registry = PluginRegistry()
registry.register_plugin("my_plugin", MyPlugin, version="1.0.0")
```

</CodeGroup>


## 设计决策

<AccordionGroup>

<Accordion title="模块化：只用你需要的部分" icon="puzzle-piece">

每个组件都能独立运行。`NERExtractor` 无需图存储即可运行，`VectorStore` 无需决策跟踪即可运行。框架从不强制实例化完整的全栈；你只为导入的部分付出成本。

</Accordion>

<Accordion title="可插拔性：无需修改核心即可扩展" icon="plug">

自定义的摄取器、提取器、校验器和导出器遵循相同的基类模式。通过 `PluginRegistry` 注册后，它们即可参与完整的流水线（包括溯源跟踪、重试策略和并行执行），而无需对核心代码做任何改动。

</Accordion>

<Accordion title="默认溯源" icon="link">

血缘跟踪在构建图谱的最底层就已内置。每个节点和边都带有指向源文档、提取方法和时间戳的 `source_id`。无需任何显式开启操作；溯源始终处于开启状态。

</Accordion>

<Accordion title="配置优于约定" icon="sliders">

集中式的 `ConfigManager` 支持环境变量覆盖。没有魔法默认值；所有行为都明确且可覆盖。适合为开发、预发布和生产环境配置不同后端的多环境部署。

</Accordion>

</AccordionGroup>


## 性能特征

| 特征 | 机制 |
| :-------------- | :--------- |
| **并行执行** | `Pipeline(workers=N)`，每个阶段可配置 worker 数量 |
| **增量处理** | 增量式图谱更新（新数据到来时无需全量重算） |
| **流式摄取** | 处理大型语料库而无需将所有内容加载到内存 |
| **后端灵活性** | 可在不更改 API 的情况下，将内存中的 NetworkX 替换为 Neo4j / FalkorDB |
| **去重 v2** | `blocking_v2`、`hybrid_v2`、`semantic_v2`：比 v1 快最多 7 倍 |
| **索引检索** | Explorer 在 118k 个节点上实现 0.004ms 搜索（v0.5.0） |

- [模块](/modules)：包含代码示例的完整模块文档。
- [深入学习](/learning-more)：配置参考、性能指南与故障排查。
- [流水线参考](/reference/pipeline)：流水线编排、worker 与重试策略。
- [核心参考](/reference/core)：框架生命周期、插件注册表与配置。
