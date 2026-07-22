from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AnalyzerContext:
    file_path: Path
    options: dict[str, Any] = field(default_factory=dict)
    shared_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzerResult:
    analyzer: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "analyzer": self.analyzer,
            "success": self.success,
            "data": self.data,
            "warnings": self.warnings,
            "errors": self.errors,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


class BaseAnalyzer(ABC):
    name = "base"
    priority = 100

    required_tools: list[str] = []
    capabilities: list[str] = []

    enabled = True

    def can_analyze(
        self,
        context: AnalyzerContext,
    ) -> bool:
        return True

    @abstractmethod
    def analyze(
        self,
        context: AnalyzerContext,
    ) -> AnalyzerResult:
        raise NotImplementedError
