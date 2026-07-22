from collections.abc import Generator
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.providers.registry import provider_registry
from app.services.provider_service import (
    get_provider,
    list_providers,
    provider_to_dict,
    set_provider_enabled,
)


router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)


class ProviderEnabledRequest(BaseModel):
    enabled: bool


class ProviderExecuteRequest(BaseModel):
    task: str
    payload: dict[str, Any] = Field(default_factory=dict)


def get_database() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("")
def list_providers_endpoint(
    db: Session = Depends(get_database),
) -> list[dict[str, Any]]:
    return [
        provider_to_dict(provider)
        for provider in list_providers(db)
    ]


@router.get("/{provider_name}/health")
def provider_health_endpoint(
    provider_name: str,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    provider_record = get_provider(
        db,
        provider_name,
    )

    if provider_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider nicht gefunden.",
        )

    if not provider_record.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider ist deaktiviert.",
        )

    try:
        provider = provider_registry.require(
            provider_name
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return provider.health_check()


@router.post("/{provider_name}/execute")
def provider_execute_endpoint(
    provider_name: str,
    request: ProviderExecuteRequest,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    provider_record = get_provider(
        db,
        provider_name,
    )

    if provider_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider nicht gefunden.",
        )

    if not provider_record.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider ist deaktiviert.",
        )

    try:
        provider = provider_registry.require(
            provider_name
        )

        return provider.execute(
            task=request.task,
            payload=request.payload,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.put("/{provider_name}/enabled")
def provider_enabled_endpoint(
    provider_name: str,
    request: ProviderEnabledRequest,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    provider_record = get_provider(
        db,
        provider_name,
    )

    if provider_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider nicht gefunden.",
        )

    provider_record = set_provider_enabled(
        db=db,
        provider=provider_record,
        enabled=request.enabled,
    )

    return provider_to_dict(provider_record)
