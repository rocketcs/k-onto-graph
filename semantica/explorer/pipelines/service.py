"""Persistent single-worker workflow service; candidates never mutate the live graph."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import threading
import time
from pathlib import Path
import hashlib

from .definitions import LABELS, SEEDS, STEPS, validate_definition
from .handlers import chunk_document, model_extract, normalize, parse_document, validate_candidate
from .repository import Conflict, Repository, digest, uid

TERMINAL = {'completed', 'preview_completed', 'failed', 'cancelled', 'interrupted'}


class Cancelled(Exception):
    pass


class PipelineService:
    def __init__(self, root, model_call=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        # The publication and live-session contract is deliberately single-process.
        import fcntl
        self.owner = (self.root / 'owner.lock').open('a+')
        try:
            fcntl.flock(self.owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.owner.close()
            raise RuntimeError('Pipeline data directory is owned by another server process')
        self.repo = Repository(root)
        self.model_call = model_call
        self.processor_version = hashlib.sha256(Path(__file__).read_bytes() + Path(__file__).with_name('handlers.py').read_bytes() + Path(__file__).with_name('xlsx_document.py').read_bytes()).hexdigest()
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.activation_lock = threading.RLock()
        with self.repo.transaction():
            for kind, name, body in SEEDS:
                identity = 'default-' + kind
                try:
                    self.repo.get('definition', identity)
                except KeyError:
                    definition = {'id': identity, 'kind': kind, 'name': name, 'revision': 1, 'body': body}
                    self.repo.put('definition', identity, definition)
                    self._version(definition)
            for run in self.repo.all('run'):
                if run['status'] in ('running', 'cancel_requested', 'publishing'):
                    if run.get('publication'):
                        run['status'] = 'completed'
                    else:
                        run['status'] = 'interrupted'
                        for step in run['steps']:
                            if step['status'] in ('running', 'pending', 'retrying'):
                                step['status'] = 'blocked'
                    self.repo.event(run, 'run.recovered', status=run['status'])
        self.thread = threading.Thread(target=self._loop, name='semantica-pipeline', daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        self.wake.set()
        self.thread.join(timeout=130)
        if self.thread.is_alive():
            raise RuntimeError('Pipeline worker did not finish its bounded request')
        self.repo.close()
        self.owner.close()

    def capabilities(self):
        ready = bool(os.getenv('DEEPSEEK_API_KEY')) or self.model_call is not None
        formats = ['.docx', '.txt', '.md']
        if importlib.util.find_spec('openpyxl'):
            formats.append('.xlsx')
        if importlib.util.find_spec('pypdf'):
            formats.append('.pdf')
        return {'formats': formats, 'max_bytes': 20 * 1024 * 1024, 'steps': LABELS,
                'models': [{'id': 'deepseek', 'model': os.getenv('SEMANTICA_PIPELINE_MODEL', 'deepseek-v4-flash'), 'available': ready}],
                'publication_mode': 'new_managed_graph', 'dag': False, 'ocr': False, 'max_active': 1}

    def upload(self, name, data, key):
        suffix = Path(name).suffix.lower()
        if suffix not in self.capabilities()['formats']:
            raise ValueError('Unsupported document format')
        if not data or len(data) > self.capabilities()['max_bytes']:
            raise ValueError('Empty document or document exceeds 20 MiB')
        if suffix in ('.docx', '.xlsx') and not data.startswith(b'PK'):
            raise ValueError('Invalid document ZIP container')
        if suffix == '.pdf' and not data.startswith(b'%PDF-'):
            raise ValueError('Invalid PDF signature')
        if suffix in ('.txt', '.md'):
            data.decode('utf-8-sig')
        artifact = self.repo.blob(data, suffix)
        def action():
            doc = {'id': uid(), 'name': Path(name).name, 'artifact': artifact, 'sha256': artifact.split('.')[0],
                   'size': len(data), 'created_at': time.time()}
            self.repo.put('document', doc['id'], doc)
            return doc
        return self.repo.once('upload', key, {'name': name, 'artifact': artifact}, action)

    def _version(self, definition):
        version = {'id': uid(), 'definition_id': definition['id'], 'kind': definition['kind'], 'name': definition['name'],
                   'body': copy.deepcopy(definition['body']), 'revision': definition['revision'], 'created_at': time.time()}
        version['hash'] = digest(version['body'])
        self.repo.put('version', version['id'], version)
        return version

    def definitions(self):
        return [{**d, 'versions': [v for v in self.repo.all('version') if v['definition_id'] == d['id']]}
                for d in self.repo.all('definition')]

    def save_definition(self, identity, payload):
        with self.repo.transaction():
            definition = self.repo.get('definition', identity)
            if payload['expected_revision'] != definition['revision']:
                raise Conflict('Draft has changed; reload before saving')
            definition['body'] = validate_definition(definition['kind'], payload['body'])
            definition['revision'] += 1
            self.repo.put('definition', identity, definition)
            return definition

    def create_definition(self, payload):
        def action():
            definition = {'id': uid(), 'kind': payload['kind'], 'name': str(payload['name'])[:120], 'revision': 1,
                          'body': validate_definition(payload['kind'], payload['body'])}
            self.repo.put('definition', definition['id'], definition)
            return definition
        return self.repo.once('definition', payload['request_key'], payload, action)

    def publish_definition(self, identity, payload):
        def action():
            definition = self.repo.get('definition', identity)
            if definition['revision'] != payload['expected_revision']:
                raise Conflict('Draft revision changed')
            validate_definition(definition['kind'], definition['body'])
            return self._version(definition)
        return self.repo.once('version:' + identity, payload['request_key'], payload, action)

    def _snapshots(self, payload, preview=False):
        if payload.get('disable_templates'):
            return {
                'flow': {'id': 'builtin:flow', 'kind': 'flow', 'name': 'Unrestricted import', 'revision': 0,
                         'body': {'steps': ['parse', 'split', 'extract', 'normalize', 'validate', 'store'], 'chunk_size': 4000, 'overlap': 200}, 'hash': 'builtin'},
                'extraction': {'id': 'builtin:extraction', 'kind': 'extraction', 'name': 'Unrestricted extraction', 'revision': 0, 'body': {}, 'hash': 'builtin'},
                'rules': {'id': 'builtin:rules', 'kind': 'rules', 'name': 'No validation rules', 'revision': 0, 'body': {'rules': []}, 'hash': 'builtin'},
            }
        snapshots = {}
        for kind in ('flow', 'extraction', 'rules'):
            reference = payload.get(kind + '_version_id')
            if not reference:
                available = [v for v in self.repo.all('version') if v.get('kind') == kind]
                if not available:
                    raise ValueError('No published %s template is available' % kind)
                reference = available[0]['id']
            if preview and reference.startswith('draft:'):
                identity, revision = reference[6:].rsplit(':', 1)
                definition = self.repo.get('definition', identity)
                if definition['revision'] != int(revision):
                    raise Conflict('Preview draft changed')
                version = {**definition, 'id': reference, 'hash': digest(definition['body'])}
            else:
                version = self.repo.get('version', reference)
            if version['kind'] != kind:
                raise ValueError('Definition type mismatch')
            version['body'] = validate_definition(kind, version['body'])
            snapshots[kind] = version
        return snapshots

    def create_run(self, payload, preview=False, parent=None, reuse=None):
        def action():
            snapshots = self._snapshots(payload, preview)
            document = self.repo.get('document', payload['document_id'])
            if payload.get('model_profile_id', 'deepseek') != 'deepseek' or not self.capabilities()['models'][0]['available']:
                raise ValueError('MODEL_NOT_CONFIGURED: configure DEEPSEEK_API_KEY on the server')
            if payload.get('publish_policy', 'manual') not in ('manual', 'auto_if_clean'):
                raise ValueError('Invalid publish policy')
            if payload.get('publish_target', 'local') not in ('local', 'neo4j'):
                raise ValueError('Invalid publication target')
            if payload.get('publish_target') == 'neo4j':
                from ..neo4j_source import connection_settings
                try:
                    connection_settings()
                except RuntimeError as error:
                    raise ValueError('Neo4j 发布目标尚未配置') from error
            if payload.get('target_graph_id') not in (None, 'new'):
                raise ValueError('This server publishes isolated new graphs; merging into existing graphs is unavailable')
            if payload.get('supersedes_publish_id'):
                raise ValueError('Replacing existing publications is unavailable; publish a new graph version instead')
            if sum(r['status'] == 'queued' for r in self.repo.all('run')) >= 20:
                raise Conflict('Queue is full')
            run = {'id': uid(), 'purpose': 'preview' if preview else 'production', 'status': 'queued',
                   'document_id': document['id'], 'document_name': document['name'], 'snapshots': snapshots,
                   'model': self.capabilities()['models'][0]['model'], 'publish_policy': payload.get('publish_policy', 'manual'),
                   'steps': [{'id': step, 'status': 'pending', 'attempt': 0} for step in snapshots['flow']['body']['steps']],
                   'last_event_seq': 0, 'created_at': time.time(), 'parent_run_id': parent, 'reuse': reuse or {},
                   'candidate_revision': 0, 'publication': None, 'quality': 'unknown'}
            run['publish_target'] = payload.get('publish_target', 'local')
            run['processor_version'] = self.processor_version
            self.repo.event(run, 'run.queued')
            return {'id': run['id'], 'status': run['status']}
        result = self.repo.once('preview' if preview else 'run', payload['request_key'], payload, action)
        self.wake.set()
        return result

    def _update(self, identity, event, step_id=None, changes=None, **data):
        with self.repo.transaction():
            run = self.repo.get('run', identity)
            if step_id:
                target = next(s for s in run['steps'] if s['id'] == step_id)
                target.update(changes or {})
            else:
                run.update(changes or {})
            self.repo.event(run, event, step_id=step_id, **data)
            return run

    def _cancel_check(self, identity):
        if self.stop.is_set() or self.repo.get('run', identity)['status'] == 'cancel_requested':
            raise Cancelled()

    def _loop(self):
        while not self.stop.is_set():
            queued = [r for r in reversed(self.repo.all('run')) if r['status'] == 'queued']
            if not queued:
                self.wake.wait(.5)
                self.wake.clear()
                continue
            self._execute(queued[0]['id'])

    def _execute(self, identity):
        from ...pipeline import ExecutionEngine
        from ...pipeline.pipeline_templates import PipelineTemplate, PipelineTemplateManager
        try:
            with self.repo.transaction():
                run = self.repo.get('run', identity)
                if run['status'] != 'queued':
                    return
                self._cancel_check(identity)
                run.update(status='running', started_at=time.time())
                self.repo.event(run, 'run.started')
            document = self.repo.get('document', run['document_id'])
            flow, template, rules = [run['snapshots'][k]['body'] for k in ('flow', 'extraction', 'rules')]
            context = {}

            def extract(data):
                client = None
                if self.model_call is None:
                    from openai import OpenAI
                    client = OpenAI(api_key=os.environ['DEEPSEEK_API_KEY'], base_url='https://api.deepseek.com/v1', timeout=90, max_retries=0)
                records, usage = [], []
                chunks = data['chunked']['chunks']
                for index, chunk in enumerate(chunks, 1):
                    self._cancel_check(identity)
                    cache_parent = run.get('parent_run_id') if run.get('resume_chunks') else None
                    cache_id = digest([cache_parent or identity, document['sha256'],
                                       self.processor_version, run['model'], template, chunk])
                    try:
                        cached = self.repo.get('chunk_result', cache_id)
                    except KeyError:
                        cached = None
                    if cached:
                        saved = self.repo.read(cached['artifact'])
                        records.append(saved['result'])
                        usage.append(saved['usage'])
                        with self.repo.transaction():
                            own_id = digest([identity, document['sha256'], self.processor_version, run['model'], template, chunk])
                            self.repo.put('chunk_result', own_id, cached)
                        self._update(identity, 'chunk.reused', chunk_id=chunk['id'], completed=index, total=len(chunks))
                        continue
                    for attempt in range(1, 4):
                        try:
                            if self.model_call:
                                result, tokens = self.model_call(chunk, template)
                            else:
                                result, tokens = model_extract(chunk, template, client, run['model'])
                            records.append(result)
                            usage.append(tokens)
                            artifact = self.repo.artifact({'result': result, 'usage': tokens})
                            with self.repo.transaction():
                                self.repo.put('chunk_result', cache_id, {'artifact': artifact})
                                own_id = digest([identity, document['sha256'], self.processor_version, run['model'], template, chunk])
                                self.repo.put('chunk_result', own_id, {'artifact': artifact})
                            self._update(identity, 'chunk.completed', chunk_id=chunk['id'], usage=tokens, completed=index, total=len(chunks))
                            break
                        except Exception as error:
                            code = getattr(error, 'status_code', None)
                            transient = code in (429, 500, 502, 503, 504) or type(error).__name__ in ('APITimeoutError', 'APIConnectionError')
                            if not transient or attempt == 3:
                                raise
                            self._update(identity, 'step.retry_scheduled', 'extract', {'status': 'retrying', 'attempt': attempt + 1}, attempt=attempt + 1)
                            if self.stop.wait(2 ** attempt):
                                raise Cancelled()
                            self._cancel_check(identity)
                            self._update(identity, 'step.retrying', 'extract', {'status': 'running'})
                return {**data, 'extractions': records, 'usage': usage}

            def processor(name, data):
                if name == 'parse':
                    return {'document': parse_document(self.repo.root / 'artifacts' / document['artifact'], document['name'])}
                if name == 'split':
                    chunked = chunk_document(data['document'], flow)
                    return {**data, 'document': {**data['document'], 'segments': chunked.pop('segments')}, 'chunked': chunked}
                if name == 'extract':
                    return extract(data)
                if name == 'normalize':
                    return {**data, 'candidate': normalize(data['extractions'], rules)}
                if name == 'statistics':
                    return {**data, 'statistics': {'entities': len(data['candidate']['entities']), 'relationships': len(data['candidate']['relationships'])}}
                if name == 'validate':
                    return {**data, 'candidate': validate_candidate(data['candidate'], data['document'], template, rules)}
                if name == 'store':
                    return data
                raise ValueError('Unregistered handler')

            def handler(name):
                def execute(data, **options):
                    self._cancel_check(identity)
                    started = time.time()
                    self._update(identity, 'step.started', name, {'status': 'running', 'attempt': 1, 'started_at': started})
                    try:
                        artifact = run['reuse'].get(name)
                        output = self.repo.read(artifact) if artifact else processor(name, data or {})
                        self._cancel_check(identity)
                        artifact = artifact or self.repo.artifact(output)
                        context.update(output)
                        candidate = output.get('candidate', {})
                        metrics = {'entities': len(candidate.get('entities', [])), 'relationships': len(candidate.get('relationships', [])),
                                   'chunks': len(output.get('chunked', {}).get('chunks', []))}
                        self._update(identity, 'step.completed', name, {'status': 'reused' if name in run['reuse'] else 'completed',
                                     'artifact': artifact, 'duration': time.time() - started, 'metrics': metrics})
                        return output
                    except Exception as error:
                        self._update(identity, 'step.failed', name, {'status': 'cancelled' if isinstance(error, Cancelled) else 'failed',
                                     'error': 'Cancelled' if isinstance(error, Cancelled) else self.safe_error(error)})
                        raise
                return execute

            manager = PipelineTemplateManager()
            manager.register_template(PipelineTemplate(name='document', description='Document workflow', steps=[{'name': s, 'type': s,
                'dependencies': [flow['steps'][i - 1]] if i else []} for i, s in enumerate(flow['steps'])]))
            builder = manager.create_pipeline_from_template('document', **{s: {'handler': handler(s)} for s in flow['steps']})
            result = ExecutionEngine(default_max_retries=0).execute_pipeline(builder.build(identity))
            self._cancel_check(identity)
            if not result.success:
                raise ValueError('A pipeline step failed; inspect the step error')
            candidate_key = self.repo.artifact(context)
            candidate = context['candidate']
            quality = candidate['quality']
            status = 'preview_completed' if run['purpose'] == 'preview' else 'awaiting_review'
            self._update(identity, 'candidate.created', changes={'status': status, 'candidate': candidate_key,
                         'candidate_revision': 1, 'quality': quality, 'finished_at': time.time()})
            if run['purpose'] != 'preview' and run.get('publish_target', 'local') == 'local' and run['publish_policy'] == 'auto_if_clean' and not candidate['issues']:
                try:
                    self.publish(identity, {'candidate_revision': 1, 'request_key': 'auto-publish-' + identity})
                except Exception as error:
                    self._update(identity, 'publication.failed', changes={'error': self.safe_error(error)})
        except Exception as error:
            with self.repo.transaction():
                run = self.repo.get('run', identity)
                cancelled = run['status'] == 'cancel_requested' or isinstance(error, Cancelled)
                run.update(status=('interrupted' if self.stop.is_set() else 'cancelled') if cancelled else 'failed',
                           error='Cancelled' if cancelled else self.safe_error(error), finished_at=time.time())
                for step in run['steps']:
                    if step['status'] in ('pending', 'running', 'retrying'):
                        step['status'] = 'cancelled' if cancelled else 'blocked'
                self.repo.event(run, 'run.finished', status=run['status'])

    @staticmethod
    def safe_error(error):
        if isinstance(error, (ValueError, KeyError)):
            return str(error)[:600]
        return '%s: %s' % (type(error).__name__, getattr(error, 'status_code', 'processing error'))

    def candidate(self, identity):
        run = self.repo.get('run', identity)
        if not run.get('candidate'):
            raise Conflict('Candidate is not available')
        return self.repo.read(run['candidate'])

    def review(self, identity, payload):
        def action():
            run = self.repo.get('run', identity)
            if run['status'] != 'awaiting_review' or payload['expected_candidate_revision'] != run['candidate_revision']:
                raise Conflict('Candidate changed or is not editable')
            data = self.repo.read(run['candidate'])
            candidate = data['candidate']
            additions = payload.get('additions', {})
            if not isinstance(additions, dict) or set(additions) - {'entities', 'relationships'}:
                raise ValueError('Invalid review additions')
            if additions:
                if not payload.get('reason', '').strip():
                    raise ValueError('Review additions require a reason')
                for kind in ('entities', 'relationships'):
                    if not isinstance(additions.get(kind, []), list) or len(additions.get(kind, [])) > 100:
                        raise ValueError('Review additions exceed record budget')
                added = normalize([additions], run['snapshots']['rules']['body'])
                existing = {r['id'] for r in candidate['entities'] + candidate['relationships']}
                for kind in ('entities', 'relationships'):
                    for record in added[kind]:
                        if record['id'] in existing:
                            raise Conflict('Candidate record already exists; edit it instead')
                        candidate[kind].append(record)
                        candidate['audit'].append({'record_id': record['id'], 'rule': 'human_add',
                                                   'after': copy.deepcopy(record), 'reason': payload['reason']})
            records = {r['id']: r for r in candidate['entities'] + candidate['relationships']}
            for patch in payload.get('patches', []):
                record = records.get(patch['record_id'])
                if record is None:
                    raise ValueError('Unknown candidate record')
                changes = patch.get('changes', {})
                allowed = {'name', 'type', 'canonical_name'} if 'name' in record else {'source', 'target', 'type', 'status', 'segment_ids', 'quantity_text', 'year_text'}
                if set(changes) - allowed:
                    raise ValueError('Unsupported review field')
                for field, value in changes.items():
                    if field == 'segment_ids':
                        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                            raise ValueError('segment_ids must be strings')
                    elif field not in ('quantity_text', 'year_text') and not isinstance(value, str):
                        raise ValueError('Review fields must contain strings')
                    elif field in ('quantity_text', 'year_text') and value is not None and not isinstance(value, str):
                        raise ValueError('Quantity/year must be a string or null')
                candidate['audit'].append({'record_id': record['id'], 'rule': 'human_edit', 'before': copy.deepcopy(record),
                                           'after': changes, 'reason': payload.get('reason', '')})
                record.update(changes)
            excluded = payload.get('excluded', candidate.get('excluded', []))
            if not isinstance(excluded, list) or any(x not in records for x in excluded):
                raise ValueError('Invalid excluded records')
            if (payload.get('patches') or excluded != candidate.get('excluded', [])) and not payload.get('reason', '').strip():
                raise ValueError('Review changes require a reason')
            if excluded != candidate.get('excluded', []):
                candidate['audit'].append({'rule': 'human_exclusion', 'before': candidate.get('excluded', []),
                                           'after': excluded, 'reason': payload['reason']})
            candidate['excluded'] = excluded
            data['candidate'] = validate_candidate(candidate, data['document'], run['snapshots']['extraction']['body'], run['snapshots']['rules']['body'])
            run['candidate'] = self.repo.artifact(data)
            run['candidate_revision'] += 1
            run['quality'] = data['candidate']['quality']
            self.repo.event(run, 'candidate.reviewed', revision=run['candidate_revision'])
            return run
        return self.repo.once('review:' + identity, payload['request_key'], payload, action)

    def publish(self, identity, payload):
        # Publication is a new immutable graph, never an incremental live-session write.
        def action():
            from ...context import ContextGraph
            from ..session import GraphSession
            run = self.repo.get('run', identity)
            if run['purpose'] == 'preview':
                raise Conflict('Preview runs cannot publish')
            if run.get('publication'):
                if payload['candidate_revision'] != run['candidate_revision']:
                    raise Conflict('Candidate revision changed')
                return run['publication']
            if run['status'] != 'awaiting_review' or payload['candidate_revision'] != run['candidate_revision']:
                raise Conflict('Run is not ready to publish')
            if payload.get('supersedes_publish_id') or payload.get('target_revision'):
                raise ValueError('Existing graph merge/replacement is unavailable')
            data = self.repo.read(run['candidate'])
            candidate = validate_candidate(data['candidate'], data['document'], run['snapshots']['extraction']['body'], run['snapshots']['rules']['body'])
            excluded = set(candidate.get('excluded', []))
            # Human review has already resolved or excluded flagged records.  Keep
            # the audit trail, but do not block publication on informational issues.
            session = GraphSession(ContextGraph())
            names, nodes = {}, {}
            for entity in candidate['entities']:
                if entity['id'] in excluded:
                    continue
                node_id = 'entity_' + digest([entity['type'], entity['canonical_name']])[:24]
                names[entity['name']] = node_id
                nodes[node_id] = {'id': node_id, 'type': entity['type'], 'properties': {'content': entity['canonical_name'],
                                 'source_document': run['document_name'], 'document_id': run['document_id'], 'run_id': identity}}
            edges = []
            for relation in candidate['relationships']:
                if relation['id'] in excluded:
                    continue
                edges.append({'id': relation['id'], 'source_id': names[relation['source']], 'target_id': names[relation['target']],
                              'type': relation['type'], 'properties': {'status': relation['status'], 'quantity': relation['quantity'],
                              'time': relation['time'], 'evidence': relation['evidence'], 'run_id': identity, 'document_id': run['document_id']}})
            session.add_nodes_and_edges(list(nodes.values()), edges)
            persist = getattr(self, 'persist_graph_import', None)
            if persist is None and os.getenv('NEO4J_URI') and os.getenv('NEO4J_PASSWORD'):
                from ..neo4j_import import persist_import
                persist = lambda ns, es: persist_import({'uri': os.getenv('NEO4J_URI'), 'user': os.getenv('NEO4J_USER', 'neo4j'), 'password': os.getenv('NEO4J_PASSWORD'), 'database': os.getenv('NEO4J_DATABASE', 'neo4j')}, ns, es)
            if persist:
                persist(list(nodes.values()), edges)
            graph_id = uid()
            path = self.root / 'artifacts' / ('graph-' + graph_id + '.json')
            session.graph.save_to_file(path)
            directory = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            check = GraphSession.from_file(str(path))
            if len(check.graph.nodes) != len(nodes) or len(check.graph.edges) != len(edges):
                raise ValueError('Graph readback verification failed')
            publication = {'id': graph_id, 'run_id': identity, 'artifact': path.name, 'revision': 1,
                           'nodes': len(nodes), 'edges': len(edges), 'name': run['document_name'], 'created_at': time.time(),
                           'candidate_revision': run['candidate_revision'], 'phase': 'visible', 'mode': 'merged_upsert'}
            self.repo.put('graph', graph_id, publication)
            run.update(publication=publication, status='completed', finished_at=time.time())
            self.repo.event(run, 'graph.published', publication=publication)
            return publication
        return self.repo.once('publish:' + identity, payload['request_key'], payload, action)

    def cancel(self, identity, payload):
        def action():
            run = self.repo.get('run', identity)
            if run['status'] in TERMINAL:
                return run
            if run['status'] == 'publishing':
                raise Conflict('Publication cannot be cancelled')
            run['status'] = 'cancelled' if run['status'] in ('queued', 'awaiting_review') else 'cancel_requested'
            if run['status'] == 'cancelled':
                for step in run['steps']:
                    if step['status'] == 'pending':
                        step['status'] = 'cancelled'
            self.repo.event(run, 'run.cancelled' if run['status'] == 'cancelled' else 'run.cancel_requested')
            return run
        return self.repo.once('cancel:' + identity, payload['request_key'], payload, action)

    def rerun_plan(self, identity, payload):
        old = self.repo.get('run', identity)
        snapshots = self._snapshots(payload)
        if payload['document_id'] != old['document_id'] or old.get('processor_version') != self.processor_version:
            start = 0
        else:
            start = len(STEPS)
            old_flow = {k: v for k, v in old['snapshots']['flow']['body'].items() if k != 'positions'}
            new_flow = {k: v for k, v in snapshots['flow']['body'].items() if k != 'positions'}
            if old_flow != new_flow:
                start = 1
            if old['snapshots']['extraction']['hash'] != snapshots['extraction']['hash'] or payload.get('force_extract') or old['model'] != self.capabilities()['models'][0]['model']:
                start = min(start, 2)
            if old['snapshots']['rules']['hash'] != snapshots['rules']['hash']:
                start = min(start, 3)
        # Revalidate and regenerate candidates; human overlays are not cached.
        start = min(start, 4)
        reuse = {}
        for step in old['steps']:
            if step['id'] not in STEPS or STEPS.index(step['id']) >= start:
                continue
            if step['status'] not in ('completed', 'reused') or not step.get('artifact'):
                break
            self.repo.read(step['artifact'])
            reuse[step['id']] = step['artifact']
        plan = {'parent_run_id': identity, 'reuse': reuse, 'recompute': [s for s in snapshots['flow']['body']['steps'] if s not in reuse],
                'mode': 'new_managed_graph', 'snapshot_hashes': {k: v['hash'] for k, v in snapshots.items()},
                'model': self.capabilities()['models'][0]['model'], 'document_id': payload['document_id']}
        plan['hash'] = digest(plan)
        return plan

    def rerun(self, identity, payload):
        plan = self.rerun_plan(identity, payload)
        if payload.get('plan_hash') != plan['hash']:
            raise Conflict('Rerun plan changed')
        return self.create_run({**payload, 'resume_chunks': not payload.get('force_extract', False)}, parent=identity, reuse=plan['reuse'])

    def compare(self, identity, other):
        def rows(run_id):
            candidate = self.candidate(run_id)['candidate']
            return {r['id']: r for r in candidate['entities'] + candidate['relationships'] if r['id'] not in candidate.get('excluded', [])}
        current, before = rows(identity), rows(other)
        current_run, previous_run = self.repo.get('run', identity), self.repo.get('run', other)
        return {'added': [current[k] for k in current.keys() - before.keys()],
                'removed': [before[k] for k in before.keys() - current.keys()],
                'changed': [{'before': before[k], 'after': current[k]} for k in current.keys() & before.keys() if current[k] != before[k]],
                'configuration': {kind: {'before': previous_run['snapshots'][kind], 'after': current_run['snapshots'][kind]}
                                  for kind in ('flow', 'extraction', 'rules') if previous_run['snapshots'][kind]['hash'] != current_run['snapshots'][kind]['hash']},
                'quality': {'before': self.candidate(other)['candidate']['issues'], 'after': self.candidate(identity)['candidate']['issues']}}
