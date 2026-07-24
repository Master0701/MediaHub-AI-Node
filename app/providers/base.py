"""Gemeinsame Schnittstellen und Datentypen für KI-Provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic
from typing import Any, Mapping
from uuid import uuid4


class BaseProvider(ABC):
    """Kompatible synchrone Provider-Schnittstelle der bestehenden REST-API."""

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


class ProviderCapability(StrEnum):
    """Aufgabentypen, die ein moderner KI-Provider unterstützen kann."""

    CHAT = "chat"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    IMAGE_ANALYSIS = "image_analysis"
    MEDIA_IDENTIFICATION = "media_identification"
    METADATA = "metadata"
    OCR = "ocr"
    QUALITY_ANALYSIS = "quality_analysis"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_GENERATION = "text_generation"
    VIDEO_ANALYSIS = "video_analysis"


class ProviderStatus(StrEnum):
    """Gesundheitszustand eines modernen Providers."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """Einheitlicher Auftrag an einen modernen KI-Provider."""

    capability: ProviderCapability
    payload: Mapping[str, Any]
    request_id: str = field(default_factory=lambda: uuid4().hex)
    timeout_seconds: float = 60.0
    preferred_provider: str | None = None
    allow_fallback: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds muss größer als 0 sein.")


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """Einheitliche Antwort eines modernen Providers."""

    request_id: str
    provider_name: str
    capability: ProviderCapability
    result: Mapping[str, Any]
    duration_ms: float
    cached: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    """Ergebnis eines modernen Provider-Health-Checks."""

    provider_name: str
    status: ProviderStatus
    message: str = ""
    latency_ms: float | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


class AIProvider(ABC):
    """Asynchrone Basisklasse für neue lokale und externe KI-Provider."""

    def __init__(
        self,
        *,
        name: str,
        capabilities: set[ProviderCapability],
        priority: int = 100,
        enabled: bool = True,
    ) -> None:
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("Der Provider-Name darf nicht leer sein.")

        self.name = normalized_name
        self.capabilities = frozenset(capabilities)
        self.priority = priority
        self.enabled = enabled

    def supports(self, capability: ProviderCapability) -> bool:
        """Prüft, ob der Provider einen Aufgabentyp unterstützt."""

        return self.enabled and capability in self.capabilities

    async def timed_execute(self, request: ProviderRequest) -> ProviderResponse:
        """Führt einen Auftrag aus und misst seine Laufzeit."""

        started = monotonic()
        result = await self.execute(request)
        duration_ms = (monotonic() - started) * 1000

        return ProviderResponse(
            request_id=request.request_id,
            provider_name=self.name,
            capability=request.capability,
            result=result,
            duration_ms=duration_ms,
        )

    @abstractmethod
    async def execute(self, request: ProviderRequest) -> Mapping[str, Any]:
        """Führt den eigentlichen Provider-Auftrag aus."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Prüft Erreichbarkeit und Funktionszustand des Providers."""
