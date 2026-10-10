"""Offline regression tests: managed runtime/model install, confirmation and safety."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from app.plugins import managed_install
from app.plugins.install_plan import InstallActionType, PluginInstallPlanBuilder
from app.plugins.installer import PluginInstaller, PluginInstallError
from app.plugins.manifest import PluginManifest
from app.plugins.preflight import DependencyCheck, PluginPreflightChecker, PluginPreflightResult


def test_manifest_keeps_model_tool_metadata():
    manifest = PluginManifest.from_dict({
        "id": "mediahub.smolvlm2", "name": "Vision", "version": "0.1.1",
        "type": "model", "entrypoint": "plugin:SmolVLM2Plugin",
        "required_tools": [{"id": "smolvlm2-model", "source": "mediahub_tools",
                            "version": "0.1.0", "required": True}],
    })
    assert manifest.tool_requirements[0].source == "mediahub_tools"
    assert manifest.tool_requirements[0].version == "0.1.0"


def test_install_plan_discloses_managed_runtime_and_model():
    preflight = PluginPreflightResult(
        plugin_id="mediahub.smolvlm2", license_present=True,
        python_requirements=(),
        required_tools=(DependencyCheck(name="smolvlm2-model", required=True,
                                        available=False, source="mediahub_tools"),),
        plugin_dependencies=(),
    )
    plan = PluginInstallPlanBuilder().build(preflight)
    assert [a.action_type for a in plan.actions] == [
        InstallActionType.RUNTIME, InstallActionType.MANAGED_TOOL,
    ]
    assert plan.requires_confirmation


def test_model_file_probe(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIAHUB_COMPUTE_RUNTIME", str(tmp_path))
    assert not managed_install.inspect_managed_tool(
        plugin_id="mediahub.smolvlm2", tool_id="smolvlm2-model"
    )
    model = managed_install._model_path()
    model.mkdir(parents=True)
    for filename in managed_install.MODEL_REQUIRED_FILES:
        (model / filename).write_text("test", encoding="utf-8")
    assert managed_install.inspect_managed_tool(
        plugin_id="mediahub.smolvlm2", tool_id="smolvlm2-model"
    )
    assert not managed_install.inspect_managed_tool(
        plugin_id="another.plugin", tool_id="smolvlm2-model"
    )


def test_smol_provision_installs_missing_model_only(monkeypatch, tmp_path):
    models = tmp_path / "models"
    models.mkdir()
    state = {"model": False, "install_count": 0, "runtime_installs": 0}

    def resolve(path):
        assert path == models
        if not state["model"]:
            raise RuntimeError("model missing")
        return models

    def install(path):
        state["model"] = True
        state["install_count"] += 1

    runtime = SimpleNamespace(
        inspect_runtime=lambda: {"ready": True},
        install_dependencies=lambda **kwargs: state.__setitem__(
            "runtime_installs", state["runtime_installs"] + 1,
        ),
        models_root=lambda: models,
    )
    model_manager = SimpleNamespace(
        MODEL_PACKAGE_VERSION="0.1.0", resolve_model_path=resolve, install_model=install
    )
    monkeypatch.setattr(managed_install, "_load_local", lambda path, file: {
        "runtime.py": runtime, "model_manager.py": model_manager,
    }[file])
    required = (SimpleNamespace(tool_id="smolvlm2-model", source="mediahub_tools",
                                version="0.1.0", required=True),)
    ready = managed_install.ensure_managed_assets(
        "mediahub.smolvlm2", tmp_path, tool_requirements=required
    )
    assert ready["ready"] is True
    assert state == {"model": True, "install_count": 1, "runtime_installs": 0}
    managed_install.ensure_managed_assets(
        "mediahub.smolvlm2", tmp_path, tool_requirements=required
    )
    assert state["install_count"] == 1  # idempotent on reinstall


def test_smol_model_version_mismatch_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(managed_install, "_load_local", lambda path, file: {
        "runtime.py": SimpleNamespace(inspect_runtime=lambda: {"ready": True}),
        "model_manager.py": SimpleNamespace(MODEL_PACKAGE_VERSION="0.1.0"),
    }[file])
    required = (SimpleNamespace(tool_id="smolvlm2-model", source="mediahub_tools",
                                version="9.9.9", required=True),)
    with pytest.raises(managed_install.ManagedProvisionError, match="Modellversion"):
        managed_install.ensure_managed_assets(
            "mediahub.smolvlm2", tmp_path, tool_requirements=required
        )


def test_gliner_provision_smoke_test(monkeypatch, tmp_path):
    calls = []
    manager = SimpleNamespace(inspect_runtime=lambda: {
        "ready": True, "python": "/test/python", "packages_path": "/test/packages"
    })
    bridge = SimpleNamespace(run_analysis=lambda **kwargs: (
        calls.append(kwargs), {"engine": "gliner", "entities": []}
    )[1])
    monkeypatch.setattr(managed_install, "_load_local", lambda path, file: {
        "runtime_manager.py": manager, "runtime_bridge.py": bridge,
    }[file])
    ready = managed_install.ensure_managed_assets("mediahub.gliner", tmp_path)
    assert ready["ready"] is True
    assert calls[0]["text"] == "NCIS"
    assert calls[0]["options"].get("mock") is None


def _gliner_package(path: Path, version: str, marker: str):
    manifest = {"id": "mediahub.gliner", "name": "GLiNER", "version": version,
                "type": "worker", "entrypoint": "plugin:MediaHubGLiNERPlugin",
                "runtime": {"isolated": True, "engine": "gliner"}}
    with ZipFile(path, "w") as arc:
        arc.writestr("mediahub.gliner/plugin.json", json.dumps(manifest))
        arc.writestr("mediahub.gliner/plugin.py", f"MARKER = {marker!r}\n")
        arc.writestr("mediahub.gliner/README.md", "GLiNER\n")
        arc.writestr("mediahub.gliner/CHANGELOG.md", "v1\n")
        arc.writestr("mediahub.gliner/LICENSE", "MIT\n")
        arc.writestr("mediahub.gliner/requirements.txt", "gliner\n")


def test_managed_plugin_installs_only_after_provision(monkeypatch, tmp_path):
    installer = PluginInstaller(plugin_root=tmp_path / "plugins", backup_root=tmp_path / "backups")
    archive = tmp_path / "gliner.zip"
    _gliner_package(archive, "0.1.1", "new")
    calls = []
    monkeypatch.setattr(
        "app.plugins.installer.ensure_managed_assets",
        lambda *args, **kw: calls.append((args, kw)),
    )
    result = installer.install(archive)
    assert result.preflight.ready is True
    assert calls[0][0][0] == "mediahub.gliner"
    assert (result.install_path / "plugin.py").read_text() == "MARKER = 'new'\n"


def test_failed_managed_provision_keeps_old_plugin(monkeypatch, tmp_path):
    installer = PluginInstaller(plugin_root=tmp_path / "plugins", backup_root=tmp_path / "backups")
    old_archive = tmp_path / "old.zip"
    new_archive = tmp_path / "new.zip"
    _gliner_package(old_archive, "0.1.0", "old")
    _gliner_package(new_archive, "0.1.1", "new")
    monkeypatch.setattr("app.plugins.installer.ensure_managed_assets", lambda *args, **kw: None)
    installer.install(old_archive)
    def failed(*args, **kwargs):
        raise RuntimeError("No network")
    monkeypatch.setattr("app.plugins.installer.ensure_managed_assets", failed)
    with pytest.raises(PluginInstallError, match="No network"):
        installer.install(new_archive)
    current = tmp_path / "plugins" / "mediahub.gliner" / "plugin.py"
    assert current.read_text() == "MARKER = 'old'\n"
    assert not (tmp_path / "plugins" / ".mediahub.gliner.installing").exists()


def test_managed_model_preflight_detects_missing_and_ready(monkeypatch, tmp_path):
    from app.plugins.package_validator import validate_plugin_package

    monkeypatch.setenv("MEDIAHUB_COMPUTE_RUNTIME", str(tmp_path / "runtime-store"))
    zip_path = tmp_path / "smol.zip"
    manifest = {
        "id": "mediahub.smolvlm2", "name": "SmolVLM2", "version": "0.1.1",
        "type": "model", "entrypoint": "plugin:SmolVLM2Plugin",
        "runtime": {"isolated": True, "engine": "smolvlm2"},
        "required_tools": [{"id": "smolvlm2-model", "version": "0.1.0",
                            "source": "mediahub_tools", "required": True}],
    }
    with ZipFile(zip_path, "w") as arc:
        arc.writestr("mediahub.smolvlm2/plugin.json", json.dumps(manifest))
        arc.writestr("mediahub.smolvlm2/README.md", "SmolVLM2")
        arc.writestr("mediahub.smolvlm2/CHANGELOG.md", "0.1.1")
        arc.writestr("mediahub.smolvlm2/LICENSE", "MIT")
        arc.writestr("mediahub.smolvlm2/requirements.txt", "torch\n")
    package = validate_plugin_package(zip_path)
    checker = PluginPreflightChecker()
    missing = checker.inspect(package)
    assert missing.python_requirements == ()  # isolated, never modify Node venv
    assert missing.required_tools[0].name == "smolvlm2-model"
    assert missing.required_tools[0].source == "mediahub_tools"
    assert not missing.required_tools[0].available
    assert not missing.ready

    model = managed_install._model_path()
    model.mkdir(parents=True)
    for filename in managed_install.MODEL_REQUIRED_FILES:
        (model / filename).write_bytes(b"file")
    ready = checker.check(package)
    assert ready.ready


def test_failed_plugin_activation_rolls_back(monkeypatch):
    from types import SimpleNamespace

    calls = []
    installer = SimpleNamespace(
        rollback=lambda **kw: calls.append(("rollback", kw)),
        remove=lambda *args, **kw: calls.append(("remove", args)),
    )
    result = SimpleNamespace(plugin_id="mediahub.smolvlm2", replaced_existing=True,
                             backup_path=Path("/tmp/known-test-backup"))
    record = SimpleNamespace(enabled=True, loaded=False, error="worker registration failed")
    with pytest.raises(managed_install.ManagedProvisionError, match="wiederhergestellt"):
        managed_install.verify_activated_plugin(
            result, record, installer=installer,
            refresh=lambda: calls.append(("refresh", None)),
        )
    assert calls[0][0] == "rollback"
    assert calls[1][0] == "refresh"


def test_healthy_managed_plugin_is_not_rolled_back():
    from types import SimpleNamespace

    result = SimpleNamespace(plugin_id="mediahub.gliner", replaced_existing=False,
                             backup_path=None)
    record = SimpleNamespace(enabled=True, loaded=True, error=None)
    managed_install.verify_activated_plugin(
        result, record, installer=None,
        refresh=lambda: (_ for _ in ()).throw(AssertionError("unexpected refresh")),
    )
