"""Fehlerklassen der Provider-Schicht."""


class ProviderError(RuntimeError):
    """Basisklasse für Fehler der Provider-Schicht."""


class ProviderNotFoundError(ProviderError):
    """Der angeforderte Provider ist nicht registriert."""


class NoProviderAvailableError(ProviderError):
    """Für die Aufgabe steht kein geeigneter Provider zur Verfügung."""


class ProviderExecutionError(ProviderError):
    """Ein Provider konnte einen Auftrag nicht erfolgreich abschließen."""

    def __init__(self, provider_name: str, message: str) -> None:
        self.provider_name = provider_name
        super().__init__(f"Provider '{provider_name}': {message}")
