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
