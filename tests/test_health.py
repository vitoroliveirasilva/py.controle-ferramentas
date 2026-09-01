from __future__ import annotations


def test_health_check_returns_ok(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["environment"] == "testing"


def test_readiness_check_marks_database_and_auth_as_ok(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["authentication"] in {
        "microsoft_configured",
        "dev_login_enabled",
    }
