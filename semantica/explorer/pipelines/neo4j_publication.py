"""Reviewed identity links and atomic, replayable Neo4j publications."""
import json
import os
from urllib.parse import urlsplit

from .repository import Conflict, digest


def driver_settings():
    from ..neo4j_source import connection_settings
    from neo4j import GraphDatabase
    try:
        settings = connection_settings()
    except RuntimeError as error:
        raise ValueError('Neo4j 发布未配置，请在服务端配置连接') from error
    return GraphDatabase.driver(settings['uri'], auth=(settings['user'], settings['password']),
                                connection_timeout=10, max_transaction_retry_time=5), settings['database']


def target_key(database):
    uri = os.getenv('NEO4J_URI') or os.getenv('GRAPH_STORE_NEO4J_URI')
    return digest([uri, database])


def candidate(service, identity, revision):
    run = service.repo.get('run', identity)
    if run['purpose'] == 'preview' or run['status'] not in ('awaiting_review', 'completed'):
        raise Conflict('运行尚未生成可发布的正式候选')
    if revision != run['candidate_revision']:
        raise Conflict('候选已修改，请重新生成对齐方案')
    from .handlers import validate_candidate
    data = service.candidate(identity)
    result = validate_candidate(data['candidate'], data['document'], run['snapshots']['extraction']['body'], run['snapshots']['rules']['body'])
    if result['issues']:
        raise Conflict('请先解决全部质量问题，再发布 Neo4j')
    return run, result


def plan(service, identity, payload):
    from neo4j import READ_ACCESS, Query
    with service.repo.lock:
        run, result = candidate(service, identity, payload['candidate_revision'])
        driver, database = driver_settings()
        with driver:
            with driver.session(database=database, default_access_mode=READ_ACCESS) as session:
                entities = []
                for entity in result['entities']:
                    if entity['id'] in result['excluded']:
                        continue
                    matches = session.run(Query(
                        'MATCH (n) WHERE NOT n:SemanticaFact AND NOT n:SemanticaPublication '
                        'AND (n.name IN $names OR n.canonical_name IN $names OR any(alias IN coalesce(n.aliases, []) WHERE alias IN $names)) '
                        'RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS properties ORDER BY elementId(n) LIMIT 21', timeout=10),
                        names=list({entity['name'], entity['canonical_name']})).data()
                    matches = json.loads(json.dumps(matches, default=str))
                    entities.append({'id': entity['id'], 'name': entity['name'], 'type': entity['type'],
                                     'matches': matches[:20], 'truncated': len(matches) > 20})
        endpoint = urlsplit(os.getenv('NEO4J_URI') or os.getenv('GRAPH_STORE_NEO4J_URI') or '')
        value = {'run_id': identity, 'candidate_revision': run['candidate_revision'],
                 'database': database, 'endpoint': '%s:%s' % (endpoint.hostname, endpoint.port or 7687),
                 'candidate_hash': digest(result), 'target': target_key(database), 'entities': entities}
        value['hash'] = digest(value)
        with service.repo.transaction():
            service.repo.put('neo4j_plan', value['hash'], value)
        return value


