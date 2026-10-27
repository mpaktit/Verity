"""SQLite repository helpers for Verity reference data."""

import json
import uuid
from datetime import datetime, timezone

from app.data.alerts import ALERT_LIBRARY
from app.data.offers import OFFER_LIBRARY
from app.data.providers import PROVIDER_LIBRARY
from app.data.sources import SOURCE_CATALOG
from app.db import get_connection


def _now():
    return datetime.now(timezone.utc).isoformat()


def seed_reference_data():
    with get_connection() as conn:
        provider_count = conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
        if provider_count == 0:
            for provider in PROVIDER_LIBRARY:
                conn.execute(
                    """INSERT INTO providers (id, name, category, website, research_coverage, status, risk_level, source_count, signal, notes, last_scan, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (provider["id"], provider["name"], provider["category"], None,
                     provider["research_coverage"], provider["status"], provider["risk_level"],
                     provider["source_count"], provider["signal"], provider["notes"],
                     provider["last_scan"], _now(), _now()),
                )

        source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        if source_count == 0:
            for source in SOURCE_CATALOG:
                conn.execute(
                    """INSERT INTO sources (id, provider_id, source_type, url, last_checked_at, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (f"source-{uuid.uuid4().hex[:8]}", source["provider_id"], source["source_type"], source["url"],
                     None, "pending", _now(), _now()),
                )

        offer_count = conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0]
        if offer_count == 0:
            for offer in OFFER_LIBRARY:
                provider = next((p for p in PROVIDER_LIBRARY if p["name"] == offer["provider"]), None)
                if provider is None:
                    continue
                conn.execute(
                    """INSERT INTO offers (id, provider_id, title, product, category, offer_type, status, reward, eligibility, source_url, risk_level, official, verified, score, expires_at, notes, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (f"offer-{uuid.uuid4().hex[:8]}", provider["id"], offer.get("product", offer["provider"]), offer["product"],
                     offer["category"], offer["offer_type"], offer["status"], offer["reward"], offer["eligibility"],
                     offer["source"], offer["risk_level"], int(offer["official"]), int(offer["verified"]), offer["score"],
                     offer["expires_at"], offer["notes"], _now(), _now()),
                )

        alert_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        if alert_count == 0:
            for alert in ALERT_LIBRARY:
                provider = next((p for p in PROVIDER_LIBRARY if p["name"] == alert.get("provider")), None)
                conn.execute(
                    """INSERT INTO alerts (id, title, message, provider_id, severity, status, last_checked, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (alert["id"], alert["title"], alert["message"], provider["id"] if provider else None,
                     alert["severity"], alert["status"], alert["last_checked"], _now(), _now()),
                )


def get_providers():
    seed_reference_data()
    providers = []
    with get_connection() as conn:
        for row in conn.execute("SELECT * FROM providers ORDER BY name"):
            sources = [r["source_type"] for r in conn.execute("SELECT source_type FROM sources WHERE provider_id = ?", (row["id"],))]
            providers.append({
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
            })
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
            offers.append({
                "provider": row["provider_name"],
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
            })
    return offers


def get_provider_detail(provider_id):
    seed_reference_data()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            return None
        sources = [r["source_type"] for r in conn.execute("SELECT source_type FROM sources WHERE provider_id = ?", (provider_id,))]
        offers = []
        for offer_row in conn.execute(
            "SELECT offers.*, providers.name AS provider_name FROM offers JOIN providers ON providers.id = offers.provider_id WHERE offers.provider_id = ?",
            (provider_id,),
        ):
            offers.append({
                "provider": offer_row["provider_name"],
                "product": offer_row["product"],
                "category": offer_row["category"],
                "offer_type": offer_row["offer_type"],
                "status": offer_row["status"],
                "reward": offer_row["reward"],
                "eligibility": offer_row["eligibility"],
                "source": offer_row["source_url"],
                "risk_level": offer_row["risk_level"],
                "official": bool(offer_row["official"]),
                "verified": bool(offer_row["verified"]),
                "score": offer_row["score"],
                "expires_at": offer_row["expires_at"],
                "notes": offer_row["notes"],
            })
        provider = {
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
        return {**provider, "offers": offers, "sources": sources}


def get_alerts():
    seed_reference_data()
    alerts = []
    with get_connection() as conn:
        for row in conn.execute(
            """SELECT alerts.*, providers.name AS provider_name
               FROM alerts LEFT JOIN providers ON providers.id = alerts.provider_id
               ORDER BY alerts.created_at DESC"""
        ):
            alerts.append({
                "id": row["id"],
                "title": row["title"],
                "message": row["message"],
                "provider": row["provider_name"],
                "severity": row["severity"],
                "status": row["status"],
                "last_checked": row["last_checked"],
            })
    return alerts
