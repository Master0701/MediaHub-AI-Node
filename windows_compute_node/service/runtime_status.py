"""Runtime status tracking for the Windows Compute Node."""

from __future__ import annotations

import threading
import time
from typing import Any


class ComputeNodeRuntimeStatus:
    """Track MediaHub contact and current Compute Node work."""

    CONNECTION_TIMEOUT_SECONDS = 30.0

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._last_authenticated_request: float | None = None

    def mark_authenticated_request(self) -> None:
        """Remember successful authenticated MediaHub/API activity."""
        with self._lock:
            self._last_authenticated_request = time.monotonic()

    def is_connected(self) -> bool:
        """Return whether authenticated activity was seen recently."""
        with self._lock:
            last_request = self._last_authenticated_request

        if last_request is None:
            return False

        return (
            time.monotonic() - last_request
            <= self.CONNECTION_TIMEOUT_SECONDS
        )

    def snapshot(
        self,
        jobs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return the current user-facing runtime state."""
        running_jobs = [
            job
            for job in jobs
            if str(job.get("status", "")).lower() == "running"
        ]

        queued_jobs = [
            job
            for job in jobs
            if str(job.get("status", "")).lower() == "queued"
        ]

        connected = self.is_connected()

        if running_jobs:
            state = "working"
            label = "Arbeitet"
        elif connected:
            state = "ready"
            label = "Bereit"
        else:
            state = "running"
            label = "Läuft"

        active_job_type = None

        if running_jobs:
            active_job_type = str(
                running_jobs[0].get("job_type") or ""
            ).strip() or None

        return {
            "state": state,
            "label": label,
            "running": True,
            "connected": connected,
            "working": bool(running_jobs),
            "active_job_type": active_job_type,
            "running_jobs": len(running_jobs),
            "queued_jobs": len(queued_jobs),
        }