def publish(service, identity, payload):
    def action():
        from neo4j import unit_of_work
        run = service.repo.get('run', identity)
        proposal = service.repo.get('neo4j_plan', payload['plan_hash'])
        if proposal['run_id'] != identity or proposal['candidate_revision'] != payload['candidate_revision']:
            raise Conflict('对齐方案已过期')
        decisions = payload.get('decisions', {})
        if set(decisions) != {e['id'] for e in proposal['entities']} or not str(payload.get('reason', '')).strip():
            raise Conflict('请为每个实体确认对齐方式并填写审核原因')
        for entity in proposal['entities']:
            if decisions[entity['id']] != 'new' and decisions[entity['id']] not in {m['id'] for m in entity['matches']}:
                raise Conflict('对齐目标不在候选范围内')
        fingerprint = digest([proposal['hash'], decisions, payload['reason']])
        publication_id = digest(['semantica-publication', identity])
        def record_receipt(receipt):
            run['neo4j_publication'] = receipt
            run['status'] = 'completed'
            service.repo.event(run, 'neo4j.published', publication=receipt)
            return receipt
        driver, database = driver_settings()
        if proposal['target'] != target_key(database):
            driver.close()
            raise Conflict('Neo4j 连接目标已改变，请重新生成对齐方案')
        with driver:
            with driver.session(database=database) as session:
                prior = session.run('MATCH (p:SemanticaPublication {id:$id}) '
                                    'RETURN p.fingerprint AS fingerprint, p.receipt AS receipt', id=publication_id).single()
                if prior:
                    if prior['fingerprint'] != fingerprint:
                        raise Conflict('此运行已按另一方案发布；请创建新的运行')
                    if prior['receipt']:
                        return record_receipt(json.loads(prior['receipt']))
                run, result = candidate(service, identity, payload['candidate_revision'])
                if proposal['candidate_hash'] != digest(result):
                    raise Conflict('对齐方案已过期')
                # Schema setup is separate from the all-or-nothing data transaction.
                for label in ('SemanticaPublication', 'SemanticaEntity', 'SemanticaFact'):
                    session.run('CREATE CONSTRAINT %s_id IF NOT EXISTS FOR (n:%s) REQUIRE n.id IS UNIQUE' % (label, label)).consume()

                @unit_of_work(timeout=60)
                def write(tx):
                    marker = tx.run('MERGE (p:SemanticaPublication {id:$id}) '
                                    'ON CREATE SET p.fingerprint=$fingerprint '
                                    'SET p.lock_version=coalesce(p.lock_version,0)+1 '
                                    'RETURN p.fingerprint AS fingerprint, p.receipt AS receipt',
                                    id=publication_id, fingerprint=fingerprint).single()
                    if marker['fingerprint'] != fingerprint:
                        raise Conflict('此运行已按另一方案发布；请创建新的运行')
                    if marker['receipt']:
                        return json.loads(marker['receipt'])
                    names = {}
                    for entity in proposal['entities']:
                        target = decisions[entity['id']]
                        if target == 'new':
                            stable = digest([identity, entity['id']])
                            target = tx.run('MERGE (n:SemanticaEntity {id:$id}) '
                                            'ON CREATE SET n.name=$name, n.entity_type=$type '
                                            'RETURN elementId(n) AS id', id=stable, name=entity['name'], type=entity['type']).single()['id']
                        else:
                            expected = next(m for m in entity['matches'] if m['id'] == target)
                            current = tx.run('MATCH (n) WHERE elementId(n)=$id '
                                             'SET n=properties(n) RETURN labels(n) AS labels, properties(n) AS properties', id=target).single()
                            if not current or digest(json.loads(json.dumps(dict(current), default=str))) != digest({'labels': expected['labels'], 'properties': expected['properties']}):
                                raise Conflict('目标实体已变更或删除，请重新审核对齐')
                        names[entity['name']] = target
                        tx.run('MATCH (p:SemanticaPublication {id:$pub}), (n) WHERE elementId(n)=$node '
                               'MERGE (p)-[:MENTIONS]->(n)', pub=publication_id, node=target).consume()
                    count = 0
                    for relation in result['relationships']:
                        if relation['id'] in result['excluded']:
                            continue
                        tx.run('MATCH (p:SemanticaPublication {id:$pub}), (a), (b) '
                               'WHERE elementId(a)=$source AND elementId(b)=$target '
                               'MERGE (f:SemanticaFact {id:$id}) '
                               'SET f.relation_type=$type, f.status=$status, f.evidence_json=$evidence, '
                               'f.quantity_json=$quantity, f.time_json=$time, f.document_id=$document '
                               'MERGE (p)-[:ASSERTS]->(f) MERGE (f)-[:SUBJECT]->(a) MERGE (f)-[:OBJECT]->(b)',
                               pub=publication_id, source=names[relation['source']], target=names[relation['target']],
                               id=digest([publication_id, relation['id']]), type=relation['type'], status=relation['status'],
                               evidence=json.dumps(relation['evidence'], ensure_ascii=False),
                               quantity=json.dumps(relation['quantity']), time=json.dumps(relation['time']), document=run['document_id']).consume()
                        count += 1
                    receipt = {'id': publication_id, 'mode': 'neo4j', 'database': database,
                               'nodes': len(names), 'facts': count, 'candidate_revision': run['candidate_revision']}
                    tx.run('MATCH (p:SemanticaPublication {id:$id}) SET p.receipt=$receipt, '
                           'p.document_id=$document, p.document_name=$name, p.run_id=$run, '
                           'p.review_json=$review, p.candidate_revision=$revision',
                           id=publication_id, receipt=json.dumps(receipt), document=run['document_id'], name=run['document_name'],
                           run=identity, review=json.dumps({'decisions': decisions, 'reason': payload['reason']}, ensure_ascii=False),
                           revision=run['candidate_revision']).consume()
                    return receipt
                receipt = session.execute_write(write)
        return record_receipt(receipt)
    return service.repo.once('neo4j-publish:' + identity, payload['request_key'], payload, action)


def reconcile(service, identity):
    """Recover the remote receipt after a lost response or local commit failure."""
    from neo4j import READ_ACCESS, Query
    with service.repo.transaction():
        run = service.repo.get('run', identity)
        driver, database = driver_settings()
        with driver, driver.session(database=database, default_access_mode=READ_ACCESS) as session:
            prior = session.run(Query('MATCH (p:SemanticaPublication {id:$id}) '
                                      'RETURN p.receipt AS receipt', timeout=10),
                                id=digest(['semantica-publication', identity])).single()
        if not prior or not prior['receipt']:
            return {'published': False}
        receipt = json.loads(prior['receipt'])
        if run.get('neo4j_publication') != receipt:
            run['neo4j_publication'] = receipt
            run['status'] = 'completed'
            service.repo.event(run, 'neo4j.reconciled', publication=receipt)
        return {'published': True, 'publication': receipt}
