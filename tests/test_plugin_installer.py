"""Tests für Installation, Backup und Rollback von AI-Plugins."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from app.plugins.installer import PluginInstaller
from app.plugins.package_validator import calculate_sha256


def create_package(
    path: Path,
    *,
    version: str,
    marker: str,
) -> None:
    manifest = {
        "id": "provider.test",
        "name": "Test Provider",
        "version": version,
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
            f"MARKER = {marker!r}\n",
        )
        archive.writestr(
            "provider.test/LICENSE",
            "MIT License\n",
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
def test_fresh_install(tmp_path: Path) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_package(
        archive_path,
        version="1.0.0",
        marker="erste-version",
    )

    installer = PluginInstaller(
        plugin_root=tmp_path / "plugins",
        backup_root=tmp_path / "backups",
    )

    result = installer.install(
        archive_path,
        expected_sha256=calculate_sha256(archive_path),
    )

    assert result.plugin_id == "provider.test"
    assert result.version == "1.0.0"
    assert result.replaced_existing is False
    assert result.backup_path is None
    assert result.preflight.ready is True
    assert (result.install_path / "plugin.json").is_file()
    assert "erste-version" in (
        result.install_path / "plugin.py"
    ).read_text(encoding="utf-8")


def test_update_creates_backup(tmp_path: Path) -> None:
    installer = PluginInstaller(
        plugin_root=tmp_path / "plugins",
        backup_root=tmp_path / "backups",
    )

    first_archive = tmp_path / "first.zip"
    second_archive = tmp_path / "second.zip"

    create_package(
        first_archive,
        version="1.0.0",
        marker="alt",
    )
    create_package(
        second_archive,
        version="1.1.0",
        marker="neu",
    )

    installer.install(first_archive)
    result = installer.install(second_archive)

    assert result.replaced_existing is True
    assert result.backup_path is not None
    assert result.backup_path.is_dir()

    installed_text = (
        result.install_path / "plugin.py"
    ).read_text(encoding="utf-8")
    backup_text = (
        result.backup_path / "plugin.py"
    ).read_text(encoding="utf-8")

    assert "neu" in installed_text
    assert "alt" in backup_text


def test_rollback_restores_backup(tmp_path: Path) -> None:
    installer = PluginInstaller(
        plugin_root=tmp_path / "plugins",
        backup_root=tmp_path / "backups",
    )

    first_archive = tmp_path / "first.zip"
    second_archive = tmp_path / "second.zip"

    create_package(
        first_archive,
        version="1.0.0",
        marker="alt",
    )
    create_package(
        second_archive,
        version="1.1.0",
        marker="neu",
    )

    installer.install(first_archive)
    update_result = installer.install(second_archive)

    restored_path = installer.rollback(
        plugin_id="provider.test",
        backup_path=update_result.backup_path,
    )

    restored_text = (
        restored_path / "plugin.py"
    ).read_text(encoding="utf-8")

    assert "alt" in restored_text


def test_list_backups(tmp_path: Path) -> None:
    installer = PluginInstaller(
        plugin_root=tmp_path / "plugins",
        backup_root=tmp_path / "backups",
    )

    first_archive = tmp_path / "first.zip"
    second_archive = tmp_path / "second.zip"

    create_package(
        first_archive,
        version="1.0.0",
        marker="alt",
    )
    create_package(
        second_archive,
        version="1.1.0",
        marker="neu",
    )

    installer.install(first_archive)
    installer.install(second_archive)

    backups = installer.list_backups("provider.test")

    assert len(backups) == 1
    assert backups[0].is_dir()
