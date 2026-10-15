from fastapi.testclient import TestClient
from app.config import settings
from app.main import app


def test_admin_endpoint_rejects_invalid_token(client):
    response = client.get(
        "/api/v1/operations/import-runs",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_admin_endpoint_requires_bearer_token(client):
    # TestClient defaults to the valid token; override it with an empty header value.
    response = client.get(
        "/api/v1/operations/import-runs",
        headers={"Authorization": ""},
    )
    assert response.status_code == 401


def test_admin_api_is_disabled_when_token_unconfigured(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_token", None)
    response = client.get("/api/v1/operations/import-runs")
    assert response.status_code == 503
    assert "disabled" in response.json()["detail"].lower()
