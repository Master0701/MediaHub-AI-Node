from __future__ import annotations

import json
import zipfile

from windows_compute_node.plugins.installer import (
    ComputePluginInstaller,
)
from windows_compute_node.plugins.loader import (
    ComputePluginLoader,
)
from windows_compute_node.workers.registry import (
    WorkerRegistry,
)


def make_shared_provider_package(tmp_path):
    package = tmp_path / "provider.mhaiplugin"

    manifest = {
        "id": "provider.mediahub_test",
        "name": "MediaHub AI Test Provider",
        "version": "1.0.0",
        "type": "provider",
        "entrypoint": "plugin:MediaHubAITestProvider",
        "api_version": "1",
        "targets": [
            "raspberry_pi",
            "windows_compute",
        ],
        "platforms": [
            "linux-aarch64",
            "windows-amd64",
        ],
        "required_capabilities": [],
    }

    plugin_code = """
class MediaHubAITestProvider:
    plugin_id = "provider.mediahub_test"
    name = "MediaHub AI Test Provider"
    version = "1.0.0"

    def health(self):
        return {
            "status": "online",
            "plugin_id": self.plugin_id,
        }

    def test(self, value="MediaHub"):
        return {
            "ok": True,
            "provider": self.plugin_id,
            "value": str(value),
        }
"""

    prefix = "provider.mediahub_test/"

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            prefix + "plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            prefix + "plugin.py",
            plugin_code,
        )

    return package


def test_shared_provider_package_installs_and_loads(
    tmp_path,
):
    plugin_root = tmp_path / "installed"

    installer = ComputePluginInstaller(
        plugin_root=plugin_root
    )

    package = make_shared_provider_package(
        tmp_path
    )

    inspected = installer.inspect_package(
        package
    )

    assert inspected["type"] == "provider"
    assert (
        inspected["entrypoint"]
        == "plugin:MediaHubAITestProvider"
    )

    result = installer.install(package)

    assert result["installed"] is True

    installed = (
        plugin_root / "provider.mediahub_test"
    )

    assert (
        installed / "plugin.json"
    ).is_file()

    assert (
        installed / "plugin.py"
    ).is_file()

    # Es darf keine zweite Paketebene entstehen.
    assert not (
        installed
        / "provider.mediahub_test"
        / "plugin.json"
    ).exists()

    workers = WorkerRegistry()

    loader = ComputePluginLoader(
        plugin_root=plugin_root,
        workers=workers,
    )

    loaded = loader.load_all()

    assert len(loaded) == 1

    plugin = loaded[0]

    assert plugin["loaded"] is True
    assert (
        plugin["plugin_id"]
        == "provider.mediahub_test"
    )
    assert plugin["type"] == "provider"
    assert plugin["workers"] == []

    # Laufzeitobjekte dürfen nicht im öffentlichen
    # Plugin-Ergebnis landen, weil dieses über die
    # JSON-API zurückgegeben wird.
    assert "instance" not in plugin

    instance = loader.instances[
        "provider.mediahub_test"
    ]

    health = instance.health()

    assert health["status"] == "online"
    assert (
        health["plugin_id"]
        == "provider.mediahub_test"
    )

    test_result = instance.test("Windows")

    assert test_result == {
        "ok": True,
        "provider": "provider.mediahub_test",
        "value": "Windows",
    }
