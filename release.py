#!/usr/bin/env python3
"""Release-Assistent für MediaHub-AI-Node.

Ablauf:
1. Repository und Werkzeuge prüfen
2. Version aus pyproject.toml lesen
3. Tests und Sicherheitsprüfungen ausführen
4. Änderungen committen und nach main pushen
5. Annotierten Versions-Tag erstellen und pushen
6. GitHub Actions erstellt daraus das Release-Paket

Aufruf:
    python release.py
    python release.py --message "MediaHub-AI-Node v0.1.0"
    python release.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_NAME = "MediaHub-AI-Node"
DEFAULT_BRANCH = "main"
DEFAULT_REMOTE = "origin"

ROOT = Path(__file__).resolve().parent
PYPROJECT = ROOT / "pyproject.toml"

SECRET_PATTERN = re.compile(
    r"""(?ix)
    (api[_-]?key|access[_-]?token|secret|password|passwd)\s*
    [:=]\s*
    ["']?([A-Za-z0-9_\-./+=]{8,})
    """
)

IGNORED_SECRET_PATHS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
}


class ReleaseError(RuntimeError):
    """Kontrollierter Abbruch des Release-Ablaufs."""


def run(
    *command: str,
    check: bool = True,
    capture: bool = False,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    print(f"\n> {printable}")

    if dry_run:
        return subprocess.CompletedProcess(command, 0, "", "")

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=False,
    )

    if capture and result.stdout:
        print(result.stdout.rstrip())
    if capture and result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)

    if check and result.returncode != 0:
        raise ReleaseError(
            f"Befehl fehlgeschlagen ({result.returncode}): {printable}"
        )
    return result


def output(*command: str) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseError(
            result.stderr.strip() or f"Befehl fehlgeschlagen: {' '.join(command)}"
        )
    return result.stdout.strip()


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise ReleaseError(f"Benötigtes Werkzeug nicht gefunden: {name}")


def read_version() -> str:
    if not PYPROJECT.is_file():
        raise ReleaseError("pyproject.toml wurde nicht gefunden.")

    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(
        r'(?ms)^\[project\].*?^version\s*=\s*"([^"]+)"',
        text,
    )
    if not match:
        raise ReleaseError(
            'Keine Projektversion unter [project] in pyproject.toml gefunden.'
        )

    version = match.group(1).strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[A-Za-z0-9._-]+)?", version):
        raise ReleaseError(f"Ungültiges Versionsformat: {version}")

    return version


def check_repository() -> None:
    if not (ROOT / ".git").exists():
        raise ReleaseError(f"{ROOT} ist kein Git-Repository.")

    branch = output("git", "branch", "--show-current")
    if branch != DEFAULT_BRANCH:
        raise ReleaseError(
            f"Aktueller Branch ist '{branch}'. Release nur von '{DEFAULT_BRANCH}'."
        )

    remote_url = output("git", "remote", "get-url", DEFAULT_REMOTE)
    if "MediaHub-AI-Node" not in remote_url:
        raise ReleaseError(
            f"Unerwartetes Git-Remote '{DEFAULT_REMOTE}': {remote_url}"
        )

    run("git", "fetch", DEFAULT_REMOTE, DEFAULT_BRANCH)

    local_head = output("git", "rev-parse", "HEAD")
    remote_head = output(
        "git", "rev-parse", f"{DEFAULT_REMOTE}/{DEFAULT_BRANCH}"
    )
    merge_base = output(
        "git", "merge-base", "HEAD", f"{DEFAULT_REMOTE}/{DEFAULT_BRANCH}"
    )

    if merge_base != remote_head and local_head != remote_head:
        raise ReleaseError(
            "Lokaler Stand und GitHub-Stand sind auseinander gelaufen. "
            "Bitte zuerst sauber synchronisieren."
        )


def scan_for_secrets() -> None:
    print("\nPrüfe versionierte Dateien auf mögliche Zugangsdaten ...")
    files = output("git", "ls-files").splitlines()
    findings: list[str] = []

    for relative in files:
        path = ROOT / relative
        if any(part in IGNORED_SECRET_PATHS for part in path.parts):
            continue
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if SECRET_PATTERN.search(line):
                lowered = line.lower()
                if any(
                    marker in lowered
                    for marker in (
                        "example",
                        "placeholder",
                        "change-me",
                        "your_",
                        "test",
                        "dummy",
                    )
                ):
                    continue
                findings.append(f"{relative}:{line_number}: {line.strip()[:160]}")

    if findings:
        print("\nMögliche Zugangsdaten gefunden:")
        for finding in findings:
            print(f"  - {finding}")
        raise ReleaseError(
            "Release aus Sicherheitsgründen abgebrochen. Fundstellen prüfen."
        )

    print("Keine offensichtlichen Zugangsdaten gefunden.")


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode == 0:
        return True

    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--tags", DEFAULT_REMOTE, tag],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def run_checks(dry_run: bool) -> None:
    run(sys.executable, "-m", "compileall", "-q", "app", "tests", dry_run=dry_run)
    run(sys.executable, "-m", "pytest", dry_run=dry_run)

    if shutil.which("ruff"):
        run("ruff", "check", ".", dry_run=dry_run)
    else:
        print("\nHinweis: ruff ist nicht installiert; Ruff-Prüfung wird übersprungen.")


def confirm_release(version: str, tag: str, message: str) -> None:
    print("\n" + "=" * 64)
    print(f"Projekt : {PROJECT_NAME}")
    print(f"Version : {version}")
    print(f"Tag     : {tag}")
    print(f"Branch  : {DEFAULT_BRANCH}")
    print(f"Commit  : {message}")
    print("=" * 64)

    answer = input(
        '\nZum Veröffentlichen exakt "RELEASE" eingeben: '
    ).strip()
    if answer != "RELEASE":
        raise ReleaseError("Release vom Benutzer abgebrochen.")


def create_release(
    version: str,
    message: str,
    skip_tests: bool,
    yes: bool,
    dry_run: bool,
) -> None:
    tag = f"v{version}"

    require_tool("git")
    check_repository()

    if tag_exists(tag):
        raise ReleaseError(
            f"Der Tag {tag} existiert bereits lokal oder auf GitHub."
        )

    if not skip_tests:
        run_checks(dry_run=dry_run)

    scan_for_secrets()

    status = output("git", "status", "--porcelain")
    if not status:
        print("\nKeine ungespeicherten Änderungen vorhanden.")
        print("Es wird der aktuelle Commit getaggt.")
    else:
        print("\nFolgende Änderungen werden veröffentlicht:")
        print(status)

    if not yes and not dry_run:
        confirm_release(version, tag, message)

    if status:
        run("git", "add", "--all", dry_run=dry_run)
        run("git", "commit", "-m", message, dry_run=dry_run)

    run("git", "push", DEFAULT_REMOTE, DEFAULT_BRANCH, dry_run=dry_run)
    run(
        "git",
        "tag",
        "-a",
        tag,
        "-m",
        f"{PROJECT_NAME} {tag}",
        dry_run=dry_run,
    )
    run("git", "push", DEFAULT_REMOTE, tag, dry_run=dry_run)

    print("\n" + "=" * 64)
    if dry_run:
        print("Trockenlauf erfolgreich. Es wurde nichts verändert.")
    else:
        print(f"Release {tag} wurde angestoßen.")
        print("GitHub Actions erstellt nun Release-Paket und SHA-256-Prüfsumme.")
    print("=" * 64)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"{PROJECT_NAME} prüfen, committen, taggen und veröffentlichen."
    )
    parser.add_argument(
        "--message",
        help="Eigene Git-Commit-Nachricht.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Tests überspringen (nicht empfohlen).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Bestätigungsabfrage überspringen.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ablauf prüfen, ohne Git zu verändern.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        version = read_version()
        message = args.message or f"Release {PROJECT_NAME} v{version}"
        create_release(
            version=version,
            message=message,
            skip_tests=args.skip_tests,
            yes=args.yes,
            dry_run=args.dry_run,
        )
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 130
    except ReleaseError as exc:
        print(f"\nFEHLER: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
