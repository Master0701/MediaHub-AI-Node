"""Geschützter REST-Endpunkt zur reinen Installationsplanung."""

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
from app.plugins.runtime import plugin_manager
from app.security.api_token import require_api_token

router = APIRouter(prefix="/plugins", tags=["AI Plugins"])

MAX_UPLOAD_SIZE = 512 * 1024 * 1024


def _installed_plugin_ids() -> set[str]:
    return {
        record.manifest.plugin_id
        for record in plugin_manager.registry.all()
    }


@router.post(
    "/plan",
    dependencies=[Depends(require_api_token)],
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
    """Prüft ein Plugin-Paket und liefert nur einen Installationsplan."""

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

        return {
            "status": "plan_created",
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
