from collections.abc import Generator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.job_service import (
    VALID_JOB_STATUSES,
    create_job,
    get_job,
    job_to_dict,
    list_jobs,
)

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


class JobCreateRequest(BaseModel):
    job_type: str = Field(
        min_length=1,
        max_length=100,
        examples=["test"],
    )
    payload: dict[str, Any] = Field(default_factory=dict)


def get_database() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
def create_job_endpoint(
    request: JobCreateRequest,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    try:
        job = create_job(
            db=db,
            job_type=request.job_type,
            payload=request.payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return job_to_dict(job)


@router.get("")
def list_jobs_endpoint(
    job_status: str | None = Query(
        default=None,
        alias="status",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_database),
) -> list[dict[str, Any]]:
    if job_status and job_status not in VALID_JOB_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ungültiger Status: {job_status}",
        )

    jobs = list_jobs(
        db=db,
        status=job_status,
        limit=limit,
    )

    return [job_to_dict(job) for job in jobs]


@router.get("/types")
def list_job_types_endpoint() -> dict:
    from app.jobs.registry import (
        job_handler_registry,
    )

    return {"job_types": (job_handler_registry.list_types())}


@router.get("/{job_id}")
def get_job_endpoint(
    job_id: int,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    job = get_job(db, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job nicht gefunden.",
        )

    return job_to_dict(job)
