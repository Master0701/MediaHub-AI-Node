"""Installer for .mhaiplugin packages."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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
        self.plugin_root = Path(plugin_root)

        self.plugin_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _prepare_isolated_runtime(self, manifest: dict[str, Any]) -> dict[str, Any] | None:
        """Provision declared Python dependencies without modifying base Python."""
        runtime = manifest.get("runtime")
        if runtime is None:
            return None
        if not isinstance(runtime, dict):
            raise PluginInstallError("runtime muss ein JSON-Objekt sein.")
        dependencies = runtime.get("dependencies", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(item, str) or not item.strip() for item in dependencies
        ):
            raise PluginInstallError("runtime.dependencies muss eine Liste von Paketnamen sein.")
        if not dependencies:
            return None
        if runtime.get("isolated") is not True:
            raise PluginInstallError("Python-Abhaengigkeiten erfordern runtime.isolated=true.")
        # Reject pip option injection and non-index sources from manifests.
        if any(
            not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.-]+\])?(?:[<>=!~]{1,2}[A-Za-z0-9.*+!_-]+(?:,[<>=!~]{1,2}[A-Za-z0-9.*+!_-]+)*)?",
                item.strip(),
            )
            for item in dependencies
        ):
            raise PluginInstallError("Unsichere oder ungueltige Python-Abhaengigkeit im Manifest.")
        from windows_compute_node.runtime_support import python_runtime

        base = python_runtime.require_python()
        plugin_id = str(manifest["id"])
        runtime_name = plugin_id.rsplit(".", 1)[-1]
        base_root = Path(
            os.environ.get("MEDIAHUB_COMPUTE_RUNTIME")
            or (Path.home() / ".mediahub" / "compute_node")
        )
        runtime_root = base_root / "plugin_runtimes" / runtime_name
        # Compatibility with the already installed Windows Speech runtime.
        # Never relocate or rebuild a working legacy environment.
        if plugin_id == "mediahub.speech_to_text" and os.environ.get("MEDIAHUB_COMPUTE_RUNTIME"):
            legacy_root = base_root / runtime_name
            legacy_python = (
                legacy_root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            )
            if legacy_python.is_file():
                runtime_root = legacy_root
        venv_dir = runtime_root / "venv"
        python_path = (
            venv_dir / "Scripts" / "python.exe" if os.name == "nt" else venv_dir / "bin" / "python"
        )

        def check_venv(executable: Path) -> bool:
            if not executable.is_file():
                return False
            result = subprocess.run(
                [str(executable), "-c", "import sys; assert sys.prefix != sys.base_prefix"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0

        def verify_packages(executable: Path) -> bool:
            check_script = (
                "import sys\n"
                "from importlib.metadata import version, PackageNotFoundError\n"
                "from packaging.requirements import Requirement\n"
                "for item in sys.argv[1:]:\n"
                "    requirement = Requirement(item)\n"
                "    try:\n"
                "        installed = version(requirement.name)\n"
                "    except PackageNotFoundError:\n"
                "        sys.exit(1)\n"
                "    if not requirement.specifier.contains(installed, prereleases=True):\n"
                "        sys.exit(1)\n"
            )
            result = subprocess.run(
                [str(executable), "-c", check_script, *dependencies],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0

        if check_venv(python_path) and verify_packages(python_path):
            return {
                "ready": True,
                "python": str(python_path),
                "root": str(runtime_root),
                "reused": True,
            }
        # Never rename, replace, or delete an existing venv, even if incomplete.
        # Repair must be a separate, explicitly approved operation.
        if venv_dir.exists():
            raise PluginInstallError(
                f"Vorhandene Plugin-Python-Umgebung nicht bereit: {venv_dir}. "
                "Keine automatische Neuinstallation; bitte separat pruefen."
            )

        # Create at its final location: Windows venv entrypoints are not reliably
        # relocatable. Preserve an existing environment for rollback.
        runtime_root.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [str(base), "-m", "venv", str(venv_dir)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0 or not check_venv(python_path):
                raise PluginInstallError(
                    "Isolierte Python-Umgebung konnte nicht erstellt werden: "
                    + (result.stderr or result.stdout or "venv nicht verfuegbar")[-1000:]
                )
            pip = subprocess.run(
                [str(python_path), "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if pip.returncode != 0:
                raise PluginInstallError("pip fehlt in der isolierten Plugin-Umgebung.")
            result = subprocess.run(
                [
                    str(python_path),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    *dependencies,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0 or not verify_packages(python_path):
                raise PluginInstallError(
                    "Plugin-Python-Abhaengigkeiten konnten nicht installiert werden: "
                    + (result.stderr or result.stdout or "Paketpruefung fehlgeschlagen")[-1500:]
                )
            return {
                "ready": True,
                "python": str(python_path),
                "root": str(runtime_root),
                "reused": False,
            }
        except Exception:
            if venv_dir.exists():
                shutil.rmtree(venv_dir, ignore_errors=True)
            raise

    def inspect_package(
        self,
        package_path: Path,
    ) -> dict[str, Any]:
        package_path = Path(package_path)

        if not package_path.is_file():
            raise PluginInstallError("Plugin-Paket nicht gefunden.")

        if package_path.suffix.lower() != ".mhaiplugin":
            raise PluginInstallError("Dateiendung muss .mhaiplugin sein.")

        if not zipfile.is_zipfile(package_path):
            raise PluginInstallError("Plugin-Paket ist kein gueltiges ZIP-Archiv.")

        with zipfile.ZipFile(
            package_path,
            "r",
        ) as archive:
            names = archive.namelist()

            self._validate_archive_names(names)

            manifest_names = [
                name for name in names if (name == "plugin.json" or name.endswith("/plugin.json"))
            ]

            if len(manifest_names) != 1:
                raise PluginInstallError("Genau ein plugin.json im Paket erwartet.")

            manifest_name = manifest_names[0]

            try:
                manifest = json.loads(archive.read(manifest_name).decode("utf-8-sig"))
            except (
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as exc:
                raise PluginInstallError("plugin.json ist ungueltig.") from exc

        self._validate_manifest(manifest)

        return manifest

    def install(
        self,
        package_path: Path,
        *,
        replace: bool = False,
    ) -> dict[str, Any]:
        package_path = Path(package_path)

        manifest = self.inspect_package(package_path)

        for dependency in manifest.get("dependencies", []):
            if not isinstance(dependency, dict):
                raise PluginInstallError("Ungueltige Plugin-Abhaengigkeit.")

            targets = dependency.get("targets", [])
            if targets and "windows_compute" not in targets:
                continue

            dependency_id = str(dependency.get("id") or "").strip()

            if not dependency_id:
                raise PluginInstallError("Plugin-Abhaengigkeit ohne ID.")

            import re

            if dependency_id in {".", ".."} or not re.fullmatch(
                r"[A-Za-z0-9_][A-Za-z0-9_.-]*",
                dependency_id,
            ):
                raise PluginInstallError(f"Ungueltige Plugin-Abhaengigkeits-ID: {dependency_id}")

            dependency_manifest = self.plugin_root / dependency_id / "plugin.json"

            if not dependency_manifest.is_file():
                raise PluginInstallError(f"Plugin-Abhaengigkeit fehlt: {dependency_id}")

            minimum_version = str(dependency.get("minimum_version") or "").strip()

            try:
                installed_manifest = json.loads(dependency_manifest.read_text(encoding="utf-8-sig"))

                if not isinstance(installed_manifest, dict):
                    raise ValueError("Ungueltiges Plugin-Manifest")

                if installed_manifest.get("id") != dependency_id:
                    raise PluginInstallError(
                        f"Plugin-Abhaengigkeit {dependency_id}: "
                        "installierte Plugin-ID stimmt nicht."
                    )

                if minimum_version:
                    installed_version = str(installed_manifest["version"]).strip()

                    def version_parts(value):
                        parts = value.split(".")
                        if not parts or not all(
                            part.isascii() and part.isdecimal() for part in parts
                        ):
                            raise ValueError("Ungueltige Version")
                        return tuple(int(part) for part in parts)

                    if version_parts(installed_version) < version_parts(minimum_version):
                        raise PluginInstallError(
                            f"Plugin-Abhaengigkeit {dependency_id}: "
                            f"Version {installed_version} ist zu alt, "
                            f"mindestens {minimum_version} erforderlich."
                        )

            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise PluginInstallError(
                    f"Plugin-Abhaengigkeit {dependency_id}: installiertes Manifest nicht pruefbar."
                ) from exc

        plugin_id = str(manifest["id"]).strip()

        target = self.plugin_root / plugin_id

        if target.exists() and not replace:
            raise PluginInstallError("Plugin ist bereits installiert.")

        with tempfile.TemporaryDirectory(prefix="mediahub_compute_plugin_") as temp_name:
            temp_root = Path(temp_name)

            extract_root = temp_root / "plugin"

            extract_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            with zipfile.ZipFile(
                package_path,
                "r",
            ) as archive:
                archive.extractall(extract_root)

            root_manifest = extract_root / "plugin.json"

            if root_manifest.is_file():
                package_root = extract_root
                manifest_path = root_manifest
            else:
                manifests = list(extract_root.glob("*/plugin.json"))

                if len(manifests) != 1:
                    raise PluginInstallError("Extrahiertes Manifest ist nicht eindeutig.")

                manifest_path = manifests[0]
                package_root = manifest_path.parent

            entrypoint = str(manifest["entrypoint"]).strip()

            entry_module = entrypoint.split(":", 1)[0]

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

            entry_file = (package_root / entry_relative).resolve()

            try:
                entry_file.relative_to(package_root.resolve())
            except ValueError as exc:
                raise PluginInstallError("Entrypoint liegt ausserhalb des Plugins.") from exc

            if not entry_file.is_file():
                raise PluginInstallError("Entrypoint-Datei fehlt.")

            runtime_status = self._prepare_isolated_runtime(manifest)

            backup = None

            if target.exists():
                backup = temp_root / "old_plugin"

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
                if backup is not None and backup.exists() and not target.exists():
                    shutil.move(
                        str(backup),
                        str(target),
                    )

                raise

        return {
            "installed": True,
            "plugin_id": plugin_id,
            "name": str(manifest.get("name") or plugin_id),
            "version": str(manifest["version"]),
            "path": str(target),
            "python_runtime": runtime_status,
        }

    def uninstall(
        self,
        plugin_id: str,
    ) -> dict[str, Any]:
        plugin_id = str(plugin_id).strip()

        if not plugin_id:
            raise PluginInstallError("Plugin-ID fehlt.")

        # Plugin-IDs dÃ¼rfen niemals als Pfade benutzt
        # werden kÃ¶nnen.
        if plugin_id in {".", ".."} or "/" in plugin_id or "\\" in plugin_id:
            raise PluginInstallError("UngÃ¼ltige Plugin-ID.")

        target = (self.plugin_root / plugin_id).resolve()

        plugin_root = self.plugin_root.resolve()

        try:
            target.relative_to(plugin_root)
        except ValueError as exc:
            raise PluginInstallError(
                "Plugin-Pfad liegt auÃŸerhalb des Plugin-Verzeichnisses."
            ) from exc

        if not target.is_dir():
            raise PluginInstallError("Plugin ist nicht installiert.")

        manifest_path = target / "plugin.json"

        name = plugin_id
        version = ""

        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            except (
                OSError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ):
                manifest = {}

            if isinstance(manifest, dict):
                name = str(manifest.get("name") or plugin_id)
                version = str(manifest.get("version") or "")

        # Deinstallation verhindern, solange andere Plugins
        # von diesem Plugin abhaengen.
        for other_dir in self.plugin_root.iterdir():
            if not other_dir.is_dir() or other_dir.resolve() == target:
                continue

            other_manifest_path = other_dir / "plugin.json"
            if not other_manifest_path.is_file():
                continue

            try:
                other_manifest = json.loads(other_manifest_path.read_text(encoding="utf-8-sig"))
                if not isinstance(other_manifest, dict):
                    raise ValueError("Manifest ist kein Objekt")

                dependencies = other_manifest.get("dependencies", [])
                if not isinstance(dependencies, list):
                    raise ValueError("Ungueltige Abhaengigkeiten")

                for dependency in dependencies:
                    if not isinstance(dependency, dict):
                        raise ValueError("Ungueltige Abhaengigkeit")

                    targets = dependency.get("targets", [])
                    if targets and "windows_compute" not in targets:
                        continue

                    if dependency.get("id") == plugin_id:
                        raise PluginInstallError(
                            f"Deinstallation blockiert: {other_dir.name} benoetigt {plugin_id}."
                        )

            except (OSError, UnicodeError, ValueError, TypeError) as exc:
                raise PluginInstallError(
                    f"Abhaengigkeiten von {other_dir.name} konnten nicht geprueft werden."
                ) from exc

        try:
            shutil.rmtree(target)
        except OSError as exc:
            raise PluginInstallError("Plugin konnte nicht deinstalliert werden.") from exc

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
            raise PluginInstallError("Manifest muss ein JSON-Objekt sein.")

        required = (
            "id",
            "name",
            "version",
            "entrypoint",
        )

        for key in required:
            value = str(manifest.get(key) or "").strip()

            if not value:
                raise PluginInstallError(f"Manifest-Feld fehlt: {key}")

        legacy_plugin_type = str(manifest.get("plugin_type") or "").strip()

        shared_plugin_type = str(manifest.get("type") or "").strip()

        if legacy_plugin_type:
            if legacy_plugin_type != "ai_node":
                raise PluginInstallError("plugin_type muss 'ai_node' sein.")
        elif not shared_plugin_type:
            raise PluginInstallError("Manifest-Feld fehlt: type")

        targets = manifest.get("targets")

        if targets is not None and "windows_compute" not in targets:
            raise PluginInstallError("Plugin ist nicht fuer windows_compute freigegeben.")

        platforms = manifest.get("platforms")

        if platforms is not None and platforms and "windows-amd64" not in platforms:
            raise PluginInstallError("Plugin unterstuetzt windows-amd64 nicht.")

        plugin_id = str(manifest["id"])

        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")

        if (
            plugin_id in {".", ".."}
            or not plugin_id
            or any(char not in allowed for char in plugin_id)
        ):
            raise PluginInstallError("Plugin-ID enthaelt ungueltige Zeichen.")

    @staticmethod
    def _validate_archive_names(
        names: list[str],
    ) -> None:
        for raw_name in names:
            normalized = raw_name.replace("\\", "/")

            path = Path(normalized)

            if path.is_absolute():
                raise PluginInstallError("Absolute Pfade sind nicht erlaubt.")

            if ".." in path.parts:
                raise PluginInstallError("Pfadnavigation mit '..' ist nicht erlaubt.")

            if len(normalized) >= 2 and normalized[1] == ":":
                raise PluginInstallError("Windows-Laufwerkspfade sind nicht erlaubt.")
