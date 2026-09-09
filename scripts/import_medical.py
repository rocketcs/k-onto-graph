#!/usr/bin/env python3
"""
将 QASystemOnMedicalKG 的 medical.json (JSONL, 8808 条疾病记录) 导入 Semantica:

  1. 知识图谱: 实体(疾病/症状/药品/科室/检查/治疗方式/食物) + 关系 → GraphBuilder
  2. 向量检索(RAG): 按疾病分节生成文本 chunk → embedding → FAISS VectorStore

用法:
  # 1) 仅解析转换, 不建图不入库 (快速验证)
  python scripts/import_medical.py --dry-run

  # 2) 小样本试跑 (前 200 条疾病)
  python scripts/import_medical.py --limit 200

  # 3) 全量导入 (8808 条, 首次需下载 embedding 模型)
  python scripts/import_medical.py
"""

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

# 确保使用仓库版代码 (site-packages 里的旧版 FAISS save 不写 meta 伴随文件)
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

DATA_PATH = Path("/Users/rocket/workspace/QASystemOnMedicalKG/data/medical.json")
OUTPUT_DIR = Path("./medical_import_output")

# ---------------------------------------------------------------------------
# 1. 字段映射: medical.json 字段 → 图实体类型 & 关系类型
# ---------------------------------------------------------------------------

# 列表型字段 → (实体类型, 关系类型) —— 全中文
LIST_FIELD_MAP = {
    "symptom": ("症状", "有症状"),          # 症状
    "category": ("科室", "属于分类"),      # 疾病分类
    "cure_department": ("科室", "就诊科室"),  # 就诊科室
    "acompany": ("疾病", "并发症"),       # 并发症 (指向其他疾病)
    "check": ("检查项目", "需做检查"),      # 检查项目
    "recommand_drug": ("药品", "推荐药品"),   # 推荐药品
    "common_drug": ("药品", "常用药品"),      # 常用药品
    "cure_way": ("治疗方式", "治疗方式"),     # 治疗方式
    "do_eat": ("食物", "宜吃"),             # 宜吃食物
    "not_eat": ("食物", "忌吃"),            # 忌吃食物
    "recommand_eat": ("食物", "推荐食谱"),    # 推荐食谱
}

# 标量字段 → 疾病实体属性 (中文名) (长文本另用于 RAG chunk)
DISEASE_PROP_MAP = {
    "desc": "概述",
    "cause": "病因",
    "prevent": "预防",
    "yibao_status": "医保",
    "get_prob": "患病概率",
    "get_way": "传染途径",
    "cured_prob": "治愈率",
    "cure_lasttime": "治疗周期",
    "cost_money": "费用",
    "easy_get": "易感人群",
}

# RAG chunk 分节: (字段/来源, 中文节名)
RAG_SECTIONS = [
    ("desc", "疾病概述"),
    ("cause", "病因"),
    ("prevent", "预防"),
    ("clinical", "症状与检查"),    # 合成节: symptom + check + acompany
    ("treatment", "治疗与用药"),   # 合成节: cure_way + drugs + 费用/周期/治愈率
    ("diet", "饮食注意"),          # 合成节: do_eat + not_eat + recommand_eat
]


def load_records(path: Path, limit: int | None = None):
    """逐行解析 JSONL (每行一个 JSON 对象), 剥离 Mongo 的 _id 字段。"""
    records, bad = [], 0
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip().rstrip(",")
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                bad += 1
                print(f"[warn] 第 {lineno} 行解析失败: {e}", file=sys.stderr)
                continue
            obj.pop("_id", None)
            records.append(obj)
            if limit and len(records) >= limit:
                break
    if bad:
        print(f"[warn] 共 {bad} 行解析失败", file=sys.stderr)
    return records


