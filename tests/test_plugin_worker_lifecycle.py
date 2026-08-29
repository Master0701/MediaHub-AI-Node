from __future__ import annotations

import json
from pathlib import Path

from app.jobs.registry import job_handler_registry
from app.plugins.loader import PluginLoader
from app.plugins.manager import PluginManager
from app.plugins.registry import PluginRegistry
from app.plugins.state import PluginStateStore
from app.plugins.worker_bridge import plugin_worker_registry

PLUGIN_ID = "test.lifecycle_worker"
WORKER_ID = "test.lifecycle_worker.worker"
JOB_TYPE = "test_lifecycle_job"


def _write_worker_plugin(
    plugin_root: Path,
    *,
    fail_after_register: bool = False,
) -> None:
    plugin_dir = plugin_root / "lifecycle_worker"
    plugin_dir.mkdir(parents=True)

    manifest = {
        "id": PLUGIN_ID,
        "name": "Lifecycle Worker",
        "version": "1.0.0",
        "type": "worker",
        "entrypoint": "plugin:LifecyclePlugin",
        "api_version": "1",
        "enabled_by_default": True,
        "capabilities": ["test_lifecycle"],
        "job_types": [JOB_TYPE],
        "targets": ["raspberry_pi"],
        "platforms": ["linux-aarch64"],
    }

    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    failure = (
        'raise RuntimeError("register failed")'
        if fail_after_register
        else "return None"
    )

    (plugin_dir / "plugin.py").write_text(
        f"""
class LifecyclePlugin:
    def register(self, context):
        def handler(request):
            return {{
                "status": "completed",
                "request": request,
            }}

        context["workers"].register(
            worker_id="{WORKER_ID}",
            name="Lifecycle Worker",
            job_types=["{JOB_TYPE}"],
            handler=handler,
        )

        {failure}
""",
        encoding="utf-8",
    )


def _cleanup() -> None:
    plugin_worker_registry.unregister_plugin(PLUGIN_ID)


