import shutil
import time
from pathlib import Path
from typing import Any, Callable

from app.analyzer.base import (
    AnalyzerContext,
    AnalyzerResult,
)
from app.analyzer.filename import (
    FilenameAnalyzer,
)
from app.analyzer.ffprobe import (
    FFProbeAnalyzer,
)
from app.analyzer.mediainfo import (
    MediaInfoAnalyzer,
)
from app.analyzer.filesystem import (
    FilesystemAnalyzer,
)
from app.analyzer.quality_fingerprint import (
    QualityFingerprintAnalyzer,
)
from app.analyzer.quality import (
    QualityAnalyzer,
)
from app.analyzer.registry import (
    analyzer_registry,
)


ProgressCallback = Callable[
    [int, str],
    None,
]


class AnalyzerManager:
    def __init__(self) -> None:
        self.registry = analyzer_registry

    def initialize_defaults(self) -> None:
        self.registry.register(
            FilenameAnalyzer()
        )
        self.registry.register(
            FilesystemAnalyzer()
        )
        self.registry.register(
            FFProbeAnalyzer()
        )
        self.registry.register(
            MediaInfoAnalyzer()
        )
        self.registry.register(
            QualityFingerprintAnalyzer()
        )
        self.registry.register(
            QualityAnalyzer()
        )

    def list_analyzers(
        self,
    ) -> list[dict[str, Any]]:
        result = []

        for analyzer in (
            self.registry.list_analyzers()
        ):
            missing_tools = (
                self._missing_tools(
                    analyzer.required_tools
                )
            )

            result.append(
                {
                    "name": analyzer.name,
                    "priority": (
                        analyzer.priority
                    ),
                    "enabled": (
                        analyzer.enabled
                    ),
                    "capabilities": list(
                        analyzer.capabilities
                    ),
                    "required_tools": list(
                        analyzer.required_tools
                    ),
                    "missing_tools": (
                        missing_tools
                    ),
                    "available": (
                        analyzer.enabled
                        and not missing_tools
                    ),
                }
            )

        return result

    def analyze(
        self,
        file_path: str | Path,
        options: dict[str, Any] | None = None,
        progress_callback: (
            ProgressCallback | None
        ) = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()

        context = AnalyzerContext(
            file_path=Path(file_path),
            options=options or {},
        )

        analyzers = (
            self.registry.list_analyzers()
        )

        results: list[AnalyzerResult] = []
        merged_data: dict[str, Any] = {}

        total = max(len(analyzers), 1)

        for index, analyzer in enumerate(
            analyzers,
            start=1,
        ):
            progress_start = int(
                ((index - 1) / total) * 90
            )

            if progress_callback:
                progress_callback(
                    progress_start,
                    analyzer.name,
                )

            if not analyzer.enabled:
                results.append(
                    AnalyzerResult(
                        analyzer=analyzer.name,
                        success=False,
                        skipped=True,
                        skip_reason=(
                            "Analyzer ist deaktiviert."
                        ),
                    )
                )
                continue

            missing_tools = (
                self._missing_tools(
                    analyzer.required_tools
                )
            )

            if missing_tools:
                results.append(
                    AnalyzerResult(
                        analyzer=analyzer.name,
                        success=False,
                        skipped=True,
                        skip_reason=(
                            "Benötigte Werkzeuge "
                            "fehlen: "
                            + ", ".join(
                                missing_tools
                            )
                        ),
                    )
                )
                continue

            try:
                if not analyzer.can_analyze(
                    context
                ):
                    results.append(
                        AnalyzerResult(
                            analyzer=(
                                analyzer.name
                            ),
                            success=False,
                            skipped=True,
                            skip_reason=(
                                "Analyzer ist für "
                                "diese Datei nicht "
                                "geeignet."
                            ),
                        )
                    )
                    continue

                result = analyzer.analyze(
                    context
                )

                results.append(result)

                if result.success:
                    merged_data.update(
                        result.data
                    )

                    context.shared_data.update(
                        result.data
                    )

            except Exception as exc:
                results.append(
                    AnalyzerResult(
                        analyzer=analyzer.name,
                        success=False,
                        errors=[str(exc)],
                    )
                )

        duration_ms = round(
            (
                time.perf_counter()
                - started
            )
            * 1000,
            2,
        )

        successful = [
            result.analyzer
            for result in results
            if result.success
            and not result.skipped
        ]

        skipped = [
            result.analyzer
            for result in results
            if result.skipped
        ]

        failed = [
            result.analyzer
            for result in results
            if not result.success
            and not result.skipped
        ]

        return {
            "file_path": str(
                context.file_path
            ),
            "analysis_stage": (
                "analyzer_pipeline"
            ),
            "pipeline_version": "5",
            "summary": {
                "successful": successful,
                "skipped": skipped,
                "failed": failed,
                "duration_ms": duration_ms,
            },
            "media": merged_data,
            "analyzers": [
                result.to_dict()
                for result in results
            ],
        }

    def _missing_tools(
        self,
        required_tools: list[str],
    ) -> list[str]:
        return [
            tool
            for tool in required_tools
            if shutil.which(tool) is None
        ]


analyzer_manager = AnalyzerManager()
analyzer_manager.initialize_defaults()
