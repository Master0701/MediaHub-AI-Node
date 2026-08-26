"""Python runtime selection for Speech-to-Text."""

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
    pass


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
        data.get("major")
        == SUPPORTED_MAJOR
        and data.get("minor")
        in SUPPORTED_MINORS
        and data.get("bits")
        == "64bit"
    )

    return {
        **data,
        "available": True,
        "supported": supported,
    }


def configured_python() -> Path | None:
    value = os.environ.get(
        "MEDIAHUB_SPEECH_PYTHON"
    )

    if not value:
        return None

    return Path(value)


def private_python() -> Path | None:
    """Return the managed private Speech Python."""

    runtime_base = os.environ.get(
        "MEDIAHUB_COMPUTE_RUNTIME"
    )

    if runtime_base:
        base = Path(runtime_base)
    else:
        base = (
            Path.home()
            / ".mediahub"
            / "compute_node"
        )

    executable = (
        base
        / "private_python"
        / "cpython-3.12.10-x64"
        / "python.exe"
    )

    if not executable.is_file():
        return None

    return executable


def launcher_candidates() -> list[Path]:
    if os.name != "nt":
        return []

    candidates = []

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
            completed.stdout
            or ""
        ).strip()

        if value:
            path = Path(value)

            if path not in candidates:
                candidates.append(path)

    return candidates


def discover_python() -> dict[str, Any]:
    configured = configured_python()

    checked = []

    if configured is not None:
        status = inspect_python(
            configured
        )

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
        status = inspect_python(
            private
        )

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
        status = inspect_python(
            candidate
        )

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
            "preferred_minor": (
                PREFERRED_MINOR
            ),
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
            "Keine kompatible isolierte "
            "Speech-Python-Runtime gefunden. "
            "Bevorzugt wird Python 3.12 x64."
        )

    return Path(
        result["python"]["executable"]
    )
