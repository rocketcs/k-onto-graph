#!/usr/bin/env python3
"""
medical.json (JSONL, 8808 条疾病记录) → Semantica 知识图谱 + RAG 向量库

LLM 抽取使用 DeepSeek V4 Flash:
  - provider = "deepseek"   → Semantica 内置 DeepSeekProvider (OpenAI 兼容)
  - model    = "deepseek-v4-flash"
  - API key 从环境变量 DEEPSEEK_API_KEY 读取 (也可 --api-key 传入)

性能设计 (相比全串行单条模式提速 20~100 倍):
  - --workers N       线程池并发 (默认 8)
  - --batch-size N    批量 prompt: 一次 LLM 调用抽取 N 条记录的实体+关系 (默认 10)
  - --max-retries 1   关闭 instructor 默认三重试 (失败一次翻一倍耗时)
  - 结果按记录缓存到 medical_import_output/llm_cache/, 中断后重跑自动续传

质量保障:
  - 批量返回按编号完整性校验, 缺条整批重试 (最多 2 次)
  - 幻觉过滤: 实体文本必须逐字出现在对应记录原文中
  - 关系端点校验: 关系的 source/target 必须是该条记录的实体

用法:
  export DEEPSEEK_API_KEY=sk-xxxx
  pip install 'semantica[llm-deepseek]'

  python scripts/import_medical_llm.py --dry-run                  # 只解析, 不调 LLM
  python scripts/import_medical_llm.py --limit 20 --batch-size 10 # 20 条快速试跑
  python scripts/import_medical_llm.py                            # 全量 8808 条
  python scripts/import_medical_llm.py --workers 16 --batch-size 20   # 更快 (注意中转站限流)
  python scripts/import_medical_llm.py --provider openai --base-url https://你的网关/v1   # 中转站
"""

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 必须在导入 semantica/torch 之前设置: 修复 sentence-transformers 多线程
# 推理时的 OpenMP 段错误 (Segmentation fault: 11)
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

DATA_PATH  = Path("/Users/rocket/workspace/QASystemOnMedicalKG/data/medical.json")
OUTPUT_DIR = Path("./medical_import_output")
CACHE_DIR  = OUTPUT_DIR / "llm_cache"

ENTITY_TYPES = ["疾病", "症状", "检查", "药物", "食物", "科室", "治疗方式"]

# 关系类型统一中文化: LLM 可能输出英文 prompt 类型, 入库时强制映射成中文
REL_TYPE_CN = {
    "has_symptom": "有症状",
    "needs_check": "需要检查",
    "treated_by": "治疗方法",
    "treated_in": "就诊科室",
    "recommand_drug": "推荐用药",
    "do_eat": "宜吃",
    "not_eat": "忌吃",
    "acompany_with": "伴有并发症",
}
REL_TYPES_ALLOWED = list(REL_TYPE_CN.values()) + list(REL_TYPE_CN.keys())

_print_lock = threading.Lock()


def log(msg: str):
    with _print_lock:
        print(msg, flush=True)


def load_records(path: Path, limit: int | None = None):
    """逐行解析 JSONL (MongoDB 导出: 每行一个对象), 剥离 _id。"""
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


def record_to_text(r: dict) -> str:
    """把一条记录转成自然语言文本 —— LLM 抽取实体/关系的信息源。"""
    name = r.get("name", "")
    parts = [f"疾病:{name}。{r.get('desc', '')}"]
    if r.get("symptom"):
        parts.append("症状:" + "、".join(r["symptom"]))
    if r.get("cause"):
        parts.append("病因:" + r["cause"].replace("\n", " "))
    if r.get("prevent"):
        parts.append("预防:" + r["prevent"].replace("\n", " "))
    if r.get("check"):
        parts.append("检查:" + "、".join(r["check"]))
    if r.get("cure_way"):
        parts.append("治疗方式:" + "、".join(r["cure_way"]))
    if r.get("cure_department"):
        parts.append("就诊科室:" + "、".join(r["cure_department"]))
    if r.get("recommand_drug") or r.get("common_drug"):
        drugs = list(dict.fromkeys((r.get("recommand_drug") or []) + (r.get("common_drug") or [])))
        parts.append("用药:" + "、".join(drugs))
    if r.get("do_eat"):
        parts.append("宜吃:" + "、".join(r["do_eat"]))
    if r.get("not_eat"):
        parts.append("忌吃:" + "、".join(r["not_eat"]))
    return "\n".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# 抽取与校验
