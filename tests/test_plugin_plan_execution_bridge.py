"""Regression tests for approved managed-plugin plan execution handoff."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.plugin_plan_execution as execution_api
from app.api.plugin_plan_execution import router
from app.plugins.install_plan import InstallAction, InstallActionType, PluginInstallPlan
from app.plugins.plan_store import PluginPlanStore
from app.security.api_token import API_TOKEN_ENV_NAME

TOKEN = "b" * 48


def make_plan(
    plugin_id: str, kinds: tuple[InstallActionType, ...], *, license_present: bool = True
) -> PluginInstallPlan:
    actions = tuple(
        InstallAction(action_type=kind, name=f"test-{kind.value}", reason="Test") for kind in kinds
    )
    return PluginInstallPlan(
        plugin_id=plugin_id,
        ready_without_changes=not actions and license_present,
        license_present=license_present,
        actions=actions,
        warnings=(),
        requires_confirmation=bool(actions),
        requires_restart=False,
    )


@pytest.mark.parametrize(
    ("plugin_id", "kinds", "license_present", "expected_status"),
    [
        ("mediahub.gliner", (InstallActionType.RUNTIME,), True, "ready_for_confirmation"),
        (
            "mediahub.smolvlm2",
            (InstallActionType.RUNTIME, InstallActionType.MANAGED_TOOL),
            True,
            "ready_for_confirmation",
        ),
        ("provider.other", (InstallActionType.RUNTIME,), True, "requirements_pending"),
        (
            "mediahub.gliner",
            (InstallActionType.RUNTIME, InstallActionType.SYSTEM_TOOL),
            True,
            "requirements_pending",
        ),
        ("mediahub.gliner", (InstallActionType.RUNTIME,), False, "requirements_pending"),
        ("provider.other", (), True, "ready_for_confirmation"),
    ],
)
def test_execute_plan_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    plugin_id: str,
    kinds: tuple[InstallActionType, ...],
    license_present: bool,
    expected_status: str,
) -> None:
    store = PluginPlanStore(storage_root=tmp_path / "plans")
    archive = tmp_path / "plugin.zip"
    archive.write_bytes(b"test archive; validator is mocked")
    plan = make_plan(plugin_id, kinds, license_present=license_present)
    stored = store.create(
        plugin_id=plugin_id,
        archive_path=archive,
        sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        plan=plan,
    )
    monkeypatch.setattr(execution_api, "plugin_plan_store", store)
    monkeypatch.setattr(execution_api, "validate_plugin_package", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        execution_api,
        "PluginPreflightChecker",
        lambda **kwargs: SimpleNamespace(inspect=lambda package: object()),
    )
    monkeypatch.setattr(
        execution_api,
        "PluginInstallPlanBuilder",
        lambda: SimpleNamespace(build=lambda preflight: plan),
    )
    monkeypatch.setattr(execution_api, "_installed_plugin_ids", lambda: set())
    monkeypatch.setenv(API_TOKEN_ENV_NAME, TOKEN)

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.post(
        f"/plugins/plan/{stored.plan_id}/execute",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == expected_status
    assert len(data["plan"]["actions"]) == len(kinds)
    if expected_status == "ready_for_confirmation" and kinds:
        assert data["execution"]["pending"] == []
        assert len(data["execution"]["deferred_to_confirmation"]) == len(kinds)
        assert store.get(stored.plan_id) is not None
    elif kinds:
        assert len(data["execution"]["pending"]) == len(kinds)
        assert "deferred_to_confirmation" not in data["execution"]


def test_execute_requires_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(API_TOKEN_ENV_NAME, TOKEN)
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).post("/plugins/plan/not-real/execute")
    assert response.status_code == 401
