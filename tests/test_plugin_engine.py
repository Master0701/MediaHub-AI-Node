"""Tests für Manifest, Erkennung, Laden und Plugin-Zustände."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.plugins.manager import PluginManager
from app.plugins.manifest import PluginManifest, PluginManifestError


def write_plugin(
    root: Path,
    *,
    plugin_id: str = "test.provider",
    enabled_by_default: bool = True,
) -> Path:
    plugin_root = root / plugin_id
    plugin_root.mkdir(parents=True)

    manifest = {
        "id": plugin_id,
        "name": "Test Provider",
        "version": "1.0.0",
        "type": "provider",
        "entrypoint": "plugin:TestPlugin",
        "enabled_by_default": enabled_by_default,
        "capabilities": ["text_generation"],
        "license": "MIT",
    }
    (plugin_root / "plugin.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (plugin_root / "plugin.py").write_text(
        "class TestPlugin:\n"
        "    name = 'test-plugin'\n",
        encoding="utf-8",
    )
    return plugin_root


def test_manifest_validation() -> None:
    manifest = PluginManifest.from_dict(
        {
            "id": "provider.ollama",
            "name": "Ollama Provider",
            "version": "1.0.0",
            "type": "provider",
            "entrypoint": "plugin:OllamaPlugin",
        }
    )

    assert manifest.plugin_id == "provider.ollama"
    assert manifest.plugin_type.value == "provider"


def test_invalid_manifest_is_rejected() -> None:
    with pytest.raises(PluginManifestError):
        PluginManifest.from_dict(
            {
                "id": "Ungültig!",
                "name": "Fehler",
                "version": "1",
                "type": "provider",
                "entrypoint": "plugin",
            }
        )


def test_discover_and_load_plugin(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_plugin(plugin_root)

    manager = PluginManager(
        plugin_root=plugin_root,
        state_path=tmp_path / "plugin-state.json",
    )

    discovered = manager.discover()
    loaded = manager.load_enabled()

    assert len(discovered) == 1
    assert len(loaded) == 1
    assert loaded[0].loaded is True
    assert loaded[0].instance.name == "test-plugin"


def test_plugin_state_is_persisted(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_plugin(plugin_root)

    state_path = tmp_path / "plugin-state.json"
    manager = PluginManager(
        plugin_root=plugin_root,
        state_path=state_path,
    )
    manager.discover()
    manager.disable("test.provider")

    new_manager = PluginManager(
        plugin_root=plugin_root,
        state_path=state_path,
    )
    discovered = new_manager.discover()

    assert discovered[0].enabled is False


def test_disabled_plugin_is_not_loaded(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugins"
    write_plugin(plugin_root, enabled_by_default=False)

    manager = PluginManager(
        plugin_root=plugin_root,
        state_path=tmp_path / "plugin-state.json",
    )
    manager.discover()

    assert manager.load_enabled() == ()
