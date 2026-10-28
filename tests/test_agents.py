"""Tests for AI agent system."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_agents_status_requires_auth():
    """Agent status endpoint requires authentication."""
    response = client.get("/api/agents/status")
    assert response.status_code == 401


def test_agents_status_returns_orchestrator_data():
    """Agent status returns orchestrator information."""
    # First create a worker and login
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.get("/api/agents/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "queue" in data
    assert "agents" in data


def test_agents_start_requires_auth():
    """Starting agents requires authentication."""
    response = client.post("/api/agents/start")
    assert response.status_code == 401


def test_agents_start_returns_success():
    """Starting agents returns success response."""
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent2@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.post("/api/agents/start", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_agents_stop_requires_auth():
    """Stopping agents requires authentication."""
    response = client.post("/api/agents/stop")
    assert response.status_code == 401


def test_agents_jobs_requires_auth():
    """Listing jobs requires authentication."""
    response = client.get("/api/agents/jobs")
    assert response.status_code == 401


def test_agents_jobs_returns_list():
    """Jobs endpoint returns list of jobs."""
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent3@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.get("/api/agents/jobs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


def test_agents_memory_requires_auth():
    """Accessing agent memory requires authentication."""
    response = client.get("/api/agents/memory")
    assert response.status_code == 401


def test_agents_memory_returns_list():
    """Memory endpoint returns list of memories."""
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent4@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.get("/api/agents/memory", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "memories" in data
    assert isinstance(data["memories"], list)


def test_agents_logs_requires_auth():
    """Accessing agent logs requires authentication."""
    response = client.get("/api/agents/logs")
    assert response.status_code == 401


def test_agents_logs_returns_list():
    """Logs endpoint returns list of logs."""
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent5@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.get("/api/agents/logs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert isinstance(data["logs"], list)


def test_ai_keys_requires_auth():
    """Listing API keys requires authentication."""
    response = client.get("/api/ai/keys")
    assert response.status_code == 401


def test_ai_keys_returns_list():
    """API keys endpoint returns list of keys."""
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent6@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.get("/api/ai/keys", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert isinstance(data["keys"], list)


def test_ai_keys_add_requires_auth():
    """Adding API keys requires authentication."""
    response = client.post(
        "/api/ai/keys",
        json={
            "provider": "anthropic",
            "key_name": "Test Key",
            "api_key": "sk-ant-test123",
        },
    )
    assert response.status_code == 401


def test_ai_keys_add_success():
    """Adding API key succeeds with valid data."""
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent7@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.post(
        "/api/ai/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "provider": "anthropic",
            "key_name": "Test Key",
            "api_key": "sk-ant-test123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "added"


def test_ai_models_requires_auth():
    """Listing AI models requires authentication."""
    response = client.get("/api/ai/models")
    assert response.status_code == 401


def test_ai_models_returns_list():
    """AI models endpoint returns list of available models."""
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent8@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.get("/api/ai/models", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)


def test_agents_research_requires_auth():
    """Triggering research requires authentication."""
    response = client.post("/api/agents/research", json={})
    assert response.status_code == 401


def test_agents_research_returns_job_count():
    """Triggering research returns job creation count."""
    signup_response = client.post(
        "/api/auth/signup",
        json={
            "name": "Test Agent User",
            "email": "agent9@test.com",
            "password": "testpassword123",
            "role": "researcher",
        },
    )
    token = signup_response.json()["token"]

    response = client.post(
        "/api/agents/research",
        headers={"Authorization": f"Bearer {token}"},
        json={"platform": "twitter"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "jobs_created" in data
