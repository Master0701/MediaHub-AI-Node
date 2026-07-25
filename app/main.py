import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import psutil
from fastapi import FastAPI

from app.api.analyzers import router as analyzers_router
from app.api.cache import router as cache_router
from app.api.jobs import router as jobs_router
from app.api.knowledge import router as knowledge_router
from app.api.knowledge_import import router as knowledge_import_router
from app.api.plugins import router as plugins_router
from app.api.plugin_plans import router as plugin_plans_router
from app.api.providers import router as providers_router
from app.api.quality import router as quality_router
from app.api.references import router as references_router
from app.config import APP_NAME, APP_VERSION, BASE_DIR
from app.database import Base, engine
from app.jobs.worker import start_worker, stop_worker
from app.plugins.runtime import plugin_manager
from app.services.provider_service import ensure_default_providers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        ensure_default_providers(db)
    finally:
        db.close()

    discovered = plugin_manager.discover()
    loaded = plugin_manager.load_enabled()

    logger.info(
        "AI-Plugins erkannt: %s; geladen: %s",
        len(discovered),
        len(loaded),
    )

    for record in discovered:
        if record.error:
            logger.warning(
                "AI-Plugin %s: %s",
                record.manifest.plugin_id,
                record.error,
            )

    start_worker()
    try:
        yield
    finally:
        stop_worker()


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Lokaler KI- und Hintergrunddienst für MediaHub.",
    lifespan=lifespan,
)

app.include_router(analyzers_router)
app.include_router(jobs_router)
app.include_router(cache_router)
app.include_router(knowledge_router)
app.include_router(providers_router)
app.include_router(plugins_router)
app.include_router(plugin_plans_router)
app.include_router(quality_router)
app.include_router(references_router)
app.include_router(knowledge_import_router)


@app.get("/")
def root() -> dict:
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "online",
    }


@app.get("/health")
def health() -> dict:
    disk = psutil.disk_usage(str(BASE_DIR))
    memory = psutil.virtual_memory()

    temperature = None
    thermal_file = Path("/sys/class/thermal/thermal_zone0/temp")

    if thermal_file.exists():
        try:
            temperature = round(
                int(thermal_file.read_text().strip()) / 1000,
                1,
            )
        except (OSError, ValueError):
            temperature = None

    records = plugin_manager.registry.all()

    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "plugins": {
            "detected": len(records),
            "enabled": sum(1 for record in records if record.enabled),
            "loaded": sum(1 for record in records if record.loaded),
            "errors": sum(1 for record in records if record.error),
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / 1024**3, 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / 1024**3, 2),
            "temperature_c": temperature,
        },
    }
