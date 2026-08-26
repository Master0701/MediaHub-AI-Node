"""Subprocess runner for Speech-to-Text."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent

ENGINE_FILE = (
    PLUGIN_DIR / "engine.py"
)


def load_engine():
    spec = importlib.util.spec_from_file_location(
        "mediahub_runtime_speech_engine",
        ENGINE_FILE,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Speech engine kann nicht "
            "geladen werden."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def main() -> int:
    try:
        raw = sys.stdin.read()

        request = json.loads(
            raw
        )

        engine = load_engine()

        result = engine.transcribe(
            input_path=request[
                "input_path"
            ],
            execution=dict(
                request.get(
                    "execution"
                )
                or {}
            ),
            options=dict(
                request.get(
                    "options"
                )
                or {}
            ),
        )

        response = {
            "ok": True,
            "result": result,
        }

        sys.stdout.write(
            json.dumps(
                response,
                ensure_ascii=False,
            )
        )

        return 0

    except Exception as exc:
        response = {
            "ok": False,
            "error": {
                "type": (
                    type(exc).__name__
                ),
                "message": str(exc),
            },
        }

        sys.stdout.write(
            json.dumps(
                response,
                ensure_ascii=False,
            )
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
