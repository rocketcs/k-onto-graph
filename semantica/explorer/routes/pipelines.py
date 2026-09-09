"""Authenticated document workflow endpoints shared by both server entry points."""
import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from ..pipelines.repository import Conflict

router = APIRouter(tags=['pipelines'])


def service(request):
    value = getattr(request.app.state, 'pipeline_service', None)
    if value is None:
        raise HTTPException(503, detail={'code': 'PIPELINE_DISABLED', 'message': 'Set SEMANTICA_PIPELINE_ENABLED=true and configure a writable data directory'})
    return value


def call(action):
    try:
        return action()
    except Conflict as exc:
        raise HTTPException(409, detail={'code': 'CONFLICT', 'message': str(exc)}) from exc
    except KeyError as exc:
        raise HTTPException(404, detail={'code': 'NOT_FOUND', 'message': 'Record or required field not found'}) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, detail={'code': 'INVALID_INPUT', 'message': str(exc)[:600]}) from exc


@router.get('/api/pipeline-capabilities')
def capabilities(request: Request):
    return service(request).capabilities()


@router.post('/api/pipeline-documents', status_code=201)
async def upload(request: Request, file: UploadFile = File(...), request_key: str = Form(...)):
    svc = service(request)
    data = bytearray()
    try:
        while True:
            chunk = await file.read(65536)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > svc.capabilities()['max_bytes']:
                raise HTTPException(413, detail={'code': 'FILE_TOO_LARGE', 'message': 'Maximum upload is 20 MiB'})
        return call(lambda: svc.upload(file.filename or '', bytes(data), request_key))
    finally:
        await file.close()


@router.get('/api/pipeline-documents/{identity}/content')
def document_content(identity: str, request: Request, run_id: str):
    svc = service(request)
    def action():
        run = svc.repo.get('run', run_id)
        if run['document_id'] != identity:
            raise KeyError(identity)
        step = next(s for s in run['steps'] if s['id'] == 'parse')
        if not step.get('artifact'):
            raise Conflict('Parsing has not completed')
        return svc.repo.read(step['artifact'])['document']
    return call(action)


@router.get('/api/pipeline-definitions')
def definitions(request: Request):
    return {'items': service(request).definitions()}


@router.post('/api/pipeline-definitions', status_code=201)
def create_definition(request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).create_definition(payload))


@router.get('/api/pipeline-definitions/{identity}')
def get_definition(identity: str, request: Request):
    return call(lambda: service(request).repo.get('definition', identity))


@router.put('/api/pipeline-definitions/{identity}')
def save_definition(identity: str, request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).save_definition(identity, payload))


@router.get('/api/pipeline-definitions/{identity}/versions')
def versions(identity: str, request: Request):
    return {'items': [v for v in service(request).repo.all('version') if v['definition_id'] == identity]}


@router.get('/api/pipeline-definition-versions/{identity}')
def version(identity: str, request: Request):
    return call(lambda: service(request).repo.get('version', identity))


@router.post('/api/pipeline-definitions/{identity}/validate')
def validate_definition(identity: str, request: Request, payload: dict = Body(...)):
    from ..pipelines.definitions import validate_definition as validate
    svc = service(request)
    return call(lambda: {'valid': True, 'body': validate(svc.repo.get('definition', identity)['kind'], payload['body'])})


@router.post('/api/pipeline-definitions/{identity}/versions', status_code=201)
def publish_definition(identity: str, request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).publish_definition(identity, payload))


@router.post('/api/pipeline-previews', status_code=202)
def preview(request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).create_run(payload, preview=True))


@router.post('/api/pipeline-runs', status_code=202)
def create_run(request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).create_run(payload))


@router.get('/api/pipeline-runs')
def runs(request: Request, status: str = '', cursor: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    items = [r for r in service(request).repo.all('run') if not status or r['status'] == status]
    return {'items': items[cursor:cursor + limit], 'next_cursor': cursor + limit if len(items) > cursor + limit else None}

@router.delete('/api/pipeline-runs', status_code=204)
def clear_runs(request: Request):
    service(request).repo.clear_pipeline_data()


@router.get('/api/pipeline-runs/{identity}')
def run(identity: str, request: Request):
    return call(lambda: service(request).repo.get('run', identity))


@router.get('/api/pipeline-runs/{identity}/events')
def events(identity: str, request: Request, after_seq: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    return call(lambda: service(request).repo.events(identity, after_seq, limit))


@router.get('/api/pipeline-runs/{identity}/results')
def results(identity: str, request: Request):
    return call(lambda: service(request).candidate(identity))


@router.put('/api/pipeline-runs/{identity}/review')
def review(identity: str, request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).review(identity, payload))


@router.post('/api/pipeline-runs/{identity}/publish')
def publish(identity: str, request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).publish(identity, payload))


