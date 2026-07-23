import logging
import threading

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.jobs.registry import job_handler_registry
from app.jobs.utils import decode_payload
from app.models import Job
from app.services.job_service import (
    get_next_queued_job,
    mark_job_completed,
    mark_job_failed,
    mark_job_running,
    update_job_progress,
)


logger = logging.getLogger("mediahub.jobs")

_stop_event = threading.Event()
_worker_thread: threading.Thread | None = None


def process_job(
    db: Session,
    job: Job,
) -> dict:
    job_type = str(job.job_type).strip()

    logger.info(
        "Verarbeite Job %s vom Typ %s.",
        job.id,
        job_type,
    )

    handler = job_handler_registry.require(
        job_type
    )

    payload = decode_payload(job)

    def report_progress(
        progress: int,
    ) -> None:
        value = max(
            0,
            min(int(progress), 99),
        )

        update_job_progress(
            db,
            job,
            value,
        )

    return handler.execute(
        db=db,
        payload=payload,
        progress_callback=report_progress,
    )


def worker_loop() -> None:
    logger.info(
        "MediaHub-Job-Worker gestartet."
    )

    while not _stop_event.is_set():
        db = SessionLocal()

        try:
            job = get_next_queued_job(db)

            if job is None:
                _stop_event.wait(2)
                continue

            mark_job_running(db, job)

            try:
                result = process_job(
                    db=db,
                    job=job,
                )

                mark_job_completed(
                    db=db,
                    job=job,
                    result=result,
                )

                logger.info(
                    "Job %s erfolgreich "
                    "abgeschlossen.",
                    job.id,
                )

            except Exception as exc:
                logger.exception(
                    "Job %s ist fehlgeschlagen.",
                    job.id,
                )

                mark_job_failed(
                    db=db,
                    job=job,
                    error=str(exc),
                )

        except Exception:
            db.rollback()

            logger.exception(
                "Fehler im "
                "MediaHub-Job-Worker."
            )

            _stop_event.wait(2)

        finally:
            db.close()

    logger.info(
        "MediaHub-Job-Worker beendet."
    )


def start_worker() -> None:
    global _worker_thread

    if (
        _worker_thread
        and _worker_thread.is_alive()
    ):
        return

    _stop_event.clear()

    _worker_thread = threading.Thread(
        target=worker_loop,
        name="mediahub-job-worker",
        daemon=True,
    )

    _worker_thread.start()


def stop_worker() -> None:
    _stop_event.set()

    if (
        _worker_thread
        and _worker_thread.is_alive()
    ):
        _worker_thread.join(
            timeout=5
        )
