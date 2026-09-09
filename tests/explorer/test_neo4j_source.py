from contextlib import contextmanager

from semantica.explorer.neo4j_source import load_session


def test_connection_environment_aliases(monkeypatch):
    import pytest
    from semantica.explorer.neo4j_source import connection_settings
    for prefix in ('NEO4J_', 'GRAPH_STORE_NEO4J_'):
        for field in ('URI', 'PASSWORD', 'USER', 'DATABASE'):
            monkeypatch.delenv(prefix + field, raising=False)
    with pytest.raises(RuntimeError, match='--env-file'):
        connection_settings()
    monkeypatch.setenv('GRAPH_STORE_NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('GRAPH_STORE_NEO4J_PASSWORD', 'test-secret')
    assert connection_settings()['user'] == 'neo4j'
    monkeypatch.setenv('NEO4J_DATABASE', 'medical')
    assert connection_settings()['database'] == 'medical'


def test_neo4j_snapshot_keeps_identity_and_maps_labels():
    class Transaction:
        def run(self, query, **parameters):
            if 'MATCH (f:SemanticaFact)' in query:
                return []
            if 'MATCH (n)' in query:
                assert 'NOT n:SemanticaFact AND NOT n:SemanticaPublication' in query
                return [{'id': 'a', 'labels': ['疾病'], 'properties': {'name': '糖尿病'}},
                        {'id': 'b', 'labels': ['食物'], 'properties': {'name': '燕麦'}},
                        {'id': 'c', 'labels': [], 'properties': {}}]
            assert parameters['ids'] == ['a', 'b']
            return [{'id': 'r1', 'source': 'a', 'target': 'b', 'type': '营养建议', 'properties': {}}]

    class Session:
        def execute_read(self, action):
            assert action.timeout == 30
            return action(Transaction())

    class Driver:
        @contextmanager
        def session(self, **options):
            assert options['default_access_mode'] == 'READ'
            assert options['database'] == 'medical'
            yield Session()

    graph, summary = load_session(Driver(), 'medical', limit=2)
    assert summary['truncated_nodes'] is True
    assert summary['nodes'] == 2 and summary['edges'] == 1
    assert graph.get_node('neo4j:a')['content'] == '糖尿病'
    assert graph.graph.edges[0].source_id == 'neo4j:a'


def test_pipeline_facts_project_to_business_edges():
    class Transaction:
        def run(self, query, **parameters):
            if 'MATCH (n)' in query:
                return [{'id': 'a', 'labels': ['SemanticaEntity'], 'properties': {'name': '循上医疗', 'entity_type': '机构'}},
                        {'id': 'b', 'labels': ['SemanticaEntity'], 'properties': {'name': '卫星诊所', 'entity_type': '设施类型'}}]
            if 'MATCH (f:SemanticaFact)' in query:
                assert parameters['ids'] == ['a', 'b']
                return [{'id': 'fact', 'source': 'a', 'target': 'b', 'type': '规划建设', 'properties': {'status': '规划'}}]
            return []

    class Session:
        def execute_read(self, action):
            return action(Transaction())

    class Driver:
        @contextmanager
        def session(self, **options):
            yield Session()

    graph, summary = load_session(Driver(), 'neo4j')
    assert (summary['nodes'], summary['edges']) == (2, 1)
    assert graph.get_node('neo4j:a')['type'] == '机构'
    assert graph.get_node('neo4j:a')['content'] == '循上医疗'
    assert graph.graph.edges[0].edge_type == '规划建设'
    assert 'evidence_json' not in graph.graph.edges[0].metadata
