from __future__ import annotations

from windows_compute_node.workers.registry import (
    WorkerRegistry,
)


def dummy_handler(payload):
    return {
        "ok": True,
        "payload": payload,
    }


def test_empty_registry():
    registry = WorkerRegistry()

    assert registry.list_workers() == []


def test_register_worker():
    registry = WorkerRegistry()

    registry.register(
        worker_id="test.worker",
        name="Test Worker",
        job_types=["test"],
        handler=dummy_handler,
    )

    workers = registry.list_workers()

    assert len(workers) == 1
    assert workers[0][
        "worker_id"
    ] == "test.worker"

    assert workers[0][
        "executable"
    ] is True


def test_find_worker_for_job():
    registry = WorkerRegistry()

    registry.register(
        worker_id="speech.test",
        name="Speech",
        job_types=[
            "speech_to_text"
        ],
        handler=dummy_handler,
    )

    worker = registry.find_for_job(
        "speech_to_text"
    )

    assert worker is not None
    assert worker[
        "worker_id"
    ] == "speech.test"


def test_disabled_worker_not_selected():
    registry = WorkerRegistry()

    registry.register(
        worker_id="disabled",
        name="Disabled",
        job_types=["test"],
        handler=dummy_handler,
        enabled=False,
    )

    assert (
        registry.find_for_job(
            "test"
        )
        is None
    )


def test_unhealthy_worker_not_selected():
    registry = WorkerRegistry()

    registry.register(
        worker_id="broken",
        name="Broken",
        job_types=["test"],
        handler=dummy_handler,
        healthy=False,
    )

    assert (
        registry.find_for_job(
            "test"
        )
        is None
    )


def test_worker_without_handler_not_selected():
    registry = WorkerRegistry()

    registry.register(
        worker_id="no.handler",
        name="No Handler",
        job_types=["test"],
        handler=None,
    )

    assert (
        registry.find_for_job(
            "test"
        )
        is None
    )


def test_wrong_job_type_not_selected():
    registry = WorkerRegistry()

    registry.register(
        worker_id="speech",
        name="Speech",
        job_types=[
            "speech_to_text"
        ],
        handler=dummy_handler,
    )

    assert (
        registry.find_for_job(
            "video_analysis"
        )
        is None
    )


def test_unregister_worker():
    registry = WorkerRegistry()

    registry.register(
        worker_id="test",
        name="Test",
        job_types=["test"],
        handler=dummy_handler,
    )

    assert registry.unregister(
        "test"
    ) is True

    assert registry.list_workers() == []
