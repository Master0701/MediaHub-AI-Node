"""Kompatible Registry für bestehende und neue KI-Provider."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeAlias

from app.providers.base import (
    AIProvider,
    BaseProvider,
    ProviderCapability,
)
from app.providers.errors import ProviderNotFoundError
from app.providers.local import LocalProvider

RegisteredProvider: TypeAlias = BaseProvider | AIProvider


def _provider_name(provider: RegisteredProvider) -> str:
    """Ermittelt den normalisierten Namen beider Provider-Generationen."""

    name = getattr(provider, "name", None)
    if name is None:
        name = getattr(provider, "provider_name", None)

    normalized = str(name or "").strip().lower()
    if not normalized:
        raise ValueError("Der Provider besitzt keinen gültigen Namen.")
    return normalized


class ProviderRegistry:
    """Registriert alte synchrone und neue asynchrone Provider gemeinsam."""

    def __init__(self) -> None:
        self._providers: dict[str, RegisteredProvider] = {}

    def register(
        self,
        provider: RegisteredProvider,
        *,
        replace: bool = True,
    ) -> None:
        """Registriert einen Provider.

        `replace=True` entspricht dem Verhalten der bisherigen Registry.
        """

        name = _provider_name(provider)
        if name in self._providers and not replace:
            raise ValueError(f"Provider '{name}' ist bereits registriert.")
        self._providers[name] = provider

    def unregister(self, provider_name: str) -> RegisteredProvider:
        """Entfernt einen Provider."""

        name = provider_name.strip().lower()
        try:
            return self._providers.pop(name)
        except KeyError as exc:
            raise ProviderNotFoundError(
                f"Provider '{name}' wurde nicht gefunden."
            ) from exc

    def get(self, provider_name: str) -> RegisteredProvider | None:
        """Liefert einen Provider oder `None` wie die bisherige REST-API."""

        return self._providers.get(provider_name.strip().lower())

    def require(self, provider_name: str) -> RegisteredProvider:
        """Liefert einen Provider oder erzeugt den bisherigen ValueError."""

        provider = self.get(provider_name)
        if provider is None:
            raise ValueError(f"Provider nicht gefunden: {provider_name}")
        return provider

    def list_names(self) -> list[str]:
        """Liefert alle Namen für Datenbankinitialisierung und REST-API."""

        return sorted(self._providers)

    def all(self) -> tuple[RegisteredProvider, ...]:
        """Liefert alle Provider stabil sortiert."""

        def sort_key(provider: RegisteredProvider) -> tuple[int, str]:
            priority = int(getattr(provider, "priority", 100))
            return priority, _provider_name(provider)

        return tuple(sorted(self._providers.values(), key=sort_key))

    def candidates(
        self,
        capability: ProviderCapability,
        *,
        exclude: Iterable[str] = (),
    ) -> tuple[AIProvider, ...]:
        """Liefert moderne aktive Provider für eine bestimmte Fähigkeit."""

        excluded = {name.strip().lower() for name in exclude}
        result: list[AIProvider] = []

        for provider in self.all():
            if not isinstance(provider, AIProvider):
                continue
            if provider.name in excluded:
                continue
            if provider.supports(capability):
                result.append(provider)

        return tuple(result)

    def __len__(self) -> int:
        return len(self._providers)


# Gemeinsame Registry der bestehenden API.
provider_registry = ProviderRegistry()
provider_registry.register(LocalProvider())
