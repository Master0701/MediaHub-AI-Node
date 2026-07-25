"""Tests für die schreibgeschützte AI-Plugin-API."""

from fastapi.testclient import TestClient

from app.main import app


def test_plugin_list_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/plugins")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["count"], int)
    assert isinstance(data["plugins"], list)


def test_unknown_plugin_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/plugins/not-installed")

    assert response.status_code == 404
    assert response.json()["detail"] == "AI-Plugin nicht gefunden."


def test_health_contains_plugin_status() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert set(response.json()["plugins"]) == {
        "detected",
        "enabled",
        "loaded",
        "errors",
    }
