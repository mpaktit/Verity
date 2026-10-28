import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.db import get_connection, init_db
from app.services.repository import get_alerts as repo_get_alerts
from app.services.repository import get_latest_scan_time
from app.services.repository import get_offers as repo_get_offers
from app.services.repository import get_provider_detail as repo_get_provider_detail
from app.services.repository import get_providers as repo_get_providers
from app.services.repository import get_research_runs
from app.services.repository import get_signals as repo_get_signals
from app.services.repository import get_sources as repo_get_sources
from app.services.repository import seed_reference_data

APP_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WORKER_STORE_PATH = APP_DATA_DIR / "workers.json"
init_db()
seed_reference_data()


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        settings.PBKDF2_ITERATIONS,
    )
    return f"{salt}:{digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or ":" not in stored_hash:
        return False
    salt, digest = stored_hash.split(":", 1)
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        settings.PBKDF2_ITERATIONS,
    )
    try:
        return hmac.compare_digest(candidate.hex(), digest)
    except Exception:
        return False


def _load_worker_store():
    workers = {}
    try:
        with get_connection() as conn:
            for row in conn.execute("SELECT * FROM workers"):
                workers[row["email"]] = {
                    "id": row["id"],
                    "name": row["name"],
                    "email": row["email"],
                    "password_hash": row["password_hash"],
                    "role": row["role"],
                    "token": row["token"],
                    "created_at": row["created_at"],
                }
    except Exception:
        pass
    if not workers and WORKER_STORE_PATH.exists():
        try:
            workers = json.loads(WORKER_STORE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            workers = {}
    return workers


def _persist_workers():
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        for worker in WORKER_LIBRARY.values():
            conn.execute(
                """INSERT INTO workers (id, name, email, password_hash, role, token, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(email) DO UPDATE SET
                     name=excluded.name, password_hash=excluded.password_hash, role=excluded.role,
                     token=excluded.token, updated_at=excluded.updated_at""",
                (
                    worker["id"],
                    worker["name"],
                    worker["email"],
                    worker["password_hash"],
                    worker["role"],
                    worker["token"],
                    worker["created_at"],
                    now,
                ),
            )


def log_audit(worker_id, action, entity_type, entity_id=None, metadata=None, ip_address=None, user_agent=None):
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO audit_log (id, worker_id, action, entity_type, entity_id, metadata, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "audit-" + uuid.uuid4().hex[:12],
                    worker_id,
                    action,
                    entity_type,
                    entity_id,
                    json.dumps(metadata or {}),
                    ip_address,
                    user_agent,
                    now,
                ),
            )
    except Exception:
        pass


def get_audit_log(limit=50):
    rows = []
    with get_connection() as conn:
        for row in conn.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)):
            rows.append(
                {
                    "id": row["id"],
                    "worker_id": row["worker_id"],
                    "action": row["action"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"],
                }
            )
    return rows


def create_watchlist(worker_email, name, filters):
    worker = next((item for item in WORKER_LIBRARY.values() if item["email"] == worker_email), None)
    if worker is None:
        raise ValueError("Worker not found.")
    now = datetime.now(timezone.utc).isoformat()
    watchlist_id = "watchlist-" + uuid.uuid4().hex[:8]
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO watchlists (id, worker_id, name, filters, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (watchlist_id, worker["id"], name, json.dumps(filters or {}), now, now),
        )
    return {"id": watchlist_id, "name": name, "filters": filters or {}, "created_at": now}


def get_watchlists(worker_email):
    worker = next((item for item in WORKER_LIBRARY.values() if item["email"] == worker_email), None)
    if worker is None:
        return []
    rows = []
    with get_connection() as conn:
        for row in conn.execute(
            "SELECT * FROM watchlists WHERE worker_id = ? ORDER BY created_at DESC", (worker["id"],)
        ):
            rows.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "filters": json.loads(row["filters"] or "{}"),
                    "created_at": row["created_at"],
                }
            )
    return rows


