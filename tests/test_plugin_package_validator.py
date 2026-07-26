"""Tests für die sichere Prüfung von AI-Plugin-Paketen."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.plugins.package_validator import (
    PluginPackageError,
    calculate_sha256,
    validate_plugin_package,
)


def create_valid_package(path: Path) -> None:
    manifest = {
        "id": "provider.test",
        "name": "Test Provider",
        "version": "1.0.0",
        "type": "provider",
        "entrypoint": "plugin:TestPlugin",
    }

    with ZipFile(path, "w") as archive:
        archive.writestr(
            "provider.test/plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "provider.test/plugin.py",
            "class TestPlugin:\n    pass\n",
        )


        archive.writestr(
            "provider.test/README.md",
            "# Testplugin\n",
        )
        archive.writestr(
            "provider.test/CHANGELOG.md",
            "# Changelog\n\n## v1.0.0\n\n- Testversion\n",
        )
        archive.writestr(
            "provider.test/requirements.txt",
            "# Keine zusätzlichen Python-Abhängigkeiten.\n",
        )
def test_valid_plugin_package(tmp_path: Path) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_valid_package(archive_path)

    result = validate_plugin_package(
        archive_path,
        expected_sha256=calculate_sha256(archive_path),
    )

    assert result.manifest.plugin_id == "provider.test"
    assert result.root_directory == "provider.test"
    assert result.file_count == 5


def test_wrong_checksum_is_rejected(tmp_path: Path) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_valid_package(archive_path)

    with pytest.raises(PluginPackageError, match="Prüfsumme"):
        validate_plugin_package(
            archive_path,
            expected_sha256="0" * 64,
        )


def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive_path = tmp_path / "plugin.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr("../plugin.json", "{}")

    with pytest.raises(PluginPackageError, match="Unsicherer Pfad"):
        validate_plugin_package(archive_path)


def test_multiple_root_directories_are_rejected(tmp_path: Path) -> None:
    archive_path = tmp_path / "plugin.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr("plugin-a/plugin.json", "{}")
        archive.writestr("plugin-b/file.txt", "test")

    with pytest.raises(PluginPackageError, match="obersten"):
        validate_plugin_package(archive_path)


def test_missing_manifest_is_rejected(tmp_path: Path) -> None:
    archive_path = tmp_path / "plugin.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr("provider.test/plugin.py", "pass\n")

    with pytest.raises(PluginPackageError, match="plugin.json"):
        validate_plugin_package(archive_path)
