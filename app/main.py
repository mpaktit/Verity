from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.services.research import get_offer_summary, get_offers, get_providers, get_research_status

app = FastAPI(
    title='Access Intelligence Platform',
    description='Public offer monitoring platform for AI and SaaS free access opportunities.',
    version='0.1.0',
)

app.mount('/static', StaticFiles(directory='app/static'), name='static')


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


@app.get('/api/research')
async def research():
    return get_research_status()
