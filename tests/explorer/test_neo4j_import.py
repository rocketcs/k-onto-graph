from types import SimpleNamespace
import os
import json
import uuid

import pytest

from semantica.context.context_graph import ContextGraph
from semantica.explorer.routes.export_import import _store_import
from semantica.explorer.session import GraphSession


def test_failed_database_write_does_not_update_memory():
    session = GraphSession(ContextGraph(advanced_analytics=False))

    def fail(nodes, edges):
        raise RuntimeError('database unavailable')

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(persist_graph_import=fail)))
    with pytest.raises(RuntimeError, match='database unavailable'):
        _store_import(request, session, [{'id': 'a', 'type': 'entity', 'properties': {}}], [])
    assert session.get_node('a') is None


def test_import_updates_memory_only_after_persistence():
    session = GraphSession(ContextGraph(advanced_analytics=False))
    writes = []

    def persist(nodes, edges):
        assert session.get_node('a') is None
        writes.append((nodes, edges))

    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(persist_graph_import=persist)))
    assert _store_import(request, session, [{'id': 'a', 'type': 'entity', 'properties': {}}], []) == (1, 0)
    assert len(writes) == 1
    assert session.get_node('a') is not None


@pytest.mark.skipif(os.getenv('NEO4J_IMPORT_LIVE') != 'true', reason='Requires local Neo4j and Explorer')
def test_live_import_is_durable_idempotent_and_atomic():
    import httpx
    from neo4j import GraphDatabase
    from semantica.explorer.neo4j_source import connection_settings, load_session

    settings = connection_settings()
    prefix = 'import-check-' + uuid.uuid4().hex
    ids = [prefix + suffix for suffix in ('-a', '-b', '-rollback')]
    data = {'nodes': [{'id': node_id, 'type': 'ImportCheck',
                       'properties': {'content': node_id, 'nested': {'test': True}}}
                      for node_id in ids[:2]],
            'edges': [{'id': prefix + '-edge', 'source': ids[0], 'target': ids[1],
                       'type': 'CHECK', 'properties': {'nested': {'score': 1}}}]}
    with GraphDatabase.driver(settings['uri'], auth=(settings['user'], settings['password'])) as driver:
        with driver.session(database=settings['database']) as db, httpx.Client(trust_env=False) as client:
            try:
                for _ in range(2):
                    response = client.post('http://127.0.0.1:8000/api/import',
                                           files={'file': ('check.json', json.dumps(data), 'application/json')})
                    assert response.status_code == 200, response.text
                assert db.run('MATCH (n:ExplorerImport) WHERE n.explorer_id IN $ids RETURN count(n) AS count', ids=ids).single()['count'] == 2
                assert db.run('MATCH ()-[r {explorer_id:$id}]->() RETURN count(r) AS count', id=prefix + '-edge').single()['count'] == 1
                snapshot, _ = load_session(driver, settings['database'])
                assert snapshot.get_node(ids[0])['properties']['nested'] == {'test': True}
                edge = next(e for e in snapshot.graph.edges if e.source_id == ids[0])
                assert edge.metadata['nested'] == {'score': 1}
                invalid = {'nodes': [{'id': ids[2], 'type': 'ImportCheck'}],
                           'edges': [{'source': ids[2], 'target': prefix + '-missing'}]}
                response = client.post('http://127.0.0.1:8000/api/import',
                                       files={'file': ('bad.json', json.dumps(invalid), 'application/json')})
                assert response.status_code == 422, response.text
                assert db.run('MATCH (n:ExplorerImport {explorer_id:$id}) RETURN count(n) AS count', id=ids[2]).single()['count'] == 0
            finally:
                db.run('MATCH (n:ExplorerImport) WHERE n.explorer_id IN $ids DETACH DELETE n', ids=ids).consume()
