"""Load a bounded Neo4j snapshot into the existing Explorer session."""
import os
import json

from .session import GraphSession
from ..context.context_graph import ContextGraph


def connection_settings():
    def value(name, default=None):
        return os.environ.get('NEO4J_' + name) or os.environ.get('GRAPH_STORE_NEO4J_' + name) or default
    missing = [name for name in ('URI', 'PASSWORD') if not value(name)]
    if missing:
        raise RuntimeError('Missing Neo4j configuration: %s. Export these variables in this terminal '
                           'or start uvicorn with --env-file /path/to/.env. '
                           'GRAPH_STORE_NEO4J_* names are also accepted.' % ', '.join('NEO4J_' + name for name in missing))
    return {name.lower(): value(name, default) for name, default in
            [('URI', None), ('PASSWORD', None), ('USER', 'neo4j'), ('DATABASE', 'neo4j')]}


def load_session(driver, database, limit=1000):
    from neo4j import READ_ACCESS, unit_of_work

    if not 1 <= limit <= 5000:
        raise ValueError('NEO4J_EXPLORE_LIMIT must be between 1 and 5000')

    @unit_of_work(timeout=30)
    def read(tx):
        nodes = [dict(row) for row in tx.run(
            'MATCH (n) WHERE NOT n:SemanticaFact AND NOT n:SemanticaPublication '
            'RETURN elementId(n) AS id, labels(n) AS labels, '
            'properties(n) AS properties ORDER BY elementId(n) LIMIT $limit', limit=limit + 1)]
        truncated_nodes = len(nodes) > limit
        nodes = nodes[:limit]
        ids = [row['id'] for row in nodes]
        edges = [dict(row) for row in tx.run(
            'MATCH (a)-[r]->(b) WHERE elementId(a) IN $ids AND elementId(b) IN $ids '
            'RETURN elementId(r) AS id, elementId(a) AS source, elementId(b) AS target, '
            'type(r) AS type, properties(r) AS properties LIMIT $limit',
            ids=ids, limit=10001)]
        # Project provenance-backed assertions into ordinary business edges.
        remaining = max(0, 10001 - len(edges))
        if remaining:
            edges.extend(dict(row) for row in tx.run(
                'MATCH (f:SemanticaFact)-[:SUBJECT]->(a), (f)-[:OBJECT]->(b) '
                'WHERE elementId(a) IN $ids AND elementId(b) IN $ids '
                'RETURN elementId(f) AS id, elementId(a) AS source, elementId(b) AS target, '
                'f.relation_type AS type, {status:f.status} AS properties LIMIT $limit',
                ids=ids, limit=remaining))
        return nodes, edges[:10000], truncated_nodes, len(edges) > 10000

    with driver.session(database=database, default_access_mode=READ_ACCESS) as session:
        nodes, edges, truncated_nodes, truncated_edges = session.execute_read(read)
    graph = GraphSession(ContextGraph(advanced_analytics=False))
    ids = {n['id']: n['properties'].get('explorer_id', 'neo4j:' + n['id']) for n in nodes}
    graph.add_nodes_and_edges([
        json.loads(n['properties']['explorer_payload']) if 'explorer_payload' in n['properties'] else
        {'id': ids[n['id']], 'type': n['properties'].get('entity_type') or next(iter(n['labels']), 'entity'),
         'properties': {**{k: v for k, v in n['properties'].items()
                              if k not in ('id', 'entity_type', 'explorer_id', 'explorer_payload')},
                        'content': str(next((n['properties'][key]
             for key in ('name', 'title', 'label', 'content') if n['properties'].get(key)), n['id'])),
             }}
        for n in nodes
    ], [
        {**(json.loads(r['properties']['explorer_payload']) if 'explorer_payload' in r['properties'] else {}),
         'id': r['properties'].get('explorer_id', 'neo4j:' + r['id']), 'source_id': ids[r['source']],
         'target_id': ids[r['target']], 'type': r['type'],
         'properties': (json.loads(r['properties']['explorer_payload']).get('properties', {})
                        if 'explorer_payload' in r['properties'] else
                        r['properties'])}
        for r in edges
    ])
    return graph, {'source': 'neo4j', 'database': database, 'nodes': len(nodes), 'edges': len(edges),
                   'truncated_nodes': truncated_nodes, 'truncated_edges': truncated_edges,
                   'mode': 'snapshot', 'writeback': False}


def create_app():
    """Uvicorn factory; connection secrets stay in the server environment."""
    from neo4j import GraphDatabase
    from fastapi import Depends
    from .app import create_app as explorer_app
    from .dependencies import require_auth

    settings = connection_settings()
    with GraphDatabase.driver(settings['uri'], auth=(settings['user'], settings['password']),
                              connection_timeout=10, max_transaction_retry_time=5) as driver:
        driver.verify_connectivity()
        session, summary = load_session(driver, settings['database'],
                                        int(os.environ.get('NEO4J_EXPLORE_LIMIT', '1000')))
    app = explorer_app(session=session)
    from .neo4j_import import persist_import
    app.state.persist_graph_import = lambda nodes, edges: persist_import(settings, nodes, edges)
    if getattr(app.state, 'pipeline_service', None) is not None:
        app.state.pipeline_service.persist_graph_import = app.state.persist_graph_import
    summary['import_persistence'] = 'neo4j'

    def refresh():
        from .markdown_resources import MarkdownResourceRegistry
        from .runtime import install_mutation_bridge
        with GraphDatabase.driver(settings['uri'], auth=(settings['user'], settings['password'])) as driver:
            refreshed, current = load_session(driver, settings['database'],
                                              int(os.environ.get('NEO4J_EXPLORE_LIMIT', '1000')))
        app.state.session = refreshed
        app.state.markdown_resources = MarkdownResourceRegistry(refreshed.graph, getattr(app.state, 'agent_memory', None))
        install_mutation_bridge(app, refreshed)
        summary.update(current, import_persistence='neo4j')

    app.state.refresh_neo4j = refresh

    @app.get('/api/neo4j/source', dependencies=[Depends(require_auth)])
    def source():
        return summary

    # The application registers a SPA catch-all; API routes must precede it.
    app.router.routes.insert(0, app.router.routes.pop())

    return app
