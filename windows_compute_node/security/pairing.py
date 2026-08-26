"""One-time pairing for the Windows Compute Node."""

from __future__ import annotations

import secrets
import time
from typing import Any


class PairingManager:
    DEFAULT_LIFETIME_SECONDS = 600

    def __init__(
        self,
        lifetime_seconds: int = DEFAULT_LIFETIME_SECONDS,
    ) -> None:
        self.lifetime_seconds = max(
            60,
            int(lifetime_seconds),
        )

        self._code: str | None = None
        self._created_at: float | None = None
        self._used = False

    def create_code(self) -> str:
        self._code = (
            f"{secrets.randbelow(1_000_000):06d}"
        )

        self._created_at = time.time()
        self._used = False

        return self._code

    def status(self) -> dict[str, Any]:
        if (
            self._code is None
            or self._created_at is None
        ):
            return {
                "active": False,
                "used": self._used,
                "expires_in_seconds": 0,
            }

        remaining = max(
            0,
            int(
                self.lifetime_seconds
                - (
                    time.time()
                    - self._created_at
                )
            ),
        )

        active = (
            not self._used
            and remaining > 0
        )

        return {
            "active": active,
            "used": self._used,
            "expires_in_seconds": remaining,
        }

    def validate(
        self,
        candidate: str | None,
    ) -> bool:
        status = self.status()

        if not status["active"]:
            return False

        provided = str(
            candidate or ""
        ).strip()

        if not provided or self._code is None:
            return False

        valid = secrets.compare_digest(
            provided,
            self._code,
        )

        if valid:
            self._used = True

        return valid
