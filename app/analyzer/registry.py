from app.analyzer.base import BaseAnalyzer


class AnalyzerRegistry:
    def __init__(self) -> None:
        self._analyzers: dict[
            str,
            BaseAnalyzer,
        ] = {}

    def register(
        self,
        analyzer: BaseAnalyzer,
    ) -> None:
        name = analyzer.name.strip().lower()

        if not name:
            raise ValueError(
                "Analyzer benötigt einen Namen."
            )

        self._analyzers[name] = analyzer

    def unregister(
        self,
        name: str,
    ) -> bool:
        normalized_name = name.strip().lower()

        if normalized_name not in self._analyzers:
            return False

        del self._analyzers[normalized_name]
        return True

    def get(
        self,
        name: str,
    ) -> BaseAnalyzer | None:
        return self._analyzers.get(
            name.strip().lower()
        )

    def list_analyzers(
        self,
    ) -> list[BaseAnalyzer]:
        return sorted(
            self._analyzers.values(),
            key=lambda analyzer: (
                analyzer.priority,
                analyzer.name,
            ),
        )

    def list_names(self) -> list[str]:
        return [
            analyzer.name
            for analyzer
            in self.list_analyzers()
        ]


analyzer_registry = AnalyzerRegistry()
