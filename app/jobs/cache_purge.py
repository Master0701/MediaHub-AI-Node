from typing import Any

from sqlalchemy.orm import Session

from app.cache.service import purge_expired_entries
from app.jobs.base import BaseJobHandler


class CachePurgeHandler(BaseJobHandler):
    job_type = "cache.purge_expired"

    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        progress_callback(25)

        deleted_count = purge_expired_entries(db)

        progress_callback(90)

        return {
            "deleted": deleted_count,
            "message": (
                "Abgelaufene Cache-Einträge "
                "wurden entfernt."
            ),
        }
