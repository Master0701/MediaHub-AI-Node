"""Serialisierung von Plugin-Datensätzen für die REST-API."""

from __future__ import annotations

from typing import Any

from app.plugins.registry import PluginRecord


def plugin_record_to_dict(record: PluginRecord) -> dict[str, Any]:
    manifest = record.manifest
    return {
        "id": manifest.plugin_id,
        "name": manifest.name,
        "version": manifest.version,
        "type": manifest.plugin_type.value,
        "api_version": manifest.api_version,
        "description": manifest.description,
        "author": manifest.author,
        "license": manifest.license_name,
        "entrypoint": manifest.entrypoint,
        "enabled": record.enabled,
        "loaded": record.loaded,
        "error": record.error,
        "capabilities": list(manifest.capabilities),
        "permissions": list(manifest.permissions),
        "required_tools": list(manifest.required_tools),
        "dependencies": [
            {
                "id": dependency.plugin_id,
                "minimum_version": dependency.minimum_version,
            }
            for dependency in manifest.dependencies
        ],
    }