def test_disable_unregisters_plugin_worker(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    plugin_root.mkdir()
    _write_worker_plugin(plugin_root)

    manager = PluginManager(
        plugin_root=plugin_root,
        state_path=tmp_path / "state.json",
    )

    try:
        manager.discover()
        manager.load_enabled()

        assert plugin_worker_registry.get(WORKER_ID)
        assert job_handler_registry.get(JOB_TYPE)

        record = manager.disable(PLUGIN_ID)

        assert record.enabled is False
        assert record.loaded is False
        assert record.instance is None
        assert plugin_worker_registry.get(WORKER_ID) is None
        assert job_handler_registry.get(JOB_TYPE) is None
    finally:
        _cleanup()


def test_discover_unloads_old_worker(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    plugin_root.mkdir()
    _write_worker_plugin(plugin_root)

    registry = PluginRegistry()
    loader = PluginLoader(
        plugin_root,
        registry,
        PluginStateStore(tmp_path / "state.json"),
    )

    try:
        loader.discover()
        loader.load_enabled()

        assert plugin_worker_registry.get(WORKER_ID)
        assert job_handler_registry.get(JOB_TYPE)

        loader.discover()

        assert plugin_worker_registry.get(WORKER_ID) is None
        assert job_handler_registry.get(JOB_TYPE) is None
    finally:
        _cleanup()


def test_failed_register_rolls_back_worker(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "plugins"
    plugin_root.mkdir()

    _write_worker_plugin(
        plugin_root,
        fail_after_register=True,
    )

    registry = PluginRegistry()
    loader = PluginLoader(
        plugin_root,
        registry,
        PluginStateStore(tmp_path / "state.json"),
    )

    loader.discover()
    loaded = loader.load_enabled()

    assert loaded == ()
    assert plugin_worker_registry.get(WORKER_ID) is None
    assert job_handler_registry.get(JOB_TYPE) is None

    record = registry.require(PLUGIN_ID)
    assert record.loaded is False
    assert "register failed" in (record.error or "")


def test_worker_cannot_replace_existing_job_handler(
    tmp_path: Path,
) -> None:
    del tmp_path

    from app.jobs.base import BaseJobHandler

    protected_job_type = "test_protected_builtin_job"

    class ProtectedHandler(BaseJobHandler):
        @property
        def job_type(self) -> str:
            return protected_job_type

        def execute(
            self,
            db,
            payload,
            progress_callback=None,
        ):
            del db, progress_callback
            return payload

    protected_handler = ProtectedHandler()

    job_handler_registry.register(
        protected_handler
    )

    def worker_handler(request):
        return request

    try:
        try:
            plugin_worker_registry.register(
                worker_id="test.collision.worker",
                name="Collision Worker",
                job_types=[protected_job_type],
                handler=worker_handler,
                metadata={
                    "plugin_id": "test.collision",
                },
            )
        except ValueError as exc:
            assert "bereits" in str(exc)
        else:
            raise AssertionError(
                "Bestehender JobHandler wurde überschrieben."
            )

        assert (
            job_handler_registry.require(
                protected_job_type
            )
            is protected_handler
        )
    finally:
        plugin_worker_registry.unregister(
            "test.collision.worker"
        )
        job_handler_registry.unregister(
            protected_job_type,
            handler=protected_handler,
        )

def test_failed_reregistration_preserves_existing_worker():
    from app.jobs.base import BaseJobHandler
    from app.jobs.registry import job_handler_registry
    from app.plugins.worker_bridge import PluginWorkerRegistry

    registry = PluginWorkerRegistry()

    def old_handler(request):
        return {"old": True, "request": request}

    registry.register(
        worker_id="worker-a",
        name="Worker A",
        job_types=["job-a"],
        handler=old_handler,
        metadata={"plugin_id": "plugin-a"},
    )

    old_job_handler = job_handler_registry.get("job-a")

    class ProtectedHandler(BaseJobHandler):
        job_type = "job-b"

        def execute(
            self,
            db,
            payload,
            progress_callback,
        ):
            return {"protected": True}

    protected = ProtectedHandler()
    job_handler_registry.register(protected)

    try:
        import pytest

        with pytest.raises(
            ValueError,
            match="bereits",
        ):
            registry.register(
                worker_id="worker-a",
                name="Worker A New",
                job_types=["job-a", "job-b"],
                handler=lambda request: {"new": True},
                metadata={"plugin_id": "plugin-a"},
            )

        worker = registry.get("worker-a")

        assert worker is not None
        assert worker["name"] == "Worker A"
        assert worker["job_types"] == ["job-a"]
        assert job_handler_registry.get("job-a") is old_job_handler
        assert job_handler_registry.get("job-b") is protected

    finally:
        registry.unregister("worker-a")
        job_handler_registry.unregister(
            "job-b",
            handler=protected,
        )


def test_partial_multijob_registration_rolls_back(monkeypatch):
    from app.jobs.registry import job_handler_registry
    from app.plugins.worker_bridge import PluginWorkerRegistry

    registry = PluginWorkerRegistry()
    original_register = job_handler_registry.register

    calls = 0

    def failing_register(handler):
        nonlocal calls
        calls += 1

        if calls == 2:
            raise RuntimeError("simulierter Registrierungsfehler")

        return original_register(handler)

    monkeypatch.setattr(
        job_handler_registry,
        "register",
        failing_register,
    )

    import pytest

    with pytest.raises(
        RuntimeError,
        match="simulierter Registrierungsfehler",
    ):
        registry.register(
            worker_id="worker-multi",
            name="Worker Multi",
            job_types=["multi-a", "multi-b"],
            handler=lambda request: {"ok": True},
            metadata={"plugin_id": "plugin-multi"},
        )

    assert registry.get("worker-multi") is None
    assert job_handler_registry.get("multi-a") is None
    assert job_handler_registry.get("multi-b") is None
