"""Manifest-Datentypen und Validierung für AI-Node-Plugins."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.plugins.errors import PluginManifestError

PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


class PluginType(StrEnum):
    """Unterstützte Typen von AI-Node-Plugins."""

    PROVIDER = "provider"
    WORKER = "worker"
    OCR = "ocr"
    AUDIO = "audio"
    VIDEO = "video"
    ANALYZER = "analyzer"
    KNOWLEDGE = "knowledge"
    CACHE = "cache"
    MODEL = "model"
    UTILITY = "utility"


@dataclass(frozen=True, slots=True)
class PluginDependency:
    """Abhängigkeit zu einem weiteren Plugin."""

    plugin_id: str
    minimum_version: str | None = None


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Validiertes Manifest eines AI-Node-Plugins."""

    plugin_id: str
    name: str
    version: str
    plugin_type: PluginType
    entrypoint: str
    api_version: str = "1"
    description: str = ""
    author: str = ""
    license_name: str = ""
    enabled_by_default: bool = True
    permissions: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    dependencies: tuple[PluginDependency, ...] = ()
    required_tools: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        """Erstellt und validiert ein Manifest aus einem Dictionary."""

        required = ("id", "name", "version", "type", "entrypoint")
        missing = [
            key
            for key in required
            if not isinstance(data.get(key), str) or not data[key].strip()
        ]
        if missing:
            raise PluginManifestError(
                "Fehlende oder leere Pflichtfelder: " + ", ".join(missing)
            )

        plugin_id = data["id"].strip().lower()
        if not PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            raise PluginManifestError(
                "Ungültige Plugin-ID. Erlaubt sind Kleinbuchstaben, Zahlen, "
                "Punkt, Unterstrich und Bindestrich."
            )

        version = data["version"].strip()
        if not VERSION_PATTERN.fullmatch(version):
            raise PluginManifestError(
                f"Ungültige Plugin-Version: {version}"
            )

        try:
            plugin_type = PluginType(data["type"].strip().lower())
        except ValueError as exc:
            allowed = ", ".join(item.value for item in PluginType)
            raise PluginManifestError(
                f"Ungültiger Plugin-Typ. Erlaubt: {allowed}"
            ) from exc

        entrypoint = data["entrypoint"].strip()
        if ":" not in entrypoint:
            raise PluginManifestError(
                "Der Entrypoint muss das Format 'modul:objekt' verwenden."
            )

        dependencies_raw = data.get("dependencies", [])
        if not isinstance(dependencies_raw, list):
            raise PluginManifestError("'dependencies' muss eine Liste sein.")

        dependencies: list[PluginDependency] = []
        for item in dependencies_raw:
            if isinstance(item, str):
                dependencies.append(
                    PluginDependency(plugin_id=item.strip().lower())
                )
                continue

            if not isinstance(item, dict) or not isinstance(
                item.get("id"), str
            ):
                raise PluginManifestError(
                    "Jede Plugin-Abhängigkeit benötigt eine 'id'."
                )

            dependencies.append(
                PluginDependency(
                    plugin_id=item["id"].strip().lower(),
                    minimum_version=(
                        str(item["minimum_version"]).strip()
                        if item.get("minimum_version")
                        else None
                    ),
                )
            )

        known_fields = {
            "id",
            "name",
            "version",
            "type",
            "entrypoint",
            "api_version",
            "description",
            "author",
            "license",
            "enabled_by_default",
            "permissions",
            "capabilities",
            "dependencies",
            "required_tools",
        }

        return cls(
            plugin_id=plugin_id,
            name=data["name"].strip(),
            version=version,
            plugin_type=plugin_type,
            entrypoint=entrypoint,
            api_version=str(data.get("api_version", "1")).strip(),
            description=str(data.get("description", "")).strip(),
            author=str(data.get("author", "")).strip(),
            license_name=str(data.get("license", "")).strip(),
            enabled_by_default=bool(data.get("enabled_by_default", True)),
            permissions=_string_tuple(data.get("permissions", [])),
            capabilities=_string_tuple(data.get("capabilities", [])),
            dependencies=tuple(dependencies),
            required_tools=_string_tuple(data.get("required_tools", [])),
            metadata={
                key: value
                for key, value in data.items()
                if key not in known_fields
            },
        )

    @classmethod
    def load(cls, manifest_path: Path) -> PluginManifest:
        """Lädt ein Manifest aus einer JSON-Datei."""

        try:
            raw = manifest_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except OSError as exc:
            raise PluginManifestError(
                f"Manifest konnte nicht gelesen werden: {manifest_path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise PluginManifestError(
                f"Ungültiges JSON in {manifest_path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise PluginManifestError(
                f"Das Manifest muss ein JSON-Objekt sein: {manifest_path}"
            )

        return cls.from_dict(data)


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise PluginManifestError("Listenfelder müssen JSON-Listen sein.")
    return tuple(
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    )
