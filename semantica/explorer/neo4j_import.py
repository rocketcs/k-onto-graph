"""Transactional persistence for Explorer JSON/CSV imports."""
import hashlib
import json


def persist_import(settings, nodes, edges):
    from neo4j import GraphDatabase

    def identifier(value):
        return '`' + str(value).replace('`', '``') + '`'

    def properties(value):
        # Preserve structured metadata losslessly; expose scalar fields to Cypher.
        return {k: v for k, v in value.items()
                if isinstance(v, (str, int, float, bool))}

    if any(not node.get('id') for node in nodes):
        raise ValueError('Every imported node requires an ID')
    with GraphDatabase.driver(settings['uri'], auth=(settings['user'], settings['password'])) as driver:
        with driver.session(database=settings['database']) as database:
            database.run('CREATE CONSTRAINT explorer_import_id IF NOT EXISTS '
                         'FOR (n:ExplorerImport) REQUIRE n.explorer_id IS UNIQUE').consume()

            def write(tx):
                for node in nodes:
                    label = identifier(node.get('type') or 'entity')
                    props = properties(node.get('properties') or {})
                    props.update(explorer_id=node['id'], explorer_payload=json.dumps(node, ensure_ascii=False))
                    tx.run('MERGE (n:ExplorerImport {explorer_id:$id}) '
                           f'SET n:{label}, n += $props', id=node['id'], props=props).consume()
                for edge in edges:
                    payload = json.dumps(edge, sort_keys=True, ensure_ascii=False)
                    edge_id = str(edge.get('id') or hashlib.sha256(payload.encode()).hexdigest())
                    relation = identifier(edge.get('type') or 'related_to')
                    props = properties(edge.get('properties') or {})
                    props.update(explorer_payload=payload)
                    source, target = edge['source_id'], edge['target_id']
                    result = tx.run(
                        'MATCH (a), (b) WHERE '
                        '(a.explorer_id=$source OR elementId(a)=$source_native) AND '
                        '(b.explorer_id=$target OR elementId(b)=$target_native) '
                        f'MERGE (a)-[r:{relation} {{explorer_id:$id}}]->(b) '
                        'SET r += $props RETURN elementId(r) AS id',
                        source=source, target=target,
                        source_native=source[6:] if source.startswith('neo4j:') else '',
                        target_native=target[6:] if target.startswith('neo4j:') else '',
                        id=edge_id, props=props).single()
                    if result is None:
                        raise ValueError('Relationship endpoint is missing from Neo4j')
            database.execute_write(write)
