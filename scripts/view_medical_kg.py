#!/usr/bin/env python3
"""
查看 medical_import_output/medical_kg_llm.json 的导入效果。

用法:
  python scripts/view_medical_kg.py                      # 总览统计
  python scripts/view_medical_kg.py --disease 百日咳     # 查看某个疾病的关系
  python scripts/view_medical_kg.py --type 药物          # 按实体类型筛选
  python scripts/view_medical_kg.py --search 呼吸        # 模糊搜索实体名
  python scripts/view_medical_kg.py --vector 糖尿病      # 向量检索测试 (需向量索引)
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

# 与导入脚本一致: 避免 sentence-transformers 多线程段错误
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

KG_PATH = Path("./medical_import_output/medical_kg_llm.json")
VECTOR_DIR = Path("./medical_import_output/medical_vector_index")


def load_kg():
    kg = json.loads(KG_PATH.read_text(encoding="utf-8"))
    return kg["entities"], kg["relationships"]


def cmd_overview(ents, rels):
    print(f"═══ 知识图谱总览 ═══")
    print(f"实体: {len(ents)}  关系: {len(rels)}")
    tc = Counter(e["type"] for e in ents)
    print(f"实体类型: {dict(tc)}")
    rc = Counter(r["type"] for r in rels)
    print(f"关系类型: {dict(rc)}")

    # 连通性: 每个疾病连接的关系数
    per_source = defaultdict(int)
    per_target = defaultdict(int)
    for r in rels:
        per_source[r["source"]] += 1
        per_target[r["target"]] += 1
    by_degree = sorted(per_source.items(), key=lambda x: -x[1])
    print(f"\n关系最多的 5 个实体:")
    for name, n in by_degree[:5]:
        print(f"  {name} — {n} 条关系")
    print(f"\n孤立实体(无任何关系): "
          f"{sum(1 for e in ents if per_source.get(e['name'], 0) == 0 and per_target.get(e['name'], 0) == 0)}")


def cmd_disease(ents, rels, name):
    ent_names = {e["name"]: e for e in ents}
    if name not in ent_names:
        print(f"未找到疾病「{name}」。现有疾病列表:")
        for e in ents:
            if e["type"] == "疾病":
                print(f"  - {e['name']}")
        sys.exit(1)
    ent = ent_names[name]
    print(f"═══ 「{name}」({ent['type']}) ═══")
    if ent.get("properties"):
        print("属性:", json.dumps(ent["properties"], ensure_ascii=False)[:200])

    print(f"\n作为主体的关系 ({sum(1 for r in rels if r['source'] == name)} 条):")
    for r in rels:
        if r["source"] == name:
            print(f"  -[{r['type']}]-> {r['target']}  (conf={r.get('confidence', 1.0):.2f})")
    print(f"\n作为客体的关系 ({sum(1 for r in rels if r['target'] == name)} 条):")
    for r in rels:
        if r["target"] == name:
            print(f"  {r['source']} -[{r['type']}]->")


def cmd_type(ents, rels, etype):
    matched = [e for e in ents if e["type"] == etype]
    print(f"═══ 实体类型「{etype}」: {len(matched)} 个 ═══")
    for e in matched[:60]:
        print(f"  {e['name']}")
    if len(matched) > 60:
        print(f"  ... 共 {len(matched)} 个")


def cmd_search(ents, rels, keyword):
    print(f"═══ 模糊搜索「{keyword}」═══")
    hits = [e for e in ents if keyword in e["name"]]
    for e in hits[:30]:
        rel_count = sum(1 for r in rels if r["source"] == e["name"] or r["target"] == e["name"])
        print(f"  {e['name']}  ({e['type']}, {rel_count} 条关系)")
    print(f"共 {len(hits)} 个匹配")


def cmd_vector(ents, rels, query, limit):
    if not VECTOR_DIR.exists():
        print(f"向量索引不存在: {VECTOR_DIR}。请先运行导入脚本生成。")
        sys.exit(1)
    print(f"═══ 向量检索: 「{query}」 ═══")
    from semantica.vector_store import VectorStore
    from semantica.embeddings import EmbeddingGenerator
    vs = VectorStore(backend="faiss", dimension=384)
    vs.load(str(VECTOR_DIR))
    gen = EmbeddingGenerator(text={
        "method": "sentence_transformers",
        "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
    })
    vs.embedder = gen
    results = vs.search(query, limit=limit)
    for r in results:
        m = r.get("metadata", {})
        score = r.get("score", r.get("similarity", "?"))
        print(f"  {m.get('disease', '?')}  (score={score:.4f})")
        text = r.get("text", "")[:100]
        if text:
            print(f"      {text}")


def main():
    ap = argparse.ArgumentParser(description="查看 medical KG 导入效果")
    ap.add_argument("--disease", default=None, help="查看某个疾病的关系")
    ap.add_argument("--type", default=None, help="按实体类型查看 (疾病/症状/检查/药物/食物/科室/治疗方式)")
    ap.add_argument("--search", default=None, help="模糊搜索实体名")
    ap.add_argument("--vector", default=None, help="向量检索查询")
    ap.add_argument("--limit", type=int, default=5, help="向量检索返回数")
    args = ap.parse_args()

    ents, rels = load_kg()
    if args.disease:
        cmd_disease(ents, rels, args.disease)
    elif args.type:
        cmd_type(ents, rels, args.type)
    elif args.search:
        cmd_search(ents, rels, args.search)
    elif args.vector:
        cmd_vector(ents, rels, args.vector, args.limit)
    else:
        cmd_overview(ents, rels)


if __name__ == "__main__":
    main()