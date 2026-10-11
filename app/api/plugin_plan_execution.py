"""Geschützte Ausführung freigegebener Installationsplan-Schritte."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.plugins.install_plan import (
    InstallActionType,
    PluginInstallPlanBuilder,
    install_plan_to_dict,
)
from app.plugins.managed_install import MANAGED_PLUGIN_IDS
from app.plugins.package_validator import (
    PluginPackageError,
    validate_plugin_package,
)
from app.plugins.plan_executor import (
    PluginPlanExecutor,
    execution_result_to_dict,
)
from app.plugins.preflight import (
    PluginPreflightChecker,
    PluginPreflightError,
)
from app.plugins.runtime import plugin_manager, plugin_plan_store
from app.security.api_token import require_api_token

router = APIRouter(prefix="/plugins", tags=["AI Plugins"])


def _installed_plugin_ids() -> set[str]:
    return {
        record.manifest.plugin_id
        for record in plugin_manager.registry.all()
    }


@router.post(
    "/plan/{plan_id}/execute",
    dependencies=[Depends(require_api_token)],
)
def execute_plugin_install_plan_endpoint(
    plan_id: str,
) -> dict[str, Any]:
    """Führt nur freigegebene Python-Paket-Schritte eines Plans aus."""

    stored = plugin_plan_store.get(plan_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installationsplan nicht gefunden oder abgelaufen.",
        )

    execution = PluginPlanExecutor(
        allow_python_packages=True,
    ).execute(stored.plan)

    try:
        package = validate_plugin_package(
            stored.archive_path,
            expected_sha256=stored.sha256,
        )
        preflight = PluginPreflightChecker(
            installed_plugin_ids=_installed_plugin_ids(),
        ).inspect(package)
        updated_plan = PluginInstallPlanBuilder().build(preflight)
        updated_stored = plugin_plan_store.update_plan(
            plan_id,
            updated_plan,
        )
    except (
        PluginPackageError,
        PluginPreflightError,
        KeyError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Managed runtimes/models are installed by PluginInstaller.install() at
    # the authenticated confirmation step, not by the generic package executor.
    # They must not block the confirmation UI as unsupported system tools.
    managed_actions = {
        InstallActionType.RUNTIME,
        InstallActionType.MANAGED_TOOL,
    }
    managed_ready_for_confirmation = (
        stored.plugin_id in MANAGED_PLUGIN_IDS
        and updated_plan.license_present
        and not execution.failed
        and bool(updated_plan.actions)
        and all(action.action_type in managed_actions for action in updated_plan.actions)
    )
    execution_data = execution_result_to_dict(execution)
    if managed_ready_for_confirmation:
        # Not executed yet: the existing approved installer will do it when
        # the user confirms. Keep the pending actions visible in the plan.
        execution_data["pending"] = []
        execution_data["deferred_to_confirmation"] = [
            {"type": action.action_type.value, "name": action.name}
            for action in updated_plan.actions
        ]

    return {
        "status": (
            "ready_for_confirmation"
            if updated_plan.ready_without_changes or managed_ready_for_confirmation
            else "requirements_pending"
        ),
        "plan_id": plan_id,
        "expires_at": updated_stored.expires_at.isoformat(),
        "execution": execution_data,
        "plan": install_plan_to_dict(updated_plan),
    }
