from app.services import monitor
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_scan_records_signals_without_live_network(monkeypatch):
    def fake_fetch(url: str):
        body = f"<html><body>Official pricing. Start a free trial for new users. Student eligibility applies. {url}</body></html>"
        return 200, body, None

    monkeypatch.setattr(monitor, "_fetch", fake_fetch)
    unique_email = f"scan-{__import__('uuid').uuid4().hex[:8]}@example.com"
    client.post("/api/auth/signup", json={"name": "Scan Worker", "email": unique_email, "password": "secretpass", "role": "researcher"})
    login = client.post("/api/auth/login", json={"email": unique_email, "password": "secretpass"})
    token = login.json()["token"]

    response = client.post("/api/monitor/run", headers={"Authorization": f"Bearer {token}"}, json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["scanned"] >= 1
    assert any(item["status"] == "checked" for item in payload["results"])

    signals = client.get("/api/signals").json()
    assert signals
    assert any(item["label"] == "free-trial" for item in signals)

    research = client.get("/api/research").json()
    assert research["checked_sources"] >= 1
    assert research["last_scan"] != "never"
