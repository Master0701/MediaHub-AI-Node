from __future__ import annotations

from windows_compute_node.jobs.queue import (
    JobQueue,
)
from windows_compute_node.workers.dispatcher import (
    JobDispatcher,
)
from windows_compute_node.workers.registry import (
    WorkerRegistry,
)


def make_dispatcher():
    jobs = JobQueue()
    workers = WorkerRegistry()

    dispatcher = JobDispatcher(
        jobs=jobs,
        workers=workers,
    )

    return jobs, workers, dispatcher


def test_successful_execution():
    jobs, workers, dispatcher = (
        make_dispatcher()
    )

    def handler(request):
        return {
            "text": "Hallo",
            "input": request[
                "payload"
            ].get("input"),
        }

    workers.register(
        worker_id="speech.test",
        name="Speech Test",
        job_types=[
            "speech_to_text"
        ],
        handler=handler,
    )

    job = jobs.create(
        job_type="speech_to_text",
        payload={
            "input": "audio.wav"
        },
    )

    result = dispatcher.execute(
        job["job_id"]
    )

    assert (
        result["status"]
        == "completed"
    )

    assert (
        result["result"][
            "worker_id"
        ]
        == "speech.test"
    )

    assert (
        result["result"][
            "output"
        ]["text"]
        == "Hallo"
    )


def test_missing_worker_fails():
    jobs, workers, dispatcher = (
        make_dispatcher()
    )

    job = jobs.create(
        job_type="unknown_job"
    )

    result = dispatcher.execute(
        job["job_id"]
    )

    assert result["status"] == "failed"

    assert (
        "Kein installierter"
        in result["error"]
    )


def test_disabled_worker_fails():
    jobs, workers, dispatcher = (
        make_dispatcher()
    )

    workers.register(
        worker_id="disabled",
        name="Disabled",
        job_types=["test"],
        handler=lambda request: {},
        enabled=False,
    )

    job = jobs.create(
        job_type="test"
    )

    result = dispatcher.execute(
        job["job_id"]
    )

    assert result["status"] == "failed"


def test_unhealthy_worker_fails():
    jobs, workers, dispatcher = (
        make_dispatcher()
    )

    workers.register(
        worker_id="unhealthy",
        name="Unhealthy",
        job_types=["test"],
        handler=lambda request: {},
        healthy=False,
    )

    job = jobs.create(
        job_type="test"
    )

    result = dispatcher.execute(
        job["job_id"]
    )

    assert result["status"] == "failed"


def test_worker_exception_fails_job():
    jobs, workers, dispatcher = (
        make_dispatcher()
    )

    def broken_handler(request):
        raise RuntimeError(
            "Worker kaputt"
        )

    workers.register(
        worker_id="broken",
        name="Broken",
        job_types=["test"],
        handler=broken_handler,
    )

    job = jobs.create(
        job_type="test"
    )

    result = dispatcher.execute(
        job["job_id"]
    )

    assert result["status"] == "failed"

    assert (
        "RuntimeError"
        in result["error"]
    )


def test_cancelled_job_not_executed():
    jobs, workers, dispatcher = (
        make_dispatcher()
    )

    called = {
        "value": False,
    }

    def handler(request):
        called["value"] = True
        return {}

    workers.register(
        worker_id="worker",
        name="Worker",
        job_types=["test"],
        handler=handler,
    )

    job = jobs.create(
        job_type="test"
    )

    jobs.cancel(
        job["job_id"]
    )

    result = dispatcher.execute(
        job["job_id"]
    )

    assert (
        result["status"]
        == "cancelled"
    )

    assert called["value"] is False


def test_completed_job_not_reexecuted():
    jobs, workers, dispatcher = (
        make_dispatcher()
    )

    calls = {
        "count": 0,
    }

    def handler(request):
        calls["count"] += 1
        return {
            "ok": True,
        }

    workers.register(
        worker_id="worker",
        name="Worker",
        job_types=["test"],
        handler=handler,
    )

    job = jobs.create(
        job_type="test"
    )

    first = dispatcher.execute(
        job["job_id"]
    )

    second = dispatcher.execute(
        job["job_id"]
    )

    assert first["status"] == "completed"
    assert second["status"] == "completed"

    assert calls["count"] == 1
