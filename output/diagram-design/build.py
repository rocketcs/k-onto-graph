from pathlib import Path
from html import escape
import sys

OUT = Path(__file__).parent
EDITORIAL = '--editorial' in sys.argv
if EDITORIAL:
    OUT = OUT / 'editorial'
    OUT.mkdir(exist_ok=True)
INK, MUTED, BLUE, TEAL = '#202b34', '#566773', '#2463ad', '#167c75'
if EDITORIAL:
    INK, MUTED, BLUE, TEAL = '#191919', '#595959', '#191919', '#b83c2d'
parts = []

def text(x, y, value, size=20, color=INK, weight=400):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(value)}</text>')

def rect(x, y, w, h, fill='#ffffff', stroke='#cbd5dc'):
    if EDITORIAL:
        fill = {'#edf5fc':'#fff2ee','#f8fafb':'#ffffff','#f7f9fa':'#ffffff','#f0f7f7':'#f3f1ef'}.get(fill,fill)
        stroke = '#b9b6b2' if stroke == '#cbd5dc' else stroke
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>')
        return
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}"/>')

def line(x1, y1, x2, y2, arrow=False):
    parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#92a3af" stroke-width="1.5"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>')

def start(slug, title, sub, num):
    parts.clear()
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" role="img" aria-labelledby="{slug}-title {slug}-desc"><title id="{slug}-title">{title}</title><desc id="{slug}-desc">{sub}</desc><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10" fill="#92a3af"/></marker></defs><style>text{{font-family:"PingFang SC","Microsoft YaHei",Arial,sans-serif;letter-spacing:0}}</style>')
    rect(0, 0, 1280, 720, '#ffffff', '#ffffff')
    text(48, 42, 'SEMANTICA / KNOWLEDGE ENGINEERING', 16, BLUE, 600)
    text(48, 98, title, 40, INK, 600)
    text(48, 136, sub, 20, MUTED)
    text(1184, 42, f'0{num}', 20, MUTED)
    line(48, 160, 1232, 160)
    if EDITORIAL:
        parts.append('<path d="M48 160 H224" stroke="#b83c2d" stroke-width="5"/>')

def finish(slug, footer):
    line(48, 658, 1232, 658)
    text(48, 692, footer, 16, MUTED)
    svg = ''.join(parts)+'</svg>'
    if EDITORIAL:
        svg = svg.replace('#92a3af','#77716b').replace('#f7f9fa','#f5f4f2').replace('#f0f7f7','#eeece9')
    (OUT/f'{slug}.svg').write_text(svg)
    (OUT/f'{slug}.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Semantica 图解</title><style>html,body{margin:0;background:#eef2f4}body{display:grid;min-height:100vh;place-items:center}svg{display:block;width:100%;height:auto;max-width:1600px}</style>'+svg+'</html>')

def box(x, y, w, title, lines, focal=False, h=124):
    if EDITORIAL:
        rect(x,y,w,h,'#fff2ee' if focal else '#ffffff','#b9b6b2')
        parts.append(f'<path d="M{x} {y} H{x+w}" stroke="'+('#b83c2d' if focal else '#191919')+'" stroke-width="4"/>')
        text(x+20,y+34,title,24,'#b83c2d' if focal else INK,600)
        for i,s in enumerate(lines): text(x+20,y+68+i*28,s,20,MUTED)
        return
    rect(x,y,w,h,'#edf5fc' if focal else '#f8fafb',BLUE if focal else '#cbd5dc')
    text(x+20,y+34,title,24,BLUE if focal else INK,600)
    for i,s in enumerate(lines): text(x+20,y+68+i*28,s,20,MUTED)

