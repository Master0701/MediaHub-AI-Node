"""Tests für die kontrollierte Ausführung von Installationsplänen."""

from __future__ import annotations

import subprocess

import pytest

from app.plugins.install_plan import (
    InstallAction,
    InstallActionType,
    PluginInstallPlan,
)
from app.plugins.plan_executor import PluginPlanExecutor


def make_plan(
    actions: tuple[InstallAction, ...],
) -> PluginInstallPlan:
    return PluginInstallPlan(
        plugin_id="provider.executor-test",
        ready_without_changes=not actions,
        license_present=True,
        actions=actions,
        warnings=(),
        requires_confirmation=bool(actions),
        requires_restart=False,
    )


def test_system_tool_remains_pending() -> None:
    plan = make_plan(
        (
            InstallAction(
                action_type=InstallActionType.SYSTEM_TOOL,
                name="tesseract-ocr",
                reason="Test",
            ),
        )
    )

    result = PluginPlanExecutor().execute(plan)

    assert result.completed == ()
    assert len(result.pending) == 1
    assert result.failed == ()


def test_ai_plugin_remains_pending() -> None:
    plan = make_plan(
        (
            InstallAction(
                action_type=InstallActionType.AI_PLUGIN,
                name="provider.base",
                reason="Test",
            ),
        )
    )

    result = PluginPlanExecutor().execute(plan)

    assert len(result.pending) == 1
    assert result.pending[0].name == "provider.base"


def test_python_install_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        *args: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["python"],
            returncode=0,
            stdout="installed",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    plan = make_plan(
        (
            InstallAction(
                action_type=InstallActionType.PYTHON_PACKAGE,
                name="example-package>=1.0",
                reason="Test",
            ),
        )
    )

    result = PluginPlanExecutor().execute(plan)

    assert len(result.completed) == 1
    assert result.successful is True


def test_python_install_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        *args: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["python"],
            returncode=1,
            stdout="",
            stderr="installation failed",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    plan = make_plan(
        (
            InstallAction(
                action_type=InstallActionType.PYTHON_PACKAGE,
                name="example-package==1.0",
                reason="Test",
            ),
        )
    )

    result = PluginPlanExecutor().execute(plan)

    assert len(result.failed) == 1
    assert result.successful is False


def test_python_install_can_be_disabled() -> None:
    plan = make_plan(
        (
            InstallAction(
                action_type=InstallActionType.PYTHON_PACKAGE,
                name="example-package",
                reason="Test",
            ),
        )
    )

    result = PluginPlanExecutor(
        allow_python_packages=False,
    ).execute(plan)

    assert len(result.pending) == 1
    assert result.completed == ()
