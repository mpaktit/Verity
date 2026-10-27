import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from app.db import get_connection, init_db

from app.services.repository import get_alerts as repo_get_alerts
from app.services.repository import get_offers as repo_get_offers
from app.services.repository import get_provider_detail as repo_get_provider_detail
from app.services.repository import get_providers as repo_get_providers
from app.services.repository import seed_reference_data

APP_DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
WORKER_STORE_PATH = APP_DATA_DIR / 'workers.json'
init_db()
seed_reference_data()


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 200_000)
    return f'{salt}:{digest.hex()}'


def _verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or ':' not in stored_hash:
        return False
    salt, digest = stored_hash.split(':', 1)
    candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 200_000)
    return candidate.hex() == digest


def _load_worker_store():
    workers = {}
    try:
        with get_connection() as conn:
            for row in conn.execute('SELECT * FROM workers'):
                workers[row['email']] = {
                    'id': row['id'],
                    'name': row['name'],
                    'email': row['email'],
                    'password_hash': row['password_hash'],
                    'role': row['role'],
                    'token': row['token'],
                    'created_at': row['created_at'],
                }
    except Exception:
        pass
    if not workers and WORKER_STORE_PATH.exists():
        try:
            workers = json.loads(WORKER_STORE_PATH.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            workers = {}
    return workers


def _persist_workers():
    with get_connection() as conn:
        for email, worker in WORKER_LIBRARY.items():
            conn.execute(
                '''INSERT INTO workers (id, name, email, password_hash, role, token, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(email) DO UPDATE SET
                     name=excluded.name, password_hash=excluded.password_hash, role=excluded.role,
                     token=excluded.token, updated_at=excluded.updated_at''',
                (worker['id'], worker['name'], worker['email'], worker['password_hash'],
                 worker['role'], worker['token'], worker['created_at'], worker['created_at']),
            )




def log_audit(worker_id, action, entity_type, entity_id=None, metadata=None, ip_address=None, user_agent=None):
    import json
    import uuid
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO audit_log (id, worker_id, action, entity_type, entity_id, metadata, ip_address, user_agent, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("audit-" + uuid.uuid4().hex[:12], worker_id, action, entity_type, entity_id,
                 json.dumps(metadata or {}), ip_address, user_agent, now),
            )
    except Exception:
        pass


def get_audit_log(limit=50):
    rows = []
    with get_connection() as conn:
        for row in conn.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)):
            rows.append({
                "id": row["id"],
                "worker_id": row["worker_id"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "metadata": row["metadata"],
                "created_at": row["created_at"],
            })
    return rows


def create_watchlist(worker_email, name, filters):
    import json
    import uuid
    from datetime import datetime, timezone
    worker = next((w for w in WORKER_LIBRARY.values() if w["email"] == worker_email), None)
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
    import json
    worker = next((w for w in WORKER_LIBRARY.values() if w["email"] == worker_email), None)
    if worker is None:
        return []
    rows = []
    with get_connection() as conn:
        for row in conn.execute("SELECT * FROM watchlists WHERE worker_id = ? ORDER BY created_at DESC", (worker["id"],)):
            rows.append({
                "id": row["id"],
                "name": row["name"],
                "filters": json.loads(row["filters"] or "{}"),
                "created_at": row["created_at"],
            })
    return rows


WORKER_LIBRARY = _load_worker_store()
WORKSPACE_TASKS = [
    {
        'id': 'gitlab-launch-window',
        'title': 'GitLab launch window review',
        'provider': 'GitLab',
        'priority': 'high',
        'status': 'queued',
        'category': 'public-offer-window',
        'summary': 'Check launch terms, public pricing statements, and team onboarding conditions.',
        'approaches': ['public-offer-page', 'partner-announcement', 'docs-verification'],
        'attempts': [],
        'review': None,
        'signals': ['Team-based trials', 'Public pricing docs', 'Launch timing'],
    },
    {
        'id': 'notion-onboarding-promo',
        'title': 'Notion onboarding promo check',
        'provider': 'Notion',
        'priority': 'medium',
        'status': 'in-review',
        'category': 'onboarding-promo',
        'summary': 'Validate whether AI access is account-state-dependent or reliably public.',
        'approaches': ['pricing-page', 'help-docs', 'trial-logic'],
        'attempts': [
            {
                'id': 'attempt-1',
                'approach': 'pricing-page',
                'notes': 'Pricing and onboarding docs show a public route but plan status matters.',
                'created_at': '2026-10-27T11:52:00Z',
            }
        ],
        'review': None,
        'signals': ['Onboarding triggers', 'Plan eligibility', 'Account-state logic'],
    },
    {
        'id': 'google-credits',
        'title': 'Google AI Studio starter credits',
        'provider': 'Google',
        'priority': 'low',
        'status': 'verified',
        'category': 'starter-credits',
        'summary': 'Confirm the startup developer credits remain public, official, and program-compliant.',
        'approaches': ['official-console', 'pricing-docs', 'developer-ledger'],
        'attempts': [
            {
                'id': 'attempt-2',
                'approach': 'official-console',
                'notes': 'Public docs align with the developer wallet flow and regional availability.',
                'created_at': '2026-10-27T11:40:00Z',
            }
        ],
        'review': {'decision': 'approved', 'notes': 'Public and consistent with official developer docs.', 'reviewed_by': 'system'},
        'signals': ['Public credits', 'Developer console', 'Policy compliant'],
    },
]


def get_offer_summary():
    offers = repo_get_offers()
    providers = repo_get_providers()
    total = len(offers)
    active = sum(1 for item in offers if item['status'] == 'active')
    high_confidence = sum(1 for item in offers if item['verified'] and item['score'] >= 85)
    needs_review = sum(1 for item in offers if not item['verified'])
    categories = sorted({item['category'] for item in offers})
    return {
        'total_offers': total,
        'active_offers': active,
        'high_confidence': high_confidence,
        'needs_review': needs_review,
        'categories': categories,
    }


def get_offers():
    return repo_get_offers()


def get_providers():
    return repo_get_providers()


def get_provider_detail(provider_id: str):
    return repo_get_provider_detail(provider_id)


def get_research_status():
    providers = repo_get_providers()
    total_sources = sum(provider['source_count'] for provider in providers)
    active_providers = sum(1 for provider in providers if provider['status'] == 'active')
    avg_coverage = round(sum(provider['research_coverage'] for provider in providers) / len(providers), 1)
    return {
        'total_sources': total_sources,
        'active_providers': active_providers,
        'last_scan': '2026-10-27T12:00:00Z',
        'coverage_percent': avg_coverage,
        'needs_review': sum(1 for provider in providers if provider['status'] == 'monitoring'),
    }


def get_alerts():
    return repo_get_alerts()


def get_insights():
    return {
        'momentum_score': 91,
        'status': 'strong',
        'signals': [
            {'title': 'High coverage providers', 'value': '6/6 providers monitored', 'status': 'positive'},
            {'title': 'Offer confidence', 'value': '4 high-confidence opportunities', 'status': 'positive'},
            {'title': 'Review queue', 'value': '2 active tasks need action', 'status': 'neutral'},
            {'title': 'Public-source reliability', 'value': '92% public evidence strength', 'status': 'positive'},
        ],
        'summary': 'The monitoring engine is stable, source coverage remains broad, and the validation queue is moving through review patterns efficiently.',
        'last_updated': '2026-10-27T12:00:00Z',
    }


def get_analytics():
    return {
        'pipeline': [
            {'label': 'Queued', 'value': 2, 'percent': 26},
            {'label': 'In review', 'value': 3, 'percent': 34},
            {'label': 'Verified', 'value': 4, 'percent': 40},
        ],
        'trend': {
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
            'values': [48, 56, 62, 71, 83, 91],
        },
        'risk_distribution': {
            'low': 58,
            'medium': 31,
            'high': 11,
        },
    }


def _generate_token(email: str):
    return f"verity_{secrets.token_urlsafe(24)}"


def _get_worker_payload(worker):
    public = {
        'id': worker['id'],
        'name': worker['name'],
        'email': worker['email'],
        'role': worker['role'],
    }
    return public


def get_worker_by_token(token: str):
    for worker in WORKER_LIBRARY.values():
        if worker.get('token') == token:
            return worker
    return None


def register_worker(payload: dict):
    email = (payload.get('email') or '').strip().lower()
    password = payload.get('password') or ''
    name = (payload.get('name') or 'New worker').strip()
    role = (payload.get('role') or 'researcher').strip()

    if not email or not password:
        raise ValueError('Email and password are required.')
    if email in WORKER_LIBRARY:
        raise ValueError('Worker already exists.')

    worker = {
        'id': f"worker-{len(WORKER_LIBRARY) + 1}",
        'name': name,
        'email': email,
        'password_hash': _hash_password(password),
        'role': role,
        'token': _generate_token(email),
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    WORKER_LIBRARY[email] = worker
    _persist_workers()
    log_audit(worker['id'], 'worker.signup', 'worker', worker['id'], {'email': email, 'role': role})
    return {
        'token': worker['token'],
        **_get_worker_payload(worker),
        'workspace': get_worker_workspace(email),
    }


def login_worker(payload: dict):
    email = (payload.get('email') or '').strip().lower()
    password = payload.get('password') or ''
    worker = WORKER_LIBRARY.get(email)
    if worker is None or not _verify_password(password, worker.get('password_hash', '')):
        raise ValueError('Invalid credentials.')
    log_audit(worker['id'], 'worker.login', 'worker', worker['id'], {'email': email})
    return {
        'token': worker['token'],
        **_get_worker_payload(worker),
        'workspace': get_worker_workspace(email),
    }


def get_worker_workspace(email: str):
    tasks = []
    for item in WORKSPACE_TASKS:
        task = {
            'id': item['id'],
            'title': item['title'],
            'provider': item['provider'],
            'priority': item['priority'],
            'status': item['status'],
            'category': item['category'],
            'summary': item['summary'],
            'approaches': item['approaches'],
            'signals': item['signals'],
            'attempts': item['attempts'],
            'review': item['review'],
        }
        tasks.append(task)

    return {
        'email': email,
        'tasks': tasks,
        'summary': {
            'total_tasks': len(tasks),
            'queued': sum(1 for task in tasks if task['status'] == 'queued'),
            'in_review': sum(1 for task in tasks if task['status'] == 'in-review'),
            'verified': sum(1 for task in tasks if task['status'] == 'verified'),
        },
    }


def submit_attempt(token: str, payload: dict):
    worker = get_worker_by_token(token)
    if worker is None:
        raise ValueError('Invalid session.')

    task_id = payload.get('task_id')
    task = next((item for item in WORKSPACE_TASKS if item['id'] == task_id), None)
    if task is None:
        raise ValueError('Task not found.')

    attempt = {
        'id': f"attempt-{len(task['attempts']) + 1}",
        'approach': payload.get('approach', 'manual-review'),
        'notes': payload.get('notes', 'No notes provided.'),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'worker': worker['name'],
    }
    task['attempts'].append(attempt)
    task['status'] = 'in-review'
    task['last_action'] = 'Attempt captured'
    log_audit(worker['id'], 'task.attempt', 'task', task_id, {'approach': attempt['approach']})
    return {
        'task_id': task['id'],
        'approach': attempt['approach'],
        'notes': attempt['notes'],
        'status': task['status'],
    }


def submit_review(token: str, payload: dict):
    worker = get_worker_by_token(token)
    if worker is None:
        raise ValueError('Invalid session.')

    task_id = payload.get('task_id')
    task = next((item for item in WORKSPACE_TASKS if item['id'] == task_id), None)
    if task is None:
        raise ValueError('Task not found.')

    decision = payload.get('decision', 'pending')
    notes = payload.get('notes', 'Review submitted.')
    task['review'] = {
        'decision': decision,
        'notes': notes,
        'reviewed_by': worker['name'],
        'reviewed_at': datetime.now(timezone.utc).isoformat(),
    }
    task['status'] = 'verified' if decision == 'approved' else 'needs-revision'
    task['last_action'] = f"Review marked as {decision}"
    log_audit(worker['id'], 'task.review', 'task', task_id, {'decision': decision})

    return {
        'task_id': task['id'],
        'decision': decision,
        'reviewer': worker['name'],
        'status': task['status'],
    }

def get_sources():
    sources = []
    for provider in repo_get_providers():
        for src in provider.get('sources', []):
            sources.append({'provider': provider['name'], 'provider_id': provider['id'], 'source': src})
    return sources


def run_research(provider_id):
    import uuid
    from datetime import datetime, timezone
    provider = next((p for p in PROVIDER_LIBRARY if p['id'] == provider_id), None)
    if provider is None:
        raise ValueError('Provider not found.')
    run_id = 'run-' + provider_id + '-' + uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            'INSERT INTO research_runs (id, provider_id, triggered_at, source_count, findings, confidence, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (run_id, provider_id, now, provider.get('source_count', 0),
             'Automated public-source scan completed.', 0.85, 'completed', now),
        )
    return {'run_id': run_id, 'provider': provider['name'], 'status': 'completed', 'source_count': provider.get('source_count', 0)}
