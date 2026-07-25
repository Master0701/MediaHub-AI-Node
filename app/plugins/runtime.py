"""Gemeinsame Laufzeitinstanzen der AI-Node-Plugin-Verwaltung."""

from app.config import (
    PLUGIN_BACKUP_DIR,
    PLUGIN_STATE_FILE,
    PLUGINS_DIR,
)
from app.plugins.installer import PluginInstaller
from app.plugins.manager import PluginManager
from app.plugins.plan_store import PluginPlanStore

plugin_manager = PluginManager(
    plugin_root=PLUGINS_DIR,
    state_path=PLUGIN_STATE_FILE,
)

plugin_installer = PluginInstaller(
    plugin_root=PLUGINS_DIR,
    backup_root=PLUGIN_BACKUP_DIR,
)

plugin_plan_store = PluginPlanStore(ttl_minutes=15)
