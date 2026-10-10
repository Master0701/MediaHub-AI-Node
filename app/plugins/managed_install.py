"""Explicit, approved provisioning for known MediaHub AI-Node plugins.

This module is deliberately allowlisted. Unknown plugins may not request
arbitrary downloaders or executable install hooks through their manifests.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

MANAGED_PLUGIN_IDS = frozenset({"mediahub.gliner", "mediahub.smolvlm2"})
MODEL_TOOL_ID = "smolvlm2-model"
MODEL_DIRECTORY_NAME = "SmolVLM2-500M-Video-Instruct"
MODEL_REQUIRED_FILES = (
    "added_tokens.json", "chat_template.json", "config.json",
    "generation_config.json", "model.safetensors", "preprocessor_config.json",
    "processor_config.json", "special_tokens_map.json", "tokenizer.json",
    "tokenizer_config.json",
)


class ManagedProvisionError(RuntimeError):
    """An explicitly approved plugin dependency cannot be made ready."""


def _compute_root() -> Path:
    base = os.environ.get("MEDIAHUB_COMPUTE_RUNTIME")
    return Path(base) if base else Path.home() / ".mediahub" / "compute_node"


def _model_path() -> Path:
    return (
        _compute_root() / "runtimes" / "smolvlm2" / "models"
        / MODEL_DIRECTORY_NAME / "model"
    )


def inspect_managed_tool(*, plugin_id: str, tool_id: str) -> bool:
    """Pure filesystem check for the one supported MediaHub_Tools asset."""
    if (plugin_id, tool_id) != ("mediahub.smolvlm2", MODEL_TOOL_ID):
        return False
    model = _model_path()
    return model.is_dir() and all((model / name).is_file() for name in MODEL_REQUIRED_FILES)


def _load_local(plugin_dir: Path, filename: str):
    path = (plugin_dir / filename).resolve()
    if not path.is_file() or path.parent != plugin_dir.resolve():
        raise ManagedProvisionError(f"Erforderliche Plugin-Datei fehlt: {filename}")
    name = "_mediahub_provision_" + filename.replace(".", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ManagedProvisionError(f"Modul nicht ladbar: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_managed_assets(
    plugin_id: str,
    plugin_dir: Path,
    *,
    tool_requirements: tuple[Any, ...] = (),
) -> dict[str, Any]:
    """Run approved runtime/model provisioning BEFORE plugin activation.

    Installation is invoked only after authenticated upload or confirmation.
    Existing ready assets are reused. A failure prevents the new plugin
    directory from replacing an installed version.
    """
    if plugin_id not in MANAGED_PLUGIN_IDS:
        return {"managed": False, "ready": True}

    for tool in tool_requirements:
        if getattr(tool, "source", "system") != "mediahub_tools":
            continue
        if (plugin_id, tool.tool_id) != ("mediahub.smolvlm2", MODEL_TOOL_ID):
            raise ManagedProvisionError(
                f"Nicht freigegebenes MediaHub_Tools-Werkzeug: {tool.tool_id}"
            )

    if plugin_id == "mediahub.gliner":
        manager = _load_local(plugin_dir, "runtime_manager.py")
        status = manager.inspect_runtime()
        if not status.get("ready"):
            manager.install_dependencies(profile="auto", capabilities=None)
            status = manager.inspect_runtime()
        if not status.get("ready"):
            raise ManagedProvisionError(f"GLiNER-Runtime nach Installation nicht bereit: {status}")

        # The plugin otherwise fetches its default model on first use.
        # Verify the real runner and prime the default model during install.
        bridge = _load_local(plugin_dir, "runtime_bridge.py")
        result = bridge.run_analysis(
            runtime_python=status["python"],
            packages_path=status["packages_path"],
            runner_path=plugin_dir / "runtime_runner.py",
            text="NCIS",
            execution={"backend": "cpu", "mode": "cpu", "cpu_threads": 2},
            options={"labels": ["organization"], "threshold": 0.35},
        )
        if result.get("engine") != "gliner":
            raise ManagedProvisionError("GLiNER hat keine echte Modellantwort geliefert.")
        return {"managed": True, "ready": True, "runtime": "gliner", "model_verified": True}

    runtime = _load_local(plugin_dir, "runtime.py")
    status = runtime.inspect_runtime()
    if not status.get("ready"):
        runtime.install_dependencies(requested_backend="auto")
        status = runtime.inspect_runtime()
    if not status.get("ready"):
        raise ManagedProvisionError(f"SmolVLM2-Runtime nach Installation nicht bereit: {status}")

    manager = _load_local(plugin_dir, "model_manager.py")
    requested = [t for t in tool_requirements if t.tool_id == MODEL_TOOL_ID]
    if len(requested) != 1 or requested[0].source != "mediahub_tools" or not requested[0].required:
        raise ManagedProvisionError("Das Pflichtmodell smolvlm2-model fehlt im Plugin-Manifest.")
    expected_version = requested[0].version
    actual_version = str(manager.MODEL_PACKAGE_VERSION)
    if expected_version is not None and expected_version != actual_version:
        raise ManagedProvisionError(
            f"SmolVLM2-Modellversion stimmt nicht: {expected_version} != {actual_version}"
        )

    models = runtime.models_root()
    try:
        model = manager.resolve_model_path(models)
    except RuntimeError:
        manager.install_model(models)
        model = manager.resolve_model_path(models)
    if not model.is_dir():
        raise ManagedProvisionError("SmolVLM2-Modellverzeichnis nach Installation fehlt.")
    return {"managed": True, "ready": True, "runtime": "smolvlm2", "model_path": str(model)}


def verify_activated_plugin(result, record, *, installer, refresh) -> None:
    """Roll back when the new managed plugin cannot be loaded into the Node.

    Runtime/model readiness alone is not enough to claim a usable install.
    The installer keeps the previous plugin until dependency setup succeeds;
    this final check protects the worker registration step too.
    """
    if result.plugin_id not in MANAGED_PLUGIN_IDS:
        return
    if record is not None and record.enabled and record.loaded and not record.error:
        return

    message = getattr(record, "error", None) or "Plugin nicht geladen oder nicht aktiviert"
    try:
        if result.replaced_existing and result.backup_path is not None:
            installer.rollback(plugin_id=result.plugin_id, backup_path=result.backup_path)
        else:
            installer.remove(result.plugin_id, create_backup=False)
        refresh()
    except Exception as exc:
        raise ManagedProvisionError(
            f"{result.plugin_id} ist nicht einsatzbereit: {message}; "
            f"automatische Rücksetzung fehlgeschlagen: {exc}"
        ) from exc
    raise ManagedProvisionError(
        f"{result.plugin_id} ist nicht einsatzbereit: {message}. "
        "Vorherige Installation wurde wiederhergestellt."
    )
