"""Build the standalone Windows Compute Node executable."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WINDOWS_NODE = ROOT / "windows_compute_node"

SPEC_FILE = (
    WINDOWS_NODE
    / "MediaHubComputeNode.spec"
)

BUILD_DIR = (
    ROOT
    / "build"
    / "windows_compute_node"
)

DIST_DIR = (
    ROOT
    / "dist"
    / "windows_compute_node"
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


def require_pyinstaller() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--version",
        ],
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "PyInstaller ist nicht installiert. "
            "Installiere es mit: "
            "python -m pip install pyinstaller"
        )


def clean() -> None:
    for path in (
        BUILD_DIR,
        DIST_DIR,
        RELEASE_DIR,
    ):
        if path.exists():
            shutil.rmtree(path)

    BUILD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    DIST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RELEASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def build_executable() -> Path:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--workpath",
        str(BUILD_DIR),
        "--distpath",
        str(DIST_DIR),
        str(SPEC_FILE),
    ]

    subprocess.run(
        command,
        cwd=ROOT,
        check=True,
    )

    executable = (
        DIST_DIR
        / "MediaHub-Compute-Node.exe"
    )

    if not executable.is_file():
        raise RuntimeError(
            f"EXE wurde nicht erzeugt: "
            f"{executable}"
        )

    return executable


def build_portable_package(
    executable: Path,
    version: str,
) -> Path:
    package_name = (
        "MediaHub-Compute-Node_"
        f"v{version}_Windows_x64"
    )

    staging = (
        BUILD_DIR
        / package_name
    )

    staging.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        executable,
        staging
        / executable.name,
    )

    # Portable installations use their runtime
    # directory beside the executable.
    (
        staging
        / "runtime"
    ).mkdir(
        parents=True,
        exist_ok=True,
    )

    zip_path = (
        RELEASE_DIR
        / f"{package_name}.zip"
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for file_path in staging.rglob("*"):
            if not file_path.is_file():
                continue

            archive.write(
                file_path,
                file_path.relative_to(
                    staging.parent
                ),
            )

    checksum = sha256_file(
        zip_path
    )

    (
        Path(
            str(zip_path)
            + ".sha256"
        )
    ).write_text(
        f"{checksum}  "
        f"{zip_path.name}\n",
        encoding="utf-8",
    )

    return zip_path


def main() -> int:
    version = read_version()

    print(
        "MediaHub Windows Compute Node "
        f"v{version}"
    )

    require_pyinstaller()
    clean()

    executable = build_executable()

    print(
        f"EXE: {executable}"
    )

    portable = build_portable_package(
        executable,
        version,
    )

    print(
        f"Portable ZIP: {portable}"
    )

    print(
        "Windows Compute Node Build "
        "erfolgreich."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