WORKER_LIBRARY = _load_worker_store()


def get_offer_summary():
    offers = repo_get_offers()
    total = len(offers)
    active = sum(1 for item in offers if item["status"] == "active")
    high_confidence = sum(1 for item in offers if item["verified"] and item["score"] >= 85)
    needs_review = sum(1 for item in offers if not item["verified"])
    categories = sorted({item["category"] for item in offers})
    return {
        "total_offers": total,
        "active_offers": active,
        "high_confidence": high_confidence,
        "needs_review": needs_review,
        "categories": categories,
    }


def get_offers():
    return repo_get_offers()


def get_providers():
    return repo_get_providers()


def get_provider_detail(provider_id: str):
    return repo_get_provider_detail(provider_id)


def get_research_status():
    providers = repo_get_providers()
    sources = repo_get_sources()
    total_sources = len(sources)
    checked = sum(1 for item in sources if item["status"] == "checked")
    errors = sum(1 for item in sources if item["status"] in {"error", "http_error"})
    active_providers = sum(1 for provider in providers if provider["status"] == "active")
    avg_coverage = round(sum(provider["research_coverage"] for provider in providers) / max(len(providers), 1), 1)
    last_scan = get_latest_scan_time() or "never"
    return {
        "total_sources": total_sources,
        "checked_sources": checked,
        "failed_sources": errors,
        "pending_sources": sum(1 for item in sources if item["status"] == "pending"),
        "active_providers": active_providers,
        "last_scan": last_scan,
        "coverage_percent": avg_coverage,
        "needs_review": sum(1 for provider in providers if provider["status"] == "monitoring"),
        "runs": get_research_runs(8),
    }


def get_alerts():
    return repo_get_alerts()


def get_sources():
    return repo_get_sources()


def get_signals(limit: int = 40):
    return repo_get_signals(limit)


def get_insights():
    summary = get_offer_summary()
    research = get_research_status()
    sources = repo_get_sources()
    workspace = _task_summary()
    reachable = research["checked_sources"]
    total = max(research["total_sources"], 1)
    momentum = round((reachable / total) * 70 + (summary["high_confidence"] / max(summary["total_offers"], 1)) * 30)
    signals = [
        {
            "title": "Reachable official sources",
            "value": f"{research['checked_sources']}/{research['total_sources']} last scan",
            "status": "positive" if research["checked_sources"] else "neutral",
        },
        {
            "title": "High-confidence offers",
            "value": f"{summary['high_confidence']} verified at 85+",
            "status": "positive" if summary["high_confidence"] else "neutral",
        },
        {
            "title": "Review queue",
            "value": f"{workspace['queued'] + workspace['in_review']} tasks open",
            "status": "neutral",
        },
        {
            "title": "Source errors",
            "value": f"{research['failed_sources']} failed fetches",
            "status": "neutral" if research["failed_sources"] == 0 else "watch",
        },
    ]
    if research["last_scan"] == "never":
        copy = "No live scan has run yet. Sign in and run verification to fetch official public pages."
        status = "idle"
    else:
        copy = "Live source checks are driving coverage, alerts, and the verification queue. Treat every finding as a public claim to confirm, not a workaround."
        status = "strong" if momentum >= 70 else "building"
    return {
        "momentum_score": momentum,
        "status": status,
        "signals": signals,
        "summary": copy,
        "last_updated": research["last_scan"],
        "source_sample": sources[:6],
    }


