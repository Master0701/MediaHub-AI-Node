"""Bridge to the isolated Speech runtime."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class SpeechRuntimeBridgeError(
    RuntimeError
):
    pass



def _runtime_site_packages(
    runtime_python: Path,
) -> Path:
    """Return site-packages of managed Python."""

    return (
        runtime_python.parent
        / "Lib"
        / "site-packages"
    )


def _cuda_runtime_directories(
    runtime_python: Path,
) -> list[Path]:
    """Return private NVIDIA DLL directories."""

    site = _runtime_site_packages(
        runtime_python
    )

    return [
        site
        / "nvidia"
        / "cublas"
        / "bin",

        site
        / "nvidia"
        / "cudnn"
        / "bin",

        site
        / "nvidia"
        / "cuda_runtime"
        / "bin",
    ]


def _subprocess_environment(
    *,
    runtime_python: Path,
    execution: dict[str, Any],
) -> dict[str, str]:
    """Build environment for Speech runtime."""

    environment = os.environ.copy()

    backend = str(
        execution.get(
            "backend",
            "cpu",
        )
    ).strip().lower()

    if backend != "cuda":
        return environment

    directories = [
        directory
        for directory
        in _cuda_runtime_directories(
            runtime_python
        )
        if directory.is_dir()
    ]

    if not directories:
        return environment

    prefix = os.pathsep.join(
        str(directory)
        for directory in directories
    )

    old_path = environment.get(
        "PATH",
        "",
    )

    environment["PATH"] = (
        prefix
        if not old_path
        else prefix
        + os.pathsep
        + old_path
    )

    return environment


def run_transcription(
    *,
    runtime_python: str | Path,
    runner_path: str | Path,
    input_path: str | Path,
    execution: dict[str, Any],
    options: dict[str, Any] | None = None,
    timeout: int = 3600,
) -> dict[str, Any]:

    runtime_python = Path(
        runtime_python
    )

    runner_path = Path(
        runner_path
    )

    if not runtime_python.is_file():
        raise SpeechRuntimeBridgeError(
            "Runtime-Python nicht gefunden: "
            f"{runtime_python}"
        )

    if not runner_path.is_file():
        raise SpeechRuntimeBridgeError(
            "Runtime-Runner nicht gefunden: "
            f"{runner_path}"
        )

    request = {
        "input_path": str(
            input_path
        ),
        "execution": dict(
            execution
        ),
        "options": dict(
            options or {}
        ),
    }

    completed = subprocess.run(
        [
            str(runtime_python),
            str(runner_path),
        ],
        input=json.dumps(
            request,
            ensure_ascii=False,
        ),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout,
        check=False,
        env=_subprocess_environment(
            runtime_python=runtime_python,
            execution=execution,
        ),
    )

    stdout = (
        completed.stdout or ""
    ).strip()

    if not stdout:
        raise SpeechRuntimeBridgeError(
            "Speech-Runtime lieferte "
            "keine JSON-Antwort. "
            f"stderr={completed.stderr!r}"
        )

    try:
        response = json.loads(
            stdout
        )
    except json.JSONDecodeError as exc:
        raise SpeechRuntimeBridgeError(
            "Ungueltige JSON-Antwort "
            "der Speech-Runtime."
        ) from exc

    if not response.get("ok"):
        error = dict(
            response.get("error")
            or {}
        )

        raise SpeechRuntimeBridgeError(
            "Speech-Runtime-Fehler: "
            f"{error.get('type', 'Error')}: "
            f"{error.get('message', '')}"
        )

    if completed.returncode != 0:
        raise SpeechRuntimeBridgeError(
            "Speech-Runtime endete mit "
            f"Code {completed.returncode}."
        )

    result = response.get(
        "result"
    )

    if not isinstance(
        result,
        dict,
    ):
        raise SpeechRuntimeBridgeError(
            "Speech-Runtime lieferte "
            "kein Ergebnisobjekt."
        )

    return result


def current_python() -> Path:
    """Only for tests/mock execution."""
    return Path(sys.executable)
