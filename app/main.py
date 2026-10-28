import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.services.monitor import scan_sources
from app.services.research import (
    create_evidence,
    create_watchlist,
    get_alerts,
    get_analytics,
    get_audit_log,
    get_insights,
    get_offer_summary,
    get_offers,
    get_provider_detail,
    get_providers,
    get_research_status,
    get_signals,
    get_sources,
    get_watchlists,
    get_worker_by_token,
    get_worker_workspace,
    login_worker,
    register_worker,
    submit_attempt,
    submit_review,
)
from app.services.ai_provider import get_ai_manager, ProviderType
from app.services.job_queue import get_job_queue, JobType, AgentType, JobStatus
from app.services.orchestrator import get_orchestrator


def _scheduler_loop(stop_event: threading.Event) -> None:
    if stop_event.wait(8):
        return
    while not stop_event.is_set():
        try:
            scan_sources()
        except Exception:
            pass
        if stop_event.wait(settings.CRAWL_INTERVAL_SECONDS):
            break


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop_event = threading.Event()
    thread = None
    if settings.ENABLE_SCHEDULER:
        thread = threading.Thread(target=_scheduler_loop, args=(stop_event,), daemon=True)
        thread.start()
    yield
    stop_event.set()


app = FastAPI(
    title="Verity",
    description="Public offer intelligence for official AI and SaaS access programs.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


def resolve_token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    if not get_worker_by_token(token):
        raise HTTPException(status_code=401, detail="Unknown worker session.")
    return token


@app.get("/")
async def index():
    return FileResponse("app/static/index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "verity",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/offers")
async def offers():
    return get_offers()


@app.get("/api/summary")
async def summary():
    return get_offer_summary()


@app.get("/api/providers")
async def providers():
    return get_providers()


@app.get("/api/providers/{provider_id}")
async def provider_detail(provider_id: str):
    detail = get_provider_detail(provider_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="provider not found")
    return detail


@app.get("/api/research")
async def research():
    return get_research_status()


@app.get("/api/sources")
async def sources():
    return get_sources()


@app.get("/api/signals")
async def signals():
    return get_signals()


@app.get("/api/alerts")
async def alerts():
    return get_alerts()


@app.get("/api/insights")
async def insights():
    return get_insights()


@app.get("/api/analytics")
async def analytics():
    return get_analytics()


@app.post("/api/monitor/run")
async def monitor_run(payload: dict | None = None, authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    provider_id = (payload or {}).get("provider_id")
    return scan_sources(provider_id)


@app.get("/api/audit")
async def audit(authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    return get_audit_log()


@app.get("/api/watchlists")
async def watchlists(authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    worker = get_worker_by_token(token)
    return get_watchlists(worker["email"])


@app.post("/api/watchlists")
async def create_watchlist_endpoint(payload: dict, authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    worker = get_worker_by_token(token)
    try:
        return create_watchlist(worker["email"], payload.get("name", "Untitled watchlist"), payload.get("filters", {}))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/evidence")
async def evidence_endpoint(payload: dict, authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    try:
        return create_evidence(token, payload.get("offer_id"), payload.get("source_url", ""), payload.get("note", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/signup")
async def signup(payload: dict):
    try:
        return register_worker(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/login")
async def login(payload: dict):
    try:
        return login_worker(payload)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/api/workspace")
async def workspace(authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    worker = get_worker_by_token(token)
    return {
        "profile": {
            "id": worker["id"],
            "name": worker["name"],
            "email": worker["email"],
            "role": worker["role"],
        },
        "workspace": get_worker_workspace(worker["email"]),
    }


@app.post("/api/workspace/attempt")
async def create_attempt(payload: dict, authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    try:
        return submit_attempt(token, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/workspace/review")
async def review_attempt(payload: dict, authorization: str | None = Header(default=None)):
    token = resolve_token(authorization)
    try:
        return submit_review(token, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Agent system endpoints
@app.get("/api/agents/status")
async def agents_status(authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    orchestrator = get_orchestrator()
    return orchestrator.get_status()


@app.post("/api/agents/start")
async def agents_start(authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    orchestrator = get_orchestrator()
    await orchestrator.start()
    return {"status": "started"}


@app.post("/api/agents/stop")
async def agents_stop(authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    orchestrator = get_orchestrator()
    await orchestrator.stop()
    return {"status": "stopped"}


@app.post("/api/agents/research")
async def trigger_research(payload: dict, authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    orchestrator = get_orchestrator()
    platform = payload.get("platform")
    result = orchestrator.trigger_research(platform)
    return result


@app.get("/api/agents/jobs")
async def list_jobs(
    status: str | None = None,
    agent_type: str | None = None,
    limit: int = 50,
    authorization: str | None = Header(default=None),
):
    resolve_token(authorization)
    queue = get_job_queue()
    job_status = JobStatus(status) if status else None
    agent = AgentType(agent_type) if agent_type else None
    jobs = queue.list_jobs(status=job_status, agent_type=agent, limit=limit)
    return {"jobs": [j.to_dict() for j in jobs]}


@app.get("/api/agents/memory")
async def get_agent_memory(
    memory_type: str | None = None,
    limit: int = 20,
    authorization: str | None = Header(default=None),
):
    resolve_token(authorization)
    from app.db import get_connection
    memories = []
    query = "SELECT * FROM agent_memory ORDER BY created_at DESC LIMIT ?"
    params = (limit,)
    if memory_type:
        query = "SELECT * FROM agent_memory WHERE memory_type = ? ORDER BY created_at DESC LIMIT ?"
        params = (memory_type, limit)
    with get_connection() as conn:
        for row in conn.execute(query, params):
            memories.append({
                "id": row["id"],
                "agent_id": row["agent_id"],
                "memory_type": row["memory_type"],
                "content": row["content"],
                "metadata": row["metadata"],
                "relevance_score": row["relevance_score"],
                "created_at": row["created_at"],
            })
    return {"memories": memories}


@app.get("/api/agents/logs")
async def get_agent_logs(
    level: str | None = None,
    limit: int = 50,
    authorization: str | None = Header(default=None),
):
    resolve_token(authorization)
    from app.db import get_connection
    logs = []
    query = "SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT ?"
    params = (limit,)
    if level:
        query = "SELECT * FROM agent_logs WHERE log_level = ? ORDER BY created_at DESC LIMIT ?"
        params = (level, limit)
    with get_connection() as conn:
        for row in conn.execute(query, params):
            logs.append({
                "id": row["id"],
                "agent_id": row["agent_id"],
                "job_id": row["job_id"],
                "log_level": row["log_level"],
                "message": row["message"],
                "context": row["context"],
                "created_at": row["created_at"],
            })
    return {"logs": logs}


# API key management endpoints
@app.get("/api/ai/keys")
async def list_api_keys(authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    manager = get_ai_manager()
    return {"keys": manager.list_api_keys()}


@app.post("/api/ai/keys")
async def add_api_key(payload: dict, authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    manager = get_ai_manager()
    try:
        provider = ProviderType(payload["provider"])
        key_id = manager.add_api_key(
            provider=provider,
            key_name=payload["key_name"],
            api_key=payload["api_key"],
            rate_limit_per_minute=payload.get("rate_limit_per_minute", 60),
            metadata=payload.get("metadata"),
        )
        return {"id": key_id, "status": "added"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/ai/keys/{key_id}")
async def deactivate_api_key(key_id: str, authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    manager = get_ai_manager()
    manager.deactivate_api_key(key_id)
    return {"status": "deactivated"}


@app.get("/api/ai/models")
async def list_ai_models(authorization: str | None = Header(default=None)):
    resolve_token(authorization)
    manager = get_ai_manager()
    models = manager.get_available_models()
    return {
        "models": [
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider.value,
                "tier": m.tier.value,
                "context_tokens": m.context_tokens,
                "max_output_tokens": m.max_output_tokens,
            }
            for m in models
        ]
    }
