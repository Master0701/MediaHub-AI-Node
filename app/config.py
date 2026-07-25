import os
from pathlib import Path

from app.version import APP_NAME, APP_VERSION  # noqa: F401

BASE_DIR = Path(os.getenv("MEDIAHUB_BASE_DIR", "/opt/mediahub"))

HOST = "0.0.0.0"
PORT = 8765

DATABASE_DIR = BASE_DIR / "database"
CACHE_DIR = BASE_DIR / "cache"
JOBS_DIR = BASE_DIR / "jobs"
LOG_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"

AI_NODE_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_NODE_DIR",
        str(BASE_DIR / "ai-node"),
    )
)
PLUGINS_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_NODE_PLUGINS_DIR",
        str(AI_NODE_DIR / "plugins"),
    )
)
PLUGIN_STATE_FILE = Path(
    os.getenv(
        "MEDIAHUB_AI_NODE_PLUGIN_STATE_FILE",
        str(AI_NODE_DIR / "data" / "plugin_state.json"),
    )
)
PLUGIN_BACKUP_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_NODE_PLUGIN_BACKUP_DIR",
        str(AI_NODE_DIR / "backups" / "plugins"),
    )
)
