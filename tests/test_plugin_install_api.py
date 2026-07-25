"""Tests für den geschützten Plugin-Installationsendpunkt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

import app.api.plugins as plugins_api
from app.main import app
from app.plugins.installer import PluginInstaller
from app.plugins.manager import PluginManager
from app.security.api_token import API_TOKEN_ENV_NAME

VALID_TOKEN = "t" * 48


def create_plugin_zip(path: Path) -> bytes:
    manifest = {
        "id": "provider.api-test",
        "name": "API Test Provider",
        "version": "1.0.0",
        "type": "provider",
        "entrypoint": "plugin:TestPlugin",
        "enabled_by_default": True,
    }

    with ZipFile(path, "w") as archive:
        archive.writestr(
            "provider.api-test/plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "provider.api-test/plugin.py",
            "class TestPlugin:\n"
            "    name = 'api-test'\n",
        )
        archive.writestr(
            "provider.api-test/LICENSE",
            "MIT License\n",
        )

    return path.read_bytes()


@pytest.fixture
def isolated_plugin_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = PluginManager(
        plugin_root=tmp_path / "plugins",
        state_path=tmp_path / "plugin-state.json",
    )
    installer = PluginInstaller(
        plugin_root=tmp_path / "plugins",
        backup_root=tmp_path / "backups",
    )

    monkeypatch.setattr(plugins_api, "plugin_manager", manager)
    monkeypatch.setattr(plugins_api, "plugin_installer", installer)
    monkeypatch.setenv(API_TOKEN_ENV_NAME, VALID_TOKEN)


def test_install_plugin_endpoint(
    tmp_path: Path,
    isolated_plugin_runtime: None,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    body = create_plugin_zip(archive_path)
    checksum = hashlib.sha256(body).hexdigest()

    with TestClient(app) as client:
        response = client.post(
            "/plugins/install",
            content=body,
            headers={
                "Authorization": f"Bearer {VALID_TOKEN}",
                "Content-Type": "application/zip",
                "X-Plugin-SHA256": checksum,
                "X-Plugin-Filename": "plugin.zip",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "installed"
    assert data["plugin"]["id"] == "provider.api-test"
    assert data["plugin"]["loaded"] is True


def test_install_requires_token(
    tmp_path: Path,
    isolated_plugin_runtime: None,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    body = create_plugin_zip(archive_path)
    checksum = hashlib.sha256(body).hexdigest()

    with TestClient(app) as client:
        response = client.post(
            "/plugins/install",
            content=body,
            headers={
                "Content-Type": "application/zip",
                "X-Plugin-SHA256": checksum,
            },
        )

    assert response.status_code == 401


def test_install_rejects_wrong_checksum(
    tmp_path: Path,
    isolated_plugin_runtime: None,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    body = create_plugin_zip(archive_path)

    with TestClient(app) as client:
        response = client.post(
            "/plugins/install",
            content=body,
            headers={
                "Authorization": f"Bearer {VALID_TOKEN}",
                "Content-Type": "application/zip",
                "X-Plugin-SHA256": "0" * 64,
            },
        )

    assert response.status_code == 400
    assert "Prüfsumme" in response.json()["detail"]


def test_install_rejects_wrong_content_type(
    tmp_path: Path,
    isolated_plugin_runtime: None,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    body = create_plugin_zip(archive_path)
    checksum = hashlib.sha256(body).hexdigest()

    with TestClient(app) as client:
        response = client.post(
            "/plugins/install",
            content=body,
            headers={
                "Authorization": f"Bearer {VALID_TOKEN}",
                "Content-Type": "application/octet-stream",
                "X-Plugin-SHA256": checksum,
            },
        )

    assert response.status_code == 415
