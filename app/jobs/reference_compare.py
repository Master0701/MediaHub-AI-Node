from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.analyzer.manager import analyzer_manager
from app.jobs.base import BaseJobHandler
from app.references.compare import (
    ReferenceCompareService,
)
from app.references.service import ReferenceService


class ReferenceCompareHandler(BaseJobHandler):
    job_type = "reference.compare"

    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        reference_id = self._reference_id(
            payload.get("reference_id")
        )

        file_path_text = self._required_text(
            payload,
            "file_path",
        )

        file_path = Path(file_path_text)

        if not file_path.exists():
            raise ValueError(
                "Die Vergleichsdatei wurde nicht "
                f"gefunden: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                "Der Vergleichspfad ist keine "
                f"Datei: {file_path}"
            )

        reference_service = ReferenceService(
            db
        )

        reference = reference_service.get(
            reference_id
        )

        if not reference.get("enabled", False):
            raise ValueError(
                "Die ausgewählte Referenz ist "
                "deaktiviert."
            )

        quality_profile = (
            self._optional_text(
                payload.get(
                    "quality_profile"
                )
            )
            or self._optional_text(
                reference.get(
                    "quality_profile"
                )
            )
            or "balanced"
        )

        supplied_options = payload.get(
            "options",
            {},
        )

        if not isinstance(
            supplied_options,
            dict,
        ):
            supplied_options = {}

        options = dict(supplied_options)
        options["quality_profile"] = (
            quality_profile
        )

        progress_callback(5)

        def analyzer_progress(
            progress: int,
            analyzer_name: str,
        ) -> None:
            del analyzer_name

            normalized = 5 + int(
                max(
                    0,
                    min(progress, 90),
                )
                * 0.85
            )

            progress_callback(
                min(normalized, 85)
            )

        analysis = analyzer_manager.analyze(
            file_path=file_path,
            options=options,
            progress_callback=(
                analyzer_progress
            ),
        )

        progress_callback(88)

        self._validate_analysis(
            analysis
        )

        allowed_difference = payload.get(
            "allowed_score_difference"
        )

        compare_service = (
            ReferenceCompareService()
        )

        comparison = compare_service.compare(
            reference=reference,
            candidate_analysis=analysis,
            allowed_score_difference=(
                allowed_difference
            ),
        )

        progress_callback(97)

        return {
            "comparison": comparison,
            "reference": {
                "id": reference.get("id"),
                "reference_uuid": (
                    reference.get(
                        "reference_uuid"
                    )
                ),
                "reference_version": (
                    reference.get(
                        "reference_version"
                    )
                ),
                "name": reference.get("name"),
            },
            "candidate": {
                "file_path": str(
                    file_path.resolve()
                ),
                "quality_profile": (
                    quality_profile
                ),
            },
            "analysis_summary": analysis.get(
                "summary",
                {},
            ),
            "candidate_quality": (
                analysis.get(
                    "media",
                    {},
                ).get(
                    "quality",
                    {},
                )
            ),
        }

    @staticmethod
    def _reference_id(
        value: Any,
    ) -> int:
        if value is None:
            raise ValueError(
                "Im Job fehlt "
                "'reference_id'."
            )

        try:
            reference_id = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "'reference_id' muss eine "
                "Ganzzahl sein."
            ) from exc

        if reference_id < 1:
            raise ValueError(
                "'reference_id' muss größer "
                "als 0 sein."
            )

        return reference_id

    @staticmethod
    def _required_text(
        payload: dict[str, Any],
        field_name: str,
    ) -> str:
        value = payload.get(field_name)

        if value is None:
            raise ValueError(
                f"Im Job fehlt '{field_name}'."
            )

        normalized = str(value).strip()

        if not normalized:
            raise ValueError(
                f"'{field_name}' darf nicht "
                "leer sein."
            )

        return normalized

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()

        return normalized or None

    @staticmethod
    def _validate_analysis(
        analysis: dict[str, Any],
    ) -> None:
        if not isinstance(analysis, dict):
            raise ValueError(
                "Die Analyzer-Pipeline hat "
                "kein gültiges Ergebnis geliefert."
            )

        summary = analysis.get(
            "summary",
            {},
        )

        if not isinstance(summary, dict):
            raise ValueError(
                "Die Analyzer-Pipeline hat keine "
                "gültige Zusammenfassung geliefert."
            )

        successful = summary.get(
            "successful",
            [],
        )

        if not isinstance(successful, list):
            successful = []

        if "quality" not in successful:
            raise ValueError(
                "Die Qualitätsanalyse der "
                "Vergleichsdatei war nicht "
                "erfolgreich."
            )
