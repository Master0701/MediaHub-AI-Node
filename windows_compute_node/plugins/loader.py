"""Loader for installed Compute-Node plugins."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from windows_compute_node.workers.registry import (
    WorkerRegistry,
)


class PluginLoadError(RuntimeError):
    pass


class ComputePluginLoader:
    def __init__(
        self,
        *,
        plugin_root: Path,
        workers: WorkerRegistry,
        capabilities_provider=None,
    ) -> None:
        self.plugin_root = Path(plugin_root)
        self.workers = workers
        self.capabilities_provider = (
            capabilities_provider
        )

        # Laufende Plugin-/Provider-Objekte bleiben
        # ausschließlich intern. API-Ergebnisse müssen
        # vollständig JSON-serialisierbar bleiben.
        self.instances: dict[str, object] = {}

    def discover(
        self,
    ) -> list[Path]:
        if not self.plugin_root.is_dir():
            return []

        result: list[Path] = []

        for path in self.plugin_root.iterdir():
            if not path.is_dir():
                continue

            if (
                path / "plugin.json"
            ).is_file():
                result.append(path)

        result.sort(
            key=lambda item: item.name.lower()
        )

        return result

    def load_all(
        self,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for plugin_dir in self.discover():
            try:
                result = self.load_plugin(
                    plugin_dir
                )
            except Exception as exc:
                result = {
                    "plugin_path": str(
                        plugin_dir
                    ),
                    "loaded": False,
                    "error": (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                }

            results.append(result)

        return results

    def load_plugin(
        self,
        plugin_dir: Path,
    ) -> dict[str, Any]:
        plugin_dir = Path(plugin_dir)

        manifest_path = (
            plugin_dir / "plugin.json"
        )

        if not manifest_path.is_file():
            raise PluginLoadError(
                "plugin.json fehlt."
            )

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise PluginLoadError(
                "plugin.json ist ungueltig."
            ) from exc

        if not isinstance(manifest, dict):
            raise PluginLoadError(
                "Manifest muss ein Objekt sein."
            )

        plugin_id = str(
            manifest.get("id")
            or ""
        ).strip()

        name = str(
            manifest.get("name")
            or plugin_id
        ).strip()

        version = str(
            manifest.get("version")
            or ""
        ).strip()

        legacy_plugin_type = str(
            manifest.get("plugin_type")
            or ""
        ).strip()

        shared_plugin_type = str(
            manifest.get("type")
            or ""
        ).strip()

        entrypoint = str(
            manifest.get("entrypoint")
            or ""
        ).strip()

        if not plugin_id:
            raise PluginLoadError(
                "Plugin-ID fehlt."
            )

        if not version:
            raise PluginLoadError(
                "Plugin-Version fehlt."
            )

        if legacy_plugin_type:
            if legacy_plugin_type != "ai_node":
                raise PluginLoadError(
                    "plugin_type muss "
                    "'ai_node' sein."
                )
        elif not shared_plugin_type:
            raise PluginLoadError(
                "Plugin-Typ fehlt."
            )

        if not entrypoint:
            raise PluginLoadError(
                "entrypoint fehlt."
            )

        if ":" in entrypoint:
            entry_module, entry_object = (
                entrypoint.split(":", 1)
            )
        else:
            entry_module = entrypoint
            entry_object = ""

        if entry_module.endswith(".py"):
            entry_relative = entry_module
        else:
            entry_relative = (
                entry_module.replace(".", "/")
                + ".py"
            )

        entry_file = (
            plugin_dir / entry_relative
        ).resolve()

        plugin_root = (
            plugin_dir.resolve()
        )

        try:
            entry_file.relative_to(
                plugin_root
            )
        except ValueError as exc:
            raise PluginLoadError(
                "entrypoint liegt ausserhalb "
                "des Plugin-Verzeichnisses."
            ) from exc

        if not entry_file.is_file():
            raise PluginLoadError(
                "Entrypoint-Datei fehlt."
            )

        module_name = (
            "mediahub_compute_plugin_"
            + plugin_id.replace(
                ".",
                "_",
            ).replace(
                "-",
                "_",
            )
        )

        spec = (
            importlib.util.spec_from_file_location(
                module_name,
                entry_file,
            )
        )

        if (
            spec is None
            or spec.loader is None
        ):
            raise PluginLoadError(
                "Entrypoint kann nicht "
                "geladen werden."
            )

        module = (
            importlib.util.module_from_spec(
                spec
            )
        )

        spec.loader.exec_module(module)

        before = {
            item["worker_id"]
            for item in (
                self.workers.list_workers()
            )
        }

        context = {
            "plugin_id": plugin_id,
            "plugin_name": name,
            "plugin_version": version,
            "plugin_path": plugin_dir,
            "workers": self.workers,
            "manifest": manifest,
            "capabilities_provider": (
                self.capabilities_provider
            ),
        }

        if callable(
            self.capabilities_provider
        ):
            context["capabilities"] = (
                self.capabilities_provider()
            )
        else:
            context["capabilities"] = {}

        plugin_instance = None

        if entry_object:
            plugin_class = getattr(
                module,
                entry_object,
                None,
            )

            if plugin_class is None:
                raise PluginLoadError(
                    "Entrypoint-Objekt fehlt: "
                    f"{entry_object}"
                )

            if not callable(plugin_class):
                raise PluginLoadError(
                    "Entrypoint-Objekt ist "
                    "nicht aufrufbar."
                )

            plugin_instance = plugin_class()

            register = getattr(
                plugin_instance,
                "register",
                None,
            )

            if callable(register):
                register(context)
        else:
            register = getattr(
                module,
                "register",
                None,
            )

            if not callable(register):
                raise PluginLoadError(
                    "Entrypoint benoetigt "
                    "register(context)."
                )

            register(context)

        after = {
            item["worker_id"]
            for item in (
                self.workers.list_workers()
            )
        }

        registered = sorted(
            after - before
        )

        # Provider-Plugins muessen nicht zwingend einen
        # Worker registrieren. Legacy-ai_node-Plugins schon.
        if (
            legacy_plugin_type == "ai_node"
            and not registered
        ):
            raise PluginLoadError(
                "Plugin hat keinen Worker "
                "registriert."
            )

        result = {
            "plugin_id": plugin_id,
            "name": name,
            "version": version,
            "loaded": True,
            "workers": registered,
        }

        if shared_plugin_type:
            result["type"] = shared_plugin_type

        if plugin_instance is not None:
            self.instances[plugin_id] = (
                plugin_instance
            )

        return result
