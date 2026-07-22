import json
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job


VALID_JOB_STATUSES = {
    "queued",
    "running",
    "completed",
    "failed",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, (Path, UUID)):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (set, frozenset, tuple)):
        return list(value)

    raise TypeError(
        f"Objekt vom Typ {type(value).__name__} "
        "ist nicht JSON-serialisierbar."
    )


def serialize_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=json_default,
    )


def deserialize_json(
    value: str | None,
    fallback_key: str,
) -> Any:
    if not value:
        return None

    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {fallback_key: value}


def create_job(
    db: Session,
    job_type: str,
    payload: dict[str, Any] | None = None,
) -> Job:
    normalized_job_type = job_type.strip()

    if not normalized_job_type:
        raise ValueError(
            "Der Job-Typ darf nicht leer sein."
        )

    job = Job(
        job_type=normalized_job_type,
        status="queued",
        progress=0,
        payload=serialize_json(payload or {}),
        result=None,
        error=None,
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job


def get_job(
    db: Session,
    job_id: int,
) -> Job | None:
    return db.get(Job, job_id)


def list_jobs(
    db: Session,
    status: str | None = None,
    limit: int = 100,
) -> list[Job]:
    query = (
        select(Job)
        .order_by(Job.id.desc())
        .limit(limit)
    )

    if status:
        query = query.where(Job.status == status)

    return list(db.scalars(query).all())


def get_next_queued_job(
    db: Session,
) -> Job | None:
    query = (
        select(Job)
        .where(Job.status == "queued")
        .order_by(Job.id.asc())
        .limit(1)
    )

    return db.scalar(query)


def mark_job_running(
    db: Session,
    job: Job,
) -> Job:
    job.status = "running"
    job.progress = 1
    job.started = utc_now()
    job.finished = None
    job.error = None

    db.commit()
    db.refresh(job)

    return job


def update_job_progress(
    db: Session,
    job: Job,
    progress: int,
) -> Job:
    job.progress = max(0, min(100, progress))

    db.commit()
    db.refresh(job)

    return job


def mark_job_completed(
    db: Session,
    job: Job,
    result: dict[str, Any] | None = None,
) -> Job:
    job.status = "completed"
    job.progress = 100
    job.result = serialize_json(result or {})
    job.error = None
    job.finished = utc_now()

    db.commit()
    db.refresh(job)

    return job


def mark_job_failed(
    db: Session,
    job: Job,
    error: str,
) -> Job:
    job.status = "failed"
    job.error = error
    job.finished = utc_now()

    db.commit()
    db.refresh(job)

    return job


def job_to_dict(
    job: Job,
) -> dict[str, Any]:
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress or 0,
        "payload": (
            deserialize_json(
                job.payload,
                "raw",
            )
            or {}
        ),
        "result": deserialize_json(
            job.result,
            "raw",
        ),
        "error": job.error,
        "created": (
            job.created.isoformat()
            if job.created
            else None
        ),
        "updated": (
            job.updated.isoformat()
            if job.updated
            else None
        ),
        "started": (
            job.started.isoformat()
            if job.started
            else None
        ),
        "finished": (
            job.finished.isoformat()
            if job.finished
            else None
        ),
    }
