---
title: "快速开始"
description: "面向 AI 的上下文与智能层：将原始数据转化为可解释、可审计的知识图谱。"
icon: "rocket"
---

<Tip>
  已经安装好了？直接跳到[快速入门](/quickstart)。需要安装帮助？请参阅[安装](/installation)。
</Tip>

## 你可以构建什么

- **GraphRAG 系统** — 将 LLM 的回答锚定在可追踪、结构化的知识上。每条论断都链接回一个源节点。
- **可问责的 AI 智能体** — 具备结构化决策历史、因果链和先例搜索能力的智能体。每个选择都会被记录且可审计。
- **生产级知识图谱** — 从多源数据构建、校验并维护企业级语义知识库。
- **合规就绪的 AI** — 每条事实都带有 W3C PROV-O 溯源。内置 HIPAA、SOX、GDPR、FDA 21 CFR Part 11 基础设施。


## 三步完成设置

<Steps>
  <Step title="安装 Semantica">
    <CodeGroup>

    ```bash pip (recommended)
    pip install semantica
    ```

    ```bash With all extras
    pip install semantica[all]
    ```

    ```bash From source
    git clone https://github.com/semantica-agi/semantica.git
    cd semantica
    pip install -e ".[dev]"
    ```

    </CodeGroup>

    <Check>
      验证安装：
      ```python
      import semantica
      print(semantica.__version__)  # 0.6.8
      ```
    </Check>
  </Step>

  <Step title="选择你的路径">
    选择与你正在构建的内容相匹配的路径：每条路径都以一个聚焦的 5 分钟示例开始。

    | 路径 | 你想要… | 从这里开始 |
    | :----- | :-------------- | :--------- |
    | **知识图谱** | 将文档转化为结构化、可查询的图谱 | [快速入门 → 第 1 步](/quickstart) |
    | **智能体上下文** | 为你的 AI 智能体提供持久记忆和决策跟踪 | [上下文参考](/reference/context) |
    | **GraphRAG** | 将 LLM 的回答锚定在结构化知识上 | [概念 → GraphRAG](/concepts#graphrag) |
    | **MCP 集成** | 从 Claude Desktop 或 VS Code 使用 Semantica | [MCP 服务器](/reference/mcp_server) |

  </Step>

  <Step title="运行流水线">
    完整的 6 步流水线：摄取、解析、提取、构建、可视化、导出，见[快速入门](/quickstart)。使用基于模式的提取（无需 API 密钥），不到 5 分钟即可完成。

    <Note>
      对于快速入门，LLM API 密钥是**可选的**。基于模式的提取开箱即用：准备好后，可升级到 LLM 提取以获得更高的准确率。
    </Note>
  </Step>
</Steps>


## 选择你的路径

<Tabs>
  <Tab title="知识图谱">
    从任意文档或数据源构建结构化知识图谱。

    ```python
    from semantica.ingest import FileIngestor
    from semantica.parse import DocumentParser
    from semantica.semantic_extract import NERExtractor, RelationExtractor
    from semantica.kg import GraphBuilder

    # 1. Ingest
    sources = FileIngestor().ingest("data/report.pdf")

    # 2. Parse (extract_text returns a plain string for any supported format)
    text = DocumentParser().extract_text(sources[0].path)

    # 3. Extract (extractors take text, return Entity / Relation objects)
    ner           = NERExtractor(method="pattern")  # no API key needed
    entities      = ner.extract(text)
    relationships = RelationExtractor(method="pattern").extract(text, entities=entities)

    # 4. Build
    graph = GraphBuilder(merge_entities=True).build(
        {"entities": entities, "relationships": relationships}
    )
    print(f"{len(graph['entities'])} nodes, {len(graph['relationships'])} edges")
    ```

    **下一步：** [完整流水线演练 →](/quickstart)
  </Tab>

  <Tab title="智能体上下文">
    为你的智能体提供持久记忆、决策跟踪和先例搜索。

    ```python
    from semantica.context import AgentContext, ContextGraph
    from semantica.vector_store import VectorStore

    context = AgentContext(
        vector_store=VectorStore(backend="faiss", dimension=768),
        knowledge_graph=ContextGraph(advanced_analytics=True),
        decision_tracking=True,
    )

    # Store a fact with provenance
    context.store("GPT-4 outperforms GPT-3.5 on reasoning by 40%")

    # Record a decision with full causal chain
    decision_id = context.record_decision(
        category="model_selection",
        scenario="Choose LLM for production pipeline",
        reasoning="GPT-4 benchmark advantage justifies cost",
        outcome="selected_gpt4",
        confidence=0.91,
    )

    # Search past decisions before making a new one
    precedents = context.find_precedents("model selection", limit=5)
    ```

    **下一步：** [上下文模块参考 →](/reference/context)
  </Tab>

  <Tab title="GraphRAG">
    将每条 LLM 回答都锚定在你的知识图谱中：杜绝无根据的断言。

    ```python
    from semantica.context import AgentContext, ContextGraph
    from semantica.vector_store import VectorStore

    context = AgentContext(
        vector_store=VectorStore(backend="faiss", dimension=768),
        knowledge_graph=ContextGraph(advanced_analytics=True),
        graph_expansion=True,       # blend graph traversal into retrieval
        max_expansion_hops=3,       # how far to walk from the seed nodes
    )

    # store() runs extraction and populates both the vector index and the graph
    context.store([
        {"content": "Steve Wozniak co-founded Apple with Steve Jobs in 1976."},
        {"content": "Tony Fadell led the iPod team at Apple, then founded Nest."},
    ])

    # GraphRAG retrieval: seed from vector matches, expand along graph edges
    results = context.retrieve(
        "What companies were founded by people who worked at Apple?",
        use_graph=True,
        expand_graph=True,
    )
    for r in results:
        print(f"[{r['score']:.3f}]  {r['content'][:70]}  (source: {r['source']})")
    ```

    每条结果都包含 `content`、`score`、`source` 和 `metadata`。如需有据可依的自然语言回答以及可审计的遍历过程，请使用 `context.query_with_reasoning(query, llm_provider=...)` — 它会返回 `response`、`reasoning_path`、`sources` 和 `confidence`。

    **下一步：** [GraphRAG 概念 →](/concepts#graphrag)
  </Tab>

  <Tab title="MCP 集成">
    从 Claude Desktop、VS Code、Cursor 或任意 MCP 客户端使用 Semantica：完成设置后无需再编写 Python 代码。

    ```bash
    pip install semantica
    ```

    添加到你的 MCP 客户端配置：

    ```json
    {
      "mcpServers": {
        "semantica": {
          "command": "semantica-mcp"
        }
      }
    }
    ```

    立即可用 15 个工具：提取实体、查询图谱、记录决策、运行推理、导出结果。

    **下一步：** [MCP 服务器参考 →](/reference/mcp_server)
  </Tab>
</Tabs>


## 核心架构

Semantica 采用模块化、分层的架构：只需导入你需要的部分。

- **[输入层](/reference/ingest)** — 从任意来源加载并准备数据。模块：`ingest`、`parse`、`split`、`normalize`
- **[语义层](/reference/semantic_extract)** — 从原始文本中提取含义。模块：`semantic_extract`、`kg`、`ontology`、`reasoning`
- **[存储层](/reference/vector_store)** — 持久化知识以供检索。模块：`embeddings`、`vector_store`、`graph_store`、`triplet_store`
- **[质量层](/reference/deduplication)** — 校验并去重。模块：`deduplication`、`conflicts`
- **[上下文层](/reference/context)** — 跟踪决策与血缘。模块：`context`、`provenance`、`change_management`
- **[输出层](/reference/export)** — 将结果交付到下游。模块：`export`、`visualization`、`pipeline`、`explorer`


## 我需要哪个模块？

参见[选择合适的模块](/choose-your-module)指南 — 它把 35+ 个开发者目标映射到全部 27 个模块中的正确起点，并为最常见的路径提供了可运行的代码。


## 后续步骤

- [核心概念](/concepts) — 深入讲解知识图谱、本体和推理。
- [快速入门教程](/quickstart) — 完整的 6 步流水线演练，附可运行代码。
- [模块参考](/modules) — 解释每一个模块、类和常见调用链。
- [API 参考](/reference/context) — 每个类和方法的完整模块文档。


## 帮助

- [Discord](https://discord.gg/sV34vps5hH) — 提问、分享项目、获取社区支持。
- [GitHub Issues](https://github.com/semantica-agi/semantica/issues) — 报告缺陷或请求新功能。
- [FAQ](/faq) — 常见问题解答。