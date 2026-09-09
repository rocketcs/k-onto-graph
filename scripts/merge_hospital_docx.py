import json,sys
from pathlib import Path
from docx import Document
base=Path('medical_import_output/hospital_doctors_semantic'); kg=json.loads((base/'hospital_doctors_kg.json').read_text())
doc=Document(sys.argv[1]); text='\n'.join(p.text.strip() for p in doc.paragraphs if p.text.strip())
# preserve document as source node and semantic topic nodes
ents={e['id']:e for e in kg['entities']}; rel=kg['relationships']; seen={(r['source'],r['target'],r['type']) for r in rel}
def add(t,n):
 i=f'{t}:{n}'; ents.setdefault(i,{'id':i,'name':n,'type':t,'properties':{'来源文件':sys.argv[1]}}); return i
h=add('医院','循上鹏瑞利医院')
terms=['慢病','功能医学','精准医疗','抗衰老','心血管','免疫系统','健康管理','筛查','营养','肿瘤','全科','外科','消化','呼吸','罕见病','生命医学','数字化医疗','多学科诊疗']
for x in terms:
 if x in text:
  t=add('专业方向',x); k=(h,t,'医院关注方向')
  if k not in seen: rel.append({'source':h,'target':t,'type':'医院关注方向','properties':{'证据':x,'来源文件':sys.argv[1]}});seen.add(k)
kg={'entities':list(ents.values()),'relationships':rel}; out=base/'hospital_doctors_merged_kg.json';out.write_text(json.dumps(kg,ensure_ascii=False),encoding='utf8');(base/'merged_docx_source.txt').write_text(text,encoding='utf8');print(len(kg['entities']),len(rel),out)
