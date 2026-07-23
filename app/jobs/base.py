from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session


class BaseJobHandler(ABC):
    job_type: str

    @abstractmethod
    def execute(
        self,
        db: Session,
        payload: dict[str, Any],
        progress_callback,
    ) -> dict[str, Any]:
        """Führt einen Job aus und gibt das Ergebnis zurück."""
        raise NotImplementedError
