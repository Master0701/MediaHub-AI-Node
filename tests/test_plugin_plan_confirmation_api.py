"""Tests für Plan-ID, Bestätigung und Abbruch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.plugin_plans as plan_api
from app.api.plugin_plans import router
from app.plugins.installer import PluginInstaller
from app.plugins.manager import PluginManager
from app.plugins.plan_store import PluginPlanStore
from app.security.api_token import API_TOKEN_ENV_NAME

VALID_TOKEN = "z" * 48


def create_package(path: Path) -> bytes:
    manifest = {
        "id": "provider.confirm-test",
        "name": "Confirm Test Provider",
        "version": "1.0.0",
        "type": "provider",
        "entrypoint": "plugin:TestPlugin",
        "enabled_by_default": True,
    }

    with ZipFile(path, "w") as archive:
        archive.writestr(
            "provider.confirm-test/plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "provider.confirm-test/plugin.py",
            "class TestPlugin:\n"
            "    name = 'confirm-test'\n",
        )
        archive.writestr(
            "provider.confirm-test/LICENSE",
            "MIT License\n",
        )

    return path.read_bytes()


@pytest.fixture
def client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    manager = PluginManager(
        plugin_root=tmp_path / "plugins",
        state_path=tmp_path / "plugin-state.json",
    )
    installer = PluginInstaller(
        plugin_root=tmp_path / "plugins",
        backup_root=tmp_path / "backups",
    )
    store = PluginPlanStore(ttl_minutes=15)

    monkeypatch.setattr(plan_api, "plugin_manager", manager)
    monkeypatch.setattr(plan_api, "plugin_installer", installer)
    monkeypatch.setattr(plan_api, "plugin_plan_store", store)
    monkeypatch.setenv(API_TOKEN_ENV_NAME, VALID_TOKEN)

    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


def create_plan(
    client: TestClient,
    body: bytes,
) -> tuple[str, str]:
    checksum = hashlib.sha256(body).hexdigest()

    response = client.post(
        "/plugins/plan",
        content=body,
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "Content-Type": "application/zip",
            "X-Plugin-SHA256": checksum,
            "X-Plugin-Filename": "plugin.zip",
        },
    )

    assert response.status_code == 200
    return response.json()["plan_id"], checksum


def test_confirm_plan_installs_plugin(
    tmp_path: Path,
    client: TestClient,
) -> None:
    body = create_package(tmp_path / "plugin.zip")
    plan_id, checksum = create_plan(client, body)

    response = client.post(
        f"/plugins/plan/{plan_id}/confirm",
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "X-Plugin-SHA256": checksum,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "installed"
    assert response.json()["plugin"]["id"] == "provider.confirm-test"


def test_plan_cannot_be_confirmed_twice(
    tmp_path: Path,
    client: TestClient,
) -> None:
    body = create_package(tmp_path / "plugin.zip")
    plan_id, checksum = create_plan(client, body)

    first = client.post(
        f"/plugins/plan/{plan_id}/confirm",
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "X-Plugin-SHA256": checksum,
        },
    )
    second = client.post(
        f"/plugins/plan/{plan_id}/confirm",
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "X-Plugin-SHA256": checksum,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 404


def test_wrong_checksum_is_rejected(
    tmp_path: Path,
    client: TestClient,
) -> None:
    body = create_package(tmp_path / "plugin.zip")
    plan_id, _ = create_plan(client, body)

    response = client.post(
        f"/plugins/plan/{plan_id}/confirm",
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "X-Plugin-SHA256": "0" * 64,
        },
    )

    assert response.status_code == 409


def test_cancel_plan(
    tmp_path: Path,
    client: TestClient,
) -> None:
    body = create_package(tmp_path / "plugin.zip")
    plan_id, _ = create_plan(client, body)

    response = client.delete(
        f"/plugins/plan/{plan_id}",
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