# ---------------------------------------------------------------------------

def build_batch_prompt(items: list[tuple[int, str]]) -> str:
    """构造批量 prompt: 每条记录一个【记录N】编号, 要求一次返回 N 组实体+关系。"""
    blocks = []
    for j, (_, text) in enumerate(items, 1):
        blocks.append(f"【记录{j}】\n{text}")
    return (
        "你是医学知识图谱信息抽取器。下面给出多条疾病记录, 每条以【记录N】开头。\n"
        "请为每条记录分别抽取实体和关系, 严格输出一个 JSON 对象, 键为记录编号字符串。\n"
        f"实体类型只允许以下之一: {', '.join(ENTITY_TYPES)}。\n"
        "关系类型只允许以下之一 (必须用中文): "
        "有症状, 需要检查, 治疗方法, 就诊科室, 推荐用药, 宜吃, 忌吃, 伴有并发症。\n"
        "规则:\n"
        "1. 实体文本必须逐字出现在对应记录的原文中, 禁止编造。\n"
        "2. 关系的 source 和 target 必须是该记录中已抽取的实体文本, type 必须是上面的中文类型。\n"
        '3. 输出格式: {"1": {"entities": [{"text": "...", "label": "症状"}], '
        '"relationships": [{"source": "...", "type": "有症状", "target": "..."}]}, "2": {...}}\n'
        "4. 输出必须是合法 JSON, 不要包含任何解释文字。\n\n"
        + "\n\n".join(blocks)
    )


def parse_batch_response(raw, expected_count: int):
    """解析批量返回, 校验编号完整性。返回 {str_index: {"entities": [...], "relationships": [...]}}。"""
    data = raw if isinstance(raw, dict) else json.loads(raw)
    expected_keys = {str(i) for i in range(1, expected_count + 1)}
    got_keys = set(data.keys())
    if got_keys != expected_keys:
        missing = sorted(expected_keys - got_keys)
        raise ValueError(f"批量返回编号不齐, 缺失: {missing}, 实际键: {sorted(got_keys)}")
    return data


def filter_entities(ent_list: list[dict], source_text: str) -> list[dict]:
    """幻觉过滤: 实体文本必须逐字出现在原文中。"""
    return [e for e in ent_list if e.get("text") and e["text"] in source_text]


def entities_to_dicts(ent_list) -> list[dict]:
    """LLM 返回的实体列表 → 图谱实体 dict。

    id 直接用实体文本 (= 关系 source/target 的取值), 保证导入 Explorer 时
    边端点能匹配到节点。实体类型放进 properties["类型"]。
    """
    out = []
    for e in ent_list:
        text = str(e.get("text", "")).strip()
        label = str(e.get("label", "实体")).strip()
        if not text:
            continue
        conf = float(e.get("confidence", 1.0))
        out.append({"id": text, "name": text, "type": label,
                    "properties": {"类型": label, "置信度": conf}})
    return out


def relations_to_dicts(rel_list, valid_names: set[str]) -> list[dict]:
    """LLM 返回的关系列表 → 图谱关系 dict; type 强制中文化, source/target 必须是实体文本。"""
    out = []
    for r in rel_list:
        s = str(r.get("source", "")).strip()
        t = str(r.get("target", "")).strip()
        p = str(r.get("type", "")).strip()
        if s in valid_names and t in valid_names and p:
            rel_type = REL_TYPE_CN.get(p, p)   # 英文→中文; 已是中文则原样
            conf = float(r.get("confidence", 1.0))
            out.append({"source": s, "target": t, "type": rel_type,
                        "properties": {"置信度": conf}})
    return out


def extract_batch(llm, items: list[tuple[int, str]], args, attempt: int = 0):
    """一次 LLM 调用抽取一批记录。失败/编号不齐时整批重试 (最多 2 次)。"""
    raw = llm.generate_structured(build_batch_prompt(items), max_retries=1)
    try:
        parsed = parse_batch_response(raw, len(items))
    except ValueError as e:
        if attempt < 2:
            log(f"      [retry] 批量({len(items)}条)编号不齐: {e} → 整批重试 {attempt + 2}/3")
            return extract_batch(llm, items, args, attempt + 1)
        raise

    result = {}   # global_index -> (ent_dicts, rel_dicts)
    for j, (global_idx, text) in enumerate(items, 1):
        chunk = parsed[str(j)]
        ents = filter_entities(chunk.get("entities", []), text)
        ent_dicts = entities_to_dicts(ents)
        valid_names = {e["name"] for e in ent_dicts}
        rel_dicts = relations_to_dicts(chunk.get("relationships", []), valid_names)
        result[global_idx] = (ent_dicts, rel_dicts)
    return result


