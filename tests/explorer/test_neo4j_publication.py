"""Opt-in integration tests against an isolated, disposable Neo4j database."""
import copy
import os

import pytest

from semantica.explorer.pipelines import neo4j_publication as publication
from semantica.explorer.pipelines.definitions import EXTRACTION, RULES
from semantica.explorer.pipelines.handlers import normalize, validate_candidate
from semantica.explorer.pipelines.repository import Conflict
from semantica.explorer.pipelines.service import PipelineService


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    if os.getenv('SEMANTICA_NEO4J_TEST') != 'disposable':
        pytest.skip('Set SEMANTICA_NEO4J_TEST=disposable for isolated Neo4j integration tests')
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver('bolt://127.0.0.1:17690', auth=('neo4j', 'pipeline-test-only'))
    driver.verify_connectivity()
    monkeypatch.setenv('NEO4J_URI', 'bolt://127.0.0.1:17690')
    monkeypatch.setenv('NEO4J_DATABASE', 'neo4j')
    monkeypatch.setattr(publication, 'driver_settings', lambda: (
        GraphDatabase.driver('bolt://127.0.0.1:17690', auth=('neo4j', 'pipeline-test-only')), 'neo4j'))
    with driver.session() as session:
        session.run('MATCH (n) DETACH DELETE n').consume()
    svc = PipelineService(tmp_path, model_call=lambda *args: None)
    def make_run(identity='run-one'):
        document = {'segments': [{'id': 'p1', 'text': '甲医院与乙学院合作。'}]}
        raw = {'entities': [{'name': '甲医院', 'type': '机构'}, {'name': '乙学院', 'type': '机构'}],
               'relationships': [{'source': '甲医院', 'target': '乙学院', 'type': '合作',
                                  'status': '文档陈述', 'segment_ids': ['p1']}]}
        result = validate_candidate(normalize([raw], RULES), document, EXTRACTION, RULES)
        run = {'id': identity, 'purpose': 'production', 'status': 'awaiting_review', 'candidate_revision': 1,
               'document_id': 'doc-' + identity, 'document_name': 'test.txt', 'last_event_seq': 0,
               'snapshots': {'extraction': {'body': EXTRACTION}, 'rules': {'body': RULES}},
               'candidate': svc.repo.artifact({'document': document, 'candidate': result})}
        with svc.repo.transaction():
            svc.repo.put('run', identity, run)
        return run
    make_run()
    yield svc, driver, make_run
    svc.close()
    driver.close()


def proposal(svc, run_id='run-one'):
    plan = publication.plan(svc, run_id, {'candidate_revision': 1})
    return plan, {'candidate_revision': 1, 'plan_hash': plan['hash'],
                  'decisions': {e['id']: 'new' for e in plan['entities']}, 'reason': '核对原文与身份',
                  'request_key': 'publish-' + run_id}


def counts(driver):
    with driver.session() as session:
        return session.run('MATCH (n) RETURN count(n) AS count').single()['count']


def test_publish_replay_and_cross_document_alignment(fixture):
    svc, driver, make_run = fixture
    plan, body = proposal(svc)
    assert all(not e['matches'] for e in plan['entities'])
    first = publication.publish(svc, 'run-one', body)
    assert first['nodes'] == 2 and first['facts'] == 1
    before = counts(driver)
    assert publication.publish(svc, 'run-one', body) == first
    assert publication.publish(svc, 'run-one', {**body, 'request_key': 'another-replay'}) == first
    assert counts(driver) == before == 4
    make_run('run-two')
    plan2, body2 = proposal(svc, 'run-two')
    assert all(len(e['matches']) == 1 for e in plan2['entities'])
    body2['decisions'] = {e['id']: e['matches'][0]['id'] for e in plan2['entities']}
    publication.publish(svc, 'run-two', body2)
    with driver.session() as session:
        assert session.run('MATCH (n:SemanticaEntity) RETURN count(n) AS count').single()['count'] == 2
        assert session.run('MATCH (f:SemanticaFact) RETURN count(f) AS count').single()['count'] == 2
        assert session.run('MATCH (p:SemanticaPublication) RETURN count(p) AS count').single()['count'] == 2


def test_same_name_requires_explicit_decision_and_preserves_existing_data(fixture):
    svc, driver, _ = fixture
    with driver.session() as session:
        session.run('CREATE (:Hospital {name:"甲医院", protected:"original"}), (:Company {name:"甲医院"})').consume()
    plan, body = proposal(svc)
    entity = next(e for e in plan['entities'] if e['name'] == '甲医院')
    assert len(entity['matches']) == 2
    with pytest.raises(Conflict):
        publication.publish(svc, 'run-one', {**body, 'decisions': {}})
    match = next(m for m in entity['matches'] if m['labels'] == ['Hospital'])
    body['decisions'][entity['id']] = match['id']
    publication.publish(svc, 'run-one', body)
    with driver.session() as session:
        assert session.run('MATCH (n:Hospital) RETURN properties(n) AS p').single()['p'] == {'name': '甲医院', 'protected': 'original'}


def test_target_changed_rolls_back_entire_publication(fixture):
    svc, driver, _ = fixture
    with driver.session() as session:
        session.run('CREATE (:Hospital {name:"乙学院"})').consume()
    plan, body = proposal(svc)
    entity = next(e for e in plan['entities'] if e['name'] == '乙学院')
    body['decisions'][entity['id']] = entity['matches'][0]['id']
    with driver.session() as session:
        session.run('MATCH (n:Hospital) SET n.changed=true').consume()
    with pytest.raises(Conflict):
        publication.publish(svc, 'run-one', body)
    assert counts(driver) == 1


