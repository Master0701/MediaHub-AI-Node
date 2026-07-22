from datetime import datetime, timezone
from typing import Any

from app.providers.base import BaseProvider


class LocalProvider(BaseProvider):
    provider_name = "local"
    provider_type = "local"

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "type": self.provider_type,
            "status": "healthy",
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    def execute(
        self,
        task: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "task": task,
            "status": "completed",
            "payload": payload,
            "message": (
                "Aufgabe wurde vom lokalen "
                "MediaHub-Provider verarbeitet."
            ),
        }
