---
title: "核心概念"
description: "Semantica 背后的核心理念：知识图谱、推理、溯源与时序智能详解。"
icon: "book-open"
---

<Info>
  刚接触 Semantica？请从[快速上手](/getting-started)中的动手示例开始，然后再回到这里深入理解。
</Info>

Semantica 将非结构化数据（文档、网页、报告、数据库）转化为**知识图谱**：一种结构化表示，AI 系统可以对其进行查询、推理，并追溯回数据来源。

从核心层面讲，Semantica 在您现有的 AI 技术栈之上增加了一个上下文与语义层。它不会取代 LangChain、LlamaIndex 或您的 LLM 提供商，而是让它们的输出变得有据可依、可追溯、可审计。

- **上下文层。** 知识图谱、GraphRAG 检索、语义嵌入与时序智能，将每一次 LLM 响应都锚定在结构化、可查询的事实之上。
- **问责层。** 溯源追踪、决策智能、冲突检测以及 W3C PROV-O 合规性，使您 AI 技术栈中的每一项论断都可审计、可解释。
- **扩展层。** `PluginRegistry` 与 `MethodRegistry` 让您可以替换或增强任意组件（摄取器、提取器、推理引擎、后端），而无需修改框架代码。

<Warning>
  **这是系统级可解释性，而非基础模型可解释性。** Semantica 不会揭示、重建或解释 LLM/基础模型*内部*发生的事情。其内部推理或思维链始终是不透明的，正如任何外部系统一样。Semantica 所解释的是模型*之外*的部分：输入给模型的上下文与数据、产出的决策、决策的溯源、相关的关系、所应用的政策，以及完整的执行轨迹。简言之，Semantica 解释并审计的是*AI 系统做了什么*，而非基础模型私有的内部推理。
</Warning>

## 知识图谱

<img src="/assets/img/diagrams/kg-structure.svg" alt="展示实体（Person、Organization、Location、Date）及其类型化关系的知识图谱节点与边结构" style={{ width: '100%', borderRadius: '12px', margin: '0 0 20px' }} />

这是 Semantica 中一切功能的基础。知识图谱以三种基本要素存储信息：

- **节点（实体）**：人物、公司、地点、事件、概念
- **边（关系）**：`works_for`、`located_in`、`founded_by`
- **属性**：名称、日期、置信度得分、来源 URL

这种结构让知识可检索、可关联、可查询。更关键的是，它是可解释的：每一个答案都可以追溯回产生它的事实与关系。

## 实体提取（NER）

扫描文本以发现并分类真实世界中的实体：

```python
# "Apple Inc. was founded by Steve Jobs in 1976 in Cupertino."
[
    Entity(text="Apple Inc.", label="ORG",    start_char=0,  end_char=10, confidence=0.98),
    Entity(text="Steve Jobs", label="PERSON", start_char=25, end_char=35, confidence=0.99),
    Entity(text="1976",       label="DATE",   start_char=39, end_char=43, confidence=0.95),
    Entity(text="Cupertino",  label="GPE",    start_char=47, end_char=56, confidence=0.97),
]
```

`NERExtractor(method=...).extract(text)` 返回一个 `Entity` 对象列表，每个对象包含 `label`、字符偏移量（`start_char` / `end_char`）、`confidence` 得分，以及记录提取方法的 `metadata` 字典。共有三种方法可用：

| 方法 | 速度 | 准确率 | 要求 |
| :------ | :----- | :-------- | :------------ |
| `"pattern"` | ⚡ 非常快 | 中等 | 无需 API 密钥：基于正则表达式 |
| `"ml"` | 快 | 高 | 本地 ML 模型 |
| `"llm"` | 中等 | 最高 | LLM 提供商：全部 9 种均受支持 |

## 关系提取

发现实体之间如何相互关联：

```python
jobs  = Entity(text="Steve Jobs", label="PERSON", start_char=25, end_char=35)
apple = Entity(text="Apple Inc.", label="ORG",    start_char=0,  end_char=10)

[
    Relation(subject=jobs,  predicate="founded",     object=apple, confidence=0.92),
    Relation(subject=apple, predicate="located_in",  object=Entity(text="Cupertino", label="GPE", start_char=47, end_char=56), confidence=0.89),
]
```

`RelationExtractor(method=...).extract(text, entities=entities)` 返回一个 `Relation` 对象列表：带类型的主语-谓语-宾语三元组（端点均为 `Entity` 对象），并带有置信度得分与来源归属。提取可通过模式规则、ML 模型或 LLM 执行。

## 知识图谱 vs. 向量存储

两者都为 AI 检索而存储信息，但它们是针对不同的任务构建的。

<Tabs>
  <Tab title="知识图谱">
    以带类型的节点和带标签的边存储**结构化事实**。可回答需要理解实体之间关系的问题。

    | 优势 | 为何重要 |
    | :-------- | :------------- |
    | **遍历** | 多跳查询：“谁创立了 Apple 校友后来加入的公司？” |
    | **可解释性** | 每个答案都能追溯到具体的节点和边：绝无黑箱检索 |
    | **时序推理** | 时点查询、`valid_from`/`valid_until` 时间窗、历史快照 |
    | **冲突检测** | 两个来源对同一事实的分歧会被暴露并得到解决 |
    | **模式强制** | SHACL 校验能在约束违规破坏结果之前将其捕获 |

    **适用场景：**当您需要结构化推理、溯源、合规性或可解释性时。

    ```python
    from semantica.kg import GraphBuilder, PathFinder

    graph = GraphBuilder(merge_entities=True).build(
        {"entities": entities, "relationships": rels}
    )
    path  = PathFinder().dijkstra_shortest_path(graph, "Steve Jobs", "Tim Cook")
    ```
  </Tab>

  <Tab title="向量存储">
    存储文本块的**稠密嵌入**。通过查找语义相似的段落来回答问题：在答案的结构事先未知时非常有用。

    | 优势 | 为何重要 |
    | :-------- | :------------- |
    | **模糊相似度** | 即使措辞不完全一致也能找到相关内容 |
    | **速度** | 大规模下亚毫秒级的近似最近邻检索 |
    | **非结构化文本** | 可直接处理段落、句子和原始文档 |
    | **简单易用** | 无需模式设计：直接嵌入并建立索引 |

    **适用场景：**当您需要对大型文本语料进行快速语义检索时。

    ```python
    from semantica.vector_store import VectorStore

    store   = VectorStore(backend="faiss", dimension=768)
    store.add_documents(["Apple was founded in 1976.", "Google was founded in 1998."])
    results = store.search("tech company founding dates", limit=5)
    ```
  </Tab>

  <Tab title="GraphRAG（两者兼用）">
    Semantica 将两者结合：向量检索为图谱遍历提供起点，而图谱则提供向量存储无法提供的结构与溯源。

    | 步骤 | 发生什么 |
    | :---- | :----------- |
    | **查询嵌入** | 用户查询被嵌入，并通过向量相似度用于查找锚点节点 |
    | **图谱遍历** | 从锚点节点进行多跳遍历，检索相关实体与关系 |
    | **上下文组装** | 事实与关系被组装起来，并为每个论断附上来源归属 |
    | **LLM 生成** | LLM 基于检索到的结构化上下文生成有据可依的答案 |

    **结果：**响应中的每一个论断都链接回具体的图谱节点：不会产生来自训练数据的幻觉，并拥有完整的审计轨迹。

    ```python
    from semantica.context import AgentContext, ContextGraph
    from semantica.vector_store import VectorStore

    context = AgentContext(
        vector_store=VectorStore(backend="faiss", dimension=768),
        knowledge_graph=ContextGraph(advanced_analytics=True),
        graph_expansion=True,
    )

    # store() extracts entities and populates the graph + vector index
    context.store([{"content": "Steve Jobs co-founded Apple Inc. in 1976."}])

    # retrieve() blends vector similarity with graph traversal
    results = context.retrieve("Who founded Apple?", use_graph=True, expand_graph=True)
    for r in results:
        print(r["score"], r["content"], r["source"])
    ```
  </Tab>
</Tabs>

## 嵌入

嵌入将文本转换为数值向量，使 AI 系统能够度量语义相似度：即使措辞完全不同，也能找到相关的概念。

Semantica 使用嵌入的目的：

- **语义检索**：按含义检索，而不仅仅是关键词
- **实体消解**：跨不同来源匹配同一实体
- **先例检索**：查找相似的历史决策
- **GraphRAG 检索**：向量与图谱遍历的混合检索
- **距离智能**：任意节点集之间的 N×N 语义距离矩阵

**受支持的模型：**Sentence-Transformers、FastEmbed、OpenAI、BGE、Ollama 本地嵌入。

## GraphRAG

GraphRAG（图谱增强的检索增强生成）通过将 LLM 响应锚定在结构化知识图谱中而非仅依赖原始文本块，从而增强 LLM 的响应质量。

<img src="/assets/img/diagrams/graphrag-flow.svg" alt="GraphRAG 流程：用户查询 → 向量检索 + 图谱遍历 → 上下文构建器 → LLM → 有据可依的答案" style={{ width: '100%', borderRadius: '12px', margin: '16px 0 20px' }} />

<Steps>
  <Step title="用户提交查询">
    查询被嵌入，并同时用于启动向量检索与图谱遍历。
  </Step>
  <Step title="混合上下文检索">
    Semantica 检索相关的图谱上下文：实体、带类型的关系以及多跳推理路径：同时结合与向量相似的文本块。
  </Step>
  <Step title="上下文构建">
    检索到的事实与推理路径被组装成结构化的提示词上下文，每个事实都标注有其来源节点与置信度。
  </Step>
  <Step title="LLM 生成有据可依的响应">
    LLM 生成的答案中，每一个论断都链接回图谱中的来源节点：不存在无依据的断言，也不会产生来自训练数据的幻觉。
  </Step>
</Steps>

<Tip>
  **GraphRAG 消除了标准 RAG 的幻觉与可追溯性问题。** 标准 RAG 检索的是文本块；GraphRAG 检索的是带类型关系的结构化事实。LLM 无法凭空捏造图谱中从未存在的结构。
</Tip>

## 本体

本体为您的知识定义模式与规则：存在哪些实体类型、哪些关系是合法的，以及适用哪些约束。

```python
ontology = {
    "classes": ["Person", "Organization", "Location"],
    "relationships": ["works_for", "located_in", "founded_by"],
    "rules": {
        "Person":       ["must_have_name"],
        "Organization": ["must_have_name", "can_have_founding_date"]
    }
}
```

Semantica 可以从您的知识图谱自动生成本体，也可以导入现有的 OWL/RDF/Turtle 本体。**本体中心（Ontology Hub）**（v0.5.0）新增了可视化编辑器、SHACL Studio、对齐编写功能以及实时健康仪表盘。完整的 6 阶段生成流水线请参阅[本体参考](/reference/ontology)。

## 推理与推断

Semantica 内置多种推理引擎，可从现有事实推导出新的知识。

```text
Known:    Steve Jobs founded Apple Inc.
Known:    Apple Inc. is headquartered in Cupertino
Inferred: Steve Jobs has a connection to Cupertino
```

<Tabs>
  <Tab title="正向链接">
    反复应用 IF/THEN 规则，直到无法再推导出新的事实。最适合告警系统、合规检查以及基于触发条件的工作流。

    ```python
    from semantica.reasoning import Reasoner

    engine = Reasoner()
    engine.add_fact("Manager(Alice)")
    engine.add_rule("IF Manager(?x) THEN HasAuthority(?x)")

    results = engine.forward_chain()   # list of InferenceResult
    for r in results:
        print(r.conclusion)           # "HasAuthority(Alice)"
    ```
  </Tab>
  <Tab title="Rete 网络">
    面向大型规则集的高效模式匹配：Rete 算法避免重新评估前提条件未发生变化的规则。最适合在数百万条事实上运行数千条规则。

    ```python
    from semantica.reasoning import ReteEngine, Rule, Fact

    engine = ReteEngine()
    engine.build_network([
        Rule(rule_id="r1", name="manager_authority",
             conditions=["Manager(?x)"], conclusion="HasAuthority(?x)"),
    ])
    engine.add_fact(Fact(fact_id="f1", predicate="Manager", arguments=["Alice"]))

    matches = engine.match_patterns()
    results = engine.execute_matches(matches)   # ["HasAuthority(?x)"]
    ```
  </Tab>
  <Tab title="LLM 推理">
    `GraphReasoner` 借助 LLM 回答针对知识图谱的开放式问题，返回基于图谱事实的自然语言答案。最适合固定规则无法预见的探索性与调查性问题。

    ```python
    from semantica.reasoning import GraphReasoner

    reasoner = GraphReasoner(provider="openai", model="gpt-4o-mini")
    answer = reasoner.reason(kg, "Which suppliers are indirectly exposed to the Acme outage?")
    ```
  </Tab>
  <Tab title="Datalog (v0.4.0)">
    支持不动点语义的递归 Horn 子句规则：可处理正向链接无法表达的传递闭包与递归关系。

    ```python
    from semantica.reasoning import DatalogReasoner

    reasoner = DatalogReasoner()
    reasoner.add_fact("parent(alice, bob)")
    reasoner.add_fact("parent(bob, charlie)")
    reasoner.add_rule("ancestor(X, Y) :- parent(X, Y).")
    reasoner.add_rule("ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z).")

    reasoner.derive_all()
    results = reasoner.query("ancestor(alice, ?Z)")   # {"Z": "bob"} and {"Z": "charlie"}, order not guaranteed
    ```
  </Tab>
  <Tab title="引擎对比">

    | 引擎 | 类 | 最佳用途 |
    | :------ | :----- | :-------- |
    | 正向链接 | `Reasoner` | 告警系统、合规检查 |
    | Rete 网络 | `ReteEngine` | 大型规则集、高事实吞吐 |
    | SPARQL 扩展 | `SPARQLReasoner` | 语义网、基于 RDF 的本体推理 |
    | Datalog (v0.4.0) | `DatalogReasoner` | 传递闭包、图谱可达性 |
    | 时序 | `TemporalReasoningEngine` | Allen 区间代数、时间感知推断 |
    | 基于图谱的 LLM | `GraphReasoner` | 开放式、调查性问题 |

  </Tab>
