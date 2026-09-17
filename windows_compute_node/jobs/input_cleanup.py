"""Lifecycle cleanup for temporary Compute-Node job inputs."""

from __future__ import annotations

import shutil
from pathlib import Path


class JobInputCleanup:
    """Removes temporary input files owned by Compute-Node jobs."""

    def __init__(
        self,
        runtime_dir: str | Path,
    ) -> None:
        self.root = (
            Path(runtime_dir)
            / "job_inputs"
        )

    def cleanup_job(
        self,
        job_id: str,
    ) -> bool:
        clean_id = str(
            job_id or ""
        ).strip()

        if not clean_id:
            return False

        target = (
            self.root
            / clean_id
        )

        # Security guard:
        # A job ID must never be able to escape job_inputs.
        try:
            target.resolve().relative_to(
                self.root.resolve()
            )
        except ValueError:
            return False

        if not target.exists():
            return False

        shutil.rmtree(
            target,
            ignore_errors=False,
        )

        return True

    def cleanup_orphans(
        self,
    ) -> int:
        """Remove leftovers from previous Compute-Node processes."""

        if not self.root.is_dir():
            return 0

        removed = 0

        for child in self.root.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(
                        child,
                        ignore_errors=False,
                    )
                else:
                    child.unlink()

                removed += 1

            except OSError:
                # One locked/corrupt leftover must not prevent
                # the Compute Node from starting.
                continue

        return removed
