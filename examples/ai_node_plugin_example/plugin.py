"""Minimales Beispiel-Plugin."""


class HelloPlugin:
    """Einfaches Testobjekt für die Plugin-Engine."""

    name = "hello-ai-node"

    def health_check(self) -> dict[str, object]:
        return {
            "status": "available",
            "plugin": self.name,
        }
