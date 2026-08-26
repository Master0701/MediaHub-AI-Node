"""Job dispatcher for Compute-Node workers."""

from __future__ import annotations

from typing import Any

from windows_compute_node.jobs.queue import (
    JobQueue,
)
from windows_compute_node.workers.registry import (
    WorkerRegistry,
)


class JobDispatcher:
    def __init__(
        self,
        *,
        jobs: JobQueue,
        workers: WorkerRegistry,
    ) -> None:
        self.jobs = jobs
        self.workers = workers

    def execute(
        self,
        job_id: str,
    ) -> dict[str, Any]:
        job = self.jobs.get(job_id)

        if job is None:
            raise KeyError(job_id)

        if job["status"] == "cancelled":
            return job

        if job["status"] != "queued":
            return job

        worker = self.workers.find_for_job(
            job["job_type"]
        )

        if worker is None:
            return self.jobs.set_status(
                job_id,
                "failed",
                error=(
                    "Kein installierter, "
                    "aktivierter und gesunder "
                    "Worker fuer Jobtyp "
                    f"{job['job_type']} "
                    "verfuegbar."
                ),
            )

        handler = worker["handler"]

        self.jobs.set_status(
            job_id,
            "running",
        )

        try:
            result = handler(
                {
                    "job_id": job_id,
                    "job_type": job[
                        "job_type"
                    ],
                    "payload": job[
                        "payload"
                    ],
                    "execution": job[
                        "execution"
                    ],
                }
            )

        except Exception as exc:
            return self.jobs.set_status(
                job_id,
                "failed",
                error=(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

        return self.jobs.set_status(
            job_id,
            "completed",
            result={
                "worker_id": worker[
                    "worker_id"
                ],
                "output": result,
            },
        )
