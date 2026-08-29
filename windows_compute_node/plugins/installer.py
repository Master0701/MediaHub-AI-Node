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

            manifest_names = [
                name
                for name in names
                if (
                    name == "plugin.json"
                    or name.endswith("/plugin.json")
                )
            ]

            if len(manifest_names) != 1:
                raise PluginInstallError(
                    "Genau ein plugin.json "
                    "im Paket erwartet."
                )

            manifest_name = manifest_names[0]

            try:
                manifest = json.loads(
                    archive.read(
                        manifest_name
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

            root_manifest = (
                extract_root
                / "plugin.json"
            )

            if root_manifest.is_file():
                package_root = extract_root
                manifest_path = root_manifest
            else:
                manifests = list(
                    extract_root.glob(
                        "*/plugin.json"
                    )
                )

                if len(manifests) != 1:
                    raise PluginInstallError(
                        "Extrahiertes Manifest "
                        "ist nicht eindeutig."
                    )

                manifest_path = manifests[0]
                package_root = (
                    manifest_path.parent
                )

            entrypoint = str(
                manifest["entrypoint"]
            ).strip()

            entry_module = (
                entrypoint.split(":", 1)[0]
            )

            if entry_module.endswith(".py"):
                entry_relative = entry_module
            else:
                entry_relative = (
                    entry_module.replace(
                        ".",
                        "/",
                    )
                    + ".py"
                )

            entry_file = (
                package_root
                / entry_relative
            ).resolve()

            try:
                entry_file.relative_to(
                    package_root.resolve()
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
                    str(package_root),
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

    def uninstall(
        self,
        plugin_id: str,
    ) -> dict[str, Any]:
        plugin_id = str(plugin_id).strip()

        if not plugin_id:
            raise PluginInstallError(
                "Plugin-ID fehlt."
            )

        # Plugin-IDs dürfen niemals als Pfade benutzt
        # werden können.
        if (
            plugin_id in {".", ".."}
            or "/" in plugin_id
            or "\\" in plugin_id
        ):
            raise PluginInstallError(
                "Ungültige Plugin-ID."
            )

        target = (
            self.plugin_root
            / plugin_id
        ).resolve()

        plugin_root = (
            self.plugin_root.resolve()
        )

        try:
            target.relative_to(plugin_root)
        except ValueError as exc:
            raise PluginInstallError(
                "Plugin-Pfad liegt außerhalb "
                "des Plugin-Verzeichnisses."
            ) from exc

        if not target.is_dir():
            raise PluginInstallError(
                "Plugin ist nicht installiert."
            )

        manifest_path = (
            target / "plugin.json"
        )

        name = plugin_id
        version = ""

        if manifest_path.is_file():
            try:
                manifest = json.loads(
                    manifest_path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                manifest = {}

            if isinstance(manifest, dict):
                name = str(
                    manifest.get("name")
                    or plugin_id
                )
                version = str(
                    manifest.get("version")
                    or ""
                )

        try:
            shutil.rmtree(target)
        except OSError as exc:
            raise PluginInstallError(
                "Plugin konnte nicht "
                "deinstalliert werden."
            ) from exc

        return {
            "uninstalled": True,
            "plugin_id": plugin_id,
            "name": name,
            "version": version,
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

        legacy_plugin_type = str(
            manifest.get("plugin_type")
            or ""
        ).strip()

        shared_plugin_type = str(
            manifest.get("type")
            or ""
        ).strip()

        if legacy_plugin_type:
            if legacy_plugin_type != "ai_node":
                raise PluginInstallError(
                    "plugin_type muss "
                    "'ai_node' sein."
                )
        elif not shared_plugin_type:
            raise PluginInstallError(
                "Manifest-Feld fehlt: type"
            )

        targets = manifest.get("targets")

        if (
            targets is not None
            and "windows_compute" not in targets
        ):
            raise PluginInstallError(
                "Plugin ist nicht fuer "
                "windows_compute freigegeben."
            )

        platforms = manifest.get("platforms")

        if (
            platforms is not None
            and platforms
            and "windows-amd64" not in platforms
        ):
            raise PluginInstallError(
                "Plugin unterstuetzt "
                "windows-amd64 nicht."
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