def test_quality_gate_and_revision_gate_before_writes(fixture):
    svc, driver, _ = fixture
    plan, body = proposal(svc)
    run = svc.repo.get('run', 'run-one')
    data = svc.candidate('run-one')
    data['candidate']['relationships'][0]['segment_ids'] = ['missing']
    run['candidate'] = svc.repo.artifact(data)
    with svc.repo.transaction():
        svc.repo.put('run', run['id'], run)
    with pytest.raises(Conflict, match='质量'):
        publication.publish(svc, run['id'], body)
    assert counts(driver) == 0


def test_remote_commit_local_failure_retry_recovers_receipt(fixture, monkeypatch):
    svc, driver, _ = fixture
    _, body = proposal(svc)
    event = svc.repo.event
    def fail(*args, **kwargs):
        raise OSError('injected local write failure after Neo4j commit')
    monkeypatch.setattr(svc.repo, 'event', fail)
    with pytest.raises(OSError):
        publication.publish(svc, 'run-one', body)
    assert counts(driver) == 4
    monkeypatch.setattr(svc.repo, 'event', event)
    publication.publish(svc, 'run-one', body)
    assert counts(driver) == 4
    assert svc.repo.get('run', 'run-one')['neo4j_publication']
    assert publication.reconcile(svc, 'run-one')['published'] is True


def test_conflicting_retry_does_not_duplicate(fixture):
    svc, driver, _ = fixture
    _, body = proposal(svc)
    publication.publish(svc, 'run-one', body)
    with pytest.raises(Conflict):
        publication.publish(svc, 'run-one', {**body, 'reason': 'different'})
    with pytest.raises(Conflict):
        publication.publish(svc, 'run-one', {**body, 'reason': 'different', 'request_key': 'different-key'})
    assert counts(driver) == 4


def test_failure_after_fact_writes_rolls_back_nodes_and_relationships(fixture, monkeypatch):
    svc, driver, _ = fixture
    _, body = proposal(svc)
    original_factory = publication.driver_settings
    class SessionProxy:
        def __init__(self, session):
            self.session = session
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.session.close()
        def run(self, *args, **kwargs):
            return self.session.run(*args, **kwargs)
        def execute_write(self, action):
            def wrapped(tx):
                class TransactionProxy:
                    def run(self, query, **parameters):
                        if 'SET p.receipt=' in query:
                            raise RuntimeError('injected failure before commit')
                        return tx.run(query, **parameters)
                return action(TransactionProxy())
            return self.session.execute_write(wrapped)
    class DriverProxy:
        def __init__(self, actual):
            self.actual = actual
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.actual.close()
        def session(self, **kwargs):
            return SessionProxy(self.actual.session(**kwargs))
    monkeypatch.setattr(publication, 'driver_settings', lambda: (DriverProxy(original_factory()[0]), 'neo4j'))
    with pytest.raises(RuntimeError, match='injected failure'):
        publication.publish(svc, 'run-one', body)
    assert counts(driver) == 0
    with driver.session() as session:
        assert session.run('MATCH ()-[r]->() RETURN count(r) AS count').single()['count'] == 0
    monkeypatch.setattr(publication, 'driver_settings', original_factory)
    assert publication.publish(svc, 'run-one', body)['facts'] == 1


def test_concurrent_publishers_share_one_remote_receipt(fixture, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    svc, driver, _ = fixture
    plan, body = proposal(svc)
    second = PipelineService(tmp_path / 'second', model_call=lambda *args: None)
    run = copy.deepcopy(svc.repo.get('run', 'run-one'))
    run['candidate'] = second.repo.artifact(svc.candidate('run-one'))
    with second.repo.transaction():
        second.repo.put('run', 'run-one', run)
        second.repo.put('neo4j_plan', plan['hash'], plan)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            receipts = list(pool.map(lambda service: publication.publish(service, 'run-one', body), [svc, second]))
        assert receipts[0] == receipts[1]
        assert counts(driver) == 4
    finally:
        second.close()


def test_preview_and_missing_reason_cannot_publish(fixture):
    svc, driver, _ = fixture
    _, body = proposal(svc)
    with pytest.raises(Conflict):
        publication.publish(svc, 'run-one', {**body, 'reason': ''})
    run = svc.repo.get('run', 'run-one')
    run['purpose'] = 'preview'
    with svc.repo.transaction():
        svc.repo.put('run', run['id'], run)
    with pytest.raises(Conflict):
        publication.publish(svc, 'run-one', body)
    assert counts(driver) == 0


def test_receipt_recovery_after_review_revision_changes(fixture, monkeypatch):
    svc, driver, _ = fixture
    _, body = proposal(svc)
    event = svc.repo.event
    monkeypatch.setattr(svc.repo, 'event', lambda *args, **kwargs: (_ for _ in ()).throw(OSError('local failure')))
    with pytest.raises(OSError):
        publication.publish(svc, 'run-one', body)
    monkeypatch.setattr(svc.repo, 'event', event)
    run = svc.repo.get('run', 'run-one')
    run['candidate_revision'] = 2
    with svc.repo.transaction():
        svc.repo.put('run', run['id'], run)
    receipt = publication.reconcile(svc, run['id'])
    assert receipt['publication']['candidate_revision'] == 1
    assert svc.repo.get('run', run['id'])['candidate_revision'] == 2
    assert counts(driver) == 4
