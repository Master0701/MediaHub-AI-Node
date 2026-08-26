"""Worker registry for installed Compute-Node plugins."""

from __future__ import annotations

import threading
from collections.abc import Callable
from copy import deepcopy
from typing import Any

WorkerHandler = Callable[
    [dict[str, Any]],
    Any,
]


class WorkerRegistry:
    def __init__(self) -> None:
        self._workers: dict[
            str,
            dict[str, Any],
        ] = {}

        self._lock = threading.RLock()

    def register(
        self,
        *,
        worker_id: str,
        name: str,
        job_types: list[str],
        handler: WorkerHandler | None = None,
        enabled: bool = True,
        healthy: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        clean_id = str(
            worker_id or ""
        ).strip()

        if not clean_id:
            raise ValueError(
                "worker_id darf nicht leer sein."
            )

        clean_types = sorted(
            {
                str(item).strip()
                for item in job_types
                if str(item).strip()
            }
        )

        if not clean_types:
            raise ValueError(
                "Worker benoetigt mindestens "
                "einen job_type."
            )

        worker = {
            "worker_id": clean_id,
            "name": str(
                name or clean_id
            ).strip(),
            "job_types": clean_types,
            "enabled": bool(enabled),
            "healthy": bool(healthy),
            "handler": handler,
            "metadata": deepcopy(
                metadata or {}
            ),
        }

        with self._lock:
            self._workers[
                clean_id
            ] = worker

    def unregister(
        self,
        worker_id: str,
    ) -> bool:
        with self._lock:
            return (
                self._workers.pop(
                    str(worker_id),
                    None,
                )
                is not None
            )

    def get(
        self,
        worker_id: str,
    ) -> dict[str, Any] | None:
        with self._lock:
            worker = self._workers.get(
                str(worker_id)
            )

            if worker is None:
                return None

            return self._public_copy(
                worker
            )

    def list_workers(
        self,
    ) -> list[dict[str, Any]]:
        with self._lock:
            workers = [
                self._public_copy(item)
                for item in self._workers.values()
            ]

        workers.sort(
            key=lambda item: item[
                "worker_id"
            ]
        )

        return workers

    def find_for_job(
        self,
        job_type: str,
    ) -> dict[str, Any] | None:
        clean_type = str(
            job_type or ""
        ).strip()

        with self._lock:
            for worker in (
                self._workers.values()
            ):
                if not worker["enabled"]:
                    continue

                if not worker["healthy"]:
                    continue

                if (
                    clean_type
                    not in worker[
                        "job_types"
                    ]
                ):
                    continue

                if worker["handler"] is None:
                    continue

                return dict(worker)

        return None

    @staticmethod
    def _public_copy(
        worker: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "worker_id": worker[
                "worker_id"
            ],
            "name": worker["name"],
            "job_types": list(
                worker["job_types"]
            ),
            "enabled": worker[
                "enabled"
            ],
            "healthy": worker[
                "healthy"
            ],
            "executable": (
                worker["handler"]
                is not None
            ),
            "metadata": deepcopy(
                worker["metadata"]
            ),
        }
