from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PENDING = ROOT / "RELEASE_NOTES_PENDING.md"
RELEASE_DIR = ROOT / "release"

AI_VERSION_FILE = ROOT / "app" / "version.py"
WINDOWS_VERSION_FILE = ROOT / "windows_compute_node" / "version.py"

LINUX_RELEASE_SCRIPT = ROOT / "release.py"
WINDOWS_BUILD_SCRIPT = (
    ROOT
    / "windows_compute_node"
    / "build_tools"
    / "build_windows.py"
)
WINDOWS_INSTALLER_SCRIPT = (
    ROOT
    / "windows_compute_node"
    / "build_tools"
    / "build_installer.py"
)

ALLOWED_RELEASE_FILES = {
    ".gitignore",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "RELEASE_CHECKLIST.md",
    "RELEASE_NOTES.md",
    "RELEASE_NOTES_PENDING.md",
    "REPOSITORY_SETUP.md",
    "SECURITY.md",
    "THIRD_PARTY_LICENSES.md",
    "install.sh",
    "pyproject.toml",
    "release.py",
    "release_node.cmd",
    "release_node.ps1",
    "release_node.py",
    "requirements.txt",
    "requirements-dev.txt",
}

ALLOWED_RELEASE_ROOTS = (
    ".github/",
    "app/",
    "docs/",
    "examples/",
    "licenses/",
    "migrations/",
    "scripts/",
    "tests/",
    "windows_compute_node/",
)


SKIP_BUILD_TESTS = False


class ReleaseError(RuntimeError):
    pass


def run(
    *args: str,
    capture: bool = False,
) -> str:
    print("> " + " ".join(args))

    result = subprocess.run(
        args,
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )

    if not capture:
        return ""

    return result.stdout.rstrip("\r\n")


def git(
    *args: str,
    capture: bool = False,
) -> str:
    return run(
        "git",
        *args,
        capture=capture,
    )


def read_python_constant(
    path: Path,
    constant_name: str,
) -> str:
    if not path.is_file():
        raise ReleaseError(
            f"Versionsdatei fehlt: {path.relative_to(ROOT)}"
        )

    namespace: dict[str, object] = {}

    exec(
        compile(
            path.read_text(
                encoding="utf-8-sig",
            ),
            str(path),
            "exec",
        ),
        {},
        namespace,
    )

    value = namespace.get(constant_name)

    if not isinstance(value, str):
        raise ReleaseError(
            f"{constant_name} fehlt in "
            f"{path.relative_to(ROOT)}."
        )

    value = value.strip()

    if not value:
        raise ReleaseError(
            f"{constant_name} ist leer."
        )

    return value


def read_ai_version() -> str:
    return read_python_constant(
        AI_VERSION_FILE,
        "APP_VERSION",
    )


def read_windows_version() -> str:
    return read_python_constant(
        WINDOWS_VERSION_FILE,
        "WINDOWS_COMPUTE_NODE_VERSION",
    )


def create_pending_release_notes(
    tag: str,
    ai_version: str,
    windows_version: str,
) -> None:
    content = (
        f"# MediaHub-AI-Node {tag}\n"
        "\n"
        f"## MediaHub-AI-Node {ai_version}\n"
        "\n"
        "- Änderungen für Raspberry Pi / Linux ergänzen.\n"
        "\n"
        f"## Windows Compute Node {windows_version}\n"
        "\n"
        "- Änderungen für Windows Compute Node ergänzen.\n"
    )

    PENDING.write_text(
        content,
        encoding="utf-8",
        newline="\n",
    )

    print("")
    print(
        "[VORBEREITET] RELEASE_NOTES_PENDING.md "
        "wurde neu erstellt."
    )
    print("")
    print(content)

    raise ReleaseError(
        "Release-Notizen wurden vorbereitet. "
        "Bitte RELEASE_NOTES_PENDING.md prüfen und "
        "die Platzhalter durch die echten Änderungen "
        "ersetzen. Danach den Release-Assistenten "
        "erneut starten."
    )


