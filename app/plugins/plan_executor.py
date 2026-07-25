"""Kontrollierte Ausführung freigegebener Plugin-Installationsschritte."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

from app.plugins.install_plan import (
    InstallAction,
    InstallActionType,
    PluginInstallPlan,
)
from app.plugins.preflight import REQUIREMENT_PATTERN


@dataclass(frozen=True, slots=True)
class InstallActionExecution:
    """Ergebnis eines einzelnen Installationsschritts."""

    action_type: InstallActionType
    name: str
    status: str
    return_code: int | None = None
    output: str = ""
    error: str = ""


@dataclass(frozen=True, slots=True)
class PluginPlanExecutionResult:
    """Ergebnis der kontrollierten Planausführung."""

    plugin_id: str
    completed: tuple[InstallActionExecution, ...]
    pending: tuple[InstallAction, ...]
    failed: tuple[InstallActionExecution, ...]

    @property
    def successful(self) -> bool:
        return not self.failed


class PluginPlanExecutor:
    """Führt ausschließlich ausdrücklich freigegebene Aktionstypen aus."""

    def __init__(self, *, allow_python_packages: bool = True) -> None:
        self.allow_python_packages = allow_python_packages

    def execute(self, plan: PluginInstallPlan) -> PluginPlanExecutionResult:
        completed: list[InstallActionExecution] = []
        pending: list[InstallAction] = []
        failed: list[InstallActionExecution] = []

        for action in plan.actions:
            if action.action_type is InstallActionType.PYTHON_PACKAGE:
                if not self.allow_python_packages:
                    pending.append(action)
                    continue

                result = self._install_python_package(action)
                if result.status == "completed":
                    completed.append(result)
                else:
                    failed.append(result)
                continue

            pending.append(action)

        return PluginPlanExecutionResult(
            plugin_id=plan.plugin_id,
            completed=tuple(completed),
            pending=tuple(pending),
            failed=tuple(failed),
        )

    @staticmethod
    def _install_python_package(
        action: InstallAction,
    ) -> InstallActionExecution:
        requirement = action.name.strip()

        if not REQUIREMENT_PATTERN.fullmatch(requirement):
            return InstallActionExecution(
                action_type=action.action_type,
                name=requirement,
                status="failed",
                error="Die Python-Anforderung besitzt ein unsicheres Format.",
            )

        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            requirement,
        ]

        try:
            process = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=1800,
            )
        except subprocess.TimeoutExpired:
            return InstallActionExecution(
                action_type=action.action_type,
                name=requirement,
                status="failed",
                error="Die Installation hat das Zeitlimit überschritten.",
            )
        except OSError as exc:
            return InstallActionExecution(
                action_type=action.action_type,
                name=requirement,
                status="failed",
                error=str(exc),
            )

        if process.returncode != 0:
            return InstallActionExecution(
                action_type=action.action_type,
                name=requirement,
                status="failed",
                return_code=process.returncode,
                output=process.stdout[-4000:],
                error=process.stderr[-4000:],
            )

        return InstallActionExecution(
            action_type=action.action_type,
            name=requirement,
            status="completed",
            return_code=process.returncode,
            output=process.stdout[-4000:],
            error=process.stderr[-4000:],
        )


def execution_result_to_dict(
    result: PluginPlanExecutionResult,
) -> dict[str, object]:
    def execution_to_dict(
        item: InstallActionExecution,
    ) -> dict[str, object]:
        return {
            "type": item.action_type.value,
            "name": item.name,
            "status": item.status,
            "return_code": item.return_code,
            "output": item.output,
            "error": item.error,
        }

    return {
        "plugin_id": result.plugin_id,
        "successful": result.successful,
        "completed": [
            execution_to_dict(item)
            for item in result.completed
        ],
        "pending": [
            {
                "type": action.action_type.value,
                "name": action.name,
                "reason": action.reason,
                "requires_confirmation": action.requires_confirmation,
            }
            for action in result.pending
        ],
        "failed": [
            execution_to_dict(item)
            for item in result.failed
        ],
    }
