"""pip bootstrap for the private Speech Python runtime."""

from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

GET_PIP_URL = (
    "https://bootstrap.pypa.io/get-pip.py"
)


class PipBootstrapError(RuntimeError):
    pass


def validate_bootstrap_url(
    url: str = GET_PIP_URL,
) -> None:
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme.lower() != "https":
        raise PipBootstrapError(
            "pip-Bootstrap muss HTTPS verwenden."
        )

    if parsed.hostname != "bootstrap.pypa.io":
        raise PipBootstrapError(
            "pip-Bootstrap darf nur von "
            "bootstrap.pypa.io geladen werden."
        )

    if parsed.path != "/get-pip.py":
        raise PipBootstrapError(
            "Unerwarteter get-pip.py-Pfad."
        )


def inspect_pip(
    python_executable: str | Path,
) -> dict[str, Any]:
    python_executable = Path(
        python_executable
    )

    if not python_executable.is_file():
        return {
            "available": False,
            "python": str(
                python_executable
            ),
            "pip": False,
        }

    completed = subprocess.run(
        [
            str(python_executable),
            "-m",
            "pip",
            "--version",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    return {
        "available": True,
        "python": str(
            python_executable
        ),
        "pip": (
            completed.returncode == 0
        ),
        "returncode": (
            completed.returncode
        ),
        "stdout": (
            completed.stdout or ""
        ).strip(),
        "stderr": (
            completed.stderr or ""
        ).strip(),
    }


def download_get_pip(
    destination: str | Path,
    *,
    url: str = GET_PIP_URL,
) -> Path:
    validate_bootstrap_url(url)

    destination = Path(
        destination
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_suffix(
        destination.suffix + ".part"
    )

    if temporary.exists():
        temporary.unlink()

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "MediaHub-Compute-Node/"
                "Speech-Runtime"
            ),
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:

            final_url = response.geturl()

            validate_bootstrap_url(
                final_url
            )

            data = response.read()

        if not data:
            raise PipBootstrapError(
                "Leere get-pip.py-Datei."
            )

        # Minimaler Plausibilitaetscheck:
        # Wir akzeptieren keine HTML-Fehlerseite.
        head = data[:512].lower()

        if b"<html" in head:
            raise PipBootstrapError(
                "get-pip.py-Download "
                "enthaelt HTML."
            )

        temporary.write_bytes(data)

        temporary.replace(
            destination
        )

    except Exception:
        if temporary.exists():
            temporary.unlink()

        raise

    return destination


def bootstrap_pip(
    python_executable: str | Path,
    bootstrap_file: str | Path,
) -> dict[str, Any]:
    python_executable = Path(
        python_executable
    )

    bootstrap_file = Path(
        bootstrap_file
    )

    before = inspect_pip(
        python_executable
    )

    if before.get("pip"):
        return {
            "installed": True,
            "changed": False,
            "status": before,
        }

    if not bootstrap_file.is_file():
        raise PipBootstrapError(
            "get-pip.py wurde nicht gefunden."
        )

    completed = subprocess.run(
        [
            str(python_executable),
            str(bootstrap_file),
            "--disable-pip-version-check",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    if completed.returncode != 0:
        raise PipBootstrapError(
            "pip-Installation fehlgeschlagen:\n"
            + (
                completed.stderr
                or completed.stdout
                or "Unbekannter Fehler"
            ).strip()
        )

    after = inspect_pip(
        python_executable
    )

    if not after.get("pip"):
        raise PipBootstrapError(
            "pip wurde nach Bootstrap "
            "nicht gefunden."
        )

    return {
        "installed": True,
        "changed": True,
        "status": after,
    }


def status_json(
    python_executable: str | Path,
) -> str:
    return json.dumps(
        inspect_pip(
            python_executable
        ),
        indent=2,
        ensure_ascii=False,
    )