def infer_tag(
    text: str,
    ai_version: str,
) -> str:
    patterns = (
        r"^#\s+MediaHub-AI-Node\s+v?(\d+\.\d+\.\d+)\b",
        r"^#\s+MediaHub AI Node\s+v?(\d+\.\d+\.\d+)\b",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        if match:
            return "v" + match.group(1)

    return "v" + ai_version


def validate_release_notes(
    text: str,
    tag: str,
    ai_version: str,
    windows_version: str,
) -> None:
    if not text.strip():
        raise ReleaseError(
            "RELEASE_NOTES_PENDING.md ist leer."
        )

    if "\ufffd" in text:
        raise ReleaseError(
            "RELEASE_NOTES_PENDING.md enthält "
            "beschädigte Unicode-Zeichen."
        )

    expected_tag = "v" + ai_version

    if tag != expected_tag:
        raise ReleaseError(
            f"Tag {tag} stimmt nicht mit der "
            f"AI-Node-Version {expected_tag} überein."
        )

    if ai_version not in text:
        raise ReleaseError(
            "Die aktuelle AI-Node-Version "
            f"{ai_version} fehlt in "
            "RELEASE_NOTES_PENDING.md."
        )

    if windows_version not in text:
        raise ReleaseError(
            "Die aktuelle Windows-Compute-Node-Version "
            f"{windows_version} fehlt in "
            "RELEASE_NOTES_PENDING.md."
        )


def normalize_status_path(
    raw: str,
) -> str:
    path = raw.replace("\\", "/").strip()

    if " -> " in path:
        path = path.split(" -> ", 1)[1]

    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]

    return path


def is_allowed_release_path(
    path: str,
) -> bool:
    normalized = normalize_status_path(path)

    return (
        normalized in ALLOWED_RELEASE_FILES
        or any(
            normalized.startswith(root)
            for root in ALLOWED_RELEASE_ROOTS
        )
    )


def worktree_entries() -> list[tuple[str, str]]:
    output = git(
        "status",
        "--porcelain=v1",
        "-z",
        capture=True,
    )

    if not output:
        return []

    entries: list[tuple[str, str]] = []
    items = output.split("\0")

    index = 0

    while index < len(items):
        item = items[index]

        if not item:
            index += 1
            continue

        status = item[:2]
        path = item[3:]

        if status[0] in {"R", "C"}:
            index += 1

            if index < len(items):
                path = items[index]

        entries.append(
            (
                status,
                normalize_status_path(path),
            )
        )

        index += 1

    return entries


def ensure_no_pre_staged_changes() -> None:
    entries = worktree_entries()

    staged = [
        f"{status} {path}"
        for status, path in entries
        if status != "??" and status[0] != " "
    ]

    if staged:
        raise ReleaseError(
            "Vor dem Release sind bereits Dateien "
            "im Git-Index gestagt. "
            "Der Release-Assistent übernimmt keine "
            "vorher gestagten Änderungen:\n"
            + "\n".join(staged)
        )

    print(
        "[OK] Keine vorher gestagten Änderungen vorhanden."
    )


def validate_release_worktree() -> None:
    entries = worktree_entries()

    unexpected = [
        f"{status} {path}"
        for status, path in entries
        if not is_allowed_release_path(path)
    ]

    if unexpected:
        raise ReleaseError(
            "Unerwartete Dateien im Arbeitsbaum. "
            "Release wurde gestoppt:\n"
            + "\n".join(unexpected)
        )

    if entries:
        print("")
        print("Offene zulässige Release-Änderungen:")

        for status, path in entries:
            print(
                f"  {status} {path}"
            )

        return

    print(
        "[OK] Keine offenen Projektaenderungen "
        "vor dem Release."
    )


def ensure_branch() -> None:
    branch = git(
        "branch",
        "--show-current",
        capture=True,
    )

    if branch != "main":
        raise ReleaseError(
            f"Release ist nur von main erlaubt. "
            f"Aktueller Branch: {branch or '<detached>'}"
        )


def ensure_remote_is_current() -> None:
    print("")
    print("===== Git-Remote prüfen =====")

    git(
        "fetch",
        "origin",
        "main",
    )

    local = git(
        "rev-parse",
        "HEAD",
        capture=True,
    )

    remote = git(
        "rev-parse",
        "origin/main",
        capture=True,
    )

    if local == remote:
        print(
            "[OK] Lokales HEAD entspricht origin/main."
        )
        return

    merge_base = git(
        "merge-base",
        "HEAD",
        "origin/main",
        capture=True,
    )

    if merge_base == remote:
        print(
            "[OK] Lokaler Branch enthält "
            "noch nicht gepushte Änderungen."
        )
        return

    raise ReleaseError(
        "Lokaler main und origin/main sind "
        "auseinandergelaufen. "
        "Release wurde gestoppt."
    )


