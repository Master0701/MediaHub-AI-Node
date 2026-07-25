"""Gemeinsame Laufzeitinstanzen der AI-Node-Plugin-Verwaltung."""

from app.config import (
    PLUGIN_BACKUP_DIR,
    PLUGIN_STATE_FILE,
    PLUGINS_DIR,
)
from app.plugins.installer import PluginInstaller
from app.plugins.manager import PluginManager

plugin_manager = PluginManager(
    plugin_root=PLUGINS_DIR,
    state_path=PLUGIN_STATE_FILE,
)

plugin_installer = PluginInstaller(
    plugin_root=PLUGINS_DIR,
    backup_root=PLUGIN_BACKUP_DIR,
)
