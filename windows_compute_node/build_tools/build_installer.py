"""Build the MediaHub Windows Compute Node installer."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

WINDOWS_NODE = (
    ROOT
    / "windows_compute_node"
)

INSTALLER_FILE = (
    WINDOWS_NODE
    / "installer"
    / "installer.iss"
)

RELEASE_DIR = (
    ROOT
    / "release"
    / "windows_compute_node"
)


def read_version() -> str:
    namespace: dict[str, object] = {}

    version_file = (
        WINDOWS_NODE
        / "version.py"
    )

    exec(
        version_file.read_text(
            encoding="utf-8-sig",
        ),
        namespace,
    )

    version = str(
        namespace[
            "WINDOWS_COMPUTE_NODE_VERSION"
        ]
    ).strip()

    if not version:
        raise RuntimeError(
            "Windows Compute Node version is empty."
        )

    return version


def find_iscc() -> Path:
    candidates = [
        Path(
            os.environ.get(
                "ProgramFiles(x86)",
                "",
            )
        )
        / "Inno Setup 6"
        / "ISCC.exe",

        Path(
            os.environ.get(
                "ProgramFiles",
                "",
            )
        )
        / "Inno Setup 6"
        / "ISCC.exe",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    found = shutil.which(
        "ISCC.exe"
    )

    if found:
        return Path(found)

    raise RuntimeError(
        "Inno Setup 6 / ISCC.exe wurde "
        "nicht gefunden."
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while chunk := handle.read(
            1024 * 1024
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> int:
    version = read_version()
    iscc = find_iscc()

    print(
        f"Inno Setup: {iscc}"
    )

    subprocess.run(
        [
            str(iscc),
            f"/DMyAppVersion={version}",
            str(INSTALLER_FILE),
        ],
        cwd=ROOT,
        check=True,
    )

    setup = (
        RELEASE_DIR
        / f"MediaHub-Compute-Node_Setup_v{version}.exe"
    )

    if not setup.is_file():
        raise RuntimeError(
            f"Setup wurde nicht erzeugt: {setup}"
        )

    checksum = sha256_file(
        setup
    )

    checksum_file = Path(
        str(setup)
        + ".sha256"
    )

    checksum_file.write_text(
        f"{checksum}  {setup.name}\n",
        encoding="utf-8",
    )

    print(
        f"Setup: {setup}"
    )

    print(
        f"SHA256: {checksum_file}"
    )

    print(
        "Windows Compute Node "
        "Installer erfolgreich gebaut."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
