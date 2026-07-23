from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.analyzer.manager import analyzer_manager
from app.jobs.base import BaseJobHandler
from app.references.service import ReferenceService


class ReferenceCreateHandler(BaseJobHandler):
    job_type = "reference.create"

    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        name = self._required_text(
            payload,
            "name",
        )

        file_path_text = self._required_text(
            payload,
            "file_path",
        )

        file_path = Path(file_path_text)

        if not file_path.exists():
            raise ValueError(
                "Die Referenzdatei wurde nicht "
                f"gefunden: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                "Der Referenzpfad ist keine Datei: "
                f"{file_path}"
            )

        description = self._optional_text(
            payload.get("description")
        )

        quality_profile = self._optional_text(
            payload.get("quality_profile")
        ) or "balanced"

        comparison_settings = payload.get(
            "comparison_settings",
            {},
        )

        if not isinstance(
            comparison_settings,
            dict,
        ):
            raise ValueError(
                "'comparison_settings' muss "
                "ein JSON-Objekt sein."
            )

        enabled = payload.get(
            "enabled",
            True,
        )

        if not isinstance(enabled, bool):
            raise ValueError(
                "'enabled' muss true oder "
                "false sein."
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

        media = analysis.get(
            "media",
            {},
        )

        if not isinstance(media, dict):
            media = {}

        quality = media.get(
            "quality",
            {},
        )

        if not isinstance(quality, dict):
            quality = {}

        quality_score = self._extract_score(
            quality
        )

        progress_callback(92)

        service = ReferenceService(db)

        reference = service.create(
            name=name,
            description=description,
            source_file_path=str(
                file_path.resolve()
            ),
            source_file_name=file_path.name,
            quality_score=quality_score,
            quality_profile=quality_profile,
            analysis=analysis,
            quality=quality,
            comparison_settings=(
                comparison_settings
            ),
            enabled=enabled,
        )

        progress_callback(98)

        return {
            "reference": reference,
            "analysis_summary": analysis.get(
                "summary",
                {},
            ),
            "quality": quality,
        }

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
    def _extract_score(
        quality: dict[str, Any],
    ) -> int | None:
        score = quality.get("score")

        if score is None:
            score = quality.get(
                "quality_score"
            )

        if score is None:
            return None

        try:
            numeric_score = int(
                round(float(score))
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

        return max(
            0,
            min(numeric_score, 100),
        )

    @staticmethod
    def _validate_analysis(
        analysis: dict[str, Any],
    ) -> None:
        summary = analysis.get(
            "summary",
            {},
        )

        if not isinstance(summary, dict):
            raise ValueError(
                "Die Analyzer-Pipeline hat "
                "keine gültige Zusammenfassung "
                "geliefert."
            )

        successful = summary.get(
            "successful",
            [],
        )

        if not isinstance(
            successful,
            list,
        ):
            successful = []

        if not successful:
            raise ValueError(
                "Kein Analyzer konnte die "
                "Referenzdatei erfolgreich "
                "untersuchen."
            )

        if "quality" not in successful:
            raise ValueError(
                "Die Qualitätsanalyse der "
                "Referenzdatei war nicht "
                "erfolgreich."
            )
