"""Ein kleiner lokaler Referenz-Provider ohne externe KI-Abhängigkeiten."""

from __future__ import annotations

from time import monotonic
from typing import Any, Mapping

from app.providers.base import (
    AIProvider,
    ProviderCapability,
    ProviderHealth,
    ProviderRequest,
    ProviderStatus,
)
from app.providers.errors import ProviderExecutionError


class LocalProvider(AIProvider):
    """Lokaler Basis-Provider für einfache Test- und Hilfsaufgaben.

    Dieser Provider ist noch kein Sprachmodell. Er stellt eine funktionierende
    Referenzimplementierung bereit, an der spätere Provider wie Ollama,
    llama.cpp, OpenAI oder spezialisierte Medienanalysen ausgerichtet werden.
    """

    def __init__(
        self,
        *,
        name: str = "local",
        priority: int = 10,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            name=name,
            capabilities={
                ProviderCapability.CLASSIFICATION,
                ProviderCapability.TEXT_GENERATION,
            },
            priority=priority,
            enabled=enabled,
        )

    async def execute(self, request: ProviderRequest) -> Mapping[str, Any]:
        if request.capability is ProviderCapability.TEXT_GENERATION:
            prompt = str(request.payload.get("prompt", "")).strip()
            if not prompt:
                raise ProviderExecutionError(
                    self.name, "Im Payload fehlt ein nichtleerer 'prompt'."
                )
            return {
                "text": prompt,
                "mode": "local_reference_echo",
            }

        if request.capability is ProviderCapability.CLASSIFICATION:
            text = str(request.payload.get("text", "")).strip()
            labels = request.payload.get("labels", ())
            if not text:
                raise ProviderExecutionError(
                    self.name, "Im Payload fehlt ein nichtleerer 'text'."
                )
            if not isinstance(labels, (list, tuple)) or not labels:
                raise ProviderExecutionError(
                    self.name, "Im Payload fehlt eine nichtleere 'labels'-Liste."
                )

            normalized = text.casefold()
            selected = next(
                (
                    str(label)
                    for label in labels
                    if str(label).casefold() in normalized
                ),
                str(labels[0]),
            )
            return {
                "label": selected,
                "confidence": 0.5,
                "mode": "local_reference_keyword",
            }

        raise ProviderExecutionError(
            self.name,
            f"Aufgabentyp '{request.capability.value}' wird nicht verarbeitet.",
        )

    async def health_check(self) -> ProviderHealth:
        started = monotonic()
        latency_ms = (monotonic() - started) * 1000
        status = (
            ProviderStatus.AVAILABLE
            if self.enabled
            else ProviderStatus.DISABLED
        )
        return ProviderHealth(
            provider_name=self.name,
            status=status,
            message="Lokaler Referenz-Provider ist betriebsbereit.",
            latency_ms=latency_ms,
            details={
                "capabilities": sorted(
                    capability.value for capability in self.capabilities
                )
            },
        )
