from __future__ import annotations

from windows_compute_node.jobs.queue import (
    JobQueue,
)


def test_create_job():
    queue = JobQueue()

    job = queue.create(
        job_type="speech_to_text",
        payload={
            "input": "test.wav",
        },
    )

    assert job["status"] == "queued"
    assert job["job_type"] == (
        "speech_to_text"
    )
    assert job["job_id"]


def test_get_job():
    queue = JobQueue()

    created = queue.create(
        job_type="test",
    )

    loaded = queue.get(
        created["job_id"]
    )

    assert loaded is not None
    assert (
        loaded["job_id"]
        == created["job_id"]
    )


def test_list_jobs():
    queue = JobQueue()

    queue.create(job_type="one")
    queue.create(job_type="two")

    assert len(
        queue.list_jobs()
    ) == 2


def test_cancel_job():
    queue = JobQueue()

    created = queue.create(
        job_type="test",
    )

    cancelled = queue.cancel(
        created["job_id"]
    )

    assert cancelled is not None
    assert (
        cancelled["status"]
        == "cancelled"
    )


def test_set_running():
    queue = JobQueue()

    created = queue.create(
        job_type="test",
    )

    running = queue.set_status(
        created["job_id"],
        "running",
    )

    assert (
        running["status"]
        == "running"
    )


def test_complete_with_result():
    queue = JobQueue()

    created = queue.create(
        job_type="test",
    )

    completed = queue.set_status(
        created["job_id"],
        "completed",
        result={
            "text": "Hallo",
        },
    )

    assert (
        completed["status"]
        == "completed"
    )

    assert completed["result"] == {
        "text": "Hallo",
    }


def test_failed_job():
    queue = JobQueue()

    created = queue.create(
        job_type="test",
    )

    failed = queue.set_status(
        created["job_id"],
        "failed",
        error="Testfehler",
    )

    assert failed["status"] == "failed"
    assert failed["error"] == "Testfehler"
