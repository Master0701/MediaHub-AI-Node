"""Tests für den geschützten Installationsplan-Endpunkt."""

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
from app.plugins.manager import PluginManager
from app.security.api_token import API_TOKEN_ENV_NAME

VALID_TOKEN = "q" * 48


def create_package(
    path: Path,
    *,
    include_license: bool = True,
    requirements: str | None = None,
) -> bytes:
    manifest = {
        "id": "provider.plan-test",
        "name": "Plan Test Provider",
        "version": "1.0.0",
        "type": "provider",
        "entrypoint": "plugin:TestPlugin",
        "enabled_by_default": True,
    }

    with ZipFile(path, "w") as archive:
        archive.writestr(
            "provider.plan-test/plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "provider.plan-test/plugin.py",
            "class TestPlugin:\n"
            "    name = 'plan-test'\n",
        )

        if include_license:
            archive.writestr(
                "provider.plan-test/LICENSE",
                "MIT License\n",
            )

        if requirements is not None:
            archive.writestr(
                "provider.plan-test/requirements.txt",
                requirements,
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
    manager.discover()

    monkeypatch.setattr(plan_api, "plugin_manager", manager)
    monkeypatch.setenv(API_TOKEN_ENV_NAME, VALID_TOKEN)

    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


def post_plan(
    client: TestClient,
    body: bytes,
) -> object:
    return client.post(
        "/plugins/plan",
        content=body,
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "Content-Type": "application/zip",
            "X-Plugin-SHA256": hashlib.sha256(body).hexdigest(),
            "X-Plugin-Filename": "plugin.zip",
        },
    )


def test_ready_plan(
    tmp_path: Path,
    client: TestClient,
) -> None:
    body = create_package(tmp_path / "plugin.zip")

    response = post_plan(client, body)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "plan_created"
    assert data["plan"]["ready_without_changes"] is True
    assert data["package"]["plugin_id"] == "provider.plan-test"


def test_missing_package_returns_action(
    tmp_path: Path,
    client: TestClient,
) -> None:
    body = create_package(
        tmp_path / "plugin.zip",
        requirements="definitely-missing-plan-package-xyz==1.0.0\n",
    )

    response = post_plan(client, body)

    assert response.status_code == 200
    plan = response.json()["plan"]
    assert plan["ready_without_changes"] is False
    assert plan["missing_count"] == 1
    assert plan["actions"][0]["type"] == "python_package"


def test_missing_license_is_reported_in_plan(
    tmp_path: Path,
    client: TestClient,
) -> None:
    body = create_package(
        tmp_path / "plugin.zip",
        include_license=False,
    )

    response = post_plan(client, body)

    assert response.status_code == 200
    plan = response.json()["plan"]
    assert plan["license_present"] is False
    assert plan["ready_without_changes"] is False


def test_plan_requires_token(
    tmp_path: Path,
    client: TestClient,
) -> None:
    body = create_package(tmp_path / "plugin.zip")

    response = client.post(
        "/plugins/plan",
        content=body,
        headers={
            "Content-Type": "application/zip",
            "X-Plugin-SHA256": hashlib.sha256(body).hexdigest(),
        },
    )

    assert response.status_code == 401
