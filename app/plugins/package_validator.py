"""Prüfung von AI-Plugin-ZIP-Paketen vor einer späteren Installation."""

from __future__ import annotations

import hashlib
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from app.plugins.errors import PluginError
from app.plugins.manifest import PluginManifest

DEFAULT_MAX_ARCHIVE_SIZE = 512 * 1024 * 1024
DEFAULT_MAX_UNCOMPRESSED_SIZE = 2 * 1024 * 1024 * 1024
DEFAULT_MAX_FILE_COUNT = 5000


class PluginPackageError(PluginError):
    """Ein Plugin-Paket ist beschädigt oder unsicher."""


@dataclass(frozen=True, slots=True)
class ValidatedPluginPackage:
    """Ergebnis einer erfolgreichen Paketprüfung."""

    archive_path: Path
    sha256: str
    manifest: PluginManifest
    root_directory: str
    file_count: int
    uncompressed_size: int


def calculate_sha256(path: Path) -> str:
    """Berechnet die SHA-256-Prüfsumme einer Datei."""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_plugin_package(
    archive_path: Path,
    *,
    expected_sha256: str | None = None,
    max_archive_size: int = DEFAULT_MAX_ARCHIVE_SIZE,
    max_uncompressed_size: int = DEFAULT_MAX_UNCOMPRESSED_SIZE,
    max_file_count: int = DEFAULT_MAX_FILE_COUNT,
) -> ValidatedPluginPackage:
    """Prüft Integrität, Pfade, Größen und Manifest eines Plugin-ZIPs."""

    archive_path = archive_path.resolve()

    if not archive_path.is_file():
        raise PluginPackageError(
            f"Plugin-Paket wurde nicht gefunden: {archive_path}"
        )

    archive_size = archive_path.stat().st_size
    if archive_size <= 0:
        raise PluginPackageError("Das Plugin-Paket ist leer.")

    if archive_size > max_archive_size:
        raise PluginPackageError(
            "Das Plugin-Paket überschreitet die erlaubte Archivgröße."
        )

    actual_sha256 = calculate_sha256(archive_path)
    if expected_sha256:
        normalized_expected = expected_sha256.strip().lower()
        if actual_sha256 != normalized_expected:
            raise PluginPackageError(
                "Die SHA-256-Prüfsumme des Plugin-Pakets stimmt nicht."
            )

    try:
        with ZipFile(archive_path) as archive:
            entries = archive.infolist()

            if not entries:
                raise PluginPackageError("Das Plugin-Paket enthält keine Dateien.")

            if len(entries) > max_file_count:
                raise PluginPackageError(
                    "Das Plugin-Paket enthält zu viele Dateien."
                )

            total_size = sum(entry.file_size for entry in entries)
            if total_size > max_uncompressed_size:
                raise PluginPackageError(
                    "Der entpackte Paketinhalt überschreitet die Größenbegrenzung."
                )

            safe_paths = [
                _validate_archive_entry(entry.filename, entry.external_attr)
                for entry in entries
            ]

            root_directory = _find_single_root_directory(safe_paths)
            manifest_name = PurePosixPath(root_directory) / "plugin.json"

            try:
                manifest_data = archive.read(str(manifest_name))
            except KeyError as exc:
                raise PluginPackageError(
                    "Im obersten Plugin-Ordner fehlt plugin.json."
                ) from exc

    except BadZipFile as exc:
        raise PluginPackageError(
            "Das Plugin-Paket ist keine gültige ZIP-Datei."
        ) from exc

    temporary_manifest = archive_path.with_suffix(
        archive_path.suffix + ".manifest.tmp"
    )

    try:
        temporary_manifest.write_bytes(manifest_data)
        manifest = PluginManifest.load(temporary_manifest)
    finally:
        temporary_manifest.unlink(missing_ok=True)

    expected_root = manifest.plugin_id.replace(".", "_")
    if root_directory not in {manifest.plugin_id, expected_root}:
        raise PluginPackageError(
            "Der oberste Paketordner muss der Plugin-ID entsprechen."
        )

    return ValidatedPluginPackage(
        archive_path=archive_path,
        sha256=actual_sha256,
        manifest=manifest,
        root_directory=root_directory,
        file_count=len(entries),
        uncompressed_size=total_size,
    )


def _validate_archive_entry(
    filename: str,
    external_attr: int,
) -> PurePosixPath:
    normalized = filename.replace("\\", "/")
    path = PurePosixPath(normalized)

    if path.is_absolute():
        raise PluginPackageError(
            f"Absoluter Pfad im Plugin-Paket ist nicht erlaubt: {filename}"
        )

    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise PluginPackageError(
            f"Unsicherer Pfad im Plugin-Paket: {filename}"
        )

    unix_mode = external_attr >> 16
    if unix_mode and stat.S_ISLNK(unix_mode):
        raise PluginPackageError(
            f"Symbolische Links sind im Plugin-Paket nicht erlaubt: {filename}"
        )

    return path


def _find_single_root_directory(
    paths: list[PurePosixPath],
) -> str:
    roots = {path.parts[0] for path in paths}

    if len(roots) != 1:
        raise PluginPackageError(
            "Das Plugin-Paket muss genau einen obersten Plugin-Ordner besitzen."
        )

    return next(iter(roots))
