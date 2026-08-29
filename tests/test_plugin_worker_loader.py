from __future__ import annotations

import json
from pathlib import Path

from app.jobs.registry import job_handler_registry
from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry
from app.plugins.state import PluginStateStore
from app.plugins.worker_bridge import plugin_worker_registry

PLUGIN_ID = "test.shared_worker"
WORKER_ID = "test.shared_worker.worker"
JOB_TYPE = "test_shared_worker_job"


def _write_plugin(plugin_root: Path) -> None:
    plugin_dir = plugin_root / "shared_worker"
    plugin_dir.mkdir(parents=True)

    manifest = {
        "id": PLUGIN_ID,
        "name": "Shared Worker Test",
        "version": "1.0.0",
        "type": "worker",
        "entrypoint": "plugin:SharedWorkerPlugin",
        "api_version": "1",
        "enabled_by_default": True,
        "capabilities": ["test_shared_worker"],
        "job_types": [JOB_TYPE],
        "targets": [
            "raspberry_pi",
            "windows_compute",
        ],
        "platforms": [
            "linux-aarch64",
            "windows-amd64",
        ],
    }

    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    (plugin_dir / "plugin.py").write_text(
        f"""
class SharedWorkerPlugin:
    def register(self, context):
        def handler(request):
            return {{
                "status": "completed",
                "request": request,
                "plugin_id": context["plugin_id"],
            }}

        context["workers"].register(
            worker_id="{WORKER_ID}",
            name="Shared Worker",
            job_types=["{JOB_TYPE}"],
            handler=handler,
            metadata={{
                "plugin_id": context["plugin_id"],
            }},
        )
""",
        encoding="utf-8",
    )


def test_shared_worker_loads_through_pi_plugin_loader(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    plugin_root.mkdir()

    _write_plugin(plugin_root)

    registry = PluginRegistry()
    state_store = PluginStateStore(
        tmp_path / "plugin_state.json"
    )
    loader = PluginLoader(
        plugin_root,
        registry,
        state_store,
    )

    try:
        discovered = loader.discover()

        assert len(discovered) == 1
        assert discovered[0].manifest.plugin_id == PLUGIN_ID
        assert discovered[0].manifest.plugin_type.value == "worker"

        loaded = loader.load_enabled()

        assert len(loaded) == 1
        assert loaded[0].loaded is True
        assert loaded[0].error is None

        worker = plugin_worker_registry.get(WORKER_ID)

        assert worker is not None
        assert worker["executable"] is True
        assert JOB_TYPE in worker["job_types"]

        job_handler = job_handler_registry.require(JOB_TYPE)

        result = job_handler.execute(
            db=None,
            payload={
                "input": "/tmp/example.wav",
            },
            progress_callback=lambda *_args, **_kwargs: None,
        )

        assert result["status"] == "completed"
        assert result["plugin_id"] == PLUGIN_ID
        assert result["request"] == {
            "payload": {
                "input": "/tmp/example.wav",
            }
        }

    finally:
        plugin_worker_registry.unregister(WORKER_ID)

    assert plugin_worker_registry.get(WORKER_ID) is None
    assert job_handler_registry.get(JOB_TYPE) is None


def test_worker_cannot_replace_another_worker_job_type(
    tmp_path: Path,
) -> None:
    del tmp_path

    def first_handler(request):
        return request

    def second_handler(request):
        return request

    plugin_worker_registry.register(
        worker_id=WORKER_ID,
        name="First Worker",
        job_types=[JOB_TYPE],
        handler=first_handler,
    )

    first_job_handler = job_handler_registry.require(
        JOB_TYPE
    )

    try:
        try:
            plugin_worker_registry.register(
                worker_id="test.replacement.worker",
                name="Replacement Worker",
                job_types=[JOB_TYPE],
                handler=second_handler,
            )
        except ValueError as exc:
            assert "bereits" in str(exc)
        else:
            raise AssertionError(
                "Job-Type-Kollision wurde nicht verhindert."
            )

        assert (
            job_handler_registry.require(JOB_TYPE)
            is first_job_handler
        )
    finally:
        plugin_worker_registry.unregister(WORKER_ID)
        plugin_worker_registry.unregister(
            "test.replacement.worker"
        )
