import hashlib
import httpx
from app.db import get_connection

def scan_sources(provider_id=None):
    results = []
    with get_connection() as conn:
        query = "SELECT * FROM sources"
        params = ()
        if provider_id:
            query += " WHERE provider_id = ?"
            params = (provider_id,)
        sources = conn.execute(query, params).fetchall()
        for source in sources:
            url = source["url"]
            status = "error"
            http_status = None
            content_hash = None
            error_message = None
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True, headers={"User-Agent": "Verity-Public-Research/0.3"}) as client:
                    response = client.get(url)
                    http_status = response.status_code
                    content_hash = hashlib.sha256(response.text.encode("utf-8", errors="ignore")).hexdigest()
                    status = "checked" if response.status_code < 400 else "http_error"
            except Exception as exc:
                error_message = str(exc)[:500]
                status = "error"
            now = _now()
            conn.execute(
                """UPDATE sources SET http_status = ?, content_hash = ?, last_checked_at = ?, status = ?, error_message = ?, updated_at = ?
                   WHERE id = ?""",
                (http_status, content_hash, now, status, error_message, now, source["id"]),
            )
            results.append({
                "source_id": source["id"],
                "provider_id": source["provider_id"],
                "url": url,
                "http_status": http_status,
                "status": status,
                "error": error_message,
            })
        # research run record per provider
        providers = {r["id"]: r for r in conn.execute("SELECT * FROM providers").fetchall()}
        scanned_providers = {s["provider_id"] for s in results}
        for pid in scanned_providers:
            conn.execute(
                """INSERT INTO research_runs (id, provider_id, triggered_at, source_count, findings, confidence, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"run-{uuid.uuid4().hex[:10]}", pid, _now(), sum(1 for r in results if r["provider_id"] == pid),
                 "Automated public-source scan completed.", 0.8, "completed", _now()),
            )
    return {"scanned": len(results), "results": results}
