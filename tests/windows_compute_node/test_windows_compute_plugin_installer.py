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


def test_nested_package_entrypoint_cannot_escape_package_root(
    tmp_path,
):
    package = (
        tmp_path
        / "nested_escape.mhaiplugin"
    )

    manifest = {
        "id": "nested.plugin",
        "name": "Nested Plugin",
        "version": "1.0.0",
        "plugin_type": "ai_node",
        "entrypoint": "../outside.py",
    }

    with zipfile.ZipFile(
        package,
        "w",
    ) as archive:
        archive.writestr(
            "nested.plugin/plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "outside.py",
            "def register(context): pass",
        )

    installer = ComputePluginInstaller(
        plugin_root=(
            tmp_path / "installed"
        )
    )

    with pytest.raises(
        PluginInstallError,
        match="Entrypoint liegt",
    ):
        installer.install(
            package
        )


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


def test_install_fails_when_python_runtime_dependency_missing(tmp_path):
    plugin_root = tmp_path / "installed"
    installer = ComputePluginInstaller(plugin_root=plugin_root)

    package = tmp_path / "smolvlm2.mhaiplugin"

    manifest = {
        "id": "mediahub.smolvlm2",
        "name": "MediaHub SmolVLM2",
        "version": "0.1.1",
        "type": "provider",
        "entrypoint": "plugin.py",
        "targets": ["windows_compute"],
        "dependencies": [
            {
                "id": "mediahub.python_runtime",
                "minimum_version": "0.1.0",
                "targets": ["windows_compute"],
            }
        ],
    }

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest))
        archive.writestr(
            "plugin.py",
            "def register(context):\n    pass\n",
        )

    with pytest.raises(PluginInstallError, match="mediahub.python_runtime"):
        installer.install(package)

    assert not (plugin_root / "mediahub.smolvlm2").exists()


def test_install_fails_when_python_runtime_version_too_old(tmp_path):
    plugin_root = tmp_path / "installed"
    runtime_dir = plugin_root / "mediahub.python_runtime"
    runtime_dir.mkdir(parents=True)

    (runtime_dir / "plugin.json").write_text(
        json.dumps({
            "id": "mediahub.python_runtime",
            "version": "0.0.9",
        }),
        encoding="utf-8",
    )

    package = tmp_path / "smolvlm2.mhaiplugin"
    manifest = {
        "id": "mediahub.smolvlm2",
        "name": "MediaHub SmolVLM2",
        "version": "0.1.1",
        "type": "provider",
        "entrypoint": "plugin.py",
        "targets": ["windows_compute"],
        "dependencies": [
            {
                "id": "mediahub.python_runtime",
                "minimum_version": "0.1.0",
                "targets": ["windows_compute"],
            }
        ],
    }

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest))
        archive.writestr(
            "plugin.py",
            "def register(context):\\n    pass\\n".replace("\\n", "\n"),
        )

    installer = ComputePluginInstaller(plugin_root=plugin_root)

    with pytest.raises(PluginInstallError, match="mediahub.python_runtime"):
        installer.install(package)

    assert not (plugin_root / "mediahub.smolvlm2").exists()


def test_uninstall_blocks_required_python_runtime(tmp_path):
    plugin_root = tmp_path / "installed"

    runtime_dir = plugin_root / "mediahub.python_runtime"
    runtime_dir.mkdir(parents=True)

    (runtime_dir / "plugin.json").write_text(
        json.dumps({
            "id": "mediahub.python_runtime",
            "name": "MediaHub Python Runtime",
            "version": "0.1.0",
        }),
        encoding="utf-8",
    )

    smolvlm_dir = plugin_root / "mediahub.smolvlm2"
    smolvlm_dir.mkdir()

    (smolvlm_dir / "plugin.json").write_text(
        json.dumps({
            "id": "mediahub.smolvlm2",
            "version": "0.1.1",
            "dependencies": [
                {
                    "id": "mediahub.python_runtime",
                    "minimum_version": "0.1.0",
                    "targets": ["windows_compute"],
                }
            ],
        }),
        encoding="utf-8",
    )

    installer = ComputePluginInstaller(plugin_root=plugin_root)

    with pytest.raises(PluginInstallError, match="mediahub.smolvlm2"):
        installer.uninstall("mediahub.python_runtime")

    assert runtime_dir.is_dir()
    assert (runtime_dir / "plugin.json").is_file()