def build_graph_elements(records):
    """把疾病记录转成 semantica GraphBuilder 需要的 entities/relationships。"""
    entities: dict[str, dict] = {}   # id -> entity dict
    relationships: list[dict] = []
    rel_keys: set[tuple] = set()     # (source, target, type) 去重

    def add_entity(etype: str, name: str, props: dict | None = None):
        eid = f"{etype}:{name}"
        if eid not in entities:
            ent = {"id": eid, "name": name, "type": etype}
            if props:
                ent["properties"] = props
            entities[eid] = ent
        elif props:
            # 实体已存在 (如先作为并发症被引用), 补上属性
            entities[eid].setdefault("properties", {}).update(props)
        return eid

    for rec in records:
        name = rec.get("name")
        if not name:
            continue
        # --- 疾病实体 (带全部标量属性, 属性名中文化) ---
        props = {DISEASE_PROP_MAP[k]: rec[k] for k in DISEASE_PROP_MAP if rec.get(k)}
        disease_id = add_entity("疾病", name, props)

        # --- 列表字段 → 关联实体 + 关系 ---
        for field, (etype, rel_type) in LIST_FIELD_MAP.items():
            values = rec.get(field) or []
            if isinstance(values, str):
                values = [values]
            for v in values:
                v = str(v).strip()
                if not v:
                    continue
                target_id = add_entity(etype, v)
                rel = {"source": disease_id, "target": target_id, "type": rel_type}
                key = (rel["source"], rel["target"], rel["type"])
                if key not in rel_keys:   # 原始数据有重复项, 去重
                    rel_keys.add(key)
                    relationships.append(rel)

    return list(entities.values()), relationships


def build_chunks(records):
    """按疾病分节生成 RAG chunk: 返回 (texts, metadata_list)。"""
    texts, metas = [], []
    for rec in records:
        name = rec.get("name") or ""
        category = " > ".join(rec.get("category") or [])

        def add(text, section):
            text = text.strip()
            if len(text) < 10:  # 过滤过短内容
                return
            texts.append(text)
            metas.append({
                "disease": name,
                "section": section,
                "category": category,
                "source": "medical.json",
            })

        for field, section_label in RAG_SECTIONS:
            if field == "clinical":
                parts = []
                if rec.get("symptom"):
                    parts.append("常见症状: " + "、".join(rec["symptom"]))
                if rec.get("check"):
                    parts.append("相关检查: " + "、".join(rec["check"]))
                if rec.get("acompany"):
                    parts.append("并发症: " + "、".join(rec["acompany"]))
                if parts:
                    add(f"{name} — {section_label}:\n" + "\n".join(parts), section_label)
            elif field == "treatment":
                parts = []
                if rec.get("cure_way"):
                    parts.append("治疗方式: " + "、".join(rec["cure_way"]))
                if rec.get("recommand_drug") or rec.get("common_drug"):
                    drugs = list(OrderedDict.fromkeys(
                        (rec.get("recommand_drug") or []) + (rec.get("common_drug") or [])))
                    parts.append("药品: " + "、".join(drugs))
                for k, label in [("cure_lasttime", "治疗周期"), ("cured_prob", "治愈率"),
                                 ("cost_money", "费用"), ("get_prob", "患病概率"),
                                 ("yibao_status", "医保")]:
                    if rec.get(k):
                        parts.append(f"{label}: {rec[k]}")
                if parts:
                    add(f"{name} — {section_label}:\n" + "\n".join(parts), section_label)
            elif field == "diet":
                parts = []
                if rec.get("do_eat"):
                    parts.append("宜吃: " + "、".join(rec["do_eat"]))
                if rec.get("not_eat"):
                    parts.append("忌吃: " + "、".join(rec["not_eat"]))
                if rec.get("recommand_eat"):
                    parts.append("推荐食谱: " + "、".join(rec["recommand_eat"]))
                if parts:
                    add(f"{name} — {section_label}:\n" + "\n".join(parts), section_label)
            elif rec.get(field):
                add(f"{name} — {section_label}:\n{rec[field]}", section_label)
    return texts, metas


