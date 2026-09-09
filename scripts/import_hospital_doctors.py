#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser(); p.add_argument('xlsx'); p.add_argument('--output-dir',default='medical_import_output/hospital_doctors_script'); a=p.parse_args()
 import openpyxl
 from semantica.kg import GraphBuilder
 from semantica.vector_store import VectorStore
 from semantica.embeddings import EmbeddingGenerator
 out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
 # semantic analysis: extract domain concepts from narrative text with auditable keyword evidence
 semantic_terms=['慢病','功能医学','精准医疗','抗衰老','心血管','免疫系统','健康管理','筛查','营养','肿瘤','全科','外科','消化','呼吸','罕见病']
 semantic=[]
 wb=openpyxl.load_workbook(a.xlsx,read_only=True,data_only=True)
 entities={}; rels=[]; texts=[]; metas=[]
 def ent(t,n,props=None):
  if not n:return None
  i=f'{t}:{n}'; entities.setdefault(i,{'id':i,'name':n,'type':t})
  if props: entities[i].setdefault('properties',{}).update(props)
  return i
 seen=set()
 for ws in wb.worksheets:
  rows=list(ws.values)
  if not rows: continue
  heads=[str(x).strip() if x is not None else '' for x in rows[0]]
  for rn,row in enumerate(rows[1:],2):
   vals={heads[i]:str(row[i]).strip() for i in range(min(len(heads),len(row))) if heads[i] and row[i] not in (None,'')}
   group=vals.get('特色医疗组'); doctor=vals.get('医生姓名')
   if not group and not doctor: continue
   hospital=ent('医院','循上鹏瑞利医院',{'来源':str(a.xlsx)})
   gid=ent('医疗组',group,{'简介':vals.get('特色医疗组简介',''),'来源工作表':ws.title,'来源行号':rn})
   did=ent('医生',doctor,{'医生简历':vals.get('医生简历',''),'医生简介':vals.get('医生简介',''),'来源工作表':ws.title,'来源行号':rn})
   for s,t,r in [(hospital,gid,'包含医疗组'),(gid,did,'拥有医生')]:
    if s and t and (s,t,r) not in seen: rels.append({'source':s,'target':t,'type':r});seen.add((s,t,r))
   full=' '.join(vals.values())
   concepts=[x for x in semantic_terms if x in full]
   for concept in concepts:
    cid=ent('专业方向',concept,{'证据':full[:500],'来源工作表':ws.title,'来源行号':rn})
    if did and (did,cid,'擅长方向') not in seen: rels.append({'source':did,'target':cid,'type':'擅长方向'}); seen.add((did,cid,'擅长方向'))
   semantic.append({'医生':doctor,'医疗组':group,'专业方向':concepts,'sheet':ws.title,'row':rn})
   text=f'医院：循上鹏瑞利医院\n医疗组：{group}\n医疗组简介：{vals.get("特色医疗组简介","")}\n医生：{doctor}\n医生简历：{vals.get("医生简历","")}\n医生简介：{vals.get("医生简介","")}'
   texts.append(text); metas.append({'医院':'循上鹏瑞利医院','医疗组':group,'医生':doctor,'source':str(a.xlsx),'sheet':ws.title,'row':rn})
 graph=GraphBuilder(merge_entities=False,resolve_conflicts=False).build({'entities':list(entities.values()),'relationships':rels})
 (out/'hospital_doctors_kg.json').write_text(json.dumps({'entities':graph['entities'],'relationships':graph['relationships']},ensure_ascii=False),encoding='utf8')
 gen=EmbeddingGenerator(); gen.set_text_model('fastembed','BAAI/bge-small-zh-v1.5'); vs=VectorStore(backend='faiss',dimension=512); vs.embedder=gen; vs.add_documents(texts,metadata=metas,batch_size=32); vs.save(str(out/'hospital_doctors_vector_index'))
 (out/'semantic_analysis.json').write_text(json.dumps(semantic,ensure_ascii=False,indent=2),encoding='utf8')
 report={'workbooks':wb.sheetnames,'entities':len(entities),'relationships':len(rels),'chunks':len(texts),'entity_types':{t:sum(e['type']==t for e in entities.values()) for t in set(e['type'] for e in entities.values())}}
 (out/'import_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8'); print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