def test_install_rejects_corrupt_dependency_manifest(tmp_path):
    plugin_root = tmp_path / "installed"
    runtime_dir = plugin_root / "mediahub.python_runtime"
    runtime_dir.mkdir(parents=True)

    (runtime_dir / "plugin.json").write_text(
        "{invalid json",
        encoding="utf-8",
    )

    package = tmp_path / "smolvlm2.mhaiplugin"
    manifest = {
        "id": "mediahub.smolvlm2",
        "name": "MediaHub SmolVLM2",
        "version": "0.1.1",
        "type": "provider",
        "entrypoint": "plugin.py",
        "targets": ["windows_compute"],
        "dependencies": [{
            "id": "mediahub.python_runtime",
            "minimum_version": "0.1.0",
            "targets": ["windows_compute"],
        }],
    }

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest))
        archive.writestr("plugin.py", "def register(context):\n    pass\n")

    installer = ComputePluginInstaller(plugin_root=plugin_root)

    with pytest.raises(PluginInstallError, match="mediahub.python_runtime"):
        installer.install(package)

    assert not (plugin_root / "mediahub.smolvlm2").exists()


def test_install_rejects_wrong_dependency_identity(tmp_path):
    plugin_root = tmp_path / "installed"
    runtime_dir = plugin_root / "mediahub.python_runtime"
    runtime_dir.mkdir(parents=True)

    (runtime_dir / "plugin.json").write_text(
        json.dumps({
            "id": "mediahub.wrong_runtime",
            "version": "0.1.0",
        }),
        encoding="utf-8",
    )

    package = tmp_path / "smolvlm2.mhaiplugin"
    manifest = {
        "id": "mediahub.smolvlm2",
        "name": "MediaHub SmolVLM2",
        "version": "0.1.1",
        "type": "provider",
        "entrypoint": "plugin.py",
        "targets": ["windows_compute"],
        "dependencies": [{
            "id": "mediahub.python_runtime",
            "minimum_version": "0.1.0",
            "targets": ["windows_compute"],
        }],
    }

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest))
        archive.writestr(
            "plugin.py",
            "def register(context):\n    pass\n",
        )

    installer = ComputePluginInstaller(plugin_root=plugin_root)

    with pytest.raises(PluginInstallError, match="mediahub.python_runtime"):
        installer.install(package)

    assert not (plugin_root / "mediahub.smolvlm2").exists()



def test_install_rejects_dependency_path_traversal(tmp_path):
    plugin_root = tmp_path / "installed"
    plugin_root.mkdir()

    # Eine fremde Datei ausserhalb des Plugin-Verzeichnisses.
    outside = tmp_path / "outside"
    outside.mkdir()

    (outside / "plugin.json").write_text(
        json.dumps({
            "id": "../outside",
            "version": "0.1.0",
        }),
        encoding="utf-8",
    )

    package = tmp_path / "smolvlm2.mhaiplugin"

    manifest = {
        "id": "mediahub.smolvlm2",
        "name": "MediaHub SmolVLM2",
        "version": "0.1.1",
        "type": "provider",
        "entrypoint": "plugin.py",
        "targets": ["windows_compute"],
        "dependencies": [{
            "id": "../outside",
            "minimum_version": "0.1.0",
            "targets": ["windows_compute"],
        }],
    }

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest))
        archive.writestr(
            "plugin.py",
            "def register(context):\\n    pass\\n",
        )

    installer = ComputePluginInstaller(plugin_root=plugin_root)

    with pytest.raises(PluginInstallError):
        installer.install(package)

    assert not (plugin_root / "mediahub.smolvlm2").exists()
    assert (outside / "plugin.json").is_file()
