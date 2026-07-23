from typing import Any

from sqlalchemy.orm import Session

from app.analyzer.manager import (
    analyzer_manager,
)
from app.jobs.base import BaseJobHandler


class MediaAnalyzeHandler(BaseJobHandler):
    job_type = "media.analyze"

    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        file_path = payload.get(
            "file_path"
        )

        if not file_path:
            raise ValueError(
                "Im Job fehlt 'file_path'."
            )

        options = payload.get(
            "options",
            {},
        )

        if not isinstance(options, dict):
            options = {}

        def analyzer_progress(
            progress: int,
            analyzer_name: str,
        ) -> None:
            normalized_progress = max(
                5,
                min(progress, 95),
            )

            progress_callback(
                normalized_progress
            )

        result = analyzer_manager.analyze(
            file_path=str(file_path),
            options=options,
            progress_callback=(
                analyzer_progress
            ),
        )

        progress_callback(95)

        return result