def get_analytics():
    summary = _task_summary()
    total = max(summary["total_tasks"], 1)
    pipeline = [
        {"label": "Queued", "value": summary["queued"], "percent": round(summary["queued"] / total * 100)},
        {"label": "In review", "value": summary["in_review"], "percent": round(summary["in_review"] / total * 100)},
        {"label": "Verified", "value": summary["verified"], "percent": round(summary["verified"] / total * 100)},
    ]
    offers = repo_get_offers()
    risk = {"low": 0, "medium": 0, "high": 0}
    for offer in offers:
        bucket = offer.get("risk_level") or "medium"
        if bucket not in risk:
            bucket = "medium"
        risk[bucket] += 1
    runs = get_research_runs(6)
    return {
        "pipeline": pipeline,
        "trend": {
            "labels": [item["provider"] for item in reversed(runs)] or ["idle"],
            "values": [int((item["confidence"] or 0) * 100) for item in reversed(runs)] or [0],
        },
        "risk_distribution": risk,
    }


def _generate_token():
    return f"verity_{secrets.token_urlsafe(24)}"


def _get_worker_payload(worker):
    return {
        "id": worker["id"],
        "name": worker["name"],
        "email": worker["email"],
        "role": worker["role"],
    }


def get_worker_by_token(token: str):
    for worker in WORKER_LIBRARY.values():
        if worker.get("token") == token:
            return worker
    return None


