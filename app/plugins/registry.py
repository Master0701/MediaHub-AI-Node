"""Registry der entdeckten AI-Node-Plugins."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.plugins.errors import PluginNotFoundError
from app.plugins.manifest import PluginManifest


@dataclass(slots=True)
class PluginRecord:
    """Ein entdecktes Plugin mit Pfad und aktuellem Zustand."""

    manifest: PluginManifest
    root_path: Path
    enabled: bool
    loaded: bool = False
    instance: object | None = None
    error: str | None = None


class PluginRegistry:
    """Verwaltet alle entdeckten Plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginRecord] = {}

    def register(
        self,
        record: PluginRecord,
        *,
        replace: bool = False,
    ) -> None:
        plugin_id = record.manifest.plugin_id
        if plugin_id in self._plugins and not replace:
            raise ValueError(
                f"Plugin '{plugin_id}' ist bereits registriert."
            )
        self._plugins[plugin_id] = record

    def get(self, plugin_id: str) -> PluginRecord | None:
        return self._plugins.get(plugin_id.strip().lower())

    def require(self, plugin_id: str) -> PluginRecord:
        record = self.get(plugin_id)
        if record is None:
            raise PluginNotFoundError(
                f"Plugin nicht gefunden: {plugin_id}"
            )
        return record

    def all(self) -> tuple[PluginRecord, ...]:
        return tuple(
            self._plugins[key]
            for key in sorted(self._plugins)
        )

    def enabled(self) -> tuple[PluginRecord, ...]:
        return tuple(
            record
            for record in self.all()
            if record.enabled
        )

    def clear(self) -> None:
        self._plugins.clear()

    def __len__(self) -> int:
        return len(self._plugins)