start('01-architecture','从文档到可用的知识图谱','数据处理建立事实基础，知识增强补充结构、推导依据与决策记录。',1)
text(48,198,'01  数据进入与知识构建',20,BLUE,600)
for x1,x2 in [(272,304),(588,620),(884,916)]: line(x1,282,x2,282,True)
box(48,220,224,'数据来源',['文件 · 网页 · 数据库','Sources'])
box(304,220,284,'接入与预处理',['Ingest → Parse','Normalize → Split'])
box(620,220,264,'语义提取',['Extract','实体 · 关系 · 三元组'],True)
box(916,220,316,'知识整理',['Conflict Detection','Deduplication → KG'])
line(1074,344,1074,400,True)
text(48,386,'02  知识增强与存储',20,BLUE,600)
line(820,460,772,460,True)
line(476,460,432,460,True)
box(820,400,412,'知识增强 → Enriched KG',['本体 Ontology · 推理 Reasoning','溯源 Provenance · 决策 Decisions'],True)
box(476,400,296,'多模型存储',['Vector Store','Graph Store：RDF / LPG'])
box(48,400,384,'交付与使用',['Export · Visualize','REST · MCP · CLI'])
line(48,554,1232,554)
text(48,590,'贯穿式支撑',24,TEAL,600)
text(264,588,'来源记录与血缘追踪  /  质量检查  /  业务规则与配置',24)
text(264,622,'按业务编排连接各模块；增强能力并非默认全部自动执行。',20,MUTED)
finish('01-architecture','阅读方向：第一行从左到右，第二行从右到左。概览聚合次级组件，保留核心数据流程。')

start('02-extraction','Extract：把原文变成可检查的事实','先明确要什么，再识别实体与关系；可信度来自证据、校验和业务验收。',2)
for x in [320,628,936]: line(x-8,258,x+12,258,True)
box(48,192,264,'1  定义抽取目标',['类型偏好 · 提示词','规则 / 模型 / LLM'])
box(340,192,280,'2  识别实体与关系',['识别人名、组织等实体','识别实体间的语义联系'],True)
box(648,192,280,'3  结构化与基础检查',['实体 · 关系 · 三元组','空值 / 端点 / 分数检查'])
box(956,192,276,'4  交给后续处理',['冲突检测与去重','形成候选知识图谱'])
text(48,360,'一个例子',20,TEAL,600)
text(208,360,'原文：张明是华星公司的工程师。',24,INK,600)
line(48,382,1232,382)
text(48,418,'实体',20,BLUE,600)
text(152,418,'张明：人物；华星公司：组织',20)
text(676,418,'关系',20,BLUE,600)
text(780,418,'张明 — 任职于 → 华星公司',20)
text(152,452,'“工程师”可建为职业属性或类型，由业务定义决定。',20,MUTED)
line(48,478,1232,478)
text(48,514,'项目已有',24,BLUE,600)
text(256,512,'多种抽取方式；结构化结果；基础校验；可接入来源记录。',20)
text(48,554,'使用者配置',24,TEAL,600)
text(256,552,'指定领域与类型；连接证据定位；制定复核和入库条件。',20)
text(48,594,'上线前验收',24,INK,600)
text(256,592,'用业务标注样本评测准确率与召回率，复核关键事实及错误案例。',20)
text(256,626,'类型偏好不是严格白名单；来源链路需显式接入。',16,MUTED)
finish('02-extraction','可信边界：模型分数不等于实测准确率；格式正确不等于事实正确，系统不承诺零错误。')

start('03-participation','知识增强：用户做什么，得到什么','四项能力协同工作；用户定义业务口径，并决定哪些结果可以采纳。',3)
xs=[208,468,728,988]
names=['本体 Ontology','推理 Reasoning','溯源 Provenance','决策 Decisions']
for x,n in zip(xs,names): text(x,210,n,24,BLUE,600)
rows=[(252,'用户提供',[
['概念、关系与业务约束','选择模板或确认候选定义'],['业务事实与推导规则','确认规则的适用范围'],['来源标识与版本信息','接入原文位置等元数据'],['取舍策略与采纳标准','处理例外和人工复核']]),
(364,'系统处理',[
['构建类、属性与层级','显式调用约束校验'],['匹配前提并绑定变量','按规则推导结论'],['关联知识与处理活动','保存来源及派生链路'],['按策略处理冲突','记录选择与裁决理由']]),
(476,'交付产物',[
['本体定义 OWL','SHACL 约束 / 违规报告'],['推导结果及相关依据','与原始事实区分使用'],['来源记录与知识血缘','可查询或导出 PROV'],['裁决结果与决策记录','采纳与否由业务决定']])]
for y,label,cols in rows:
    parts.append(f'<rect x="48" y="{y-24}" width="1184" height="96" fill="'+('#f0f7f7' if label=='交付产物' else '#f7f9fa')+'"/>')
    text(68,y+14,label,24,TEAL if label=='交付产物' else INK,600)
    for x,ls in zip(xs,cols):
        for k,s in enumerate(ls): text(x,y+8+32*k,s,20)
