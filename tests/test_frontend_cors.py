from fastapi.testclient import TestClient
from app.main import app


def test_local_frontend_origin_is_allowed_for_read_only_api():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/sources/status",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_untrusted_frontend_origin_is_not_allowed():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/sources/status",
            headers={
                "Origin": "https://example.invalid",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert "access-control-allow-origin" not in response.headers
