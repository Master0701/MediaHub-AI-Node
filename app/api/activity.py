"""Activity- und Heartbeat-Endpunkte des MediaHub AI Node."""

from fastapi import APIRouter, Depends

from app.plugins.runtime import node_activity
from app.security.api_token import require_api_token

router = APIRouter(
    prefix="/activity",
    tags=["activity"],
)


@router.post(
    "/heartbeat",
    dependencies=[Depends(require_api_token)],
)
def mediahub_heartbeat() -> dict:
    """Registriert einen authentifizierten MediaHub-Heartbeat."""

    node_activity.mediahub_heartbeat()

    return {
        "ok": True,
        "activity": node_activity.status(),
    }


@router.get("/status")
def activity_status() -> dict:
    """Liefert den aktuellen Activity-/Ruhemodusstatus."""

    return node_activity.status()
