"""Geschützte REST-Endpunkte für Plugin-Installationspläne."""

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

from app.plugins.install_plan import (
    PluginInstallPlanBuilder,
    install_plan_to_dict,
)
from app.plugins.package_validator import (
    PluginPackageError,
    validate_plugin_package,
)
from app.plugins.preflight import (
    PluginPreflightChecker,
    PluginPreflightError,
)
from app.plugins.runtime import (
    plugin_installer,
    plugin_manager,
    plugin_plan_store,
)
from app.plugins.serialization import plugin_record_to_dict
from app.security.api_token import require_api_token

router = APIRouter(prefix="/plugins", tags=["AI Plugins"])

MAX_UPLOAD_SIZE = 512 * 1024 * 1024
WRITE_DEPENDENCIES = [Depends(require_api_token)]


def _installed_plugin_ids() -> set[str]:
    return {
        record.manifest.plugin_id
        for record in plugin_manager.registry.all()
    }


def _refresh_plugins() -> None:
    plugin_manager.discover()
    plugin_manager.load_enabled()


@router.post(
    "/plan",
    dependencies=WRITE_DEPENDENCIES,
)
async def create_plugin_install_plan_endpoint(
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
            prefix="mediahub-ai-plugin-plan-",
            suffix=".zip",
            delete=False,
        ) as temporary_file:
            temporary_file.write(body)
            temporary_path = Path(temporary_file.name)

        package = validate_plugin_package(
            temporary_path,
            expected_sha256=x_plugin_sha256,
        )

        preflight = PluginPreflightChecker(
            installed_plugin_ids=_installed_plugin_ids(),
        ).inspect(package)

        plan = PluginInstallPlanBuilder().build(preflight)

        stored = plugin_plan_store.create(
            plugin_id=package.manifest.plugin_id,
            archive_path=temporary_path,
            sha256=package.sha256,
            plan=plan,
        )

        return {
            "status": "plan_created",
            "plan_id": stored.plan_id,
            "created_at": stored.created_at.isoformat(),
            "expires_at": stored.expires_at.isoformat(),
            "package": {
                "plugin_id": package.manifest.plugin_id,
                "name": package.manifest.name,
                "version": package.manifest.version,
                "type": package.manifest.plugin_type.value,
                "sha256": package.sha256,
                "file_count": package.file_count,
                "uncompressed_size": package.uncompressed_size,
            },
            "plan": install_plan_to_dict(plan),
        }

    except (
        PluginPackageError,
        PluginPreflightError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@router.post(
    "/plan/{plan_id}/confirm",
    dependencies=WRITE_DEPENDENCIES,
)
def confirm_plugin_install_plan_endpoint(
    plan_id: str,
    x_plugin_sha256: Annotated[
        str,
        Header(alias="X-Plugin-SHA256"),
    ],
) -> dict[str, Any]:
    stored = plugin_plan_store.get(plan_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installationsplan nicht gefunden oder abgelaufen.",
        )

    if stored.sha256 != x_plugin_sha256.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Die SHA-256-Prüfsumme passt nicht zum gespeicherten Plan.",
        )

    if stored.plan.requires_confirmation and stored.plan.actions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Der Installationsplan enthält noch nicht ausgeführte "
                "Voraussetzungen und kann deshalb nicht bestätigt werden."
            ),
        )

    consumed = plugin_plan_store.consume(plan_id)

    try:
        result = plugin_installer.install(
            consumed.archive_path,
            expected_sha256=consumed.sha256,
            installed_plugin_ids=_installed_plugin_ids(),
        )

        _refresh_plugins()
        record = plugin_manager.registry.get(result.plugin_id)

        return {
            "status": "installed",
            "plan_id": plan_id,
            "plugin": (
                plugin_record_to_dict(record)
                if record is not None
                else None
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
    finally:
        plugin_plan_store.finalize_consumed(consumed)


@router.delete(
    "/plan/{plan_id}",
    dependencies=WRITE_DEPENDENCIES,
)
def cancel_plugin_install_plan_endpoint(
    plan_id: str,
) -> dict[str, str]:
    stored = plugin_plan_store.get(plan_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installationsplan nicht gefunden oder abgelaufen.",
        )

    plugin_plan_store.delete(plan_id)

    return {
        "status": "cancelled",
        "plan_id": plan_id,
    }
