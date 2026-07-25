"""Zentrale Verwaltung der AI-Node-Plugins."""

from __future__ import annotations

from pathlib import Path

from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRecord, PluginRegistry
from app.plugins.state import PluginStateStore


class PluginManager:
    """Fassade für Erkennung, Laden und Aktivierungszustände."""

    def __init__(
        self,
        *,
        plugin_root: Path,
        state_path: Path,
    ) -> None:
        self.registry = PluginRegistry()
        self.state_store = PluginStateStore(state_path)
        self.loader = PluginLoader(
            plugin_root,
            self.registry,
            self.state_store,
        )

    def discover(self) -> tuple[PluginRecord, ...]:
        return self.loader.discover()

    def load_enabled(self) -> tuple[PluginRecord, ...]:
        return self.loader.load_enabled()

    def enable(self, plugin_id: str) -> PluginRecord:
        record = self.registry.require(plugin_id)
        record.enabled = True
        self.state_store.set_enabled(plugin_id, True)
        self.state_store.save()
        return record

    def disable(self, plugin_id: str) -> PluginRecord:
        record = self.registry.require(plugin_id)
        record.enabled = False
        record.loaded = False
        record.instance = None
        self.state_store.set_enabled(plugin_id, False)
        self.state_store.save()
        return record
