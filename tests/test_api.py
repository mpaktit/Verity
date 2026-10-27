from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get('/api/health')
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'


def test_offers_endpoint_returns_list():
    response = client.get('/api/offers')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_offers_include_provider_and_status():
    response = client.get('/api/offers')
    offers = response.json()
    first = offers[0]
    assert 'provider' in first
    assert 'status' in first


def test_providers_endpoint_returns_provider_data():
    response = client.get('/api/providers')
    assert response.status_code == 200
    providers = response.json()
    assert isinstance(providers, list)
    assert len(providers) >= 1
    first = providers[0]
    assert 'name' in first
    assert 'research_coverage' in first


def test_monitor_endpoint_has_research_clock_and_sources():
    response = client.get('/api/research')
    assert response.status_code == 200
    payload = response.json()
    assert 'total_sources' in payload
    assert 'active_providers' in payload
    assert 'last_scan' in payload
