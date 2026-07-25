"""Fehlerklassen der AI-Node-Plugin-Engine."""


class PluginError(RuntimeError):
    """Basisklasse für Plugin-Fehler."""


class PluginManifestError(PluginError):
    """Das Plugin-Manifest ist ungültig."""


class PluginNotFoundError(PluginError):
    """Das gewünschte Plugin wurde nicht gefunden."""


class PluginLoadError(PluginError):
    """Ein Plugin konnte nicht geladen werden."""


class PluginCompatibilityError(PluginError):
    """Ein Plugin ist nicht mit diesem AI-Node kompatibel."""
