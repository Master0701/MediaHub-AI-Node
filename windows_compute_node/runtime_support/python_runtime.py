"""Shared Python runtime selection for MediaHub Windows Compute Node."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

SUPPORTED_MAJOR = 3
SUPPORTED_MINORS = (12, 11, 10, 9)
PREFERRED_MINOR = 12


class RuntimePythonError(RuntimeError):
    """Raised when no compatible Python runtime is available."""


def inspect_python(
    executable: str | Path,
) -> dict[str, Any]:
    executable = Path(executable)

    if not executable.is_file():
        return {
            "executable": str(executable),
            "available": False,
            "supported": False,
        }

    code = (
        "import json,platform,sys;"
        "print(json.dumps({"
        "'major':sys.version_info.major,"
        "'minor':sys.version_info.minor,"
        "'micro':sys.version_info.micro,"
        "'bits':platform.architecture()[0],"
        "'executable':sys.executable"
        "}))"
    )

    completed = subprocess.run(
        [
            str(executable),
            "-c",
            code,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    if completed.returncode != 0:
        return {
            "executable": str(executable),
            "available": True,
            "supported": False,
            "error": (
                completed.stderr or ""
            ).strip(),
        }

    try:
        data = json.loads(
            completed.stdout.strip()
        )
    except Exception as exc:
        return {
            "executable": str(executable),
            "available": True,
            "supported": False,
            "error": str(exc),
        }

    supported = (
        data.get("major") == SUPPORTED_MAJOR
        and data.get("minor") in SUPPORTED_MINORS
        and data.get("bits") == "64bit"
    )

    return {
        **data,
        "available": True,
        "supported": supported,
    }


def configured_python() -> Path | None:
    # New generic override.
    value = os.environ.get(
        "MEDIAHUB_COMPUTE_PYTHON"
    )

    # Backward compatibility with the existing Speech setup.
    if not value:
        value = os.environ.get(
            "MEDIAHUB_SPEECH_PYTHON"
        )

    if not value:
        return None

    return Path(value)


def private_python() -> Path | None:
    """Return a verified private Python from configured or user runtime roots."""
    configured = os.environ.get("MEDIAHUB_COMPUTE_RUNTIME")
    roots = []
    if configured:
        roots.append(Path(configured))
    user_root = Path.home() / ".mediahub" / "compute_node"
    if user_root not in roots:
        roots.append(user_root)

    for base in roots:
        for directory in (
            "cpython-3.12.10-x64-astral-20250409",
            "cpython-3.12.10-x64",
        ):
            executable = base / "private_python" / directory / "python.exe"
            if executable.is_file() and inspect_managed_python(executable).get("ready"):
                return executable
    return None


def launcher_candidates() -> list[Path]:
    if os.name != "nt":
        return []

    candidates: list[Path] = []

    for minor in SUPPORTED_MINORS:
        completed = subprocess.run(
            [
                "py",
                f"-3.{minor}",
                "-c",
                (
                    "import sys;"
                    "print(sys.executable)"
                ),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            check=False,
        )

        if completed.returncode != 0:
            continue

        value = (
            completed.stdout or ""
        ).strip()

        if value:
            path = Path(value)

            if path not in candidates:
                candidates.append(path)

    return candidates


def discover_python() -> dict[str, Any]:
    configured = configured_python()
    checked: list[dict[str, Any]] = []

    if configured is not None:
        status = inspect_python(configured)
        checked.append(status)

        if status.get("supported"):
            return {
                "found": True,
                "source": "configured",
                "python": status,
                "checked": checked,
            }

    private = private_python()

    if private is not None:
        status = inspect_python(private)
        status["managed"] = True
        checked.append(status)

        if status.get("supported"):
            return {
                "found": True,
                "source": "mediahub_private",
                "python": status,
                "checked": checked,
            }

    for candidate in launcher_candidates():
        status = inspect_python(candidate)
        checked.append(status)

        if status.get("supported"):
            return {
                "found": True,
                "source": "launcher",
                "python": status,
                "checked": checked,
            }

    return {
        "found": False,
        "source": None,
        "python": None,
        "checked": checked,
        "required": {
            "major": SUPPORTED_MAJOR,
            "preferred_minor": PREFERRED_MINOR,
            "supported_minors": list(
                SUPPORTED_MINORS
            ),
            "architecture": "64bit",
        },
    }


def require_python() -> Path:
    result = discover_python()

    if not result["found"]:
        raise RuntimePythonError(
            "Keine kompatible isolierte MediaHub-"
            "Python-Runtime gefunden. "
            "Bevorzugt wird Python 3.12 x64."
        )

    return Path(
        result["python"]["executable"]
    )


def inspect_managed_python(
    executable: str | Path | None = None,
) -> dict[str, Any]:
    """Check the managed portable CPython 3.12.10 x64 runtime."""
    if executable is None:
        base = os.environ.get("MEDIAHUB_COMPUTE_RUNTIME")
        root = (
            Path(base)
            if base
            else Path.home() / ".mediahub" / "compute_node"
        )
        executable = (
            root / "private_python" / "cpython-3.12.10-x64-astral-20250409" / "python.exe"
            if base
            else (
                private_python()
                or root / "private_python" / "cpython-3.12.10-x64-astral-20250409" / "python.exe"
            )
        )

    python = Path(executable)
    result: dict[str, Any] = {
        "executable": str(python),
        "available": python.is_file(),
        "ready": False,
    }
    if not result["available"]:
        return result

    code = (
        "import sys, venv, ensurepip; "
        "assert sys.version_info[:3] == (3, 12, 10); "
        "assert sys.maxsize > 2**32"
    )
    try:
        completed = subprocess.run(
            [str(python), "-I", "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        result["ready"] = completed.returncode == 0
        if not result["ready"]:
            result["error"] = (
                completed.stderr.strip()
                or f"Python-Pruefung fehlgeschlagen: {completed.returncode}"
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)

    return result