def main():
    ap = argparse.ArgumentParser(description="导入 medical.json 到 Semantica (KG + 向量库)")
    ap.add_argument("--dry-run", action="store_true", help="仅解析统计, 不建图/不入向量库")
    ap.add_argument("--limit", type=int, default=None, help="只取前 N 条疾病记录")
    ap.add_argument("--skip-kg", action="store_true", help="跳过知识图谱构建")
    ap.add_argument("--skip-vector", action="store_true", help="跳过向量库构建")
    args = ap.parse_args()

    print(f"[1/4] 读取 {DATA_PATH} ...")
    records = load_records(DATA_PATH, limit=args.limit)
    print(f"      解析出 {len(records)} 条疾病记录")

    print("[2/4] 转换为实体/关系/chunk ...")
    entities, relationships = build_graph_elements(records)
    texts, metas = build_chunks(records)
    type_counts = {}
    for e in entities:
        type_counts[e["type"]] = type_counts.get(e["type"], 0) + 1
    rel_counts = {}
    for r in relationships:
        rel_counts[r["type"]] = rel_counts.get(r["type"], 0) + 1
    print(f"      实体 {len(entities)} 个: {type_counts}")
    print(f"      关系 {len(relationships)} 条: {rel_counts}")
    print(f"      RAG chunk {len(texts)} 个")

    if args.dry_run:
        # 落盘一份转换结果供检查
        OUTPUT_DIR.mkdir(exist_ok=True)
        sample = {
            "entities_sample": entities[:10],
            "relationships_sample": relationships[:10],
            "chunks_sample": [
                {"metadata": m, "text": t[:300]} for t, m in list(zip(texts, metas))[:5]
            ],
        }
        out = OUTPUT_DIR / "converted_sample.json"
        out.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[dry-run] 样例已写入 {out}, 未建图/未入库")
        return

    # --- 3. 构建知识图谱 ---
    if not args.skip_kg:
        from semantica.kg import GraphBuilder

        print("[3/4] 构建知识图谱 (GraphBuilder) ...")
        # 数据已按唯一 id 去重, 关闭实体合并与冲突解决 (fuzzy 匹配对 2.7万实体极慢)
        builder = GraphBuilder(merge_entities=False, resolve_conflicts=False)
        graph = builder.build({"entities": entities, "relationships": relationships})
        meta = graph.get("metadata", {})
        print(f"      完成: entities={meta.get('num_entities', len(graph.get('entities', [])))}, "
              f"relationships={meta.get('num_relationships', len(graph.get('relationships', [])))}")
        OUTPUT_DIR.mkdir(exist_ok=True)
        kg_path = OUTPUT_DIR / "medical_kg.json"
        kg_path.write_text(json.dumps({
            "entities": graph.get("entities", []),
            "relationships": graph.get("relationships", []),
        }, ensure_ascii=False), encoding="utf-8")
        print(f"      图数据已保存: {kg_path}")

    # --- 4. 向量库 (RAG) ---
    if not args.skip_vector:
        from semantica.vector_store import VectorStore

        print("[4/4] 生成 embedding 并写入 FAISS 向量库 ...")
        vs = VectorStore(backend="faiss", dimension=512)  # bge-small-zh-v1.5 输出 512 维
        # 中文 embedding 模型 (512 维, fastembed 后端, 不依赖 torchaudio)
        try:
            from semantica.embeddings import EmbeddingGenerator
            gen = EmbeddingGenerator()
            gen.set_text_model("fastembed", "BAAI/bge-small-zh-v1.5")
            vs.embedder = gen
        except Exception as e:
            print(f"      [warn] 使用默认 embedder: {e}")

        vector_ids = vs.add_documents(texts, metadata=metas, batch_size=64)
        print(f"      已入库 {len(vector_ids)} 个向量")

        index_dir = OUTPUT_DIR / "medical_vector_index"
        vs.save(str(index_dir))
        print(f"      向量索引已保存: {index_dir}")

        # 检索验证
        query = "糖尿病有什么症状"
        results = vs.search(query, limit=3)
        print(f"\n[验证] 检索: “{query}”")
        for r in results:
            m = r.get("metadata", {})
            print(f"  - {m.get('disease')} / {m.get('section')} (score={r.get('score', r.get('similarity', '?'))})")


if __name__ == "__main__":
    main()
