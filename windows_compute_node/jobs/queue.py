"""Thread-safe in-memory job queue."""

from __future__ import annotations

import threading
import time
import uuid
from copy import deepcopy
from typing import Any

VALID_STATES = {
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
}


class JobQueue:
    def __init__(self) -> None:
        self._jobs: dict[
            str,
            dict[str, Any],
        ] = {}

        self._lock = threading.RLock()

    def create(
        self,
        *,
        job_type: str,
        payload: dict[str, Any] | None = None,
        execution: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_type = str(
            job_type or ""
        ).strip()

        if not clean_type:
            raise ValueError(
                "job_type darf nicht leer sein."
            )

        now = time.time()
        job_id = str(uuid.uuid4())

        job = {
            "job_id": job_id,
            "job_type": clean_type,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "payload": deepcopy(
                payload or {}
            ),
            "execution": deepcopy(
                execution or {}
            ),
            "result": None,
            "error": None,
        }

        with self._lock:
            self._jobs[job_id] = job

        return deepcopy(job)

    def get(
        self,
        job_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(
                str(job_id)
            )

            if job is None:
                return None

            return deepcopy(job)

    def list_jobs(
        self,
    ) -> list[dict[str, Any]]:
        with self._lock:
            jobs = list(
                self._jobs.values()
            )

            jobs.sort(
                key=lambda item: item[
                    "created_at"
                ]
            )

            return deepcopy(jobs)

    def cancel(
        self,
        job_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(
                str(job_id)
            )

            if job is None:
                return None

            if job["status"] in {
                "completed",
                "failed",
                "cancelled",
            }:
                return deepcopy(job)

            job["status"] = "cancelled"
            job["updated_at"] = time.time()

            return deepcopy(job)

    def set_status(
        self,
        job_id: str,
        status: str,
        *,
        result: Any = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        clean_status = str(
            status or ""
        ).strip()

        if clean_status not in VALID_STATES:
            raise ValueError(
                f"Ungueltiger Job-Status: "
                f"{clean_status}"
            )

        with self._lock:
            job = self._jobs.get(
                str(job_id)
            )

            if job is None:
                raise KeyError(job_id)

            job["status"] = clean_status
            job["updated_at"] = time.time()

            if result is not None:
                job["result"] = deepcopy(
                    result
                )

            if error is not None:
                job["error"] = str(error)

            return deepcopy(job)
