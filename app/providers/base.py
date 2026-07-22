from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    provider_name: str
    provider_type: str

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Prüft, ob der Provider einsatzbereit ist."""
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        task: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Führt eine Aufgabe über den Provider aus."""
        raise NotImplementedError