def process_batch_job(llm_factory, items, args):
    """线程池 worker: 处理一批记录 (缓存命中直接返回)。"""
    llm = llm_factory()
    out = {}
    uncached = []
    for global_idx, text in items:
        cache_file = CACHE_DIR / f"record_{global_idx:05d}.json"
        if cache_file.exists() and not args.skip_cache:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            out[global_idx] = (cached["entities"], cached["relationships"])
        else:
            uncached.append((global_idx, text))

    if uncached:
        results = extract_batch(llm, uncached, args)
        for global_idx, (ent_dicts, rel_dicts) in results.items():
            out[global_idx] = (ent_dicts, rel_dicts)
            if not args.skip_cache:
                cache_file = CACHE_DIR / f"record_{global_idx:05d}.json"
                cache_file.write_text(
                    json.dumps({"entities": ent_dicts, "relationships": rel_dicts},
                               ensure_ascii=False), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description="medical.json → Semantica KG (DeepSeek V4 Flash LLM 抽取)")
    ap.add_argument("--dry-run", action="store_true", help="仅解析, 不调 LLM")
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 条")
    ap.add_argument("--model", default="deepseek-v4-flash", help="LLM 模型名")
    ap.add_argument("--provider", default="deepseek", help="provider: deepseek|novita|openai ...")
    ap.add_argument("--base-url", default=None,
                    help="OpenAI 兼容网关地址 (中转站/Coding Plan), 配此参数时 provider 自动视为 openai")
    ap.add_argument("--api-key", default=None, help="API key (默认读 DEEPSEEK_API_KEY)")
    ap.add_argument("--workers", type=int, default=8, help="并发线程数 (默认 8)")
    ap.add_argument("--batch-size", type=int, default=10, help="每条 LLM 调用处理的记录数 (默认 10)")
    ap.add_argument("--max-retries", type=int, default=1, help="单次生成的 LLM 重试次数 (默认 1)")
    ap.add_argument("--skip-vector", action="store_true", help="跳过向量库")
    ap.add_argument("--skip-cache", action="store_true", help="不使用/写入抽取缓存")
    args = ap.parse_args()

    if args.base_url and args.provider == "deepseek":
        args.provider = "openai"   # DeepSeekProvider 的 base_url 是硬编码, 中转站必须走 OpenAIProvider

    # 关闭 Semantica 进度条刷屏 (我们自己打印进度)
    try:
        from semantica.utils.progress_tracker import get_progress_tracker
        get_progress_tracker().enabled = False
    except Exception:
        pass

    # ---------- 1. 解析 ----------
    print(f"[1/4] 读取 {DATA_PATH} ...")
    records = load_records(DATA_PATH, limit=args.limit)
    texts = [record_to_text(r) for r in records]
    print(f"      解析出 {len(records)} 条疾病记录")

    if args.dry_run:
        OUTPUT_DIR.mkdir(exist_ok=True)
        (OUTPUT_DIR / "texts_sample.json").write_text(
            json.dumps(texts[:3], ensure_ascii=False, indent=2), encoding="utf-8")
        print("[dry-run] 完成, 未调用 LLM。样例文本: ", texts[0][:120], "...")
        return

    # ---------- 2. LLM 抽取 (批量 + 并发) ----------
    from semantica.semantic_extract.providers import create_provider

    def llm_factory():
        return create_provider(
            args.provider, model=args.model, api_key=args.api_key,
            base_url=args.base_url, max_retries=args.max_retries,
        )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    items = list(enumerate(texts, 1))                      # [(global_idx, text), ...]
    batches = [items[i:i + args.batch_size] for i in range(0, len(items), args.batch_size)]
    total_calls = len(batches)
    print(f"[2/4] DeepSeek {args.model} 批量抽取 "
          f"({len(records)}条 / {args.batch_size}条每批 ≈ {total_calls} 次 LLM 调用, 并发 {args.workers}) ...")

    all_entities, all_relationships = [], []
    done = 0
    t0 = __import__("time").time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(process_batch_job, llm_factory, b, args) for b in batches]
        for fut in as_completed(futures):
            try:
                batch_out = fut.result()
            except Exception as e:
                log(f"      [error] 批量抽取失败: {e}")
                continue
            for idx, (ent_dicts, rel_dicts) in sorted(batch_out.items()):
                all_entities.extend(ent_dicts)
                all_relationships.extend(rel_dicts)
            done += 1
            elapsed = __import__("time").time() - t0
            rate = done / max(elapsed, 0.001)
            eta = (total_calls - done) / max(rate, 1e-9)
            log(f"      {done}/{total_calls} 批  实体 {len(all_entities)}  关系 {len(all_relationships)}"
                f"  ({rate:.1f} 批/s, ETA {eta/60:.1f} 分钟)")

    print(f"      完成: 实体 {len(all_entities)}  关系 {len(all_relationships)}")

    # ---------- 3. 建图 ----------
    print("[3/4] 构建知识图谱 (GraphBuilder, merge_entities=True) ...")
    from semantica.kg import GraphBuilder
    builder = GraphBuilder(merge_entities=True)
    graph = builder.build({"entities": all_entities, "relationships": all_relationships})
    meta = graph.get("metadata", {})
    print(f"      完成: entities={meta.get('num_entities', len(graph.get('entities', [])))}, "
          f"relationships={meta.get('num_relationships', len(graph.get('relationships', [])))}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    # --- 端点一致性修复 (GraphBuilder merge 会合并同名实体但不改写关系端点) ---
    entities_out = graph.get("entities", [])
    relationships_out = graph.get("relationships", [])
    for e in entities_out:
        e["id"] = e.get("name", e.get("id"))     # id 统一为纯名称

    alias = {}   # 被合并的旧名(去 "类型:" 前缀) → 合并后的实体 id
    for e in entities_out:
        for old in e.get("merged_from", []):
            alias[old.split(":", 1)[-1]] = e["id"]

    ids = {e["id"] for e in entities_out}
    unresolved_names = set()
    for r in relationships_out:
        for key in ("source", "target"):
            v = r[key]
            if v not in ids:
                if v in alias:
                    r[key] = alias[v]            # 别名: 指向合并后的实体
                else:
                    unresolved_names.add(v)      # 真丢失: 补实体节点
    for name in unresolved_names:
        entities_out.append({"id": name, "name": name, "type": "相关",
                             "properties": {"类型": "相关", "置信度": 1.0}})

    kg_path = OUTPUT_DIR / "medical_kg_llm.json"
    kg_path.write_text(json.dumps({"entities": entities_out,
                                   "relationships": relationships_out},
                                  ensure_ascii=False), encoding="utf-8")
    print(f"      图数据已保存: {kg_path}")

    # ---------- 4. 向量库 (RAG, 本地 embedding, 不花钱) ----------
    if not args.skip_vector:
        from semantica.vector_store import VectorStore
        print("[4/4] 生成 embedding 并写入 FAISS 向量库 (中文多语言模型 384 维) ...")
        vs = VectorStore(backend="faiss", dimension=384)
        try:
            from semantica.embeddings import EmbeddingGenerator
            # 注意: 必须在初始化时就指定 sentence_transformers, 不能先建默认
            # (fastembed) 再 set_text_model 切换 —— 两个推理引擎共存会段错误
            gen = EmbeddingGenerator(text={
                "method": "sentence_transformers",
                "model_name": "paraphrase-multilingual-MiniLM-L12-v2",
            })
            vs.embedder = gen
        except Exception as e:
            print(f"      [warn] 使用默认 embedder: {e}")
        metas = [{"disease": r.get("name"), "source": "medical.json"} for r in records]
        ids = vs.add_documents(texts, metadata=metas, batch_size=64)
        index_dir = OUTPUT_DIR / "medical_vector_index"
        vs.save(str(index_dir))
        print(f"      已入库 {len(ids)} 个向量 -> {index_dir}")

        results = vs.search("糖尿病有什么症状", limit=3)
        print("\n[验证] 检索 “糖尿病有什么症状”:")
        for r in results:
            m = r.get("metadata", {})
            print(f"  - {m.get('disease')} (score={r.get('score', r.get('similarity', '?'))})")


if __name__ == "__main__":
    main()