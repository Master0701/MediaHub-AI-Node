"""Job dispatcher for Compute-Node workers."""

from __future__ import annotations

from typing import Any

from windows_compute_node.jobs.input_cleanup import (
    JobInputCleanup,
)
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
        runtime_dir,
    ) -> None:
        self.jobs = jobs
        self.workers = workers
        self.input_cleanup = JobInputCleanup(
            runtime_dir
        )

    def _cleanup_input(
        self,
        job_id: str,
    ) -> None:
        try:
            self.input_cleanup.cleanup_job(
                job_id
            )
        except OSError:
            # Cleanup-Probleme duerfen das eigentliche
            # Worker-Ergebnis nicht zerstoeren.
            pass

    def execute(
        self,
        job_id: str,
    ) -> dict[str, Any]:
        job = self.jobs.get(job_id)

        if job is None:
            raise KeyError(job_id)

        if job["status"] == "cancelled":
            self._cleanup_input(job_id)
            return job

        if job["status"] != "queued":
            return job

        worker = self.workers.find_for_job(
            job["job_type"]
        )

        if worker is None:
            failed_job = self.jobs.set_status(
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

            self._cleanup_input(job_id)
            return failed_job

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
            failed_job = self.jobs.set_status(
                job_id,
                "failed",
                error=(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

            self._cleanup_input(job_id)
            return failed_job

        completed_job = self.jobs.set_status(
            job_id,
            "completed",
            result={
                "worker_id": worker[
                    "worker_id"
                ],
                "output": result,
            },
        )

        self._cleanup_input(job_id)
        return completed_job
