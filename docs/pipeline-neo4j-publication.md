# Pipeline 发布到 Neo4j

在 Enrich → Pipeline 选择发布目标“Neo4j 知识库”，上传并运行。服务端须配置 NEO4J_URI、NEO4J_USER、NEO4J_PASSWORD 和 NEO4J_DATABASE（默认 neo4j）。沿用 Explorer API 鉴权；凭据不进入浏览器。

## 审核与发布

1. 有质量问题时保持待审核，在结果审核中修订、排除或补充记录并填写原因。人工修订也必须重新通过校验。
2. 点击“发布到 Neo4j”，核对目标地址、数据库、每个实体的候选标签及属性。
3. 每个实体明确选择“新建独立实体”或已有实体，并填写审核原因，才可提交。

名称、规范名和已有 aliases 仅用于召回候选，不代表身份相同。目前是人工消歧，不是自动语义匹配；不支持从全库任意搜索选择，也不保证召回所有别名。候选超过 20 个时显示截断提示。审核后目标属性变更会阻止提交并要求重新审核。

新实体 ID 由运行 ID 和候选实体 ID 稳定生成。SemanticaEntity、SemanticaFact、SemanticaPublication 各有 id 唯一约束。跨文档复用身份依赖审核时选择同一个已有节点；选择新建会保留独立实体，即使名称相同。既有节点使用 Neo4j elementId 定位并校验审核时的属性快照，不会覆盖其业务属性。

## 事务与恢复

一次发布的实体、事实、来源连接、审核记录和发布回执在一个 Neo4j 数据事务中提交。中途失败整体回滚。唯一约束作为数据库 schema 初始化单独执行，需要相应建约束权限。

运行 ID 确定唯一发布 ID。相同方案重试返回同一回执，已发布运行不能换方案再次提交；改用新运行保留修订来源。request_key 复用时请求体必须相同。并发提交通过唯一约束和发布节点写锁协调。

浏览器断线或本地保存失败时，点击“核对提交结果”从 Neo4j 恢复回执。重新打开发布入口也会先核对回执。SQLite 与 Neo4j 不构成分布式事务，远端回执是恢复依据。

## 图谱结构与查询

新关系保存为带来源的 SemanticaFact 事实节点，避免不同文档互相覆盖。结构为 publication → ASSERTS → fact，fact → SUBJECT → 主体，fact → OBJECT → 客体。publication 通过 MENTIONS 关联涉及的实体。

```cypher
MATCH (p:SemanticaPublication)-[:ASSERTS]->(f:SemanticaFact)
MATCH (f)-[:SUBJECT]->(s), (f)-[:OBJECT]->(o)
RETURN p.document_name AS document, s.name AS subject,
       f.relation_type AS predicate, o.name AS object,
       f.status AS status, f.evidence_json AS evidence
LIMIT 100
```

原有节点属性与关系保留；事实记录携带 document_id、证据、时间、数量和状态。不同运行的相同陈述保留各自来源，目前不做事实级跨文档去重或旧贡献替换。只查询实体间直接边的旧 Cypher 需要适配上述事实结构。

Pipeline 仍保留本地中间产物和审核记录。8014 的 Neo4j Explore 是加载时的快照，发布后须重新加载数据或重启该服务；当前不会自动推送新增事实到快照。

## API

- POST /api/pipeline-runs/{id}/neo4j-plan：candidate_revision，返回绑定候选版本和数据库的对齐方案。
- POST /api/pipeline-runs/{id}/neo4j-publish：candidate_revision、plan_hash、decisions（候选实体 ID 到 new 或候选 elementId）、reason、request_key。
- POST /api/pipeline-runs/{id}/neo4j-reconcile：恢复已提交回执。

创建运行时 publish_target=neo4j。即使请求 auto_if_clean，Neo4j 目标仍等待身份审核。试跑和存在质量问题的候选不可发布。已有本地发布的正式运行也可额外发布到 Neo4j。

## 隔离集成测试

tests/explorer/test_neo4j_publication.py 仅在 SEMANTICA_NEO4J_TEST=disposable 时连接专用 17690 测试端口，测试会清空该测试库，严禁将其改为业务库。覆盖真实事务回滚、并发幂等、身份复用、质量门禁和回执恢复。
