"""REST-Endpunkte für AI-Node-Plugins."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)

from app.plugins.installer import PluginInstallError
from app.plugins.package_validator import PluginPackageError
from app.plugins.runtime import plugin_installer, plugin_manager
from app.plugins.serialization import plugin_record_to_dict
from app.security.api_token import require_api_token

router = APIRouter(prefix="/plugins", tags=["AI Plugins"])

MAX_UPLOAD_SIZE = 512 * 1024 * 1024


@router.get("")
def list_plugins_endpoint() -> dict[str, Any]:
    """Listet alle vom AI-Node erkannten Plugins."""

    plugins = [
        plugin_record_to_dict(record)
        for record in plugin_manager.registry.all()
    ]

    return {
        "count": len(plugins),
        "enabled_count": sum(
            1 for plugin in plugins if plugin["enabled"]
        ),
        "loaded_count": sum(
            1 for plugin in plugins if plugin["loaded"]
        ),
        "plugins": plugins,
    }


@router.get("/{plugin_id}")
def get_plugin_endpoint(plugin_id: str) -> dict[str, Any]:
    """Liefert den Status eines einzelnen Plugins."""

    record = plugin_manager.registry.get(plugin_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI-Plugin nicht gefunden.",
        )

    return plugin_record_to_dict(record)


@router.post(
    "/install",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_token)],
)
async def install_plugin_endpoint(
    request: Request,
    x_plugin_sha256: Annotated[
        str,
        Header(alias="X-Plugin-SHA256"),
    ],
    x_plugin_filename: Annotated[
        str | None,
        Header(alias="X-Plugin-Filename"),
    ] = None,
) -> dict[str, Any]:
    """Installiert ein geprüftes Plugin-ZIP.

    Der ZIP-Inhalt wird als roher Request-Body mit
    `Content-Type: application/zip` übertragen.
    """

    content_type = request.headers.get("content-type", "")
    if "application/zip" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Der Request-Body muss ein ZIP-Paket enthalten.",
        )

    body = await request.body()

    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Das hochgeladene Plugin-Paket ist leer.",
        )

    if len(body) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Das Plugin-Paket überschreitet die erlaubte Upload-Größe.",
        )

    suffix = Path(x_plugin_filename or "plugin.zip").suffix.lower()
    if suffix != ".zip":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur ZIP-Pakete sind erlaubt.",
        )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix="mediahub-ai-plugin-upload-",
            suffix=".zip",
            delete=False,
        ) as temporary_file:
            temporary_file.write(body)
            temporary_path = Path(temporary_file.name)

        result = plugin_installer.install(
            temporary_path,
            expected_sha256=x_plugin_sha256,
        )

        plugin_manager.discover()
        plugin_manager.load_enabled()

        record = plugin_manager.registry.get(result.plugin_id)

        return {
            "status": "installed",
            "plugin": (
                plugin_record_to_dict(record)
                if record is not None
                else {
                    "id": result.plugin_id,
                    "version": result.version,
                    "enabled": False,
                    "loaded": False,
                    "error": "Plugin wurde installiert, aber nicht erkannt.",
                }
            ),
            "installation": {
                "sha256": result.sha256,
                "replaced_existing": result.replaced_existing,
                "backup_created": result.backup_path is not None,
                "backup_path": (
                    str(result.backup_path)
                    if result.backup_path is not None
                    else None
                ),
            },
        }

    except PluginPackageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PluginInstallError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