text(48,600,'贯穿全程',24,TEAL,600)
text(208,598,'溯源应随抽取、校验、推导和裁决持续记录，而非结束后补做。',24)
text(208,632,'本体定义“如何表达”；规则决定“如何推导”；业务审核决定“是否采纳”。',20,MUTED)
finish('03-participation','能力边界：来源可追查不代表内容已被证实；审批记录能力不等于已提供自动审批界面。')

start('04-implementation','知识增强的实现机制','模块内部各有处理链路，通过业务编排接入知识图谱。',4)
lanes=[
('本体','OntologyEngine','输入与构建',['实体关系 / 文本 / 模板 / 外部本体','按类型归类，生成属性与层级'],'标准化与校验',['OWL 表达；生成 SHACL 约束','显式调用 pyshacl，返回违规报告']),
('推理','Reasoner','载入与匹配',['add_fact / add_rule','匹配规则前提并绑定变量'],'推导与返回',['前向链推导；后向链查找依据','规则示例：工程师(x) → 员工(x)']),
('溯源','ProvenanceManager','记录与关联',['知识 ID、来源、执行者与时间','接入处理活动及派生关系'],'保存与查询',['内存或 SQLite 保存记录','追踪血缘，导出 PROV 来源记录']),
('决策','Resolver + Recorder','输入与策略选择',['冲突候选值、来源与业务上下文','投票 / 可信度 / 时效 / 置信度'],'记录与业务采纳',['保存裁决结果、理由及关联实体','连接业务复核，由业务决定采纳'])]
for i,(name,component,a,al,b,bl) in enumerate(lanes):
    y=184+i*112
    line(704,y+48,752,y+48,True)
    text(48,y+28,name,28,TEAL if i==2 else BLUE,600)
    text(48,y+60,component,16,MUTED)
    rect(284,y,420,104,'#f7f9fa')
    rect(752,y,480,104,'#f0f7f7' if i==2 else '#f7f9fa')
    text(300,y+24,a,20,INK,600)
    text(768,y+24,b,20,INK,600)
    for j,s in enumerate(al):text(300,y+56+j*32,s,20,MUTED)
    for j,s in enumerate(bl):text(768,y+56+j*32,s,20,MUTED)
text(48,646,'组合产物：本体定义 + 推导结果 + 来源链路 + 决策记录 → 增强知识图谱',20,TEAL,600)
finish('04-implementation','实现边界：本体验证器尚未接入完整 OWL 一致性推理；冲突处理与决策记录需编排连接。')

slugs=['01-architecture','02-extraction','03-participation','04-implementation']
titles=['整体架构','Extract 提取与可信机制','知识增强：用户参与与产物','知识增强：内部实现']
gallery='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Semantica 图解</title><style>body{font-family:"PingFang SC",sans-serif;margin:40px auto;max-width:1280px;padding:0 24px;color:#202b34;background:#f4f6f7}img{width:100%;height:auto}section{margin:40px 0}a{color:#2463ad;margin-right:24px}</style><h1>Semantica：从提取到知识增强</h1><p>四张 16:9 图解 · 可编辑 SVG / HTML · 高清 PNG</p>'
for slug,title in zip(slugs,titles):
    gallery+=f'<section><h2>{title}</h2><p><a href="{slug}.png">PNG 图片</a><a href="{slug}.svg">SVG 源图</a><a href="{slug}.html">独立页面</a></p><img src="{slug}.svg" alt="{title}"></section>'
(OUT/'index.html').write_text(gallery+'</html>')
