"""Sichere Erkennung und kontrolliertes Laden von AI-Node-Plugins."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from app.plugins.errors import PluginLoadError, PluginManifestError
from app.plugins.manifest import PluginManifest
from app.plugins.registry import PluginRecord, PluginRegistry
from app.plugins.state import PluginStateStore


class PluginLoader:
    """Entdeckt Plugin-Ordner und lädt aktivierte Entrypoints."""

    manifest_name = "plugin.json"

    def __init__(
        self,
        plugin_root: Path,
        registry: PluginRegistry,
        state_store: PluginStateStore,
    ) -> None:
        self.plugin_root = plugin_root
        self.registry = registry
        self.state_store = state_store

    def discover(self) -> tuple[PluginRecord, ...]:
        """Sucht direkte Unterordner mit `plugin.json`."""

        self.registry.clear()
        self.state_store.load()

        if not self.plugin_root.exists():
            return ()

        for child in sorted(self.plugin_root.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue

            manifest_path = child / self.manifest_name
            if not manifest_path.is_file():
                continue

            try:
                manifest = PluginManifest.load(manifest_path)
                enabled = self.state_store.is_enabled(
                    manifest.plugin_id,
                    default=manifest.enabled_by_default,
                )
                record = PluginRecord(
                    manifest=manifest,
                    root_path=child.resolve(),
                    enabled=enabled,
                )
            except PluginManifestError:
                continue

            self.registry.register(record)

        return self.registry.all()

    def load_enabled(self) -> tuple[PluginRecord, ...]:
        """Lädt alle aktivierten Plugins in Abhängigkeitsreihenfolge."""

        loaded: list[PluginRecord] = []
        pending = {
            record.manifest.plugin_id: record
            for record in self.registry.enabled()
        }

        while pending:
            progress = False

            for plugin_id, record in tuple(pending.items()):
                dependencies = {
                    dependency.plugin_id
                    for dependency in record.manifest.dependencies
                }

                missing = {
                    dependency
                    for dependency in dependencies
                    if self.registry.get(dependency) is None
                }
                if missing:
                    record.error = (
                        "Fehlende Plugin-Abhängigkeiten: "
                        + ", ".join(sorted(missing))
                    )
                    del pending[plugin_id]
                    progress = True
                    continue

                unresolved = {
                    dependency
                    for dependency in dependencies
                    if not self.registry.require(dependency).loaded
                }
                if unresolved:
                    continue

                try:
                    self.load(record)
                    loaded.append(record)
                except PluginLoadError as exc:
                    record.error = str(exc)

                del pending[plugin_id]
                progress = True

            if not progress:
                for record in pending.values():
                    record.error = (
                        "Zyklische oder deaktivierte Plugin-Abhängigkeit."
                    )
                break

        return tuple(loaded)

    def load(self, record: PluginRecord) -> object:
        """Lädt den in `plugin.json` angegebenen Entrypoint."""

        module_name, object_name = record.manifest.entrypoint.split(":", 1)
        module_file = (
            record.root_path
            / Path(*module_name.split("."))
        ).with_suffix(".py")

        if not module_file.is_file():
            package_init = (
                record.root_path
                / Path(*module_name.split("."))
                / "__init__.py"
            )
            module_file = package_init

        if not module_file.is_file():
            raise PluginLoadError(
                f"Entrypoint-Modul fehlt: {record.manifest.entrypoint}"
            )

        unique_name = (
            "mediahub_ai_plugin_"
            + record.manifest.plugin_id.replace("-", "_").replace(".", "_")
        )

        spec = importlib.util.spec_from_file_location(
            unique_name,
            module_file,
            submodule_search_locations=(
                [str(module_file.parent)]
                if module_file.name == "__init__.py"
                else None
            ),
        )
        if spec is None or spec.loader is None:
            raise PluginLoadError(
                f"Entrypoint konnte nicht vorbereitet werden: {module_file}"
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = module

        try:
            spec.loader.exec_module(module)
            entrypoint = getattr(module, object_name)
            instance = entrypoint() if isinstance(entrypoint, type) else entrypoint
        except Exception as exc:
            sys.modules.pop(unique_name, None)
            raise PluginLoadError(
                f"Plugin '{record.manifest.plugin_id}' konnte nicht "
                f"geladen werden: {exc}"
            ) from exc

        record.instance = instance
        record.loaded = True
        record.error = None
        return instance
