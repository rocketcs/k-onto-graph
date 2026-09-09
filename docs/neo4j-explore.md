# Neo4j 数据在 Explore 中展示

入口：`semantica.explorer.neo4j_source:create_app`。
需要 Neo4j 5+（使用 elementId）及 Python neo4j 驱动。

服务端环境变量：

- `NEO4J_URI`：实例连接地址。
- `NEO4J_USER`：用户名，默认 neo4j。
- `NEO4J_PASSWORD`：密码。
- `NEO4J_DATABASE`：数据库，默认 neo4j。
- `NEO4J_EXPLORE_LIMIT`：加载节点上限，默认 1000，最大 5000。

配置好上述连接变量后，从仓库根目录启动独立本地页面：

```sh
ALLOWED_ORIGINS=http://127.0.0.1:8014 \
SEMANTICA_ALLOW_ANONYMOUS=true \
.venv/bin/python -m uvicorn semantica.explorer.neo4j_source:create_app \
  --factory --host 127.0.0.1 --port 8014
```

进入 http://127.0.0.1:8014，点击 Knowledge Explorer。
`GET /api/neo4j/source` 返回加载数量和截断标记。

该入口启动时执行固定的只读 Cypher，加载前 N 个节点及它们之间最多 10000 条关系；事务超时 30 秒。大图展示的是子集，不代表全库。连接关闭后，Explore 使用内存快照进行搜索、邻域和图谱浏览；重启该入口才会重新读取 Neo4j。页面编辑不会回写数据库。

本入口没有任意 Cypher 控制台、实时数据库搜索或 Pipeline 写入功能。建议使用数据库只读账号。当前代码的自动化测试验证读取配置和图谱映射，真实连接需要实际实例配置。
