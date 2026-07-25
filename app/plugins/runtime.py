"""Gemeinsame Laufzeitinstanz der AI-Node-Plugin-Engine."""

from app.config import PLUGIN_STATE_FILE, PLUGINS_DIR
from app.plugins.manager import PluginManager

plugin_manager = PluginManager(
    plugin_root=PLUGINS_DIR,
    state_path=PLUGIN_STATE_FILE,
)
