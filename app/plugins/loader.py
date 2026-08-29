"""Sichere Erkennung und kontrolliertes Laden von AI-Node-Plugins."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from app.plugins.errors import PluginLoadError, PluginManifestError
from app.plugins.manifest import PluginManifest
from app.plugins.registry import PluginRecord, PluginRegistry
from app.plugins.state import PluginStateStore
from app.plugins.worker_bridge import plugin_worker_registry


class _PluginWorkerContext:
    """Bindet Worker-Registrierungen an ein Plugin."""

    def __init__(
        self,
        registry: object,
        plugin_id: str,
    ) -> None:
        self._registry = registry
        self._plugin_id = plugin_id.strip().lower()

    def register(self, **kwargs: object) -> None:
        metadata = dict(
            kwargs.pop("metadata", {}) or {}
        )
        metadata["plugin_id"] = self._plugin_id
        kwargs["metadata"] = metadata
        self._registry.register(**kwargs)

    def unregister(self, worker_id: str) -> bool:
        worker = self._registry.get(worker_id)

        if worker is None:
            return False

        if worker.get("plugin_id") != self._plugin_id:
            return False

        return self._registry.unregister(worker_id)

    def get(self, worker_id: str) -> dict | None:
        return self._registry.get(worker_id)


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

        for record in self.registry.all():
            self.unload(record)

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

            register = getattr(instance, "register", None)
            if callable(register):
                context = {
                    "plugin_id": record.manifest.plugin_id,
                    "plugin_name": record.manifest.name,
                    "plugin_version": record.manifest.version,
                    "plugin_path": record.root_path,
                    "workers": _PluginWorkerContext(
                        plugin_worker_registry,
                        record.manifest.plugin_id,
                    ),
                    "manifest": {
                        "id": record.manifest.plugin_id,
                        "name": record.manifest.name,
                        "version": record.manifest.version,
                        "type": record.manifest.plugin_type.value,
                        "entrypoint": record.manifest.entrypoint,
                        "capabilities": list(
                            record.manifest.capabilities
                        ),
                        **record.manifest.metadata,
                    },
                    "capabilities": {},
                    "capabilities_provider": None,
                }
                register(context)
        except Exception as exc:
            plugin_worker_registry.unregister_plugin(
                record.manifest.plugin_id
            )
            sys.modules.pop(unique_name, None)
            raise PluginLoadError(
                f"Plugin '{record.manifest.plugin_id}' konnte nicht "
                f"geladen werden: {exc}"
            ) from exc

        record.instance = instance
        record.loaded = True
        record.error = None
        return instance

    def unload(self, record: PluginRecord) -> None:
        """Entfernt Laufzeitregistrierungen eines Plugins."""

        plugin_worker_registry.unregister_plugin(
            record.manifest.plugin_id
        )

        unique_name = (
            "mediahub_ai_plugin_"
            + record.manifest.plugin_id
            .replace("-", "_")
            .replace(".", "_")
        )
        sys.modules.pop(unique_name, None)

        record.loaded = False
        record.instance = None
