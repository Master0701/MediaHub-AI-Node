from collections.abc import Generator
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.cache.service import (
    cache_entry_to_dict,
    delete_cache_entry,
    get_cache_entry,
    list_cache_entries,
    purge_expired_entries,
    set_cache_entry,
)
from app.database import SessionLocal


router = APIRouter(
    prefix="/cache",
    tags=["Cache"],
)


class CacheEntryWrite(BaseModel):
    value: Any
    source: str | None = Field(
        default=None,
        max_length=100,
    )
    content_type: str = Field(
        default="application/json",
        max_length=100,
    )
    file_path: str | None = None
    checksum: str | None = Field(
        default=None,
        max_length=128,
    )
    ttl_seconds: int | None = Field(
        default=None,
        ge=1,
    )


def get_database() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.put(
    "/{namespace}/{cache_key}",
)
def write_cache_endpoint(
    namespace: str,
    cache_key: str,
    request: CacheEntryWrite,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    entry = set_cache_entry(
        db=db,
        namespace=namespace,
        cache_key=cache_key,
        value=request.value,
        source=request.source,
        content_type=request.content_type,
        file_path=request.file_path,
        checksum=request.checksum,
        ttl_seconds=request.ttl_seconds,
    )

    return cache_entry_to_dict(entry)


@router.get(
    "/{namespace}/{cache_key}",
)
def read_cache_endpoint(
    namespace: str,
    cache_key: str,
    include_expired: bool = False,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    entry = get_cache_entry(
        db=db,
        namespace=namespace,
        cache_key=cache_key,
        include_expired=include_expired,
    )

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Cache-Eintrag nicht gefunden "
                "oder abgelaufen."
            ),
        )

    return cache_entry_to_dict(entry)


@router.delete(
    "/{namespace}/{cache_key}",
)
def delete_cache_endpoint(
    namespace: str,
    cache_key: str,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    deleted = delete_cache_entry(
        db=db,
        namespace=namespace,
        cache_key=cache_key,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cache-Eintrag nicht gefunden.",
        )

    return {
        "deleted": True,
        "namespace": namespace,
        "cache_key": cache_key,
    }


@router.get("")
def list_cache_endpoint(
    namespace: str | None = None,
    include_expired: bool = False,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
    db: Session = Depends(get_database),
) -> list[dict[str, Any]]:
    entries = list_cache_entries(
        db=db,
        namespace=namespace,
        include_expired=include_expired,
        limit=limit,
    )

    return [
        cache_entry_to_dict(entry)
        for entry in entries
    ]


@router.post("/purge-expired")
def purge_expired_endpoint(
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    deleted_count = purge_expired_entries(db)

    return {
        "deleted": deleted_count,
    }
