"""API token handling for the Windows Compute Node."""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

MINIMUM_TOKEN_LENGTH = 32


class NodeApiToken:
    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path = Path(path)

    def load_or_create(self) -> str:
        token = self._load()

        if token:
            return token

        token = secrets.token_urlsafe(48)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "api_token": token,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return token

    def validate(
        self,
        candidate: str | None,
    ) -> bool:
        configured = self.load_or_create()

        provided = str(
            candidate or ""
        ).strip()

        if len(configured) < MINIMUM_TOKEN_LENGTH:
            return False

        if not provided:
            return False

        return secrets.compare_digest(
            provided,
            configured,
        )

    def _load(self) -> str | None:
        if not self.path.is_file():
            return None

        try:
            data: dict[str, Any] = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        token = str(
            data.get("api_token") or ""
        ).strip()

        if len(token) < MINIMUM_TOKEN_LENGTH:
            return None

        return token
