"""SQLite repository helpers for Verity reference data."""

import json
import uuid
from datetime import datetime, timezone

from app.data.alerts import ALERT_LIBRARY
from app.data.offers import OFFER_LIBRARY
from app.data.providers import PROVIDER_LIBRARY
from app.data.sources import SOURCE_CATALOG
from app.data.tasks import TASK_LIBRARY
from app.db import get_connection


def _now():
    return datetime.now(timezone.utc).isoformat()


def seed_reference_data():
    with get_connection() as conn:
        for provider in PROVIDER_LIBRARY:
            conn.execute(
                """INSERT INTO providers (id, name, category, website, research_coverage, status, risk_level, source_count, signal, notes, last_scan, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     name=excluded.name, category=excluded.category, notes=excluded.notes""",
                (
                    provider["id"],
                    provider["name"],
                    provider["category"],
                    None,
                    provider["research_coverage"],
                    provider["status"],
                    provider["risk_level"],
                    provider["source_count"],
                    provider["signal"],
                    provider["notes"],
                    provider["last_scan"],
                    _now(),
                    _now(),
                ),
            )

        for source in SOURCE_CATALOG:
            existing = conn.execute("SELECT id FROM sources WHERE url = ?", (source["url"],)).fetchone()
            if existing:
                continue
            conn.execute(
                """INSERT INTO sources (id, provider_id, source_type, url, last_checked_at, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"source-{uuid.uuid4().hex[:8]}",
                    source["provider_id"],
                    source["source_type"],
                    source["url"],
                    None,
                    "pending",
                    _now(),
                    _now(),
                ),
            )

        offer_count = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
        if offer_count == 0:
            for offer in OFFER_LIBRARY:
                provider = next((item for item in PROVIDER_LIBRARY if item["name"] == offer["provider"]), None)
                if provider is None:
                    continue
                conn.execute(
                    """INSERT INTO offers (id, provider_id, title, product, category, offer_type, status, reward, eligibility, source_url, risk_level, official, verified, score, expires_at, notes, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"offer-{uuid.uuid4().hex[:8]}",
                        provider["id"],
                        offer.get("product", offer["provider"]),
                        offer["product"],
                        offer["category"],
                        offer["offer_type"],
                        offer["status"],
                        offer["reward"],
                        offer["eligibility"],
                        offer["source"],
                        offer["risk_level"],
                        int(offer["official"]),
                        int(offer["verified"]),
                        offer["score"],
                        offer["expires_at"],
                        offer["notes"],
                        _now(),
                        _now(),
                    ),
                )

        alert_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        if alert_count == 0:
            for alert in ALERT_LIBRARY:
                provider = next((item for item in PROVIDER_LIBRARY if item["name"] == alert.get("provider")), None)
                conn.execute(
                    """INSERT INTO alerts (id, title, message, provider_id, severity, status, last_checked, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        alert["id"],
                        alert["title"],
                        alert["message"],
                        provider["id"] if provider else None,
                        alert["severity"],
                        alert["status"],
                        alert["last_checked"],
                        _now(),
                        _now(),
                    ),
                )

        for task in TASK_LIBRARY:
            conn.execute(
                """INSERT INTO tasks (id, title, provider_id, provider_name, priority, status, category, summary, approaches, signals, last_action, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO NOTHING""",
                (
                    task["id"],
                    task["title"],
                    task["provider_id"],
                    task["provider_name"],
                    task["priority"],
                    task["status"],
                    task["category"],
                    task["summary"],
                    json.dumps(task["approaches"]),
                    json.dumps(task["signals"]),
                    None,
                    _now(),
                    _now(),
                ),
            )

        for provider in PROVIDER_LIBRARY:
            count = conn.execute(
                "SELECT COUNT(*) FROM sources WHERE provider_id = ?", (provider["id"],)
            ).fetchone()[0]
            conn.execute("UPDATE providers SET source_count = ? WHERE id = ?", (count, provider["id"]))


def _offer_from_row(row) -> dict:
    return {
        "id": row["id"],
        "provider": row["provider_name"],
        "provider_id": row["provider_id"],
        "product": row["product"],
        "category": row["category"],
        "offer_type": row["offer_type"],
        "status": row["status"],
        "reward": row["reward"],
        "eligibility": row["eligibility"],
        "source": row["source_url"],
        "risk_level": row["risk_level"],
        "official": bool(row["official"]),
        "verified": bool(row["verified"]),
        "score": row["score"],
        "expires_at": row["expires_at"],
        "notes": row["notes"],
    }


def get_providers():
    seed_reference_data()
    providers = []
    with get_connection() as conn:
        for row in conn.execute("SELECT * FROM providers ORDER BY name"):
            sources = [
                {"id": item["id"], "source_type": item["source_type"], "url": item["url"], "status": item["status"]}
                for item in conn.execute(
                    "SELECT id, source_type, url, status FROM sources WHERE provider_id = ?", (row["id"],)
                )
            ]
            providers.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "research_coverage": row["research_coverage"],
                    "status": row["status"],
                    "risk_level": row["risk_level"],
                    "source_count": row["source_count"],
                    "signal": row["signal"],
                    "last_scan": row["last_scan"],
                    "sources": sources,
                    "notes": row["notes"],
                }
            )
    return providers


def get_offers():
    seed_reference_data()
    offers = []
    with get_connection() as conn:
        for row in conn.execute(
            """SELECT offers.*, providers.name AS provider_name
               FROM offers JOIN providers ON providers.id = offers.provider_id
               ORDER BY offers.score DESC"""
        ):
            offers.append(_offer_from_row(row))
    return offers


def get_provider_detail(provider_id):
    seed_reference_data()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            return None
        sources = [
            {
                "id": item["id"],
                "source_type": item["source_type"],
                "url": item["url"],
                "status": item["status"],
                "http_status": item["http_status"],
                "last_checked_at": item["last_checked_at"],
                "error_message": item["error_message"],
            }
            for item in conn.execute("SELECT * FROM sources WHERE provider_id = ?", (provider_id,))
        ]
        offers = []
        for offer_row in conn.execute(
            "SELECT offers.*, providers.name AS provider_name FROM offers JOIN providers ON providers.id = offers.provider_id WHERE offers.provider_id = ?",
            (provider_id,),
        ):
            offers.append(_offer_from_row(offer_row))
        latest_signals = [
            {
                "label": item["label"],
                "snippet": item["snippet"],
                "weight": item["weight"],
                "created_at": item["created_at"],
            }
            for item in conn.execute(
                """SELECT * FROM source_signals WHERE provider_id = ? ORDER BY created_at DESC LIMIT 12""",
                (provider_id,),
            )
        ]
        return {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "research_coverage": row["research_coverage"],
            "status": row["status"],
            "risk_level": row["risk_level"],
            "source_count": row["source_count"],
            "signal": row["signal"],
            "last_scan": row["last_scan"],
            "notes": row["notes"],
            "offers": offers,
            "sources": sources,
            "live_signals": latest_signals,
        }


def get_alerts():
    seed_reference_data()
    alerts = []
    with get_connection() as conn:
        for row in conn.execute(
            """SELECT alerts.*, providers.name AS provider_name
               FROM alerts LEFT JOIN providers ON providers.id = alerts.provider_id
               ORDER BY alerts.created_at DESC"""
        ):
            alerts.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "message": row["message"],
                    "provider": row["provider_name"],
                    "severity": row["severity"],
                    "status": row["status"],
                    "last_checked": row["last_checked"],
                }
            )
    return alerts


def get_sources():
    seed_reference_data()
    sources = []
    with get_connection() as conn:
        for row in conn.execute(
            """SELECT sources.*, providers.name AS provider_name
               FROM sources JOIN providers ON providers.id = sources.provider_id
               ORDER BY providers.name, sources.source_type"""
        ):
            sources.append(
                {
                    "id": row["id"],
                    "provider": row["provider_name"],
                    "provider_id": row["provider_id"],
                    "source_type": row["source_type"],
                    "url": row["url"],
                    "status": row["status"],
                    "http_status": row["http_status"],
                    "last_checked_at": row["last_checked_at"],
                    "error_message": row["error_message"],
                    "content_hash": row["content_hash"],
                }
            )
    return sources


def get_signals(limit: int = 40):
    seed_reference_data()
    signals = []
    with get_connection() as conn:
        for row in conn.execute(
            """SELECT source_signals.*, providers.name AS provider_name, sources.url AS source_url
               FROM source_signals
               JOIN providers ON providers.id = source_signals.provider_id
               JOIN sources ON sources.id = source_signals.source_id
               ORDER BY source_signals.created_at DESC
               LIMIT ?""",
            (limit,),
        ):
            signals.append(
                {
                    "id": row["id"],
                    "provider": row["provider_name"],
                    "provider_id": row["provider_id"],
                    "label": row["label"],
                    "snippet": row["snippet"],
                    "weight": row["weight"],
                    "source_url": row["source_url"],
                    "created_at": row["created_at"],
                }
            )
    return signals


def get_latest_scan_time():
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(last_checked_at) AS last_scan FROM sources").fetchone()
        return row["last_scan"] if row else None


def get_research_runs(limit: int = 12):
    runs = []
    with get_connection() as conn:
        for row in conn.execute(
            """SELECT research_runs.*, providers.name AS provider_name
               FROM research_runs JOIN providers ON providers.id = research_runs.provider_id
               ORDER BY research_runs.created_at DESC LIMIT ?""",
            (limit,),
        ):
            runs.append(
                {
                    "id": row["id"],
                    "provider": row["provider_name"],
                    "triggered_at": row["triggered_at"],
                    "source_count": row["source_count"],
                    "findings": row["findings"],
                    "confidence": row["confidence"],
                    "status": row["status"],
                }
            )
    return runs
