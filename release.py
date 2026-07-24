#!/usr/bin/env python3
"""Prüft MediaHub-AI-Node und erstellt Release-ZIP und SHA-256-Datei.

Dieses Skript führt keine Git-Commits, Pushes oder Tag-Erstellung aus.
Es ist für den lokalen Aufruf und für GitHub Actions vorgesehen.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RELEASE_DIR = ROOT / "release"
PROJECT_NAME = "MediaHub-AI-Node"

INCLUDED = (
    "app",
    "docs",
    "examples",
    "licenses",
    "migrations",
    "scripts",
    ".env.example",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "RELEASE_NOTES_PENDING.md",
    "REPOSITORY_SETUP.md",
    "SECURITY.md",
    "THIRD_PARTY_LICENSES.md",
    "init_database.py",
    "pyproject.toml",
    "requirements.txt",
)

EXCLUDED_DIRS = {
    ".git", ".github", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "build", "dist",
    "release", "data", "cache", "logs", "runtime", "jobs", "backups",
    "models", "node_modules",
}

EXCLUDED_SUFFIXES = {
    ".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".key", ".pem",
}


class ReleaseError(RuntimeError):
    pass


def run_check(command: list[str], label: str) -> None:
    print(f"\n== {label} ==")
    print("> " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise ReleaseError(
            f"{label} fehlgeschlagen (Exit-Code {result.returncode})."
        )


def read_version() -> str:
    version_file = ROOT / "app" / "version.py"
    if not version_file.is_file():
        raise ReleaseError("app/version.py wurde nicht gefunden.")

    namespace: dict[str, object] = {}
    exec(
        compile(
            version_file.read_text(encoding="utf-8"),
            str(version_file),
            "exec",
        ),
        {},
        namespace,
    )

    version = namespace.get("APP_VERSION")
    if not isinstance(version, str) or not version.strip():
        raise ReleaseError("APP_VERSION fehlt in app/version.py.")
    return version.strip()


def check_required_files() -> None:
    required = (
        "app",
        "licenses",
        "LICENSE",
        "README.md",
        "SECURITY.md",
        "THIRD_PARTY_LICENSES.md",
        "pyproject.toml",
        "requirements.txt",
    )
    missing = [name for name in required if not (ROOT / name).exists()]
    if missing:
        raise ReleaseError(
            "Erforderliche Dateien fehlen: " + ", ".join(missing)
        )


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.startswith(".env") and path.name != ".env.example":
        return False
    return path.is_file()


def collect_files() -> list[Path]:
    files: set[Path] = set()

    for name in INCLUDED:
        item = ROOT / name
        if not item.exists():
            continue

        if item.is_file():
            if should_include(item):
                files.add(item)
        else:
            for path in item.rglob("*"):
                if should_include(path):
                    files.add(path)

    if not files:
        raise ReleaseError("Keine Dateien für das Release gefunden.")

    return sorted(files, key=lambda p: p.as_posix().lower())


def create_zip(version: str, files: list[Path]) -> Path:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = RELEASE_DIR / f"{PROJECT_NAME}_v{version}.zip"
    package_root = f"{PROJECT_NAME}_v{version}"

    if archive_path.exists():
        archive_path.unlink()

    print("\n== Release-Paket erstellen ==")
    print(f"Zieldatei: {archive_path.relative_to(ROOT)}")
    print(f"Dateien: {len(files)}")

    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source in files:
            relative = source.relative_to(ROOT)
            archive.write(
                source,
                (Path(package_root) / relative).as_posix(),
            )

    if not archive_path.is_file() or archive_path.stat().st_size == 0:
        raise ReleaseError("ZIP-Datei wurde nicht korrekt erstellt.")

    return archive_path


def create_sha256(archive_path: Path) -> Path:
    digest = hashlib.sha256()
    with archive_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    checksum_path = archive_path.with_suffix(".zip.sha256")
    checksum_path.write_text(
        f"{digest.hexdigest()}  {archive_path.name}\n",
        encoding="utf-8",
        newline="\n",
    )
    return checksum_path


def verify_zip(archive_path: Path) -> None:
    print("\n== ZIP-Archiv prüfen ==")
    with zipfile.ZipFile(archive_path, "r") as archive:
        broken = archive.testzip()
        names = archive.namelist()

    if broken:
        raise ReleaseError(f"Beschädigter ZIP-Eintrag: {broken}")
    if not any(name.endswith("/app/main.py") for name in names):
        raise ReleaseError("app/main.py fehlt im ZIP.")
    if not any(name.endswith("/LICENSE") for name in names):
        raise ReleaseError("LICENSE fehlt im ZIP.")

    print("ZIP-Archiv ist vollständig und lesbar.")


def main() -> int:
    try:
        print("MediaHub-AI-Node – Release-Prüfung und Paketbau")
        print(f"Projektordner: {ROOT}")

        version = read_version()
        print(f"Version: {version}")

        check_required_files()

        run_check(
            [sys.executable, "-m", "compileall", "-q", "app", "tests"],
            "Python-Syntax prüfen",
        )
        run_check(
            [sys.executable, "-m", "pytest"],
            "Tests ausführen",
        )
        run_check(
            [sys.executable, "-m", "ruff", "check", "."],
            "Ruff-Codeprüfung",
        )

        if RELEASE_DIR.exists():
            shutil.rmtree(RELEASE_DIR)
        RELEASE_DIR.mkdir(parents=True, exist_ok=True)

        files = collect_files()
        archive = create_zip(version, files)
        checksum = create_sha256(archive)
        verify_zip(archive)

        print("\n" + "=" * 68)
        print("RELEASE-PAKET ERFOLGREICH ERSTELLT")
        print(f"ZIP:    {archive.relative_to(ROOT)}")
        print(f"SHA256: {checksum.relative_to(ROOT)}")
        print(f"Größe:  {archive.stat().st_size:,} Bytes")
        print("=" * 68)
        return 0

    except ReleaseError as exc:
        print(f"\nFEHLER: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(
            f"\nUNERWARTETER FEHLER: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
