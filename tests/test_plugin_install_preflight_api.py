"""Tests für die integrierte Installations-Vorabprüfung."""

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

VALID_TOKEN = "p" * 48


def create_package(
    path: Path,
    *,
    include_license: bool = True,
    requirements: str | None = None,
    dependencies: list[dict[str, str]] | None = None,
) -> bytes:
    manifest = {
        "id": "provider.preflight-api",
        "name": "Preflight API Provider",
        "version": "1.0.0",
        "type": "provider",
        "entrypoint": "plugin:TestPlugin",
        "enabled_by_default": True,
        "dependencies": dependencies or [],
    }

    with ZipFile(path, "w") as archive:
        archive.writestr(
            "provider.preflight-api/plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "provider.preflight-api/plugin.py",
            "class TestPlugin:\n"
            "    name = 'preflight-api'\n",
        )

        if include_license:
            archive.writestr(
                "provider.preflight-api/LICENSE",
                "MIT License\n",
            )

        archive.writestr(
            "provider.preflight-api/requirements.txt",
            requirements
            if requirements is not None
            else "# Keine zusätzlichen Python-Abhängigkeiten.\n",
        )
        archive.writestr(
            "provider.preflight-api/README.md",
            "# Testplugin\n",
        )
        archive.writestr(
            "provider.preflight-api/CHANGELOG.md",
            "# Changelog\n\n## v1.0.0\n\n- Testversion\n",
        )

    return path.read_bytes()


@pytest.fixture
def runtime(
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


def post_package(
    client: TestClient,
    body: bytes,
) -> object:
    return client.post(
        "/plugins/install",
        content=body,
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "Content-Type": "application/zip",
            "X-Plugin-SHA256": hashlib.sha256(body).hexdigest(),
            "X-Plugin-Filename": "plugin.zip",
        },
    )


def test_install_returns_preflight_result(
    tmp_path: Path,
    runtime: None,
) -> None:
    body = create_package(tmp_path / "plugin.zip")

    with TestClient(app) as client:
        response = post_package(client, body)

    assert response.status_code == 201
    assert response.json()["preflight"]["ready"] is True
    assert response.json()["preflight"]["license_present"] is True


def test_install_rejects_missing_license(
    tmp_path: Path,
    runtime: None,
) -> None:
    body = create_package(
        tmp_path / "plugin.zip",
        include_license=False,
    )

    with TestClient(app) as client:
        response = post_package(client, body)

    assert response.status_code == 400
    assert "Lizenzdatei" in response.json()["detail"]


def test_install_rejects_missing_python_dependency(
    tmp_path: Path,
    runtime: None,
) -> None:
    body = create_package(
        tmp_path / "plugin.zip",
        requirements="definitely-missing-mediahub-package-xyz==1.0.0\n",
    )

    with TestClient(app) as client:
        response = post_package(client, body)

    assert response.status_code == 400
    assert "Fehlende Plugin-Voraussetzungen" in response.json()["detail"]


def test_install_rejects_missing_plugin_dependency(
    tmp_path: Path,
    runtime: None,
) -> None:
    body = create_package(
        tmp_path / "plugin.zip",
        dependencies=[
            {
                "id": "provider.required",
                "minimum_version": "1.0.0",
            }
        ],
    )

    with TestClient(app) as client:
        response = post_package(client, body)

    assert response.status_code == 400
    assert "provider.required" in response.json()["detail"]
