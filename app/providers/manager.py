"""Routing, Fallback und Health-Checks für mehrere KI-Provider."""

from __future__ import annotations

import asyncio

from app.providers.base import (
    AIProvider,
    ProviderHealth,
    ProviderRequest,
    ProviderResponse,
)
from app.providers.errors import (
    NoProviderAvailableError,
    ProviderExecutionError,
)
from app.providers.registry import ProviderRegistry


class ProviderManager:
    """Wählt passende Provider aus und führt Aufträge mit Fallback aus."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry or ProviderRegistry()

    def register(self, provider: AIProvider, *, replace: bool = False) -> None:
        self.registry.register(provider, replace=replace)

    async def execute(self, request: ProviderRequest) -> ProviderResponse:
        """Führt einen Auftrag beim bevorzugten oder besten Provider aus."""

        candidates = list(self.registry.candidates(request.capability))

        if request.preferred_provider:
            preferred = request.preferred_provider.strip().lower()
            candidates.sort(key=lambda provider: provider.name != preferred)

        if not candidates:
            raise NoProviderAvailableError(
                f"Kein aktiver Provider unterstützt '{request.capability.value}'."
            )

        errors: list[str] = []

        for provider in candidates:
            try:
                async with asyncio.timeout(request.timeout_seconds):
                    return await provider.timed_execute(request)
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                if not request.allow_fallback:
                    raise ProviderExecutionError(
                        provider.name, str(exc)
                    ) from exc

        details = "; ".join(errors)
        raise NoProviderAvailableError(
            "Alle geeigneten Provider sind fehlgeschlagen. " + details
        )

    async def health_checks(self) -> tuple[ProviderHealth, ...]:
        """Prüft alle Provider parallel."""

        providers = self.registry.all()
        if not providers:
            return ()

        results = await asyncio.gather(
            *(provider.health_check() for provider in providers),
            return_exceptions=True,
        )

        health_entries: list[ProviderHealth] = []
        for provider, result in zip(providers, results, strict=True):
            if isinstance(result, BaseException):
                from app.providers.base import ProviderStatus

                health_entries.append(
                    ProviderHealth(
                        provider_name=provider.name,
                        status=ProviderStatus.UNAVAILABLE,
                        message=str(result),
                    )
                )
            else:
                health_entries.append(result)

        return tuple(health_entries)
