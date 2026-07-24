"""Beispiele zur Verwendung der Provider-Schicht."""

from __future__ import annotations

import asyncio

from app.providers import (
    LocalProvider,
    ProviderCapability,
    ProviderManager,
    ProviderRequest,
)


async def main() -> None:
    manager = ProviderManager()
    manager.register(LocalProvider())

    response = await manager.execute(
        ProviderRequest(
            capability=ProviderCapability.TEXT_GENERATION,
            payload={"prompt": "MediaHub-AI-Node ist bereit."},
        )
    )

    print(response.result)


if __name__ == "__main__":
    asyncio.run(main())
