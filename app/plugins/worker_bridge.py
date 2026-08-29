"""Adapter zwischen gemeinsamen .mhaiplugin-Workern und Pi-Jobs."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from app.jobs.base import BaseJobHandler
from app.jobs.registry import job_handler_registry

WorkerHandler = Callable[..., dict[str, Any]]


class PluginWorkerJobHandler(BaseJobHandler):
    """Adaptiert einen gemeinsamen Plugin-Worker an BaseJobHandler."""

    def __init__(
        self,
        *,
        job_type: str,
        handler: WorkerHandler,
    ) -> None:
        self.job_type = job_type
        self._handler = handler

    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        del db

        request = dict(payload)

        if (
            "payload" not in request
            and "execution" not in request
        ):
            request = {
                "payload": dict(payload),
            }

        result = self._handler(request)

        if not isinstance(result, dict):
            return {"result": result}

        return result


class PluginWorkerRegistry:
    """Windows-kompatible Worker-Registry-Fassade für den Pi-Node."""

    def __init__(self) -> None:
        self._workers: dict[str, dict[str, Any]] = {}

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
        clean_id = str(worker_id or "").strip()

        if not clean_id:
            raise ValueError("worker_id darf nicht leer sein.")

        clean_types = sorted(
            {
                str(item).strip()
                for item in job_types
                if str(item).strip()
            }
        )

        if not clean_types:
            raise ValueError(
                "Worker benötigt mindestens einen job_type."
            )

        worker_metadata = deepcopy(metadata or {})
        plugin_id = str(
            worker_metadata.get("plugin_id", "")
        ).strip().lower()

        existing_worker = self._workers.get(clean_id)
        if existing_worker is not None:
            existing_plugin_id = str(
                existing_worker.get("plugin_id", "")
            ).strip().lower()

            if (
                existing_plugin_id
                and plugin_id
                and existing_plugin_id != plugin_id
            ):
                raise ValueError(
                    f"Worker-ID '{clean_id}' gehört bereits "
                    f"Plugin '{existing_plugin_id}'."
                )

            self.unregister(clean_id)

        for job_type in clean_types:
            current = job_handler_registry.get(job_type)

            if current is None:
                continue

            owned_by_same_worker = (
                existing_worker is not None
                and current
                in existing_worker.get(
                    "job_handlers",
                    {},
                ).values()
            )

            if not owned_by_same_worker:
                raise ValueError(
                    f"Job-Typ '{job_type}' ist bereits "
                    "durch einen anderen Handler registriert."
                )

        worker = {
            "worker_id": clean_id,
            "name": str(name or clean_id).strip(),
            "job_types": clean_types,
            "enabled": bool(enabled),
            "healthy": bool(healthy),
            "handler": handler,
            "metadata": worker_metadata,
            "plugin_id": plugin_id,
            "job_handlers": {},
        }

        self._workers[clean_id] = worker

        if (
            handler is not None
            and worker["enabled"]
            and worker["healthy"]
        ):
            for job_type in clean_types:
                adapter = PluginWorkerJobHandler(
                    job_type=job_type,
                    handler=handler,
                )
                job_handler_registry.register(adapter)
                worker["job_handlers"][job_type] = adapter

    def worker_ids_for_plugin(
        self,
        plugin_id: str,
    ) -> tuple[str, ...]:
        clean_plugin_id = str(plugin_id).strip().lower()

        return tuple(
            worker_id
            for worker_id, worker in self._workers.items()
            if worker.get("plugin_id") == clean_plugin_id
        )

    def unregister_plugin(
        self,
        plugin_id: str,
    ) -> tuple[str, ...]:
        worker_ids = self.worker_ids_for_plugin(plugin_id)

        for worker_id in worker_ids:
            self.unregister(worker_id)

        return worker_ids

    def unregister(self, worker_id: str) -> bool:
        worker = self._workers.pop(
            str(worker_id),
            None,
        )

        if worker is None:
            return False

        for job_type, adapter in worker.get(
            "job_handlers",
            {},
        ).items():
            job_handler_registry.unregister(
                job_type,
                handler=adapter,
            )

        return True

    def get(self, worker_id: str) -> dict[str, Any] | None:
        worker = self._workers.get(str(worker_id))
        if worker is None:
            return None
        return self._public_copy(worker)

    def list_workers(self) -> list[dict[str, Any]]:
        workers = [
            self._public_copy(worker)
            for worker in self._workers.values()
        ]
        workers.sort(key=lambda item: item["worker_id"])
        return workers

    def find_for_job(
        self,
        job_type: str,
    ) -> dict[str, Any] | None:
        clean_type = str(job_type or "").strip()

        for worker in self._workers.values():
            if not worker["enabled"] or not worker["healthy"]:
                continue
            if clean_type not in worker["job_types"]:
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
            "worker_id": worker["worker_id"],
            "name": worker["name"],
            "job_types": list(worker["job_types"]),
            "enabled": worker["enabled"],
            "healthy": worker["healthy"],
            "executable": worker["handler"] is not None,
            "metadata": deepcopy(worker["metadata"]),
        }


plugin_worker_registry = PluginWorkerRegistry()
