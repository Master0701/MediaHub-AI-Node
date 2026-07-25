"""Schreibgeschützte REST-Endpunkte für AI-Node-Plugins."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.plugins.runtime import plugin_manager
from app.plugins.serialization import plugin_record_to_dict

router = APIRouter(prefix="/plugins", tags=["AI Plugins"])


@router.get("")
def list_plugins_endpoint() -> dict[str, Any]:
    plugins = [
        plugin_record_to_dict(record)
        for record in plugin_manager.registry.all()
    ]
    return {
        "count": len(plugins),
        "enabled_count": sum(1 for item in plugins if item["enabled"]),
        "loaded_count": sum(1 for item in plugins if item["loaded"]),
        "plugins": plugins,
    }


@router.get("/{plugin_id}")
def get_plugin_endpoint(plugin_id: str) -> dict[str, Any]:
    record = plugin_manager.registry.get(plugin_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI-Plugin nicht gefunden.",
        )
    return plugin_record_to_dict(record)
