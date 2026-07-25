"""Plugin-System des MediaHub-AI-Nodes."""

from app.plugins.manager import PluginManager
from app.plugins.runtime import plugin_manager

__all__ = ["PluginManager", "plugin_manager"]
