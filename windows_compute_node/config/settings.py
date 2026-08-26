"""Persistent settings for the Windows Compute Node."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "schema_version": 1,
    "node_name": "MediaHub Compute Node",
    "listen_host": "0.0.0.0",
    "listen_port": 8766,
    "execution": {
        "default_mode": "auto",
        "cpu_threads": "auto",
        "gpu_device": "auto",
    },
    "connection": {
        "require_authentication": True,
        "allow_remote_jobs": True,
    },
}


class NodeSettings:
    def __init__(
        self,
        path: Path,
    ) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.is_file():
            data = self._copy_defaults()
            self.save(data)
            return data

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
            data = self._copy_defaults()
            self.save(data)
            return data

        return self._merge_defaults(data)

    def save(
        self,
        data: dict[str, Any],
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _copy_defaults() -> dict[str, Any]:
        return json.loads(
            json.dumps(DEFAULT_SETTINGS)
        )

    def _merge_defaults(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        merged = self._copy_defaults()

        for key, value in data.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key].update(value)
            else:
                merged[key] = value

        return merged
