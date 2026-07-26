import os
from pathlib import Path

from app.version import APP_NAME, APP_VERSION  # noqa: F401


BASE_DIR = Path(
    os.getenv(
        "MEDIAHUB_BASE_DIR",
        "/opt/mediahub",
    )
)

AI_NODE_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_NODE_DIR",
        str(BASE_DIR / "ai-node"),
    )
)


HOST = os.getenv(
    "MEDIAHUB_AI_HOST",
    "0.0.0.0",
)

PORT = int(
    os.getenv(
        "MEDIAHUB_AI_PORT",
        "8765",
    )
)


DATABASE_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_DATABASE_DIR",
        str(AI_NODE_DIR / "data"),
    )
)

CACHE_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_CACHE_DIR",
        str(AI_NODE_DIR / "cache"),
    )
)

JOBS_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_JOBS_DIR",
        str(AI_NODE_DIR / "jobs"),
    )
)

LOG_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_LOG_DIR",
        str(AI_NODE_DIR / "logs"),
    )
)

MODELS_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_MODELS_DIR",
        str(AI_NODE_DIR / "models"),
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

PLUGIN_PLAN_DIR = Path(
    os.getenv(
        "MEDIAHUB_AI_NODE_PLUGIN_PLAN_DIR",
        str(AI_NODE_DIR / "data" / "plugin_plans"),
    )
)
