"""Kontrollierte Installation, Backup, Entfernung und Rollback für AI-Plugins."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from app.plugins.errors import PluginError
from app.plugins.package_validator import (
    ValidatedPluginPackage,
    validate_plugin_package,
)
from app.plugins.preflight import (
    PluginPreflightChecker,
    PluginPreflightResult,
)


class PluginInstallError(PluginError):
    """Ein Plugin konnte nicht sicher verwaltet werden."""


@dataclass(frozen=True, slots=True)
class PluginInstallResult:
    """Ergebnis einer erfolgreichen Plugin-Installation."""

    plugin_id: str
    version: str
    install_path: Path
    backup_path: Path | None
    sha256: str
    replaced_existing: bool
    preflight: PluginPreflightResult


@dataclass(frozen=True, slots=True)
class PluginRemoveResult:
    """Ergebnis einer kontrollierten Plugin-Entfernung."""

    plugin_id: str
    removed_path: Path
    backup_path: Path | None


class PluginInstaller:
    """Installiert, entfernt und restauriert Plugins mit Backup."""

    def __init__(
        self,
        *,
        plugin_root: Path,
        backup_root: Path,
    ) -> None:
        self.plugin_root = plugin_root.resolve()
        self.backup_root = backup_root.resolve()

    def install(
        self,
        archive_path: Path,
        *,
        expected_sha256: str | None = None,
        installed_plugin_ids: set[str] | None = None,
    ) -> PluginInstallResult:
        package = validate_plugin_package(
            archive_path,
            expected_sha256=expected_sha256,
        )

        preflight = PluginPreflightChecker(
            installed_plugin_ids=installed_plugin_ids or set(),
        ).check(package)

        self.plugin_root.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)

        install_path = (
            self.plugin_root / package.manifest.plugin_id
        ).resolve()
        self._ensure_inside_root(install_path, self.plugin_root)

        replaced_existing = install_path.exists()
        backup_path = None

        with tempfile.TemporaryDirectory(
            prefix="mediahub-ai-plugin-"
        ) as temporary_directory:
            temporary_root = Path(temporary_directory)
            extracted_root = self._extract_to_temporary(
                package,
                temporary_root,
            )

            staged_path = (
                self.plugin_root
                / f".{package.manifest.plugin_id}.installing"
            ).resolve()
            self._ensure_inside_root(staged_path, self.plugin_root)

            if staged_path.exists():
                shutil.rmtree(staged_path)

            shutil.copytree(extracted_root, staged_path)

            try:
                if replaced_existing:
                    backup_path = self._create_backup(
                        package.manifest.plugin_id,
                        install_path,
                    )
                    shutil.rmtree(install_path)

                staged_path.replace(install_path)
            except Exception as exc:
                self._restore_after_failure(
                    install_path=install_path,
                    staged_path=staged_path,
                    backup_path=backup_path,
                )
                raise PluginInstallError(
                    f"Installation von '{package.manifest.plugin_id}' "
                    f"fehlgeschlagen: {exc}"
                ) from exc

        return PluginInstallResult(
            plugin_id=package.manifest.plugin_id,
            version=package.manifest.version,
            install_path=install_path,
            backup_path=backup_path,
            sha256=package.sha256,
            replaced_existing=replaced_existing,
            preflight=preflight,
        )

    def remove(
        self,
        plugin_id: str,
        *,
        create_backup: bool = True,
    ) -> PluginRemoveResult:
        normalized_id = plugin_id.strip().lower()
        install_path = (self.plugin_root / normalized_id).resolve()
        self._ensure_inside_root(install_path, self.plugin_root)

        if not install_path.is_dir():
            raise PluginInstallError(
                f"Plugin nicht installiert: {normalized_id}"
            )

        backup_path = None
        if create_backup:
            self.backup_root.mkdir(parents=True, exist_ok=True)
            backup_path = self._create_backup(
                normalized_id,
                install_path,
            )

        try:
            shutil.rmtree(install_path)
        except OSError as exc:
            raise PluginInstallError(
                f"Plugin '{normalized_id}' konnte nicht entfernt werden: {exc}"
            ) from exc

        return PluginRemoveResult(
            plugin_id=normalized_id,
            removed_path=install_path,
            backup_path=backup_path,
        )

    def rollback(
        self,
        *,
        plugin_id: str,
        backup_path: Path,
    ) -> Path:
        normalized_id = plugin_id.strip().lower()
        install_path = (self.plugin_root / normalized_id).resolve()
        resolved_backup = backup_path.resolve()

        self._ensure_inside_root(install_path, self.plugin_root)
        self._ensure_inside_root(resolved_backup, self.backup_root)

        if not resolved_backup.is_dir():
            raise PluginInstallError(
                f"Plugin-Backup nicht gefunden: {resolved_backup}"
            )

        staged_restore = (
            self.plugin_root / f".{normalized_id}.restoring"
        ).resolve()

        if staged_restore.exists():
            shutil.rmtree(staged_restore)

        shutil.copytree(resolved_backup, staged_restore)

        try:
            if install_path.exists():
                shutil.rmtree(install_path)
            staged_restore.replace(install_path)
        except Exception as exc:
            if staged_restore.exists():
                shutil.rmtree(staged_restore)
            raise PluginInstallError(
                f"Rollback von '{normalized_id}' fehlgeschlagen: {exc}"
            ) from exc

        return install_path

    def list_backups(self, plugin_id: str) -> tuple[Path, ...]:
        normalized_id = plugin_id.strip().lower()
        plugin_backup_root = (
            self.backup_root / normalized_id
        ).resolve()

        self._ensure_inside_root(plugin_backup_root, self.backup_root)

        if not plugin_backup_root.is_dir():
            return ()

        return tuple(
            sorted(
                (
                    path
                    for path in plugin_backup_root.iterdir()
                    if path.is_dir()
                ),
                reverse=True,
            )
        )

    def resolve_backup(
        self,
        *,
        plugin_id: str,
        backup_name: str,
    ) -> Path:
        normalized_id = plugin_id.strip().lower()
        normalized_backup = backup_name.strip()

        if (
            not normalized_backup
            or "/" in normalized_backup
            or "\\" in normalized_backup
        ):
            raise PluginInstallError("Ungültiger Backup-Name.")

        backup_path = (
            self.backup_root / normalized_id / normalized_backup
        ).resolve()
        self._ensure_inside_root(backup_path, self.backup_root)
        return backup_path

    def _extract_to_temporary(
        self,
        package: ValidatedPluginPackage,
        temporary_root: Path,
    ) -> Path:
        with ZipFile(package.archive_path) as archive:
            archive.extractall(temporary_root)

        extracted_root = (
            temporary_root / package.root_directory
        ).resolve()

        self._ensure_inside_root(extracted_root, temporary_root.resolve())

        if not extracted_root.is_dir():
            raise PluginInstallError(
                "Der geprüfte Plugin-Hauptordner wurde nicht entpackt."
            )

        return extracted_root

    def _create_backup(
        self,
        plugin_id: str,
        install_path: Path,
    ) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = (
            self.backup_root / plugin_id / timestamp
        ).resolve()

        self._ensure_inside_root(backup_path, self.backup_root)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(install_path, backup_path)

        return backup_path

    @staticmethod
    def _ensure_inside_root(
        path: Path,
        root: Path,
    ) -> None:
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise PluginInstallError(
                f"Pfad liegt außerhalb des erlaubten Bereichs: {path}"
            ) from exc

    @staticmethod
    def _restore_after_failure(
        *,
        install_path: Path,
        staged_path: Path,
        backup_path: Path | None,
    ) -> None:
        if staged_path.exists():
            shutil.rmtree(staged_path)

        if backup_path and backup_path.is_dir():
            if install_path.exists():
                shutil.rmtree(install_path)
            shutil.copytree(backup_path, install_path)