def run_checks(
    skip_tests: bool,
) -> None:
    print("")
    print("===== Prüfungen =====")

    run(
        sys.executable,
        "scripts/check_third_party_licenses.py",
    )

    if skip_tests:
        print(
            "[SKIP] Syntax, Tests und Ruff "
            "wurden übersprungen."
        )
        return

    run(
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "app",
        "tests",
        "windows_compute_node",
    )

    run(
        sys.executable,
        "-m",
        "pytest",
    )

    run(
        sys.executable,
        "-m",
        "ruff",
        "check",
        ".",
    )

    run(
        "git",
        "diff",
        "--check",
    )


def build_all() -> None:
    print("")
    print("===== Linux / Raspberry Pi bauen =====")

    linux_command = [
        sys.executable,
        str(LINUX_RELEASE_SCRIPT),
    ]

    if SKIP_BUILD_TESTS:
        linux_command.append("--skip-tests")

    run(
        *linux_command,
    )

    print("")
    print("===== Windows Portable bauen =====")

    run(
        sys.executable,
        str(WINDOWS_BUILD_SCRIPT),
    )

    print("")
    print("===== Windows Setup bauen =====")

    run(
        sys.executable,
        str(WINDOWS_INSTALLER_SCRIPT),
    )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def verify_checksum(
    artifact: Path,
) -> None:
    checksum_file = Path(
        str(artifact) + ".sha256"
    )

    if not checksum_file.is_file():
        raise ReleaseError(
            f"SHA256-Datei fehlt: "
            f"{checksum_file.relative_to(ROOT)}"
        )

    content = checksum_file.read_text(
        encoding="utf-8",
    ).strip()

    expected = sha256_file(
        artifact,
    )

    if not content.startswith(expected):
        raise ReleaseError(
            f"SHA256 stimmt nicht für "
            f"{artifact.name}."
        )


def verify_artifacts(
    ai_version: str,
    windows_version: str,
) -> None:
    print("")
    print("===== Release-Artefakte prüfen =====")

    linux_zip = (
        RELEASE_DIR
        / f"MediaHub-AI-Node_v{ai_version}.zip"
    )

    windows_dir = (
        RELEASE_DIR
        / "windows_compute_node"
    )

    portable = (
        windows_dir
        / (
            "MediaHub-Compute-Node_"
            f"v{windows_version}_Windows_x64.zip"
        )
    )

    setup = (
        windows_dir
        / (
            "MediaHub-Compute-Node_Setup_"
            f"v{windows_version}.exe"
        )
    )

    artifacts = (
        linux_zip,
        portable,
        setup,
    )

    for artifact in artifacts:
        if not artifact.is_file():
            raise ReleaseError(
                f"Release-Artefakt fehlt: "
                f"{artifact.relative_to(ROOT)}"
            )

        if artifact.stat().st_size <= 0:
            raise ReleaseError(
                f"Release-Artefakt ist leer: "
                f"{artifact.relative_to(ROOT)}"
            )

        verify_checksum(
            artifact,
        )

        print(
            "[OK] "
            f"{artifact.relative_to(ROOT)}"
        )

        print(
            "[OK] "
            f"{Path(str(artifact) + '.sha256').relative_to(ROOT)}"
        )


def file_fingerprint(
    path: str,
) -> str:
    target = ROOT / path

    if not target.exists():
        return "<missing>"

    if target.is_dir():
        return "<directory>"

    digest = hashlib.sha256()

    with target.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def snapshot_release_paths(
    paths: set[str],
) -> dict[str, str]:
    return {
        path: file_fingerprint(path)
        for path in sorted(paths)
    }