@router.post('/api/pipeline-runs/{identity}/neo4j-plan')
def neo4j_plan(identity: str, request: Request, payload: dict = Body(...)):
    from ..pipelines.neo4j_publication import plan
    return call(lambda: plan(service(request), identity, payload))


@router.post('/api/pipeline-runs/{identity}/neo4j-publish')
async def neo4j_publish(identity: str, request: Request, payload: dict = Body(...)):
    from ..pipelines.neo4j_publication import publish
    receipt = await asyncio.to_thread(call, lambda: publish(service(request), identity, payload))
    refresh = getattr(request.app.state, 'refresh_neo4j', None)
    if refresh:
        await asyncio.to_thread(refresh)
        await request.app.state.ws_manager.broadcast('graph_replaced', {'source': 'neo4j'})
    return receipt


@router.post('/api/pipeline-runs/{identity}/neo4j-reconcile')
def neo4j_reconcile(identity: str, request: Request):
    from ..pipelines.neo4j_publication import reconcile
    return call(lambda: reconcile(service(request), identity))


@router.post('/api/pipeline-runs/{identity}/cancel', status_code=202)
def cancel(identity: str, request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).cancel(identity, payload))


@router.post('/api/pipeline-runs/{identity}/rerun-plan')
def rerun_plan(identity: str, request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).rerun_plan(identity, payload))


@router.post('/api/pipeline-runs/{identity}/reruns', status_code=202)
def rerun(identity: str, request: Request, payload: dict = Body(...)):
    return call(lambda: service(request).rerun(identity, payload))


@router.get('/api/pipeline-runs/{identity}/comparison')
def comparison(identity: str, request: Request, other_run_id: str):
    return call(lambda: service(request).compare(identity, other_run_id))


@router.get('/api/pipeline-graphs')
def graphs(request: Request):
    return {'items': service(request).repo.all('graph'), 'active': getattr(request.app.state, 'pipeline_active_graph', None)}


@router.get('/api/pipeline-graphs/{identity}/download')
def download_graph(identity: str, request: Request):
    svc = service(request)
    graph = call(lambda: svc.repo.get('graph', identity))
    return FileResponse(svc.root / 'artifacts' / graph['artifact'], filename='graph-%s.json' % identity, media_type='application/json')


@router.get('/api/pipeline-runs/{identity}/export')
def export_run(identity: str, request: Request):
    svc = service(request)
    return call(lambda: {'run': svc.repo.get('run', identity), 'result': svc.candidate(identity),
                         'events': svc.repo.events(identity, 0, 10000)})


@router.post('/api/pipeline-graphs/{identity}/activate')
async def activate_graph(identity: str, request: Request, payload: dict = Body(...)):
    from ..session import GraphSession
    from ..markdown_resources import MarkdownResourceRegistry
    from ..runtime import install_mutation_bridge
    svc = service(request)
    def activate():
        with svc.activation_lock:
            graph = svc.repo.get('graph', identity)
            if payload.get('revision') != graph['revision']:
                raise Conflict('Graph revision changed')
            active = getattr(request.app.state, 'pipeline_active_graph', None)
            if payload.get('expected_active_graph_id') != active:
                raise Conflict('Active graph changed')
            if active:
                old = request.app.state.session
                if old._graph_revision != getattr(request.app.state, 'pipeline_active_baseline', 0):
                    raise Conflict('Active graph has edits; switching is blocked in this version. Export edits and restart Explorer to open another snapshot')
            elif not payload.get('confirm_switch'):
                raise Conflict('Opening a result replaces the active Explorer view; confirm_switch is required')
            session = GraphSession.from_file(str(svc.root / 'artifacts' / graph['artifact']))
            request.app.state.session = session
            request.app.state.markdown_resources = MarkdownResourceRegistry(session.graph, getattr(request.app.state, 'agent_memory', None))
            install_mutation_bridge(request.app, session)
            request.app.state.pipeline_active_graph = identity
            request.app.state.pipeline_active_baseline = session._graph_revision
            return {'graph_id': identity, 'revision': graph['revision']}
    result = call(activate)
    await request.app.state.ws_manager.broadcast('graph_replaced', result)
    return result


def start_pipeline_service(app):
    if os.getenv('SEMANTICA_PIPELINE_ENABLED', '').lower() != 'true':
        return
    from ..pipelines.service import PipelineService
    root = os.getenv('SEMANTICA_PIPELINE_DATA_DIR', str(Path.home() / '.semantica' / 'explorer' / 'pipelines'))
    app.state.pipeline_service = PipelineService(root)


async def stop_pipeline_service(app):
    svc = getattr(app.state, 'pipeline_service', None)
    if svc:
        await asyncio.get_running_loop().run_in_executor(None, svc.close)
