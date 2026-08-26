"""Installer for .mhaiplugin packages."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any


class PluginInstallError(RuntimeError):
    pass


class ComputePluginInstaller:
    def __init__(
        self,
        *,
        plugin_root: Path,
    ) -> None:
        self.plugin_root = Path(
            plugin_root
        )

        self.plugin_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def inspect_package(
        self,
        package_path: Path,
    ) -> dict[str, Any]:
        package_path = Path(
            package_path
        )

        if not package_path.is_file():
            raise PluginInstallError(
                "Plugin-Paket nicht gefunden."
            )

        if (
            package_path.suffix.lower()
            != ".mhaiplugin"
        ):
            raise PluginInstallError(
                "Dateiendung muss "
                ".mhaiplugin sein."
            )

        if not zipfile.is_zipfile(
            package_path
        ):
            raise PluginInstallError(
                "Plugin-Paket ist kein "
                "gueltiges ZIP-Archiv."
            )

        with zipfile.ZipFile(
            package_path,
            "r",
        ) as archive:
            names = archive.namelist()

            self._validate_archive_names(
                names
            )

            if "plugin.json" not in names:
                raise PluginInstallError(
                    "plugin.json fehlt im "
                    "Paketstamm."
                )

            try:
                manifest = json.loads(
                    archive.read(
                        "plugin.json"
                    ).decode("utf-8")
                )
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as exc:
                raise PluginInstallError(
                    "plugin.json ist "
                    "ungueltig."
                ) from exc

        self._validate_manifest(
            manifest
        )

        return manifest

    def install(
        self,
        package_path: Path,
        *,
        replace: bool = False,
    ) -> dict[str, Any]:
        package_path = Path(
            package_path
        )

        manifest = self.inspect_package(
            package_path
        )

        plugin_id = str(
            manifest["id"]
        ).strip()

        target = (
            self.plugin_root
            / plugin_id
        )

        if target.exists() and not replace:
            raise PluginInstallError(
                "Plugin ist bereits "
                "installiert."
            )

        with tempfile.TemporaryDirectory(
            prefix="mediahub_compute_plugin_"
        ) as temp_name:
            temp_root = Path(
                temp_name
            )

            extract_root = (
                temp_root / "plugin"
            )

            extract_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            with zipfile.ZipFile(
                package_path,
                "r",
            ) as archive:
                archive.extractall(
                    extract_root
                )

            manifest_path = (
                extract_root
                / "plugin.json"
            )

            if not manifest_path.is_file():
                raise PluginInstallError(
                    "Extrahiertes Manifest "
                    "fehlt."
                )

            entrypoint = str(
                manifest["entrypoint"]
            ).strip()

            entry_file = (
                extract_root
                / entrypoint
            ).resolve()

            try:
                entry_file.relative_to(
                    extract_root.resolve()
                )
            except ValueError as exc:
                raise PluginInstallError(
                    "Entrypoint liegt "
                    "ausserhalb des Plugins."
                ) from exc

            if not entry_file.is_file():
                raise PluginInstallError(
                    "Entrypoint-Datei fehlt."
                )

            backup = None

            if target.exists():
                backup = (
                    temp_root
                    / "old_plugin"
                )

                shutil.move(
                    str(target),
                    str(backup),
                )

            try:
                shutil.move(
                    str(extract_root),
                    str(target),
                )
            except Exception:
                if (
                    backup is not None
                    and backup.exists()
                    and not target.exists()
                ):
                    shutil.move(
                        str(backup),
                        str(target),
                    )

                raise

        return {
            "installed": True,
            "plugin_id": plugin_id,
            "name": str(
                manifest.get("name")
                or plugin_id
            ),
            "version": str(
                manifest["version"]
            ),
            "path": str(target),
        }

    @staticmethod
    def _validate_manifest(
        manifest: Any,
    ) -> None:
        if not isinstance(
            manifest,
            dict,
        ):
            raise PluginInstallError(
                "Manifest muss ein "
                "JSON-Objekt sein."
            )

        required = (
            "id",
            "name",
            "version",
            "plugin_type",
            "entrypoint",
        )

        for key in required:
            value = str(
                manifest.get(key)
                or ""
            ).strip()

            if not value:
                raise PluginInstallError(
                    f"Manifest-Feld fehlt: "
                    f"{key}"
                )

        if (
            manifest["plugin_type"]
            != "ai_node"
        ):
            raise PluginInstallError(
                "plugin_type muss "
                "'ai_node' sein."
            )

        plugin_id = str(
            manifest["id"]
        )

        allowed = set(
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789._-"
        )

        if any(
            char not in allowed
            for char in plugin_id
        ):
            raise PluginInstallError(
                "Plugin-ID enthaelt "
                "ungueltige Zeichen."
            )

    @staticmethod
    def _validate_archive_names(
        names: list[str],
    ) -> None:
        for raw_name in names:
            normalized = (
                raw_name
                .replace("\\", "/")
            )

            path = Path(normalized)

            if path.is_absolute():
                raise PluginInstallError(
                    "Absolute Pfade sind "
                    "nicht erlaubt."
                )

            if ".." in path.parts:
                raise PluginInstallError(
                    "Pfadnavigation mit '..' "
                    "ist nicht erlaubt."
                )

            if (
                len(normalized) >= 2
                and normalized[1] == ":"
            ):
                raise PluginInstallError(
                    "Windows-Laufwerkspfade "
                    "sind nicht erlaubt."
                )
