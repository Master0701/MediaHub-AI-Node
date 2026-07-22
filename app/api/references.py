from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.references.service import (
    ReferenceProfileNameExistsError,
    ReferenceProfileNotFoundError,
    ReferenceService,
)


router = APIRouter(
    prefix="/references",
    tags=["references"],
)


def get_session():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


class ReferenceSourceRequest(BaseModel):
    file_path: str | None = None
    file_name: str | None = None


class ReferenceCreateRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )
    description: str | None = None
    source: ReferenceSourceRequest | None = None
    quality_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    quality_profile: str | None = None
    analysis: dict[str, Any] = Field(
        default_factory=dict,
    )
    quality: dict[str, Any] = Field(
        default_factory=dict,
    )
    comparison_settings: dict[str, Any] = Field(
        default_factory=dict,
    )
    enabled: bool = True


class ReferenceUpdateRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    description: str | None = None
    source: ReferenceSourceRequest | None = None
    quality_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    quality_profile: str | None = None
    analysis: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
    comparison_settings: (
        dict[str, Any] | None
    ) = None
    enabled: bool | None = None


@router.get("")
def list_references(
    enabled_only: bool = Query(
        default=False,
    ),
    session: Session = Depends(
        get_session
    ),
) -> dict[str, Any]:
    service = ReferenceService(session)

    profiles = service.list(
        enabled_only=enabled_only
    )

    return {
        "count": len(profiles),
        "references": profiles,
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_reference(
    request: ReferenceCreateRequest,
    session: Session = Depends(
        get_session
    ),
) -> dict[str, Any]:
    service = ReferenceService(session)

    source = request.source

    try:
        return service.create(
            name=request.name,
            description=request.description,
            source_file_path=(
                source.file_path
                if source
                else None
            ),
            source_file_name=(
                source.file_name
                if source
                else None
            ),
            quality_score=(
                request.quality_score
            ),
            quality_profile=(
                request.quality_profile
            ),
            analysis=request.analysis,
            quality=request.quality,
            comparison_settings=(
                request.comparison_settings
            ),
            enabled=request.enabled,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except ReferenceProfileNameExistsError:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ein Referenzprofil mit diesem "
                "Namen existiert bereits."
            ),
        )


@router.get("/{profile_id}")
def get_reference(
    profile_id: int,
    session: Session = Depends(
        get_session
    ),
) -> dict[str, Any]:
    service = ReferenceService(session)

    try:
        return service.get(profile_id)

    except ReferenceProfileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=(
                "Referenzprofil wurde "
                "nicht gefunden."
            ),
        )


@router.put("/{profile_id}")
def update_reference(
    profile_id: int,
    request: ReferenceUpdateRequest,
    session: Session = Depends(
        get_session
    ),
) -> dict[str, Any]:
    service = ReferenceService(session)

    source = request.source

    update_data = request.model_dump(
        exclude_unset=True
    )

    arguments: dict[str, Any] = {}

    for field in (
        "name",
        "description",
        "quality_score",
        "quality_profile",
        "analysis",
        "quality",
        "comparison_settings",
        "enabled",
    ):
        if field in update_data:
            arguments[field] = update_data[field]

    if "source" in update_data:
        arguments["source_file_path"] = (
            source.file_path
            if source
            else None
        )
        arguments["source_file_name"] = (
            source.file_name
            if source
            else None
        )

    try:
        return service.update(
            profile_id,
            **arguments,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except ReferenceProfileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=(
                "Referenzprofil wurde "
                "nicht gefunden."
            ),
        )

    except ReferenceProfileNameExistsError:
        raise HTTPException(
            status_code=409,
            detail=(
                "Ein Referenzprofil mit diesem "
                "Namen existiert bereits."
            ),
        )


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_reference(
    profile_id: int,
    session: Session = Depends(
        get_session
    ),
) -> Response:
    service = ReferenceService(session)

    try:
        service.delete(profile_id)

    except ReferenceProfileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=(
                "Referenzprofil wurde "
                "nicht gefunden."
            ),
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )
