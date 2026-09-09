---
title: "菜谱"
description: "交互式 Jupyter 笔记本，涵盖从您的第一个知识图谱到生产级 GraphRAG 系统的全部内容。"
icon: "flask"
---

<Tip>
  **从哪里开始：**
  - **Semantica 新手**：从[核心教程](#core-tutorials)开始
  - **正在构建应用**：参见[高级概念](#advanced-concepts)
  - **需要安装帮助**：参见[安装指南](/installation)
</Tip>

<Note>
  先决条件：Python 3.8+、Jupyter，以及您常用 LLM 提供商的 API 密钥。
</Note>


## 精选菜谱

- **[您的第一个知识图谱](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/08_Your_First_Knowledge_Graph.ipynb)**：在 20 分钟内从原始文本构建出可查询的知识图谱。主题：提取、图谱构建、可视化 · *初级*


## 核心教程

掌握 Semantica 框架的必备指南。

- **[欢迎使用 Semantica](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/01_Welcome_to_Semantica.ipynb)**：以交互方式介绍框架的核心理念和所有模块。主题：框架概览、架构 · *初级*
- **[数据摄取](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/02_Data_Ingestion.ipynb)**：从文件、网页、数据库、数据流、订阅源、代码仓库、电子邮件和 MCP 加载数据。主题：FileIngestor、WebIngestor、DBIngestor · *初级*
- **[文档解析](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/03_Document_Parsing.ipynb)**：从 PDF、DOCX 和 HTML 等复杂格式中提取干净的文本。主题：OCR、PDF 解析、文本提取 · *初级*
- **[数据规范化](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/04_Data_Normalization.ipynb)**：用于清理、规范化并准备文本的流水线。主题：文本清理、Unicode、格式化 · *初级*
- **[实体提取](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/05_Entity_Extraction.ipynb)**：使用 NER 识别人物、组织和自定义实体。主题：NER、spaCy、LLM 提取 · *初级*
- **[关系提取](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/06_Relation_Extraction.ipynb)**：发现并分类实体之间的关系。主题：关系分类、依存句法解析 · *初级*
- **[嵌入生成](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/12_Embedding_Generation.ipynb)**：创建并管理用于语义搜索的向量嵌入。主题：嵌入、OpenAI、HuggingFace · *中级*
- **[向量存储](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/13_Vector_Store.ipynb)**：搭建用于相似性搜索和检索的向量存储。*中级*
- **[图存储](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/09_Graph_Store.ipynb)**：在 Neo4j 或 FalkorDB 中持久化知识图谱。主题：Neo4j、Cypher、持久化 · *中级*
- **[本体](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/14_Ontology.ipynb)**：定义领域模式和本体来组织您的数据。主题：OWL、RDF、模式设计 · *中级*
- **[种子数据](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/25_Seed_Data.ipynb)**：在提取运行之前，从可信的 CSV、JSON、数据库和 API 来源引导初始化知识图谱。主题：SeedDataManager、基础图谱 · *中级*
- **[语义层基础](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/26_Semantic_Layer_Basics.ipynb)**：收官教程，将知识图谱、生成的本体、显式映射、与本体对齐的 RDF 以及 SPARQL 查询结合在一起。主题：语义层、本体映射、Oxigraph、SPARQL · *中级*


## 高级概念

深入探讨高级功能、自定义配置和复杂工作流。

- **[高级提取](https://github.com/semantica-agi/semantica/blob/main/cookbook/advanced/01_Advanced_Extraction.ipynb)**：自定义提取器、基于 LLM 的提取以及复杂模式匹配。主题：自定义模型、正则表达式、LLM · *高级*
- **[高级图谱分析](https://github.com/semantica-agi/semantica/blob/main/cookbook/advanced/02_Advanced_Graph_Analytics.ipynb)**：中心性、社区发现和路径查找算法。主题：PageRank、Louvain、最短路径 · *高级*
- **[高级上下文工程](https://github.com/semantica-agi/semantica/blob/main/cookbook/advanced/11_Advanced_Context_Engineering.ipynb)**：使用 FAISS 和 Neo4j 为 AI 智能体构建的持久记忆系统。主题：智能体记忆、GraphRAG、实体注入 · *高级*
- **[完整可视化套件](https://github.com/semantica-agi/semantica/blob/main/cookbook/advanced/03_Complete_Visualization_Suite.ipynb)**：面向图谱的交互式网络、分析和时序可视化。主题：PyVis、NetworkX、D3.js · *中级*
- **[冲突解决](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/17_Conflict_Detection_and_Resolution.ipynb)**：处理来自多个来源的矛盾信息的策略。主题：真值发现、投票、置信度 · *高级*
- **[多格式导出](https://github.com/semantica-agi/semantica/blob/main/cookbook/advanced/05_Multi_Format_Export.ipynb)**：导出为 RDF、OWL、JSON-LD 和 NetworkX 格式。主题：序列化、互操作性 · *中级*
- **[多源集成](https://github.com/semantica-agi/semantica/blob/main/cookbook/advanced/06_Multi_Source_Data_Integration.ipynb)**：将来自不同来源的数据合并为统一的图谱。主题：实体解析、合并、融合 · *高级*
- **[推理与推断](https://github.com/semantica-agi/semantica/blob/main/cookbook/advanced/08_Reasoning_and_Inference.ipynb)**：利用逻辑推理从已有事实中推断出新的知识。主题：逻辑规则、推理引擎 · *高级*
- **[时序知识图谱](https://github.com/semantica-agi/semantica/blob/main/cookbook/advanced/10_Temporal_Knowledge_Graphs.ipynb)**：对随时间变化的数据进行建模和查询。主题：时间序列、时序逻辑、Allen 代数 · *高级*
- **[溯源追踪](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/22_Provenance_Tracking.ipynb)**：对齐 W3C PROV-O 规范的实体、关系和分块的血缘追踪与校验和验证。主题：PROV-O、血缘、校验和、失效 · *高级*
- **[推理模块](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/23_Reasoning.ipynb)**：通过前向链、后向链和 Datalog 策略从已有事实推导新的知识。主题：推理器、Datalog、解释 · *高级*
- **[变更管理](https://github.com/semantica-agi/semantica/blob/main/cookbook/introduction/24_Change_Management.ipynb)**：针对知识图谱和本体的版本控制、审计跟踪和数据完整性校验。主题：ChangeLogEntry、版本存储、数据完整性 · *高级*


## 运行方式

<Steps>
  <Step title="安装 Semantica">
    ```bash
    pip install semantica[all]
    pip install jupyter
    ```
  </Step>
  <Step title="克隆代码仓库（可选，用于源码安装）">
    ```bash
    git clone https://github.com/semantica-agi/semantica.git
    cd semantica
    pip install -e ".[all]"
    pip install jupyter
    ```
  </Step>
  <Step title="启动 Jupyter">
    ```bash
    jupyter notebook
    ```
  </Step>
</Steps>

<Tip>
  您也可以使用 Docker 运行此菜谱：

  ```bash
  docker run -p 8888:8888 semantica/semantica-cookbook
  ```
</Tip>
