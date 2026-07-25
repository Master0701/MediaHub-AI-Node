"""Tests für Lizenz-, Tool- und Abhängigkeitsprüfung."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.plugins.package_validator import validate_plugin_package
from app.plugins.preflight import (
    PluginPreflightChecker,
    PluginPreflightError,
)


def create_package(
    path: Path,
    *,
    include_license: bool = True,
    requirements: str | None = None,
    required_tools: list[str] | None = None,
    dependencies: list[dict[str, str]] | None = None,
) -> None:
    manifest = {
        "id": "provider.preflight",
        "name": "Preflight Provider",
        "version": "1.0.0",
        "type": "provider",
        "entrypoint": "plugin:TestPlugin",
        "required_tools": required_tools or [],
        "dependencies": dependencies or [],
    }

    with ZipFile(path, "w") as archive:
        archive.writestr(
            "provider.preflight/plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "provider.preflight/plugin.py",
            "class TestPlugin:\n    pass\n",
        )

        if include_license:
            archive.writestr(
                "provider.preflight/LICENSE",
                "MIT License\n",
            )

        if requirements is not None:
            archive.writestr(
                "provider.preflight/requirements.txt",
                requirements,
            )


def test_valid_package_without_requirements(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_package(archive_path)

    package = validate_plugin_package(archive_path)
    result = PluginPreflightChecker().check(package)

    assert result.ready is True
    assert result.license_present is True
    assert result.warnings


def test_missing_license_is_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_package(
        archive_path,
        include_license=False,
    )

    package = validate_plugin_package(archive_path)

    with pytest.raises(
        PluginPreflightError,
        match="Lizenzdatei",
    ):
        PluginPreflightChecker().check(package)


def test_missing_python_package_is_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_package(
        archive_path,
        requirements="definitely-not-installed-package-xyz==1.0.0\n",
    )

    package = validate_plugin_package(archive_path)

    with pytest.raises(
        PluginPreflightError,
        match="Fehlende",
    ):
        PluginPreflightChecker().check(package)


def test_missing_tool_is_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_package(
        archive_path,
        required_tools=["definitely-not-a-real-tool-xyz"],
    )

    package = validate_plugin_package(archive_path)

    with pytest.raises(
        PluginPreflightError,
        match="Fehlende",
    ):
        PluginPreflightChecker().check(package)


def test_plugin_dependency_is_checked(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_package(
        archive_path,
        dependencies=[
            {
                "id": "provider.base",
                "minimum_version": "1.0.0",
            }
        ],
    )

    package = validate_plugin_package(archive_path)

    result = PluginPreflightChecker(
        installed_plugin_ids={"provider.base"}
    ).check(package)

    assert result.ready is True
    assert result.plugin_dependencies[0].available is True


def test_invalid_requirement_syntax_is_rejected(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "plugin.zip"
    create_package(
        archive_path,
        requirements="-r https://example.invalid/requirements.txt\n",
    )

    package = validate_plugin_package(archive_path)

    with pytest.raises(
        PluginPreflightError,
        match="Nicht unterstützte",
    ):
        PluginPreflightChecker().check(package)
