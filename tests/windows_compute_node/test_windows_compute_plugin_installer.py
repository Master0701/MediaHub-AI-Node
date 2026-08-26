from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from windows_compute_node.plugins.installer import (
    ComputePluginInstaller,
    PluginInstallError,
)


def make_package(
    root: Path,
    *,
    name: str = "test.mhaiplugin",
    plugin_id: str = "test.plugin",
    plugin_type: str = "ai_node",
    include_entrypoint: bool = True,
):
    package = root / name

    manifest = {
        "id": plugin_id,
        "name": "Test Plugin",
        "version": "1.0.0",
        "plugin_type": plugin_type,
        "entrypoint": "plugin.py",
    }

    with zipfile.ZipFile(
        package,
        "w",
    ) as archive:
        archive.writestr(
            "plugin.json",
            json.dumps(manifest),
        )

        if include_entrypoint:
            archive.writestr(
                "plugin.py",
                "def register(context):\n"
                "    pass\n",
            )

    return package


def test_inspect_valid_package(
    tmp_path,
):
    installer = ComputePluginInstaller(
        plugin_root=(
            tmp_path / "installed"
        )
    )

    package = make_package(
        tmp_path
    )

    manifest = (
        installer.inspect_package(
            package
        )
    )

    assert manifest["id"] == (
        "test.plugin"
    )


def test_install_package(
    tmp_path,
):
    plugin_root = (
        tmp_path / "installed"
    )

    installer = ComputePluginInstaller(
        plugin_root=plugin_root
    )

    package = make_package(
        tmp_path
    )

    result = installer.install(
        package
    )

    assert result["installed"] is True

    target = (
        plugin_root
        / "test.plugin"
    )

    assert (
        target / "plugin.json"
    ).is_file()

    assert (
        target / "plugin.py"
    ).is_file()


def test_wrong_extension_fails(
    tmp_path,
):
    package = (
        tmp_path / "bad.zip"
    )

    package.write_bytes(b"test")

    installer = ComputePluginInstaller(
        plugin_root=(
            tmp_path / "installed"
        )
    )

    with pytest.raises(
        PluginInstallError
    ):
        installer.inspect_package(
            package
        )


def test_wrong_plugin_type_fails(
    tmp_path,
):
    installer = ComputePluginInstaller(
        plugin_root=(
            tmp_path / "installed"
        )
    )

    package = make_package(
        tmp_path,
        plugin_type="mediahub",
    )

    with pytest.raises(
        PluginInstallError
    ):
        installer.inspect_package(
            package
        )


def test_missing_entrypoint_fails_install(
    tmp_path,
):
    installer = ComputePluginInstaller(
        plugin_root=(
            tmp_path / "installed"
        )
    )

    package = make_package(
        tmp_path,
        include_entrypoint=False,
    )

    with pytest.raises(
        PluginInstallError
    ):
        installer.install(
            package
        )


def test_existing_plugin_requires_replace(
    tmp_path,
):
    installer = ComputePluginInstaller(
        plugin_root=(
            tmp_path / "installed"
        )
    )

    package = make_package(
        tmp_path
    )

    installer.install(package)

    with pytest.raises(
        PluginInstallError
    ):
        installer.install(package)


def test_replace_existing_plugin(
    tmp_path,
):
    installer = ComputePluginInstaller(
        plugin_root=(
            tmp_path / "installed"
        )
    )

    package = make_package(
        tmp_path
    )

    installer.install(package)

    result = installer.install(
        package,
        replace=True,
    )

    assert result["installed"] is True


def test_path_traversal_fails(
    tmp_path,
):
    package = (
        tmp_path
        / "evil.mhaiplugin"
    )

    manifest = {
        "id": "evil.plugin",
        "name": "Evil",
        "version": "1.0.0",
        "plugin_type": "ai_node",
        "entrypoint": "plugin.py",
    }

    with zipfile.ZipFile(
        package,
        "w",
    ) as archive:
        archive.writestr(
            "plugin.json",
            json.dumps(manifest),
        )

        archive.writestr(
            "../evil.py",
            "bad = True",
        )

        archive.writestr(
            "plugin.py",
            "def register(context): pass",
        )

    installer = ComputePluginInstaller(
        plugin_root=(
            tmp_path / "installed"
        )
    )

    with pytest.raises(
        PluginInstallError
    ):
        installer.inspect_package(
            package
        )
