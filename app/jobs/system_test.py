import time
from typing import Any

from sqlalchemy.orm import Session

from app.jobs.base import BaseJobHandler


class SystemTestHandler(BaseJobHandler):
    job_type = "system.test"

    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        progress_callback(10)
        time.sleep(0.3)

        progress_callback(50)
        time.sleep(0.3)

        progress_callback(90)
        time.sleep(0.3)

        return {
            "message": (
                "MediaHub-Testauftrag erfolgreich "
                "verarbeitet."
            ),
            "payload": payload,
        }
