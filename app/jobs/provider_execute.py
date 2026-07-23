from typing import Any

from sqlalchemy.orm import Session

from app.jobs.base import BaseJobHandler
from app.providers.registry import provider_registry
from app.services.provider_service import get_provider


class ProviderExecuteHandler(BaseJobHandler):
    job_type = "provider.execute"

    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        provider_name = str(
            payload.get("provider", "local")
        ).strip()

        task = str(
            payload.get("task", "job-task")
        ).strip()

        task_payload = payload.get(
            "payload",
            {},
        )

        if not isinstance(task_payload, dict):
            task_payload = {
                "value": task_payload,
            }

        progress_callback(20)

        provider_record = get_provider(
            db,
            provider_name,
        )

        if provider_record is None:
            raise ValueError(
                f"Provider nicht gefunden: "
                f"{provider_name}"
            )

        if not provider_record.enabled:
            raise ValueError(
                f"Provider ist deaktiviert: "
                f"{provider_name}"
            )

        progress_callback(50)

        provider = provider_registry.require(
            provider_name
        )

        result = provider.execute(
            task=task,
            payload=task_payload,
        )

        progress_callback(90)

        return result
