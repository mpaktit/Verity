"""Public-source monitoring: fetch official pages, extract signals, store evidence."""

from __future__ import annotations

import hashlib
import uuid

import httpx

from app.config import settings
from app.db import get_connection
from app.services.extractor import extract_signals, score_page
from app.services.repository import _now


def _fetch(url: str) -> tuple[int | None, str, str | None]:
    headers = {"User-Agent": settings.USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        with httpx.Client(timeout=settings.CRAWL_TIMEOUT_SECONDS, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            return response.status_code, response.text[:200_000], None
    except Exception as exc:  # noqa: BLE001 - record any fetch failure as source error
        return None, "", str(exc)[:500]


def scan_sources(provider_id: str | None = None) -> dict:
    results: list[dict] = []
    now = _now()

    with get_connection() as conn:
        query = "SELECT * FROM sources"
        params: tuple = ()
        if provider_id:
            query += " WHERE provider_id = ?"
            params = (provider_id,)
        query += " ORDER BY provider_id, source_type"
        sources = conn.execute(query, params).fetchall()

        scanned_providers: set[str] = set()
        for source in sources:
            url = source["url"]
            previous_hash = source["content_hash"]
            http_status, body, error_message = _fetch(url)
            content_hash = hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest() if body else None
            signals = extract_signals(body) if body else []
            signal_score = score_page(signals, http_status)
            changed = bool(previous_hash and content_hash and previous_hash != content_hash)

            if http_status is None:
                status = "error"
            elif http_status >= 400:
                status = "http_error"
            else:
                status = "checked"

            conn.execute(
                """UPDATE sources
                   SET http_status = ?, content_hash = ?, last_content = ?, last_checked_at = ?,
                       status = ?, error_message = ?, updated_at = ?
                   WHERE id = ?""",
                (http_status, content_hash, body[:8000] if body else None, now, status, error_message, now, source["id"]),
            )
            conn.execute(
                """INSERT INTO source_snapshots (id, source_id, http_status, content_hash, signal_score, changed, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"snap-{uuid.uuid4().hex[:12]}", source["id"], http_status, content_hash, signal_score, int(changed), now),
            )
            for signal in signals:
                conn.execute(
                    """INSERT INTO source_signals (id, source_id, provider_id, label, snippet, weight, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"sig-{uuid.uuid4().hex[:12]}",
                        source["id"],
                        source["provider_id"],
                        signal["label"],
                        signal["snippet"][:500],
                        signal["weight"],
                        now,
                    ),
                )

            if changed:
                conn.execute(
                    """INSERT INTO alerts (id, title, message, provider_id, severity, status, last_checked, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"alert-{uuid.uuid4().hex[:10]}",
                        "Official source changed",
                        f"Content hash changed on {url}. Re-review eligibility language before acting.",
                        source["provider_id"],
                        "medium",
                        "active",
                        now,
                        now,
                        now,
                    ),
                )

            labels = [item["label"] for item in signals]
            conn.execute(
                "UPDATE providers SET last_scan = ?, updated_at = ?, signal = COALESCE(?, signal) WHERE id = ?",
                (now, now, ", ".join(labels[:4]) or None, source["provider_id"]),
            )
            scanned_providers.add(source["provider_id"])
            results.append(
                {
                    "source_id": source["id"],
                    "provider_id": source["provider_id"],
                    "url": url,
                    "http_status": http_status,
                    "status": status,
                    "changed": changed,
                    "signal_score": signal_score,
                    "signals": labels,
                    "error": error_message,
                }
            )

        for pid in scanned_providers:
            provider_results = [item for item in results if item["provider_id"] == pid]
            checked = sum(1 for item in provider_results if item["status"] == "checked")
            coverage = round((checked / max(len(provider_results), 1)) * 100, 1)
            conn.execute(
                "UPDATE providers SET research_coverage = ?, source_count = ?, status = ?, updated_at = ? WHERE id = ?",
                (
                    coverage,
                    len(provider_results),
                    "active" if coverage >= 50 else "monitoring",
                    now,
                    pid,
                ),
            )
            conn.execute(
                """INSERT INTO research_runs (id, provider_id, triggered_at, source_count, findings, confidence, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"run-{uuid.uuid4().hex[:10]}",
                    pid,
                    now,
                    len(provider_results),
                    f"Public scan complete. {checked}/{len(provider_results)} sources reachable.",
                    round(coverage / 100, 2),
                    "completed",
                    now,
                ),
            )

    return {"scanned": len(results), "results": results, "completed_at": now}
