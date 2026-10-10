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
class PluginToolRequirement:
    """Ein Systemwerkzeug oder eine deklarierte verwaltete Plugin-Abhängigkeit."""

    tool_id: str
    source: str = "system"
    version: str | None = None
    required: bool = True
    targets: tuple[str, ...] = ()


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
    tool_requirements: tuple[PluginToolRequirement, ...] = ()
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

        tool_requirements = _parse_tool_requirements(
            data.get("required_tools", [])
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
            required_tools=tuple(
                tool.tool_id for tool in tool_requirements
            ),
            tool_requirements=tool_requirements,
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


def _parse_tool_requirements(
    raw: Any,
) -> tuple[PluginToolRequirement, ...]:
    """Erkennt alte String- und neue Objektform ohne Metadatenverlust.

    Die Quelle steuert später den Installationsplan. Fehlende oder
    ungültige Angaben werden nicht stillschweigend entfernt.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise PluginManifestError("'required_tools' muss eine Liste sein.")

    items: list[PluginToolRequirement] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            tool_id = item.strip()
            source = "system"
            version = None
            required = True
            targets: tuple[str, ...] = ()
        elif isinstance(item, dict):
            tool_id_value = item.get("id")
            if not isinstance(tool_id_value, str):
                raise PluginManifestError("Ein 'required_tools'-Objekt benötigt 'id'.")
            tool_id = tool_id_value.strip()
            source_value = item.get("source", "system")
            if not isinstance(source_value, str) or not source_value.strip():
                raise PluginManifestError("Ungültige Quelle in 'required_tools'.")
            source = source_value.strip().lower()
            version_value = item.get("version")
            if version_value is not None and not isinstance(version_value, str):
                raise PluginManifestError("Ungültige Version in 'required_tools'.")
            version = version_value.strip() if version_value else None
            required_value = item.get("required", True)
            if not isinstance(required_value, bool):
                raise PluginManifestError("'required' muss boolesch sein.")
            required = required_value
            target_value = item.get("targets", [])
            if not isinstance(target_value, list) or any(
                not isinstance(target, str) or not target.strip()
                for target in target_value
            ):
                raise PluginManifestError("Ungültige 'targets' in 'required_tools'.")
            targets = tuple(target.strip() for target in target_value)
        else:
            raise PluginManifestError("Ungültiger Eintrag in 'required_tools'.")

        if not PLUGIN_ID_PATTERN.fullmatch(tool_id):
            raise PluginManifestError(f"Ungültige Werkzeug-ID: {tool_id!r}")
        if tool_id in seen:
            raise PluginManifestError(f"Doppeltes Pflichtwerkzeug: {tool_id}")
        seen.add(tool_id)
        items.append(PluginToolRequirement(
            tool_id=tool_id,
            source=source,
            version=version,
            required=required,
            targets=targets,
        ))
    return tuple(items)


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