def ensure_initial_paths_unchanged(
    initial_fingerprints: dict[str, str],
) -> None:
    changed = []

    for path, original in initial_fingerprints.items():
        current = file_fingerprint(path)

        if current != original:
            changed.append(path)

    if changed:
        raise ReleaseError(
            "Bereits beim Start vorhandene Release-Dateien "
            "wurden während des Release-Laufs verändert. "
            "Möglicherweise arbeitet ein anderer Prozess "
            "oder ein anderes Fenster am Repository.\n"
            "Release wurde aus Sicherheitsgründen gestoppt:\n"
            + "\n".join(changed)
        )

    print(
        "[OK] Keine parallelen Änderungen an den "
        "ursprünglichen Release-Dateien erkannt."
    )


def stage_release_changes(
    initial_paths: set[str],
    initial_fingerprints: dict[str, str],
) -> list[str]:
    print("")
    print("===== Release-Dateien stagen =====")

    ensure_no_pre_staged_changes()

    ensure_initial_paths_unchanged(
        initial_fingerprints,
    )

    current_entries = worktree_entries()
    current_paths = {
        path
        for _status, path in current_entries
    }

    new_paths = sorted(
        current_paths - initial_paths
    )

    if new_paths:
        raise ReleaseError(
            "Während des Release-Laufs sind neue "
            "Änderungen aufgetaucht. "
            "Aus Sicherheitsgründen wurde gestoppt:\n"
            + "\n".join(new_paths)
        )

    paths_to_stage = sorted(
        initial_paths & current_paths
    )

    if paths_to_stage:
        git(
            "add",
            "-A",
            "--",
            *paths_to_stage,
        )

    staged_output = git(
        "diff",
        "--cached",
        "--name-only",
        "-z",
        capture=True,
    )

    staged = [
        normalize_status_path(item)
        for item in staged_output.split("\0")
        if item.strip()
    ]

    unexpected = [
        path
        for path in staged
        if not is_allowed_release_path(path)
    ]

    if unexpected:
        git(
            "restore",
            "--staged",
            "--",
            *unexpected,
        )

        raise ReleaseError(
            "Unerwartete Dateien wurden aus dem "
            "Release-Commit entfernt:\n"
            + "\n".join(unexpected)
        )

    return staged


def commit_release_changes(
    tag: str,
    initial_paths: set[str],
    initial_fingerprints: dict[str, str],
) -> None:
    staged = stage_release_changes(
        initial_paths,
        initial_fingerprints,
    )

    if not staged:
        print(
            "Keine Quellcode- oder Release-"
            "Änderungen zu committen."
        )
        return

    print("")
    print("Dateien im Release-Commit:")

    for path in staged:
        print(
            f"  - {path}"
        )

    git(
        "commit",
        "-m",
        f"Prepare MediaHub-AI-Node {tag} release",
    )


def ensure_clean_before_publish() -> None:
    status = git(
        "status",
        "--porcelain",
        capture=True,
    )

    if status:
        raise ReleaseError(
            "Der Arbeitsbaum ist nach dem "
            "Release-Commit nicht sauber:\n"
            + status
        )

    print(
        "[OK] Arbeitsbaum ist nach dem "
        "Release-Commit sauber."
    )


def ensure_tag_is_free(
    tag: str,
) -> None:
    local = git(
        "tag",
        "--list",
        tag,
        capture=True,
    )

    if local:
        raise ReleaseError(
            f"Der Tag {tag} existiert lokal bereits."
        )

    remote = git(
        "ls-remote",
        "--tags",
        "origin",
        f"refs/tags/{tag}",
        capture=True,
    )

    if remote:
        raise ReleaseError(
            f"Der Tag {tag} existiert auf origin bereits."
        )


def show_release_summary(
    tag: str,
    ai_version: str,
    windows_version: str,
    pending_text: str,
) -> None:
    print("")
    print("=" * 68)
    print("LETZTE RELEASE-KONTROLLE")
    print("=" * 68)
    print(f"Release-Tag:              {tag}")
    print(f"Pi/Linux AI Node:         {ai_version}")
    print(f"Windows Compute Node:     {windows_version}")
    print("")
    print("===== RELEASE-NOTIZEN =====")
    print("")
    print(pending_text.rstrip())
    print("")
    print("=" * 68)


