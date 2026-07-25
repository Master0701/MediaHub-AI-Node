"""Tests für bestätigungspflichtige AI-Plugin-Installationspläne."""

from __future__ import annotations

from app.plugins.install_plan import (
    InstallActionType,
    PluginInstallPlanBuilder,
    install_plan_to_dict,
)
from app.plugins.preflight import (
    DependencyCheck,
    PluginPreflightResult,
)


def test_ready_plan_has_no_actions() -> None:
    preflight = PluginPreflightResult(
        plugin_id="provider.ready",
        license_present=True,
        python_requirements=(),
        required_tools=(),
        plugin_dependencies=(),
    )

    plan = PluginInstallPlanBuilder().build(preflight)

    assert plan.ready_without_changes is True
    assert plan.requires_confirmation is False
    assert plan.missing_count == 0


def test_missing_python_package_creates_action() -> None:
    preflight = PluginPreflightResult(
        plugin_id="provider.python",
        license_present=True,
        python_requirements=(
            DependencyCheck(
                name="sentence-transformers>=3.0",
                required=True,
                available=False,
            ),
        ),
        required_tools=(),
        plugin_dependencies=(),
    )

    plan = PluginInstallPlanBuilder().build(preflight)

    assert plan.missing_count == 1
    assert plan.actions[0].action_type is InstallActionType.PYTHON_PACKAGE
    assert "pip install" in plan.actions[0].command_preview


def test_missing_tool_creates_action() -> None:
    preflight = PluginPreflightResult(
        plugin_id="ocr.test",
        license_present=True,
        python_requirements=(),
        required_tools=(
            DependencyCheck(
                name="tesseract-ocr",
                required=True,
                available=False,
            ),
        ),
        plugin_dependencies=(),
    )

    plan = PluginInstallPlanBuilder().build(preflight)

    assert plan.actions[0].action_type is InstallActionType.SYSTEM_TOOL
    assert plan.actions[0].name == "tesseract-ocr"


def test_missing_ai_plugin_creates_action() -> None:
    preflight = PluginPreflightResult(
        plugin_id="analyzer.test",
        license_present=True,
        python_requirements=(),
        required_tools=(),
        plugin_dependencies=(
            DependencyCheck(
                name="provider.base",
                required=True,
                available=False,
            ),
        ),
    )

    plan = PluginInstallPlanBuilder().build(preflight)

    assert plan.actions[0].action_type is InstallActionType.AI_PLUGIN
    assert plan.requires_confirmation is True


def test_plan_serialization() -> None:
    preflight = PluginPreflightResult(
        plugin_id="provider.serialize",
        license_present=True,
        python_requirements=(
            DependencyCheck(
                name="example-package",
                required=True,
                available=False,
            ),
        ),
        required_tools=(),
        plugin_dependencies=(),
        warnings=("Testwarnung",),
    )

    plan = PluginInstallPlanBuilder().build(preflight)
    data = install_plan_to_dict(plan)

    assert data["plugin_id"] == "provider.serialize"
    assert data["missing_count"] == 1
    assert data["warnings"] == ["Testwarnung"]
    assert data["actions"][0]["type"] == "python_package"
