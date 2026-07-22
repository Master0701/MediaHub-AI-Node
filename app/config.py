from pathlib import Path

from app.version import APP_NAME, APP_VERSION

BASE_DIR = Path("/opt/mediahub")

HOST = "0.0.0.0"
PORT = 8765

DATABASE_DIR = BASE_DIR / "database"
CACHE_DIR = BASE_DIR / "cache"
JOBS_DIR = BASE_DIR / "jobs"
LOG_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"
