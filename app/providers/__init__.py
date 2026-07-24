"""Erweiterbare und rückwärtskompatible KI-Provider-Schicht."""

from app.providers.base import (
    AIProvider,
    BaseProvider,
    ProviderCapability,
    ProviderHealth,
    ProviderRequest,
    ProviderResponse,
    ProviderStatus,
)
from app.providers.errors import (
    NoProviderAvailableError,
    ProviderError,
    ProviderExecutionError,
    ProviderNotFoundError,
)
from app.providers.local import LocalProvider as LegacyLocalProvider
from app.providers.local_provider import LocalProvider
from app.providers.manager import ProviderManager
from app.providers.registry import ProviderRegistry, provider_registry

__all__ = [
    "AIProvider",
    "BaseProvider",
    "LegacyLocalProvider",
    "LocalProvider",
    "NoProviderAvailableError",
    "ProviderCapability",
    "ProviderError",
    "ProviderExecutionError",
    "ProviderHealth",
    "ProviderManager",
    "ProviderNotFoundError",
    "ProviderRegistry",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderStatus",
    "provider_registry",
]
