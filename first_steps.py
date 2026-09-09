"""
first_steps.py — Semantica 本地第一课脚本

把官方 docs/quickstart.md 的端到端管线 + README 的 Decision Intelligence
Quick Start 合成一个可重复运行的脚本,全部使用 pattern 抽取,
不需要 LLM API key,不需要联网下载模型。

运行方式(在项目根目录):
    .venv/bin/python first_steps.py

学习时的对照材料:
    - docs/quickstart.md     端到端管线逐步说明
    - docs/concepts.md       核心概念(知识图谱 vs 向量库,GraphRAG,溯源)
    - docs/guides/*.md       每个能力模块的专题指南
    - cookbook/introduction  26 个入门 notebook(与下面步骤一一对应)
"""
import os
import tempfile

# ---------------- 0. 版本确认 ----------------
import semantica
print(f"semantica {semantica.__version__}")

# ---------------- 1. Ingest:读入文档 ----------------
from semantica.ingest import FileIngestor

sample_text = (
    "Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne "
    "in 1976 in Cupertino, California. Apple acquired Beats Electronics in 2014. "
    "Tim Cook is the CEO of Apple. Microsoft was founded by Bill Gates and "
    "Paul Allen in 1975 in Albuquerque, New Mexico."
)
sample_dir = tempfile.mkdtemp(prefix="semantica_demo_")
sample_path = os.path.join(sample_dir, "sample.txt")
with open(sample_path, "w", encoding="utf-8") as fh:
    fh.write(sample_text)

sources = FileIngestor().ingest(sample_path)
print(f"[1-ingest] 读入 {len(sources)} 个 source")

# ---------------- 2. Parse:抽取结构化文本 ----------------
from semantica.parse import DocumentParser

parsed = DocumentParser().parse(sources[0].path)
full_text = parsed["full_text"]
print(f"[2-parse ] 解析出 {len(full_text)} 字符文本")

# ---------------- 3. Extract:NER + 关系抽取(pattern,免 LLM key) ----------------
from semantica.semantic_extract import NERExtractor, RelationExtractor

entities = NERExtractor(method="pattern").extract(full_text)
print(f"[3-extract] NER 找到 {len(entities)} 个实体: "
      f"{[e.text for e in entities]}")

relationships = RelationExtractor(method="pattern").extract(
    full_text, entities=entities
)
print(f"[3-extract] 找到 {len(relationships)} 个关系:")
for r in relationships[:8]:
    print(f"             {r.subject.text} --{r.predicate}--> {r.object.text}")

# ---------------- 4. Build:构建知识图谱 ----------------
from semantica.kg import GraphBuilder

graph = GraphBuilder(merge_entities=False).build(
    {"entities": entities, "relationships": relationships}
)
print(f"[4-build ] 图谱: {len(graph['entities'])} 节点 / "
      f"{len(graph['relationships'])} 条边")

# ---------------- 5. Export:导出为 RDF/TTL ----------------
from semantica.export import RDFExporter

ttl_path = os.path.join(sample_dir, "graph.ttl")
RDFExporter().export(graph, file_path=ttl_path, format="turtle")
print(f"[5-export] 已导出 {ttl_path}(RDF/Turtle,W3C 标准)")

# ---------------- 6. Decision Intelligence:决策即对象 ----------------
from semantica.context import ContextGraph

cg = ContextGraph(advanced_analytics=True)

decision_id = cg.record_decision(
    category="vendor_selection",
    scenario="Choose cloud provider for HIPAA workload",
    reasoning="AWS offers BAA, mature HIPAA tooling, and existing team expertise",
    outcome="selected_aws",
    confidence=0.93,
)
print(f"[6-decision] 记录决策 id={decision_id}")

chain = cg.trace_decision_chain(decision_id)
print(f"[6-decision] 因果链: {chain}")

try:
    similar = cg.find_similar_decisions("cloud vendor", max_results=5)
    print(f"[6-decision] 相似历史决策: {similar}")
except Exception as exc:  # 语义检索可能触发模型下载,首次失败可后续再跑
    print(f"[6-decision] find_similar_decisions 跳过: {type(exc).__name__}: {exc}")

print("\n✅ 端到端管线全部跑通。下一步见 docs/learning-more.md 与 cookbook/introduction。")