"""Persistenter Aktivierungszustand der AI-Node-Plugins."""

from __future__ import annotations

import json
from pathlib import Path


class PluginStateStore:
    """Speichert aktivierte und deaktivierte Plugins als JSON."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self._states: dict[str, bool] = {}

    def load(self) -> None:
        """Lädt den Zustand, falls die Datei vorhanden ist."""

        if not self.state_path.exists():
            self._states = {}
            return

        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Plugin-Zustandsdatei muss ein JSON-Objekt sein.")

        self._states = {
            str(plugin_id).strip().lower(): bool(enabled)
            for plugin_id, enabled in data.items()
        }

    def save(self) -> None:
        """Schreibt den Zustand atomar auf die Festplatte."""

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(
            self.state_path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(self._states, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.state_path)

    def is_enabled(self, plugin_id: str, *, default: bool = True) -> bool:
        """Liefert den gespeicherten Zustand oder einen Standardwert."""

        return self._states.get(plugin_id.strip().lower(), default)

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        """Setzt den Zustand eines Plugins."""

        self._states[plugin_id.strip().lower()] = bool(enabled)

    def all(self) -> dict[str, bool]:
        """Liefert eine Kopie aller gespeicherten Zustände."""

        return dict(self._states)
