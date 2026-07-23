from typing import Any

from sqlalchemy.orm import Session

from app.jobs.base import BaseJobHandler
from app.knowledge.service import (
    item_to_dict,
    search_items,
)


class KnowledgeSearchHandler(BaseJobHandler):
    job_type = "knowledge.search"

    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        query = payload.get("query")
        media_type = payload.get("media_type")

        limit_value = payload.get("limit", 100)

        try:
            limit = int(limit_value)
        except (TypeError, ValueError):
            limit = 100

        limit = max(1, min(limit, 500))

        progress_callback(25)

        items = search_items(
            db=db,
            query=str(query) if query else None,
            media_type=(
                str(media_type)
                if media_type
                else None
            ),
            limit=limit,
        )

        progress_callback(80)

        return {
            "count": len(items),
            "items": [
                item_to_dict(item)
                for item in items
            ],
        }
