"""Erzeugt bestätigungspflichtige Installationspläne für AI-Plugins."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.plugins.preflight import PluginPreflightResult


class InstallActionType(StrEnum):
    """Typ eines geplanten Installationsschritts."""

    PYTHON_PACKAGE = "python_package"
    SYSTEM_TOOL = "system_tool"
    AI_PLUGIN = "ai_plugin"


@dataclass(frozen=True, slots=True)
class InstallAction:
    """Ein einzelner Schritt eines Installationsplans."""

    action_type: InstallActionType
    name: str
    reason: str
    command_preview: str | None = None
    requires_confirmation: bool = True
    requires_restart: bool = False


@dataclass(frozen=True, slots=True)
class PluginInstallPlan:
    """Vollständiger Plan vor einer späteren automatischen Installation."""

    plugin_id: str
    ready_without_changes: bool
    license_present: bool
    actions: tuple[InstallAction, ...]
    warnings: tuple[str, ...]
    requires_confirmation: bool
    requires_restart: bool

    @property
    def missing_count(self) -> int:
        return len(self.actions)


class PluginInstallPlanBuilder:
    """Wandelt ein Vorprüfungsergebnis in einen Installationsplan um."""

    def build(
        self,
        preflight: PluginPreflightResult,
    ) -> PluginInstallPlan:
        actions: list[InstallAction] = []

        for check in preflight.python_requirements:
            if check.available:
                continue

            package_name = check.name
            actions.append(
                InstallAction(
                    action_type=InstallActionType.PYTHON_PACKAGE,
                    name=package_name,
                    reason="Benötigtes Python-Paket ist nicht installiert.",
                    command_preview=f"python -m pip install {package_name}",
                )
            )

        for check in preflight.required_tools:
            if check.available:
                continue

            tool_name = check.name
            actions.append(
                InstallAction(
                    action_type=InstallActionType.SYSTEM_TOOL,
                    name=tool_name,
                    reason="Benötigtes Systemwerkzeug ist nicht verfügbar.",
                    command_preview=f"sudo apt install {tool_name}",
                    requires_restart=False,
                )
            )

        for check in preflight.plugin_dependencies:
            if check.available:
                continue

            actions.append(
                InstallAction(
                    action_type=InstallActionType.AI_PLUGIN,
                    name=check.name,
                    reason="Benötigtes AI-Plugin ist nicht installiert.",
                    command_preview=None,
                )
            )

        requires_restart = any(
            action.requires_restart
            for action in actions
        )

        return PluginInstallPlan(
            plugin_id=preflight.plugin_id,
            ready_without_changes=not actions and preflight.license_present,
            license_present=preflight.license_present,
            actions=tuple(actions),
            warnings=preflight.warnings,
            requires_confirmation=bool(actions),
            requires_restart=requires_restart,
        )


def install_plan_to_dict(
    plan: PluginInstallPlan,
) -> dict[str, object]:
    """Serialisiert einen Installationsplan für REST oder MediaHub."""

    return {
        "plugin_id": plan.plugin_id,
        "ready_without_changes": plan.ready_without_changes,
        "license_present": plan.license_present,
        "missing_count": plan.missing_count,
        "requires_confirmation": plan.requires_confirmation,
        "requires_restart": plan.requires_restart,
        "warnings": list(plan.warnings),
        "actions": [
            {
                "type": action.action_type.value,
                "name": action.name,
                "reason": action.reason,
                "command_preview": action.command_preview,
                "requires_confirmation": action.requires_confirmation,
                "requires_restart": action.requires_restart,
            }
            for action in plan.actions
        ],
    }
