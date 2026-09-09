---
title: "常见问题"
description: "关于 Semantica 的常见问题：安装、功能、集成与故障排查。"
icon: "circle-question"
---

<Info>
  使用 **Ctrl+F** / **Cmd+F** 搜索本页。常用跳转：[安装](#installation) · [数据与功能](#data--features) · [故障排查](#troubleshooting)
</Info>

## 快速解答

| 问题 | 答案 |
| :-------- | :------ |
| 许可证？ | MIT：永久免费，无付费墙功能 |
| Python 版本？ | 3.8+（推荐 3.11+） |
| 需要 API 密钥吗？ | 可选：模式提取无需任何密钥即可工作 |
| 兼容 LangChain / LlamaIndex 吗？ | 可以：Semantica 是叠加于其上的一个层，而非替代品 |
| 可用于生产环境吗？ | 可以：1,000+ 项测试，每个版本都包含安全修复（参见 [CHANGELOG](https://github.com/semantica-agi/semantica/blob/main/CHANGELOG.md)） |
| 最新版本？ | **v0.6.8**（2026 年 9 月） |
| 支持本地 LLM 吗？ | 支持：通过 LiteLLM 使用 Ollama，HuggingFaceLLM 用于离线（air-gapped）环境 |


## 常规问题

<AccordionGroup>

<Accordion title="Semantica 是什么？" icon="info-circle">

Semantica 是一个用于为 AI 构建上下文图和决策智能层的开源框架。它能够将非结构化数据（文档、API、数据库）转化为带有完整溯源跟踪的结构化知识图谱，使 AI 系统变得可解释、可审计。

它不是 LangChain 或 LlamaIndex 的替代品，而是叠加于其上的**问责层**：记录决策、将事实追溯到来源，并让推理过程变得透明。

</Accordion>

<Accordion title="我可以用 Semantica 构建什么？" icon="hammer">

- 从文档和多源数据构建知识图谱
- 具有图基检索与来源归因能力的 GraphRAG 系统
- 具有结构化决策历史和语义记忆的 AI 智能体
- 具备 W3C PROV-O 沿袭的合规流水线（HIPAA、SOX、GDPR、FDA 21 CFR Part 11）
- 跟踪事实随时间变化的时间图谱
- 带 SHACL 校验的本体驱动知识库

</Accordion>

<Accordion title="Semantica 与 LangChain 或 LlamaIndex 有何不同？" icon="scale-balanced">

大多数框架止步于检索或生成。Semantica 增加了一个**问责层**：每个决策都被记录，每个事实都关联到来源，每个推理步骤都可解释。它专为需要审计 AI *为何*得出某个结论（而不只是它说了什么）的环境而设计。

Semantica 与这些框架协同工作，而非相互对抗。

</Accordion>

<Accordion title="Semantica 会解释 LLM 的内部推理或思维链（chain-of-thought）吗？" icon="triangle-exclamation">

不会。这是**系统级的可解释性，而非基础模型的可解释性**。Semantica 不会暴露、重建或解释 LLM/基础模型*内部*发生的过程。其内部推理或思维链仍然是不透明的，这与任何外部系统的情况一致。

Semantica 解释的是模型*之外*的部分：使用了哪些上下文和数据、产生了什么决策、其背后的溯源、相关的关系、所应用的政策，以及由此形成的决策轨迹。

简而言之，Semantica 解释并审计的是 *AI 系统做了什么*，而不是基础模型私有的内部推理。

</Accordion>

<Accordion title="Semantica 是免费的吗？" icon="tag">

是的：MIT 许可证，无厂商锁定，无付费墙功能。某些能力需要第三方 API 密钥（例如 OpenAI 嵌入、Groq 推理），但 Semantica 本身始终免费且开源。

</Accordion>

<Accordion title="最新版本是什么？" icon="star">

**v0.6.8**：2026 年 9 月发布。

亮点：现在每个版本都经过加密签名（SLSA 构建溯源 + Sigstore，弥补了 OpenSSF Scorecard Signed-Releases 的缺口）；真正的向量存储枚举（`scan_vectors()`/`iter_vectors()`）现已覆盖 FAISS/SQLiteVec/PgVector/Qdrant/Weaviate/Milvus，使 `store migrate` 真正可用；新增一流的 Anthropic/Gemini/Ollama/DeepSeek/Novita LLM 提供商封装；新增面向 CI 的本体质量门禁；以及 35 项正确性修复。0.6.x 系列还加入了对 LangChain 和 CrewAI 的一流支持，以及采用确定性 IRI 的 Semantica RDF 词汇表。完整历史请参见 [CHANGELOG](https://github.com/semantica-agi/semantica/blob/main/CHANGELOG.md)。

```bash
pip install --upgrade semantica
```

</Accordion>

</AccordionGroup>


## 安装

<AccordionGroup>

<Accordion title="我该如何安装 Semantica？" icon="download">

```bash
pip install semantica
```

关于虚拟环境配置、可选附加包（`[gpu]`、`[all]` 及特定提供商）以及特定平台的故障排查，请参见[安装](/installation)。

</Accordion>

<Accordion title="我需要什么 Python 版本？" icon="python">

Python **3.8 或更高版本**。推荐使用 Python 3.11+ 以获得最佳性能和兼容性。

</Accordion>

<Accordion title="Windows 上 [all] 附加包安装失败" icon="windows">

这是一个已知问题：已在 **v0.5.0** 中修复。请升级：

```bash
pip install --upgrade semantica
```

如果你使用的是较旧版本，请单独安装附加包：先执行 `pip install "semantica[core]"`，再添加 `[llm-openai]`、`[gpu]` 等。

</Accordion>

<Accordion title="系统要求是什么？" icon="server">

| 要求 | 最低配置 | 推荐配置 |
| :----------- | :------- | :----------- |
| Python | 3.8 | 3.11+ |
| 内存 | 4 GB | 16 GB+ |
| 存储 | 2 GB | 20 GB+ |
| GPU | 可选 | CUDA（用于嵌入和 ML 模型） |

</Accordion>

</AccordionGroup>


## 数据与功能

<AccordionGroup>

<Accordion title="Semantica 支持哪些数据源？" icon="database">

| 类别 | 数据源 |
| :-------- | :------- |
| **文件** | PDF、DOCX、HTML、JSON、CSV、Excel、PPTX、Parquet（v0.5.0）、XML（v0.5.0）、压缩包 |
| **网页** | `WebIngestor` 爬取、RSS 订阅、站点地图 |
| **数据库** | PostgreSQL、MySQL、Snowflake、Databricks（通过 `DBIngestor` / `SnowflakeIngestor` / `DatabricksIngestor`） |
| **NoSQL** | MongoDB（通过 `MongoIngestor`）、DuckDB（通过 `DuckDBIngestor`） |
| **流式数据** | Kafka、通过 `StreamIngestor` 进行实时摄取 |
| **协议** | MCP（模型上下文协议，通过 `MCPIngestor`） |
| **云端** | Google Drive（通过 `GDriveIngestor`）、HuggingFace 数据集 |

</Accordion>

<Accordion title="我可以使用自己的模型吗？" icon="robot">

可以。Semantica 支持：

- **自定义 NER 和提取模型**：通过 `method_registry` 注册
- **自定义嵌入模型**：任何带有 `.encode()` 接口的模型
- **自定义 LLM 提供商**：通过 LiteLLM（100 多个模型）或直接集成提供商
- **自定义流水线处理器**：通过 `PluginRegistry` 注册

</Accordion>

<Accordion title="Semantica 支持 GPU 吗？" icon="bolt">

支持。在可用的情况下，GPU 会自动用于嵌入生成、ML 模型推理和向量运算。安装 GPU 支持：

```bash
pip install "semantica[gpu]"
```

其中包括带 CUDA 的 PyTorch、FAISS GPU 和 CuPy。

</Accordion>

<Accordion title="Semantica 如何处理大型数据集？" icon="layer-group">

- **批量处理**：以可配置的分块大小处理文档，以控制内存占用
- **并行处理**：`semantica.pipeline` 模块可以在同一依赖层中并发运行相互独立且并行安全的步骤（参见[流水线指南](/guides/pipeline)）
- **增量处理**：在新数据到来时增量更新图谱，无需完全重新计算
- **持久化后端**：将内存中的 NetworkX 替换为 Neo4j、FalkorDB 或 Apache AGE，以支撑大规模生产图谱

</Accordion>

<Accordion title="什么是时间智能（Temporal Intelligence）？" icon="clock">

`TemporalKnowledgeGraph` 会为节点和边附加 `valid_from` / `valid_until` 时间窗口，从而实现按时间点查询和历史分析。支持全部 13 种 Allen 区间代数关系以及 OWL-Time 导出。

```python
from semantica.kg import TemporalKnowledgeGraph

tkg = TemporalKnowledgeGraph()
tkg.add_temporal_triple("A", "caused", "B", valid_from="2024-01", valid_until="2024-06")
snapshot = tkg.query_at_time("2024-03")
```

自 v0.4.0 起可用。

</Accordion>

<Accordion title="什么是本体中心（Ontology Hub）？" icon="sitemap">

一个覆盖完整本体生命周期的可视化浏览界面：通过 `semantica.explorer` 启动。包括：

- **可视化编辑器**：创建和编辑类、属性与关系
- **SHACL Studio**：编写、校验并导出 SHACL 形状
- **对齐编写**：跨本体映射概念
- **健康仪表盘**：覆盖率、一致性及约束违规指标
- **版本控制**：本体变更的差异对比与历史记录

自 v0.5.0 起可用。

</Accordion>

<Accordion title="什么是距离智能（Distance Intelligence）？" icon="compass">

对图中任意实体的语义邻域探索。返回带有距离带分类的结构化邻近数据。

- 一组实体间的 N×N 距离矩阵
- 以单个节点为中心的自我（Ego）模式可视化
- 距离带：基于嵌入阈值的 `near` / `mid` / `far`
- 针对重复查询的嵌入缓存优化

自 v0.5.0 起可用。

</Accordion>

<Accordion title="我的 NER 提取器在自定义网关上会静默回退到模式提取" icon="triangle-exclamation">

已在 **v0.5.0** 中修复。对于不兼容的网关，`response_format=json_object` 参数现在会被有条件地省略，并自动应用普通的 `generate()` 加 JSON 解析的回退方案。升级以修复：

```bash
pip install --upgrade semantica
```

</Accordion>

</AccordionGroup>


## 技术细节

<AccordionGroup>

<Accordion title="支持哪些图数据库？" icon="diagram-project">

- **Neo4j**：行业标准，Cypher 查询语言
- **FalkorDB**：Redis 协议，超低延迟
- **Apache AGE**：PostgreSQL 扩展，OpenCypher
- **Amazon Neptune**：AWS 托管服务，SPARQL 和 Gremlin
- **NetworkX**：内存中运行，适用于开发和中小型图谱

</Accordion>

<Accordion title="支持哪些导出格式？" icon="file-export">

RDF（Turtle、JSON-LD、N-Triples、XML）、Apache Parquet、ArangoDB AQL、Apache Arrow、LPG、CSV、YAML、OWL 本体以及距离矩阵。

</Accordion>

<Accordion title="支持哪些向量存储？" icon="server">

FAISS、Pinecone、Weaviate、Qdrant、Milvus、PgVector 以及内存向量存储。所有后端共享相同的 `VectorStore` API：只需改动一行即可切换。

</Accordion>

<Accordion title="支持哪些 LLM 提供商？" icon="microchip">

Groq、OpenAI、Anthropic、Google Gemini、Ollama（完全本地运行）、DeepSeek、Novita AI、LiteLLM（通过统一接口支持 100 多个模型），以及任何兼容 OpenAI 的网关。

</Accordion>

<Accordion title="Semantica 可以用于生产环境吗？" icon="shield-check">

可以。每个版本都附带：

- 在 Python 3.8–3.12 上通过 1,000+ 项测试
- 具备指数退避和可配置重试策略的 `PipelineValidator` 和 `FailureHandler`
- 覆盖所有模块的 W3C PROV-O 溯源跟踪
- 带 SHA-256 校验和与完整审计轨迹的变更管理
- 持续的安全加固：针对 eval 注入、pickle 反序列化、SQL 注入、XXE、SSRF、ReDoS 和路径遍历的修复均已落地于近期的各个版本（参见 [CHANGELOG](https://github.com/semantica-agi/semantica/blob/main/CHANGELOG.md) 中的安全章节）

</Accordion>

</AccordionGroup>


## 故障排查

<AccordionGroup>

<Accordion title="ModuleNotFoundError: No module named 'semantica'" icon="xmark-circle">

请确认已激活正确的 Python 环境：

```bash
pip list | grep semantica
pip install --upgrade semantica
```

</Accordion>

<Accordion title="安装因依赖错误而失败" icon="xmark-circle">

```bash
pip install --upgrade pip wheel
pip install semantica
```

如果 `[all]` 在 Windows 上失败，请改为单独安装附加包。

</Accordion>

<Accordion title="处理过程中出现内存错误" icon="memory">

减小批处理大小、启用流式摄取，或切换到持久化图后端：

```python
from semantica.graph_store import FalkorDBStore
store   = FalkorDBStore(host="localhost", port=6379)
builder = GraphBuilder(merge_entities=True, graph_store=store)
```

</Accordion>

<Accordion title="嵌入或推理速度慢" icon="gauge-high">

安装 GPU 支持并确认 CUDA 可用：

```bash
pip install "semantica[gpu]"
nvidia-smi  # confirm GPU is visible
```

</Accordion>

<Accordion title="Windows 上的 Unicode / cp1252 崩溃" icon="windows">

已在 **v0.5.0** 中修复。请升级，或为较旧版本设置编码环境变量：

```bash
pip install --upgrade semantica
# or for older versions:
set PYTHONIOENCODING=utf-8
```

</Accordion>

</AccordionGroup>


## 支持

- [Discord](https://discord.gg/sV34vps5hH)：社区聊天与实时支持。
- [GitHub Issues](https://github.com/semantica-agi/semantica/issues)：提交缺陷报告与功能请求。
- [参与贡献](/contributing-guide)：帮助改进 Semantica。
