import json,sys,re
from pathlib import Path
from docx import Document
b=Path('medical_import_output/hospital_doctors_semantic'); base=json.loads((b/'hospital_doctors_kg.json').read_text()); es={e['id']:e for e in base['entities']};rs=base['relationships'];seen={(x['source'],x['target'],x['type']) for x in rs}; fn=sys.argv[1]; d=Document(fn)
terms=['营养不良','营养低下','老年营养','健康饮食','体重减轻','膳食摄入不足','恶性肿瘤','炎症','肌肉量减少','低BMI','维生素D','维生素B12','蛋白质','能量摄入','营养评估','GLIM标准','吞咽困难','吸收不良']
h='医院:循上鹏瑞利医院'
for term in terms:
 ev=[i for i,p in enumerate(d.paragraphs,1) if term in p.text]
 if not ev:continue
 typ='营养素' if term.startswith(('维生素','蛋白质')) else '营养主题';i=f'{typ}:{term}';es[i]={'id':i,'name':term,'type':typ,'properties':{'来源文件':fn,'证据段落':ev[:30],'出现次数':len(ev)}}; k=(h,i,'涵盖营养主题')
 if k not in seen:rs.append({'source':h,'target':i,'type':'涵盖营养主题'});seen.add(k)
out=b/'hospital_doctors_clean_kg.json';out.write_text(json.dumps({'entities':list(es.values()),'relationships':rs},ensure_ascii=False),encoding='utf8');print(len(es),len(rs))
