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
    Query,
    Request,
    status,
)

from app.plugins.installer import PluginInstallError
from app.plugins.package_validator import PluginPackageError
from app.plugins.preflight import PluginPreflightError
from app.plugins.runtime import plugin_installer, plugin_manager
from app.plugins.serialization import plugin_record_to_dict
from app.security.api_token import require_api_token

router = APIRouter(prefix="/plugins", tags=["AI Plugins"])

MAX_UPLOAD_SIZE = 512 * 1024 * 1024
WRITE_DEPENDENCIES = [Depends(require_api_token)]


def _refresh_plugins() -> None:
    plugin_manager.discover()
    plugin_manager.load_enabled()


def _installed_plugin_ids() -> set[str]:
    return {
        record.manifest.plugin_id
        for record in plugin_manager.registry.all()
    }


@router.get("")
def list_plugins_endpoint() -> dict[str, Any]:
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
    dependencies=WRITE_DEPENDENCIES,
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
            installed_plugin_ids=_installed_plugin_ids(),
        )

        _refresh_plugins()
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
            "preflight": {
                "ready": result.preflight.ready,
                "license_present": result.preflight.license_present,
                "warnings": list(result.preflight.warnings),
                "python_requirements": [
                    {
                        "name": check.name,
                        "available": check.available,
                        "installed_version": check.installed_version,
                        "details": check.details,
                    }
                    for check in result.preflight.python_requirements
                ],
                "required_tools": [
                    {
                        "name": check.name,
                        "available": check.available,
                        "details": check.details,
                    }
                    for check in result.preflight.required_tools
                ],
                "plugin_dependencies": [
                    {
                        "name": check.name,
                        "available": check.available,
                        "details": check.details,
                    }
                    for check in result.preflight.plugin_dependencies
                ],
            },
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

    except (
        PluginPackageError,
        PluginPreflightError,
    ) as exc:
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


@router.post(
    "/{plugin_id}/enable",
    dependencies=WRITE_DEPENDENCIES,
)
def enable_plugin_endpoint(plugin_id: str) -> dict[str, Any]:
    try:
        plugin_manager.enable(plugin_id)
        _refresh_plugins()
        record = plugin_manager.registry.require(plugin_id)
        return {
            "status": "enabled",
            "plugin": plugin_record_to_dict(record),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{plugin_id}/disable",
    dependencies=WRITE_DEPENDENCIES,
)
def disable_plugin_endpoint(plugin_id: str) -> dict[str, Any]:
    try:
        plugin_manager.disable(plugin_id)
        _refresh_plugins()
        record = plugin_manager.registry.require(plugin_id)
        return {
            "status": "disabled",
            "plugin": plugin_record_to_dict(record),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{plugin_id}",
    dependencies=WRITE_DEPENDENCIES,
)
def remove_plugin_endpoint(
    plugin_id: str,
    create_backup: Annotated[bool, Query()] = True,
) -> dict[str, Any]:
    try:
        result = plugin_installer.remove(
            plugin_id,
            create_backup=create_backup,
        )
        _refresh_plugins()
        return {
            "status": "removed",
            "plugin_id": result.plugin_id,
            "backup_created": result.backup_path is not None,
            "backup_path": (
                str(result.backup_path)
                if result.backup_path is not None
                else None
            ),
        }
    except PluginInstallError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{plugin_id}/backups",
    dependencies=WRITE_DEPENDENCIES,
)
def list_plugin_backups_endpoint(plugin_id: str) -> dict[str, Any]:
    backups = plugin_installer.list_backups(plugin_id)
    return {
        "plugin_id": plugin_id.strip().lower(),
        "count": len(backups),
        "backups": [
            {
                "name": path.name,
                "path": str(path),
            }
            for path in backups
        ],
    }


@router.post(
    "/{plugin_id}/rollback/{backup_name}",
    dependencies=WRITE_DEPENDENCIES,
)
def rollback_plugin_endpoint(
    plugin_id: str,
    backup_name: str,
) -> dict[str, Any]:
    try:
        backup_path = plugin_installer.resolve_backup(
            plugin_id=plugin_id,
            backup_name=backup_name,
        )
        install_path = plugin_installer.rollback(
            plugin_id=plugin_id,
            backup_path=backup_path,
        )
        _refresh_plugins()

        record = plugin_manager.registry.get(plugin_id)

        return {
            "status": "restored",
            "plugin_id": plugin_id.strip().lower(),
            "install_path": str(install_path),
            "plugin": (
                plugin_record_to_dict(record)
                if record is not None
                else None
            ),
        }
    except PluginInstallError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