</Tabs>

`Reasoner.forward_chain()` 返回携带所应用规则（`rule_used`）及触发前提的 `InferenceResult` 对象，而 `ExplanationGenerator` 会将其转化为分步骤的自然语言说明：这里的推理**并非**黑箱。

## 时序智能

知识会随时间变化。时序图(graph)为节点和边附加 `valid_from` / `valid_until` 时间窗，从而支持时点查询与历史分析。

```python
from semantica.kg import TemporalGraphQuery
from datetime import datetime

query_engine = TemporalGraphQuery(enable_temporal_reasoning=True)

# Query the graph as it existed on a specific date
snapshot = query_engine.query_at_time(kg, query="", at_time=datetime(2021, 6, 15))
```

**支持的特性：**Allen 区间代数（全部 13 种时序关系）、OWL-Time 导出、`recorded_at` 时间戳标记、时序溯源。

**常见用途：**跟踪公司管理层变动、政策演变、研究时间线、金融工具历史、监管合规时间窗。

## 距离智能

探索图谱中任意实体的语义邻域：有助于理解哪些概念在语义上相近、检测聚类，以及可视化知识的拓扑结构。

```python
from semantica.kg import SimilarityCalculator

calc = SimilarityCalculator(method="cosine")   # "cosine" | "euclidean" | "manhattan" | "correlation"

# Similarity for every unique pair of node embeddings: {(node_a, node_b): score}
pairs = calc.pairwise_similarity({"apple": vec_apple, "google": vec_google, "nest": vec_nest})

# Or rank a set of embeddings by closeness to one query vector
nearest = calc.find_most_similar(embeddings, query_embedding, top_k=10)
```

**特性：**N×N 语义距离矩阵、自我中心（ego）模式可视化、距离带分类（`direct` / `near` / `mid-range` / `distant`）、面向大型图的嵌入缓存优化。

[可视化模块](/reference/visualization) 将距离矩阵渲染为交互式热力图与自我中心模式的邻域图。[Explorer](/reference/explorer) 则将距离智能直接嵌入浏览器仪表盘中。

## 去重与实体消解

现实世界的数据中，同一实体往往以多个名称出现：“Apple”、“Apple Inc.”、“Apple Computer Inc.”。Semantica 的去重流水线能够检测出这些重复项、合并属性、解决冲突，并保留原始来源的溯源信息。

<Tabs>
  <Tab title="策略">

    | 策略 | 算法 | 最佳用途 |
    | :-------- | :--------- | :-------- |
    | `v1` | Jaro-Winkler 字符串相似度 | 小型数据集、快速的基线方案 |
    | `blocking_v2` | 候选分块（blocking）+ 相似度 | 大型语料：减少 O(n²) 比较次数 |
    | `hybrid_v2` | 分块 + 语义嵌入匹配 | 结构化/非结构化混合的实体名称 |
    | `semantic_v2` | 纯基于嵌入的消解 | 比 v1 快最多 7 倍；可处理缩写与别名 |

  </Tab>
  <Tab title="配置">
    ```python
    from semantica.deduplication import DuplicateDetector, EntityMerger

    detector   = DuplicateDetector(similarity_threshold=0.85)
    candidates = detector.detect_duplicates(entities)

    merger     = EntityMerger()
    operations = merger.merge_duplicates(entities, strategy="keep_most_complete")
    ```
  </Tab>
</Tabs>

## 溯源与可审计性

Semantica 中的每一个事实都链接回：

- 它来源的**源文档**
- 所使用的**提取方法**（pattern / ML / LLM）
- 图谱构建过程中应用的**本体规则**
- 产生任何推断事实的**推理步骤**

<Note>
  这是符合 W3C PROV-O 规范的谱系信息：适用于需要审计轨迹的受监管行业（HIPAA、SOX、GDPR、FDA 21 CFR Part 11）。`ProvenanceManager.export_prov(format="turtle")` 将记录的谱系序列化为 PROV-O RDF。
