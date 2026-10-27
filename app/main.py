from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.research import (
    get_alerts,
    get_analytics,
    get_insights,
    get_offer_summary,
    get_offers,
    get_provider_detail,
    get_providers,
    get_research_status,
    get_worker_by_token,
    get_worker_workspace,
    login_worker,
    register_worker,
    submit_attempt,
    submit_review,
)

app = FastAPI(
    title='Access Intelligence Platform',
    description='Public offer monitoring platform for AI and SaaS free access opportunities.',
    version='0.1.0',
)

app.mount('/static', StaticFiles(directory='app/static'), name='static')


def resolve_token(authorization: str | None):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing or invalid bearer token.')
    token = authorization.split(' ', 1)[1].strip()
    if not get_worker_by_token(token):
        raise HTTPException(status_code=401, detail='Unknown worker session.')
    return token


@app.get('/')
async def index():
    return FileResponse('app/static/index.html')


@app.get('/api/health')
async def health():
    return {
        'status': 'ok',
        'service': 'access-intelligence',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }


@app.get('/api/offers')
async def offers():
    return get_offers()


@app.get('/api/summary')
async def summary():
    return get_offer_summary()


@app.get('/api/providers')
async def providers():
    return get_providers()


@app.get('/api/providers/{provider_id}')
async def provider_detail(provider_id: str):
    detail = get_provider_detail(provider_id)
    if detail is None:
        return {'detail': 'provider not found'}
    return detail


@app.get('/api/research')
async def research():
    return get_research_status()


@app.get('/api/alerts')
async def alerts():
    return get_alerts()


@app.get('/api/insights')
async def insights():
    return get_insights()


@app.get('/api/analytics')
async def analytics():
    return get_analytics()


@app.post('/api/auth/signup')
async def signup(payload: dict):
    try:
        return register_worker(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/auth/login')
async def login(payload: dict):
    try:
        return login_worker(payload)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get('/api/workspace')
async def workspace(authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    worker = get_worker_by_token(token)
    return {
        'profile': {
            'id': worker['id'],
            'name': worker['name'],
            'email': worker['email'],
            'role': worker['role'],
        },
        'workspace': get_worker_workspace(worker['email']),
    }


@app.post('/api/workspace/attempt')
async def create_attempt(payload: dict, authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    try:
        return submit_attempt(token, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post('/api/workspace/review')
async def review_attempt(payload: dict, authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    try:
        return submit_review(token, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
