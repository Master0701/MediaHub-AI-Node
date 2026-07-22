from app.providers.base import BaseProvider
from app.providers.local import LocalProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}

    def register(
        self,
        provider: BaseProvider,
    ) -> None:
        self._providers[
            provider.provider_name
        ] = provider

    def get(
        self,
        provider_name: str,
    ) -> BaseProvider | None:
        return self._providers.get(provider_name)

    def require(
        self,
        provider_name: str,
    ) -> BaseProvider:
        provider = self.get(provider_name)

        if provider is None:
            raise ValueError(
                f"Provider nicht gefunden: "
                f"{provider_name}"
            )

        return provider

    def list_names(self) -> list[str]:
        return sorted(self._providers.keys())


provider_registry = ProviderRegistry()
provider_registry.register(LocalProvider())
