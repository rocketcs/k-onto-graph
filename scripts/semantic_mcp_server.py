#!/usr/bin/env python3
"""HTTP MCP bridge for K-ACP: graph + RAG access with source citations."""
import json, os, re
from pathlib import Path
from mcp.server.fastmcp import FastMCP
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'medical_import_output/curated_hospital_knowledge'
KG=json.loads((DATA/'knowledge_graph.json').read_text(encoding='utf8'))
TABLES=json.loads((DATA/'tables.json').read_text(encoding='utf8')) if (DATA/'tables.json').exists() else []
CHUNKS=[]
with (DATA/'chunks.jsonl').open(encoding='utf8') as _f:
 for _line in _f:
  try: CHUNKS.append(json.loads(_line))
  except Exception: pass
ENT={x['id']:x for x in KG['entities']}; REL=KG['relationships']
try:
 from semantica.vector_store import VectorStore
 V=VectorStore(backend='faiss',dimension=512); V.load(str(DATA/'rag_index'))
 from semantica.embeddings import EmbeddingGenerator
 _g=EmbeddingGenerator(); _g.set_text_model('fastembed','BAAI/bge-small-zh-v1.5'); V.embedder=_g
except Exception as e: V=None; print('RAG unavailable:',e)
mcp=FastMCP('semantica-hospital-knowledge', host=os.getenv('SEMANTICA_MCP_HOST','127.0.0.1'), port=int(os.getenv('SEMANTICA_MCP_PORT','8020')))
@mcp.tool()
def graph_search(query:str, entity_type:str='', limit:int=20)->dict:
 q=query.lower(); hits=[]
 for e in ENT.values():
  if entity_type and e.get('type')!=entity_type: continue
  blob=json.dumps(e,ensure_ascii=False).lower()
  if q in blob: hits.append(e)
 return json.dumps({'total':len(hits),'items':hits[:max(1,min(limit,100))]},ensure_ascii=False)
@mcp.tool()
def graph_neighbors(node_id:str, limit:int=100)->dict:
 edges=[r for r in REL if r.get('source')==node_id or r.get('target')==node_id][:limit]
 nodes=[ENT[x] for r in edges for x in (r.get('source'),r.get('target')) if x in ENT]
 return json.dumps({'node':ENT.get(node_id),'edges':edges,'nodes':list({x['id']:x for x in nodes}.values())},ensure_ascii=False)
@mcp.tool()
def graph_path(source:str,target:str)->dict:
 adj={}
 for r in REL: adj.setdefault(r['source'],[]).append(r)
 q=[(source,[])]; seen={source}
 while q:
  n,path=q.pop(0)
  if n==target:return json.dumps({'found':True,'path':path},ensure_ascii=False)
  for r in adj.get(n,[]):
   if r['target'] not in seen:seen.add(r['target']);q.append((r['target'],path+[r]))
 return json.dumps({'found':False,'path':[]},ensure_ascii=False)
@mcp.tool()
def food_composition_search(query:str, limit:int=20)->str:
 out=[]
 # 附录IV/常见食物成分表对应白皮书末尾的结构化表格（可能跨多个 Word 表格）
 q=query.replace('附录Ⅳ','附录IV').replace('附录4','附录IV')
 if ('附录IV' in q or '常见食物成分' in q) and TABLES:
  groups={}
  for t in TABLES:
   if t.get('table')==38: groups.setdefault(t.get('table'),[]).append(t)
  out=[x for xs in groups.values() for x in xs]
 else:
  terms=[x for x in re.split(r'[\\s，,、；;]+',query) if len(x)>1]
  for t in TABLES:
   s=' '.join(t.get('values',[]))
   if any(k in s for k in terms): out.append(t)
 return json.dumps({'query':query,'items':out[:limit]},ensure_ascii=False)

@mcp.tool()
def rag_search(query:str, limit:int=5)->dict:
 if V is None:return json.dumps({'error':'RAG index unavailable'},ensure_ascii=False)
 hits=V.search(query,limit=max(1,min(limit,20)))
 if not hits:
  terms=[x for x in re.split(r'\\s+',query) if len(x)>1]
  hits=[{'text':c['text'],'metadata':c['metadata'],'score':1.0} for c in CHUNKS if any(x in c['text'] for x in terms)][:max(1,min(limit,20))]
 return json.dumps({'query':query,'items':hits},ensure_ascii=False)
@mcp.tool()
def knowledge_search(query:str, limit:int=5)->dict:
 """Hybrid search: graph hits plus RAG evidence."""
 return json.dumps({'graph':json.loads(graph_search(query,limit=limit)),'rag':json.loads(rag_search(query,limit=limit))},ensure_ascii=False)
if __name__=='__main__': mcp.run(transport=os.getenv('SEMANTICA_MCP_TRANSPORT','sse'))