</Note>

```python
from semantica.provenance import ProvenanceManager

prov = ProvenanceManager()
prov.track_entity("apple_inc", source="report.pdf",
                  metadata={"extractor": "NamedEntityRecognizer", "confidence": 0.98})

record = prov.get_provenance("apple_inc")   # dict; use get_lineage() for the full chain
print(record["source_document"])
print(record["timestamp"])
print(record["checksum"])
print(record["metadata"])          # extractor, confidence, and any custom keys
```

## 决策智能

在 Semantica 中，每一个 agent 决策都是一等公民对象：被记录、具备因果关联，并且可按先例进行检索。这就是 AI 流水线的**问责层**：决策不再是转瞬即逝的日志消息，而是可查询的知识图谱节点。

```python
decision_id = context.record_decision(
    category="model_selection",
    scenario="Choose LLM for production pipeline",
    reasoning="GPT-4 benchmark advantage justifies 3x cost increase",
    outcome="selected_gpt4",
    confidence=0.91,
)

# Find similar past decisions before making a new one
precedents = context.find_precedents("model selection reasoning", limit=5)

# Trace downstream impact of a past decision
influence  = context.analyze_decision_influence(decision_id)
```

<Tip>
  **在每次高风险决策之前使用 `find_precedents()`。** 对所有已记录决策进行混合相似度检索，可以浮现可能适用的历史推理：从而减少不同 agent 运行之间的不一致，并实现从 AI 决策历史中进行真正的组织学习。
</Tip>

## 冲突检测

当多个来源对同一事实存在分歧时，Semantica 会标记并解决冲突，而不是静默地选取其中一个值。

**解决策略：**

- **时间近因**：优先采用最新的来源
- **来源可信度**：优先采用最可靠的来源（可信度得分可配置）
- **多数投票**：聚合所有来源，当 ≥ 2 个来源一致时采用
- **人工复核**：标记交由人工裁决；流水线在不阻塞的情况下继续运行

有关 `ConflictResolver`、`SourceTracker` 和 `InvestigationGuideGenerator` 的详细信息，请参阅[冲突参考](/reference/conflicts)。

## 自定义插件开发

Semantica 生而为扩展而设计。任何组件：摄取器、提取器、图谱构建器、推理引擎：都可以用运行时注册的自定义实现来替换或增强。

<AccordionGroup>
  <Accordion title="PluginRegistry：按名称替换任意组件">

    `PluginRegistry` 提供跨所有模块的动态插件发现、注册与加载。在字符串键下注册您自己的类；无论该键在配置或流水线步骤中何处被引用，Semantica 都会使用您的实现。

    ```python
    from semantica.core import PluginRegistry

    registry = PluginRegistry()

    # Register a custom ingestor
    registry.register_plugin(
        "my_sql_ingestor", MySQLIngestor,
        version="1.0.0",
        description="PostgreSQL ingestor for internal warehouse",
        capabilities=["ingest"],
    )

    # Load and use
    plugin = registry.load_plugin("my_sql_ingestor", connection_string="postgresql://...")
    result = plugin.execute("SELECT * FROM documents")

    # Reference by name in pipeline YAML: no code changes needed
    ```

    ```yaml
    steps:
      - name: ingest
        plugin: my_sql_ingestor
        config:
          connection_string: "${DB_URL}"
    ```

    **可用的扩展点：**摄取器、解析器、规范化器、提取器、推理引擎、导出格式、向量存储后端、图存储后端、可视化渲染器。

  </Accordion>
  <Accordion title="MethodRegistry：将内置图谱操作替换为您自己的实现">

    `method_registry` 允许您为某个知识图谱任务（`build`、`analyze`、`centrality`、`resolve` 等）在某个名称下注册替代实现，然后在任何执行该任务的地方选用它。

    ```python
    from semantica.kg import method_registry
    from semantica.kg.methods import calculate_centrality

    def fast_centrality(graph, **kwargs):
        """Custom centrality implementation."""
        ...

    # register(task, name, func)
    method_registry.register("centrality", "fast_centrality", fast_centrality)

    # The task wrappers consult method_registry, so the name is now selectable:
    scores = calculate_centrality(kg, method="fast_centrality")

    print(method_registry.list_all("centrality"))   # {"centrality": ["fast_centrality", ...]}
    ```

  </Accordion>
</AccordionGroup>

- [快速入门教程](/quickstart)：通过代码构建完整的流水线。
- [模块指南](/modules)：每个模块都配有示例讲解。
- [API 参考](/reference/context)：完整的技术参考。