def register_worker(payload: dict):
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    name = (payload.get("name") or "New worker").strip()
    role = (payload.get("role") or "researcher").strip()

    if not email or not password:
        raise ValueError("Email and password are required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if email in WORKER_LIBRARY:
        raise ValueError("Worker already exists.")

    worker = {
        "id": f"worker-{uuid.uuid4().hex[:10]}",
        "name": name,
        "email": email,
        "password_hash": _hash_password(password),
        "role": role,
        "token": _generate_token(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    WORKER_LIBRARY[email] = worker
    _persist_workers()
    log_audit(worker["id"], "worker.signup", "worker", worker["id"], {"email": email, "role": role})
    return {
        "token": worker["token"],
        **_get_worker_payload(worker),
        "workspace": get_worker_workspace(email),
    }


def login_worker(payload: dict):
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    worker = WORKER_LIBRARY.get(email)
    if worker is None or not _verify_password(password, worker.get("password_hash", "")):
        raise ValueError("Invalid credentials.")
    log_audit(worker["id"], "worker.login", "worker", worker["id"], {"email": email})
    return {
        "token": worker["token"],
        **_get_worker_payload(worker),
        "workspace": get_worker_workspace(email),
    }


def _parse_json_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _load_tasks():
    seed_reference_data()
    tasks = []
    with get_connection() as conn:
        for row in conn.execute("SELECT * FROM tasks ORDER BY created_at"):
            attempts = []
            for attempt in conn.execute(
                "SELECT * FROM task_attempts WHERE task_id = ? ORDER BY created_at", (row["id"],)
            ):
                attempts.append(
                    {
                        "id": attempt["id"],
                        "approach": attempt["approach"],
                        "notes": attempt["notes"],
                        "created_at": attempt["created_at"],
                        "worker_id": attempt["worker_id"],
                    }
                )
            review_row = conn.execute(
                "SELECT * FROM task_reviews WHERE task_id = ? ORDER BY reviewed_at DESC LIMIT 1",
                (row["id"],),
            ).fetchone()
            review = None
            if review_row:
                review = {
                    "decision": review_row["decision"],
                    "notes": review_row["notes"],
                    "reviewed_by": review_row["reviewer_id"],
                    "reviewed_at": review_row["reviewed_at"],
                }
            tasks.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "provider": row["provider_name"],
                    "provider_id": row["provider_id"],
                    "priority": row["priority"],
                    "status": row["status"],
                    "category": row["category"],
                    "summary": row["summary"],
                    "approaches": _parse_json_list(row["approaches"]),
                    "signals": _parse_json_list(row["signals"]),
                    "attempts": attempts,
                    "review": review,
                    "last_action": row["last_action"],
                }
            )
    return tasks


def _task_summary(tasks=None):
    items = tasks if tasks is not None else _load_tasks()
    return {
        "total_tasks": len(items),
        "queued": sum(1 for task in items if task["status"] == "queued"),
        "in_review": sum(1 for task in items if task["status"] == "in-review"),
        "verified": sum(1 for task in items if task["status"] == "verified"),
    }


def get_worker_workspace(email: str):
    tasks = _load_tasks()
    return {
        "email": email,
        "tasks": tasks,
        "summary": _task_summary(tasks),
    }


def submit_attempt(token: str, payload: dict):
    worker = get_worker_by_token(token)
    if worker is None:
        raise ValueError("Invalid session.")

    task_id = payload.get("task_id")
    notes = (payload.get("notes") or "").strip()
    approach = (payload.get("approach") or "manual-review").strip()
    if not task_id or not notes:
        raise ValueError("Task and notes are required.")

    now = datetime.now(timezone.utc).isoformat()
    attempt_id = f"attempt-{uuid.uuid4().hex[:10]}"
    with get_connection() as conn:
        task = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task is None:
            raise ValueError("Task not found.")
        conn.execute(
            """INSERT INTO task_attempts (id, task_id, worker_id, approach, notes, evidence_urls, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (attempt_id, task_id, worker["id"], approach, notes, "[]", now),
        )
        conn.execute(
            "UPDATE tasks SET status = ?, last_action = ?, updated_at = ? WHERE id = ?",
            ("in-review", "Attempt captured", now, task_id),
        )
    log_audit(worker["id"], "task.attempt", "task", task_id, {"approach": approach})
    return {
        "task_id": task_id,
        "approach": approach,
        "notes": notes,
        "status": "in-review",
    }


def submit_review(token: str, payload: dict):
    worker = get_worker_by_token(token)
    if worker is None:
        raise ValueError("Invalid session.")

    task_id = payload.get("task_id")
    decision = payload.get("decision") or "pending"
    notes = payload.get("notes") or "Review submitted."
    if not task_id:
        raise ValueError("Task is required.")

    now = datetime.now(timezone.utc).isoformat()
    status = "verified" if decision == "approved" else "needs-revision"
    with get_connection() as conn:
        task = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task is None:
            raise ValueError("Task not found.")
        conn.execute(
            """INSERT INTO task_reviews (id, task_id, reviewer_id, decision, notes, requires_manager_approval, reviewed_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"review-{uuid.uuid4().hex[:10]}", task_id, worker["id"], decision, notes, 0, now, now),
        )
        conn.execute(
            "UPDATE tasks SET status = ?, last_action = ?, updated_at = ? WHERE id = ?",
            (status, f"Review marked as {decision}", now, task_id),
        )
    log_audit(worker["id"], "task.review", "task", task_id, {"decision": decision})
    return {
        "task_id": task_id,
        "decision": decision,
        "reviewer": worker["name"],
        "status": status,
    }


def run_research(provider_id=None):
    from app.services.monitor import scan_sources

    return scan_sources(provider_id)


def create_evidence(worker_token, offer_id, source_url, note):
    worker = get_worker_by_token(worker_token)
    if worker is None:
        raise ValueError("Invalid session.")
    if not offer_id or not source_url:
        raise ValueError("Offer and source URL are required.")
    now = datetime.now(timezone.utc).isoformat()
    evidence_id = "evidence-" + uuid.uuid4().hex[:8]
    with get_connection() as conn:
        offer = conn.execute("SELECT id FROM offers WHERE id = ?", (offer_id,)).fetchone()
        if offer is None:
            raise ValueError("Offer not found.")
        conn.execute(
            "INSERT INTO evidence (id, offer_id, source_url, note, validated_by, validated_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (evidence_id, offer_id, source_url, note, worker["name"], now, now),
        )
    log_audit(worker["id"], "evidence.create", "evidence", evidence_id, {"offer_id": offer_id})
    return {
        "id": evidence_id,
        "offer_id": offer_id,
        "source_url": source_url,
        "note": note,
        "validated_by": worker["name"],
    }
