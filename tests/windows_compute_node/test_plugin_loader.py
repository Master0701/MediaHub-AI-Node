from __future__ import annotations

import json
from pathlib import Path

from windows_compute_node.plugins.loader import (
    ComputePluginLoader,
)
from windows_compute_node.workers.registry import (
    WorkerRegistry,
)


def write_plugin(
    root: Path,
    *,
    plugin_id: str = "test.plugin",
    plugin_type: str = "ai_node",
    entrypoint: str = "plugin.py",
    register_worker: bool = True,
):
    plugin = root / "plugin"
    plugin.mkdir()

    manifest = {
        "id": plugin_id,
        "name": "Test Plugin",
        "version": "1.0.0",
        "plugin_type": plugin_type,
        "entrypoint": entrypoint,
    }

    (
        plugin / "plugin.json"
    ).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    if register_worker:
        code = """
def handler(request):
    return {"ok": True}

def register(context):
    context["workers"].register(
        worker_id="test.worker",
        name="Test Worker",
        job_types=["test_job"],
        handler=handler,
        metadata={
            "plugin_id": context[
                "plugin_id"
            ],
        },
    )
"""
    else:
        code = """
def register(context):
    pass
"""

    (
        plugin / "plugin.py"
    ).write_text(
        code,
        encoding="utf-8",
    )

    return plugin


def test_discover_plugin(tmp_path):
    workers = WorkerRegistry()

    write_plugin(tmp_path)

    loader = ComputePluginLoader(
        plugin_root=tmp_path,
        workers=workers,
    )

    assert len(loader.discover()) == 1


def test_load_plugin_registers_worker(
    tmp_path,
):
    workers = WorkerRegistry()

    plugin = write_plugin(tmp_path)

    loader = ComputePluginLoader(
        plugin_root=tmp_path,
        workers=workers,
    )

    result = loader.load_plugin(plugin)

    assert result["loaded"] is True
    assert result["plugin_id"] == (
        "test.plugin"
    )

    worker = workers.find_for_job(
        "test_job"
    )

    assert worker is not None


def test_wrong_plugin_type_fails(
    tmp_path,
):
    workers = WorkerRegistry()

    write_plugin(
        tmp_path,
        plugin_type="mediahub",
    )

    loader = ComputePluginLoader(
        plugin_root=tmp_path,
        workers=workers,
    )

    result = loader.load_all()

    assert result[0]["loaded"] is False
    assert "plugin_type" in (
        result[0]["error"]
    )


def test_missing_entrypoint_fails(
    tmp_path,
):
    workers = WorkerRegistry()

    write_plugin(
        tmp_path,
        entrypoint="missing.py",
    )

    loader = ComputePluginLoader(
        plugin_root=tmp_path,
        workers=workers,
    )

    result = loader.load_all()

    assert result[0]["loaded"] is False


def test_plugin_without_worker_fails(
    tmp_path,
):
    workers = WorkerRegistry()

    write_plugin(
        tmp_path,
        register_worker=False,
    )

    loader = ComputePluginLoader(
        plugin_root=tmp_path,
        workers=workers,
    )

    result = loader.load_all()

    assert result[0]["loaded"] is False

    assert (
        "keinen Worker"
        in result[0]["error"]
    )


def test_empty_plugin_directory(
    tmp_path,
):
    workers = WorkerRegistry()

    loader = ComputePluginLoader(
        plugin_root=tmp_path,
        workers=workers,
    )

    assert loader.load_all() == []



def test_loader_blocks_missing_dependency_before_code_execution(tmp_path):
    import json

    import pytest

    from windows_compute_node.plugins.loader import (
        ComputePluginLoader,
        PluginLoadError,
    )
    from windows_compute_node.workers.registry import WorkerRegistry

    plugin_root = tmp_path / "plugins"
    plugin_dir = plugin_root / "mediahub.smolvlm2"
    plugin_dir.mkdir(parents=True)

    marker = tmp_path / "plugin_was_executed.txt"

    manifest = {
        "id": "mediahub.smolvlm2",
        "name": "MediaHub SmolVLM2",
        "version": "0.1.1",
        "type": "provider",
        "entrypoint": "plugin.py",
        "dependencies": [{
            "id": "mediahub.python_runtime",
            "minimum_version": "0.1.0",
            "targets": ["windows_compute"],
        }],
    }

    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    plugin_code = (
        "from pathlib import Path" + chr(10)
        + f"Path({str(marker)!r}).write_text('executed')" + chr(10)
    )

    (plugin_dir / "plugin.py").write_text(
        plugin_code,
        encoding="utf-8",
    )

    loader = ComputePluginLoader(
        plugin_root=plugin_root,
        workers=WorkerRegistry(),
    )

    with pytest.raises(PluginLoadError, match="mediahub.python_runtime"):
        loader.load_plugin(plugin_dir)

    assert not marker.exists()


def test_loader_blocks_unhealthy_python_runtime_before_execution(
    tmp_path, monkeypatch
):
    import json

    import pytest

    from windows_compute_node.plugins.loader import (
        ComputePluginLoader,
        PluginLoadError,
    )
    from windows_compute_node.workers.registry import WorkerRegistry

    plugin_root = tmp_path / "plugins"
    runtime_dir = plugin_root / "mediahub.python_runtime"
    runtime_dir.mkdir(parents=True)

    (runtime_dir / "plugin.json").write_text(
        json.dumps({
            "id": "mediahub.python_runtime",
            "version": "0.1.0",
            "type": "utility",
            "entrypoint": "plugin:MediaHubPythonRuntimePlugin",
        }),
        encoding="utf-8",
    )

    plugin_dir = plugin_root / "mediahub.smolvlm2"
    plugin_dir.mkdir()

    (plugin_dir / "plugin.json").write_text(
        json.dumps({
            "id": "mediahub.smolvlm2",
            "name": "MediaHub SmolVLM2",
            "version": "0.1.1",
            "type": "provider",
            "entrypoint": "plugin.py",
            "dependencies": [{
                "id": "mediahub.python_runtime",
                "minimum_version": "0.1.0",
                "targets": ["windows_compute"],
            }],
        }),
        encoding="utf-8",
    )

    marker = tmp_path / "plugin_was_executed.txt"

    (plugin_dir / "plugin.py").write_text(
        "from pathlib import Path" + chr(10)
        + f"Path({str(marker)!r}).write_text('executed')" + chr(10),
        encoding="utf-8",
    )

    monkeypatch.setenv(
        "MEDIAHUB_COMPUTE_RUNTIME",
        str(tmp_path / "missing_runtime"),
    )

    loader = ComputePluginLoader(
        plugin_root=plugin_root,
        workers=WorkerRegistry(),
    )

    with pytest.raises(PluginLoadError, match="mediahub.python_runtime"):
        loader.load_plugin(plugin_dir)

    assert not marker.exists()
