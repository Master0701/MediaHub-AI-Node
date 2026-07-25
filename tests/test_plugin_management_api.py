"""Tests für Aktivierung, Entfernung, Backup und Rollback."""

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

VALID_TOKEN = "m" * 48
AUTH_HEADERS = {"Authorization": f"Bearer {VALID_TOKEN}"}


def create_plugin_zip(
    path: Path,
    *,
    version: str = "1.0.0",
    marker: str = "erste-version",
) -> bytes:
    manifest = {
        "id": "provider.manage-test",
        "name": "Manage Test Provider",
        "version": version,
        "type": "provider",
        "entrypoint": "plugin:TestPlugin",
        "enabled_by_default": True,
    }

    with ZipFile(path, "w") as archive:
        archive.writestr(
            "provider.manage-test/plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "provider.manage-test/plugin.py",
            "class TestPlugin:\n"
            f"    marker = {marker!r}\n",
        )
        archive.writestr(
            "provider.manage-test/LICENSE",
            "MIT License\n",
        )

    return path.read_bytes()


@pytest.fixture
def runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PluginManager, PluginInstaller]:
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

    return manager, installer


def install_via_api(
    client: TestClient,
    tmp_path: Path,
    *,
    version: str = "1.0.0",
    marker: str = "erste-version",
) -> None:
    archive_path = tmp_path / f"{version}.zip"
    body = create_plugin_zip(
        archive_path,
        version=version,
        marker=marker,
    )
    checksum = hashlib.sha256(body).hexdigest()

    response = client.post(
        "/plugins/install",
        content=body,
        headers={
            **AUTH_HEADERS,
            "Content-Type": "application/zip",
            "X-Plugin-SHA256": checksum,
            "X-Plugin-Filename": archive_path.name,
        },
    )

    assert response.status_code == 201


def test_disable_and_enable_plugin(
    tmp_path: Path,
    runtime: tuple[PluginManager, PluginInstaller],
) -> None:
    with TestClient(app) as client:
        install_via_api(client, tmp_path)

        disabled = client.post(
            "/plugins/provider.manage-test/disable",
            headers=AUTH_HEADERS,
        )
        enabled = client.post(
            "/plugins/provider.manage-test/enable",
            headers=AUTH_HEADERS,
        )

    assert disabled.status_code == 200
    assert disabled.json()["plugin"]["enabled"] is False
    assert enabled.status_code == 200
    assert enabled.json()["plugin"]["enabled"] is True


def test_remove_plugin_creates_backup(
    tmp_path: Path,
    runtime: tuple[PluginManager, PluginInstaller],
) -> None:
    with TestClient(app) as client:
        install_via_api(client, tmp_path)

        response = client.delete(
            "/plugins/provider.manage-test",
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "removed"
    assert response.json()["backup_created"] is True


def test_list_backups_and_rollback(
    tmp_path: Path,
    runtime: tuple[PluginManager, PluginInstaller],
) -> None:
    with TestClient(app) as client:
        install_via_api(
            client,
            tmp_path,
            version="1.0.0",
            marker="alt",
        )
        install_via_api(
            client,
            tmp_path,
            version="1.1.0",
            marker="neu",
        )

        backups = client.get(
            "/plugins/provider.manage-test/backups",
            headers=AUTH_HEADERS,
        )

        backup_name = backups.json()["backups"][0]["name"]

        rollback = client.post(
            f"/plugins/provider.manage-test/rollback/{backup_name}",
            headers=AUTH_HEADERS,
        )

    assert backups.status_code == 200
    assert backups.json()["count"] == 1
    assert rollback.status_code == 200
    assert rollback.json()["status"] == "restored"


def test_management_requires_token(
    tmp_path: Path,
    runtime: tuple[PluginManager, PluginInstaller],
) -> None:
    with TestClient(app) as client:
        install_via_api(client, tmp_path)

        response = client.post(
            "/plugins/provider.manage-test/disable"
        )

    assert response.status_code == 401
