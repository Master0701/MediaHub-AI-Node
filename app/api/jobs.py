from collections.abc import Generator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import JOBS_DIR
from app.database import SessionLocal
from app.security.api_token import require_api_token
from app.services.job_service import (
    VALID_JOB_STATUSES,
    create_job,
    finalize_preparing_job,
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
    preparing: bool = False


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
            initial_status=(
                "preparing"
                if request.preparing
                else "queued"
            ),
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


@router.put(
    "/{job_id}/input",
    dependencies=[Depends(require_api_token)],
)
async def upload_job_input_endpoint(
    job_id: int,
    request: Request,
    x_filename: str | None = Header(
        default=None,
        alias="X-Filename",
    ),
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    job = get_job(db, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job nicht gefunden.",
        )

    if job.status != "preparing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job befindet sich nicht im Status preparing.",
        )

    raw_name = (x_filename or "").strip()
    safe_name = Path(raw_name).name

    if (
        not safe_name
        or safe_name in {".", ".."}
        or safe_name != raw_name
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ungültiger Dateiname.",
        )

    try:
        content_length = int(
            request.headers.get("content-length") or "0"
        )
    except ValueError:
        content_length = 0

    if content_length <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leerer Upload.",
        )

    upload_dir = JOBS_DIR / "job_inputs" / str(job_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    target = upload_dir / safe_name
    temporary = target.with_suffix(
        target.suffix + ".part"
    )

    if temporary.exists():
        temporary.unlink()

    received = 0

    try:
        with temporary.open("wb") as handle:
            async for chunk in request.stream():
                if not chunk:
                    continue

                handle.write(chunk)
                received += len(chunk)

        if received != content_length:
            raise ValueError(
                "Upload wurde nicht vollständig übertragen: "
                f"{received} von {content_length} Bytes."
            )

        temporary.replace(target)

        job = finalize_preparing_job(
            db=db,
            job=job,
            payload_updates={
                "input": str(target),
                "input_info": {
                    "filename": safe_name,
                    "size": received,
                },
            },
        )

    except Exception as exc:
        if temporary.exists():
            temporary.unlink()

        if target.exists():
            target.unlink()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Input-Upload fehlgeschlagen: {exc}",
        ) from exc

    return {
        "job": job_to_dict(job),
        "input": {
            "filename": safe_name,
            "size": received,
            "path": str(target),
        },
    }


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
