"""Tests für Registrierung, Auswahl und Fallback der KI-Provider."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from app.providers import (
    AIProvider,
    LocalProvider,
    NoProviderAvailableError,
    ProviderCapability,
    ProviderHealth,
    ProviderManager,
    ProviderRequest,
    ProviderStatus,
)


class FailingProvider(AIProvider):
    def __init__(self) -> None:
        super().__init__(
            name="failing",
            capabilities={ProviderCapability.TEXT_GENERATION},
            priority=1,
        )

    async def execute(self, request: ProviderRequest) -> Mapping[str, Any]:
        raise RuntimeError("absichtlicher Testfehler")

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name=self.name,
            status=ProviderStatus.UNAVAILABLE,
        )


@pytest.mark.anyio
async def test_local_provider_text_generation() -> None:
    manager = ProviderManager()
    manager.register(LocalProvider())

    response = await manager.execute(
        ProviderRequest(
            capability=ProviderCapability.TEXT_GENERATION,
            payload={"prompt": "Test"},
        )
    )

    assert response.provider_name == "local"
    assert response.result["text"] == "Test"
    assert response.duration_ms >= 0


@pytest.mark.anyio
async def test_manager_uses_fallback_provider() -> None:
    manager = ProviderManager()
    manager.register(FailingProvider())
    manager.register(LocalProvider(priority=10))

    response = await manager.execute(
        ProviderRequest(
            capability=ProviderCapability.TEXT_GENERATION,
            payload={"prompt": "Fallback"},
        )
    )

    assert response.provider_name == "local"
    assert response.result["text"] == "Fallback"


@pytest.mark.anyio
async def test_manager_can_disable_fallback() -> None:
    manager = ProviderManager()
    manager.register(FailingProvider())
    manager.register(LocalProvider(priority=10))

    with pytest.raises(Exception, match="failing"):
        await manager.execute(
            ProviderRequest(
                capability=ProviderCapability.TEXT_GENERATION,
                payload={"prompt": "Kein Fallback"},
                allow_fallback=False,
            )
        )


@pytest.mark.anyio
async def test_missing_capability_raises_error() -> None:
    manager = ProviderManager()
    manager.register(LocalProvider())

    with pytest.raises(NoProviderAvailableError):
        await manager.execute(
            ProviderRequest(
                capability=ProviderCapability.VIDEO_ANALYSIS,
                payload={"path": "video.mkv"},
            )
        )


@pytest.mark.anyio
async def test_health_checks() -> None:
    manager = ProviderManager()
    manager.register(LocalProvider())

    health = await manager.health_checks()

    assert len(health) == 1
    assert health[0].provider_name == "local"
    assert health[0].status is ProviderStatus.AVAILABLE