def publish(
    tag: str,
) -> None:
    print("")
    print("===== Veröffentlichung =====")

    git(
        "push",
        "origin",
        "main",
    )

    head = git(
        "rev-parse",
        "HEAD",
        capture=True,
    )

    remote = git(
        "rev-parse",
        "origin/main",
        capture=True,
    )

    if head != remote:
        raise ReleaseError(
            "origin/main zeigt nach dem Push "
            "nicht auf HEAD."
        )

    print("")
    print("===== Tag unmittelbar vor Veröffentlichung prüfen =====")

    ensure_tag_is_free(
        tag,
    )

    git(
        "tag",
        "-a",
        tag,
        "-m",
        f"MediaHub-AI-Node {tag}",
    )

    git(
        "push",
        "origin",
        tag,
    )

    tagged = git(
        "rev-list",
        "-n",
        "1",
        tag,
        capture=True,
    )

    if head != tagged:
        raise ReleaseError(
            f"Tag {tag} zeigt nicht auf HEAD."
        )

    print(
        f"Release {tag} wurde erfolgreich "
        "angestoßen."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "MediaHub-AI-Node Release-Assistent"
        )
    )

    parser.add_argument(
        "--tag",
        help="Release-Tag, z. B. v0.8.20",
    )

    parser.add_argument(
        "--skip-tests",
        action="store_true",
    )

    parser.add_argument(
        "--no-push",
        action="store_true",
    )

    parser.add_argument(
        "--yes",
        action="store_true",
    )

    args = parser.parse_args()

    global SKIP_BUILD_TESTS
    SKIP_BUILD_TESTS = args.skip_tests

    print("")
    print("=" * 68)
    print("MediaHub-AI-Node Release-Assistent")
    print("=" * 68)

    ensure_branch()
    ensure_remote_is_current()
    ensure_no_pre_staged_changes()
    validate_release_worktree()

    initial_entries = worktree_entries()
    initial_paths = {
        path
        for _status, path in initial_entries
    }

    initial_fingerprints = snapshot_release_paths(
        initial_paths,
    )

    ai_version = read_ai_version()
    windows_version = read_windows_version()

    if args.tag:
        tag = args.tag
    else:
        tag = "v" + ai_version

    if not tag.startswith("v"):
        tag = "v" + tag

    expected_tag = "v" + ai_version

    if tag != expected_tag:
        raise ReleaseError(
            f"Tag {tag} stimmt nicht mit der "
            f"AI-Node-Version {expected_tag} überein. "
            "Bitte zuerst app/version.py auf die "
            "gewünschte Release-Version setzen."
        )

    ensure_tag_is_free(
        tag,
    )

    if not PENDING.is_file():
        create_pending_release_notes(
            tag,
            ai_version,
            windows_version,
        )

    pending_text = PENDING.read_text(
        encoding="utf-8",
    )

    validate_release_notes(
        pending_text,
        tag,
        ai_version,
        windows_version,
    )

    print("")
    print(f"AI-Node Release:        {tag}")
    print(
        "AI-Node Version:        "
        f"{ai_version}"
    )
    print(
        "Windows Compute Node:   "
        f"{windows_version}"
    )

    run_checks(
        skip_tests=args.skip_tests,
    )

    build_all()

    verify_artifacts(
        ai_version,
        windows_version,
    )

    commit_release_changes(
        tag,
        initial_paths,
        initial_fingerprints,
    )

    ensure_clean_before_publish()

    show_release_summary(
        tag,
        ai_version,
        windows_version,
        pending_text,
    )

    if args.no_push:
        print("")
        print(
            "Lokaler Release-Lauf abgeschlossen "
            "(--no-push)."
        )
        return 0

    if not args.yes:
        print("")

        answer = input(
            f"Release {tag} jetzt veröffentlichen? "
            "Zum Bestätigen RELEASE eingeben: "
        )

        if answer.strip() != "RELEASE":
            raise ReleaseError(
                "Veröffentlichung wurde nicht bestätigt."
            )

    publish(
        tag,
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except subprocess.CalledProcessError as exc:
        print(
            "\nFEHLER: "
            f"Befehl fehlgeschlagen "
            f"({exc.returncode}).",
            file=sys.stderr,
        )

        raise SystemExit(
            exc.returncode
        )

    except KeyboardInterrupt:
        print(
            "\nAbgebrochen.",
            file=sys.stderr,
        )

        raise SystemExit(
            130
        )

    except Exception as exc:
        print(
            f"\nFEHLER: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(
            1
        )
