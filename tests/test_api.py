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


def test_provider_detail_endpoint_returns_provider_context():
    response = client.get('/api/providers/github')
    assert response.status_code == 200
    payload = response.json()
    assert payload['id'] == 'github'
    assert 'offers' in payload
    assert 'sources' in payload


def test_alerts_endpoint_returns_product_alerts():
    response = client.get('/api/alerts')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert 'title' in first
    assert 'severity' in first


def test_signup_creates_worker_account():
    unique_email = f"nora-{__import__('uuid').uuid4().hex[:8]}@example.com"
    payload = {
        'name': 'Nora Worker',
        'email': unique_email,
        'password': 'secretpass',
        'role': 'researcher',
    }
    response = client.post('/api/auth/signup', json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body['email'] == payload['email']
    assert 'token' in body
    assert body['role'] == 'researcher'


def test_login_returns_worker_profile_and_workspace():
    unique_email = f"nora-login-{__import__('uuid').uuid4().hex[:8]}@example.com"
    client.post('/api/auth/signup', json={
        'name': 'Nora Worker',
        'email': unique_email,
        'password': 'secretpass',
        'role': 'researcher',
    })
    payload = {
        'email': unique_email,
        'password': 'secretpass',
    }
    response = client.post('/api/auth/login', json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body['email'] == payload['email']
    assert 'workspace' in body
    assert 'tasks' in body['workspace']


def test_worker_can_submit_attempt_and_review():
    unique_email = f"worker-review-{__import__('uuid').uuid4().hex[:8]}@example.com"
    client.post('/api/auth/signup', json={'name': 'Review Worker', 'email': unique_email, 'password': 'secretpass', 'role': 'researcher'})
    login = client.post('/api/auth/login', json={'email': unique_email, 'password': 'secretpass'})
    token = login.json()['token']

    attempt = client.post(
        '/api/workspace/attempt',
        headers={'Authorization': f'Bearer {token}'},
        json={'task_id': 'gitlab-launch-window', 'approach': 'public-offer-page', 'notes': 'Checked launch terms and verified pricing page.'}
    )
    assert attempt.status_code == 200
    attempt_body = attempt.json()
    assert attempt_body['approach'] == 'public-offer-page'

    review = client.post(
        '/api/workspace/review',
        headers={'Authorization': f'Bearer {token}'},
        json={'task_id': 'gitlab-launch-window', 'decision': 'approved', 'notes': 'Offer is publicly documented and consistent.'}
    )
    assert review.status_code == 200
    review_body = review.json()
    assert review_body['decision'] == 'approved'


def test_worker_profile_hides_plaintext_password_and_uses_secure_workspace_data():
    unique_email = f"secure-{__import__('uuid').uuid4().hex[:8]}@example.com"
    response = client.post('/api/auth/signup', json={
        'name': 'Secure Worker',
        'email': unique_email,
        'password': 'verysecurepass',
        'role': 'analyst',
    })
    assert response.status_code == 200
    payload = response.json()
    assert 'password' not in payload
    assert len(payload['token']) > 20
    assert 'workspace' in payload
    assert payload['workspace']['summary']['total_tasks'] >= 1


def test_insights_endpoint_returns_operation_snapshot():
    response = client.get('/api/insights')
    assert response.status_code == 200
    payload = response.json()
    assert 'signals' in payload
    assert 'momentum_score' in payload
    assert payload['signals']


def test_analytics_endpoint_returns_review_pipeline_snapshot():
    response = client.get('/api/analytics')
    assert response.status_code == 200
    payload = response.json()
    assert 'pipeline' in payload
    assert 'trend' in payload
    assert isinstance(payload['pipeline'], list)
