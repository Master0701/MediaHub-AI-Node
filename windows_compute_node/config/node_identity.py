"""Persistent identity for a Windows Compute Node."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


class NodeIdentity:
    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path = Path(path)

    def load_or_create(
        self,
    ) -> dict[str, Any]:
        existing = self._load()

        if existing is not None:
            return existing

        identity = {
            "schema_version": 1,
            "node_id": str(uuid.uuid4()),
        }

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            json.dumps(
                identity,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return identity

    def _load(
        self,
    ) -> dict[str, Any] | None:
        if not self.path.is_file():
            return None

        try:
            data = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        node_id = str(
            data.get("node_id") or ""
        ).strip()

        if not node_id:
            return None

        return data
