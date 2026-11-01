"""Installer for .mhaiplugin packages."""

from __future__ import annotations

import importlib.util
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

    def _prepare_gliner_runtime(
        self, manifest: dict[str, Any], package_root: Path
    ) -> dict[str, Any]:
        """Use the existing, GPU-aware GLiNER runtime installer on Windows."""
        if manifest.get("id") != "mediahub.gliner":
            raise PluginInstallError("Ungueltiges GLiNER-Plugin.")
        runtime = manifest.get("runtime")
        if (
            not isinstance(runtime, dict)
            or runtime.get("engine") != "gliner"
            or runtime.get("isolated") is not True
        ):
            raise PluginInstallError("GLiNER benoetigt seine deklarierte isolierte Runtime.")
        manager_file = package_root / "runtime_manager.py"
        if not manager_file.is_file():
            raise PluginInstallError("GLiNER-Runtime-Manager fehlt im Plugin-Paket.")

        spec = importlib.util.spec_from_file_location(
            "mediahub_gliner_install_runtime", manager_file
        )
        if spec is None or spec.loader is None:
            raise PluginInstallError("GLiNER-Runtime-Manager kann nicht geladen werden.")
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)

        from windows_compute_node.hardware.capabilities import get_capabilities

        capabilities = get_capabilities()
        requested_profile = (
            os.environ.get("MEDIAHUB_GLINER_INSTALL_PROFILE", "auto").strip().lower()
        )
        if requested_profile not in {"auto", "cpu", "cuda"}:
            raise PluginInstallError("Ungueltiges GLiNER-Installationsprofil.")
        selection = manager.select_install_profile(
            requested=requested_profile, capabilities=capabilities
        )
        profile = selection["selected"]
        status = manager.inspect_runtime()
        acceleration = manager.inspect_acceleration() if status.get("ready") else {}
        matching = bool(status.get("ready")) and (
            bool(acceleration.get("cuda_available")) if profile == "cuda"
            else not bool(acceleration.get("cuda_built"))
        )
        if matching:
            return {
                **status, "install_profile": selection,
                "acceleration": acceleration, "reused": True,
            }

        # An existing runtime is user data: do not silently replace or migrate it.
        root = manager.default_runtime_root()
        if (root / "venv").exists() or (root / "packages").exists():
            raise PluginInstallError(
                "GLiNER-Runtime ist vorhanden, passt aber nicht zum erkannten "
                f"{profile.upper()}-Profil. Keine automatische Ueberschreibung: {root}"
            )

        try:
            installed = manager.install_dependencies(profile=profile, capabilities=capabilities)
        except Exception as exc:
            raise PluginInstallError(
                f"GLiNER-{profile.upper()}-Runtime konnte nicht installiert werden: {exc}"
            ) from exc
        if not installed.get("ready"):
            raise PluginInstallError("GLiNER-Runtime wurde installiert, ist aber nicht bereit.")
        if profile == "cuda" and not installed.get("acceleration", {}).get("cuda_available"):
            raise PluginInstallError("GLiNER-CUDA-Runtime ist nach Installation nicht verfuegbar.")
        return {**installed, "reused": False}

    def _prepare_smolvlm2_runtime(
        self, manifest: dict[str, Any], package_root: Path
    ) -> dict[str, Any]:
        """Prepare SmolVLM2 with its own installer, analogous to GLiNER."""
        if manifest.get("id") != "mediahub.smolvlm2":
            raise PluginInstallError("Ungueltiges SmolVLM2-Plugin.")
        runtime = manifest.get("runtime")
        if (
            not isinstance(runtime, dict)
            or runtime.get("engine") != "smolvlm2"
            or runtime.get("isolated") is not True
        ):
            raise PluginInstallError("SmolVLM2 benoetigt seine deklarierte isolierte Runtime.")
        manager_file = package_root / "runtime.py"
        if not manager_file.is_file():
            raise PluginInstallError("SmolVLM2-Runtime-Manager fehlt im Plugin-Paket.")
        spec = importlib.util.spec_from_file_location(
            "mediahub_smolvlm2_install_runtime", manager_file
        )
        if spec is None or spec.loader is None:
            raise PluginInstallError("SmolVLM2-Runtime-Manager kann nicht geladen werden.")
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)

        requested = os.environ.get("MEDIAHUB_SMOLVLM2_INSTALL_PROFILE", "auto").strip().lower()
        if requested not in {"auto", "cpu", "cuda"}:
            raise PluginInstallError("Ungueltiges SmolVLM2-Installationsprofil.")
        existing = manager.inspect_runtime()
        if existing.get("ready"):
            torch = existing.get("torch") or {}
            if requested == "cuda" and not torch.get("cuda_available"):
                raise PluginInstallError(
                    "Vorhandene SmolVLM2-Runtime hat kein nutzbares CUDA; "
                    "keine automatische Ueberschreibung."
                )
            if requested == "cpu" and torch.get("cuda_runtime"):
                raise PluginInstallError(
                    "Vorhandene SmolVLM2-Runtime nutzt CUDA; "
                    "keine automatische Ueberschreibung."
                )
            return {**existing, "reused": True}
        root = manager.runtime_root()
        if (root / "venv").exists():
            raise PluginInstallError(
                "Vorhandene SmolVLM2-Runtime ist nicht bereit. "
                f"Keine automatische Ueberschreibung: {root}"
            )
        try:
            installed = manager.install_dependencies(requested_backend=requested)
        except Exception as exc:
            raise PluginInstallError(
                f"SmolVLM2-Runtime konnte nicht installiert werden: {exc}"
            ) from exc
        if not installed.get("ready"):
            raise PluginInstallError("SmolVLM2-Runtime wurde installiert, ist aber nicht bereit.")
        if (
            (requested == "cuda" or installed.get("selected_backend") == "cuda")
            and not (installed.get("torch") or {}).get("cuda_available")
        ):
            raise PluginInstallError(
                "SmolVLM2-CUDA-Runtime ist nach Installation nicht verfuegbar."
            )
        return {**installed, "reused": False}

    def _prepare_smolvlm2_model(
        self, manifest: dict[str, Any], package_root: Path, runtime_status: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Provision the required MediaHub_Tools asset before publishing the plugin."""
        if not runtime_status or not runtime_status.get("ready"):
            raise PluginInstallError("SmolVLM2-Modell benoetigt eine bereite Runtime.")
        tools = manifest.get("required_tools")
        if not isinstance(tools, list):
            raise PluginInstallError("SmolVLM2 required_tools fehlt oder ist ungueltig.")
        matching = [
            item for item in tools
            if isinstance(item, dict) and item.get("id") == "smolvlm2-model"
                    and (not item.get("targets") or "windows_compute" in item["targets"])]
        if (
            len(matching) != 1
            or matching[0].get("required") is not True
            or matching[0].get("source") != "mediahub_tools"
            or str(matching[0].get("version")) != "0.1.0"
        ):
            raise PluginInstallError(
                "SmolVLM2-Modellabhaengigkeit ist ungueltig oder nicht unterstuetzt."
            )
        manager_file = package_root / "model_manager.py"
        if not manager_file.is_file():
            raise PluginInstallError("SmolVLM2-Modell-Manager fehlt im Plugin-Paket.")
        spec = importlib.util.spec_from_file_location(
            "mediahub_smolvlm2_install_model", manager_file
        )
        if spec is None or spec.loader is None:
            raise PluginInstallError("SmolVLM2-Modell-Manager kann nicht geladen werden.")
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)
        models_root = Path(runtime_status["root"]) / "models"
        try:
            try:
                existing = manager.resolve_model_path(models_root)
            except RuntimeError:
                existing = None
            if existing is not None:
                return {"ready": True, "model_path": str(existing), "reused": True,
                        "tool_id": "smolvlm2-model", "source": "mediahub_tools"}
            installed = manager.install_model(models_root)
            verified = manager.resolve_model_path(models_root)
            if not installed.get("installed") or not installed.get("ready"):
                raise PluginInstallError("SmolVLM2-Modell wurde nicht vollstaendig installiert.")
            return {**installed, "ready": True, "model_path": str(verified), "reused": False}
        except Exception as exc:
            raise PluginInstallError(
                f"SmolVLM2-Modell konnte nicht bereitgestellt werden: {exc}"
            ) from exc

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

    def _prepare_declared_model(
        self, manifest: dict[str, Any], runtime_status: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Install a manifest-declared Hugging Face model in the approved isolated runtime."""
        model = manifest.get("model")
        if model is None:
            return None
        if not isinstance(model, dict):
            raise PluginInstallError("Modellkonfiguration muss ein Objekt sein.")
        if not runtime_status or not runtime_status.get("ready"):
            raise PluginInstallError(
                "Modell benoetigt eine einsatzbereite isolierte Python-Runtime."
            )

        repository = model.get("repository")
        directory = model.get("directory")
        if (
            not isinstance(repository, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
                or not isinstance(directory, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", directory)
                or directory in {".", ".."}):
            raise PluginInstallError("Ungueltige Modellquelle oder Modellverzeichnis.")
        if model.get("installation") != "during_plugin_install":
            raise PluginInstallError("Unbekannte Modell-Installationsart.")
        required = model.get("required_files")
        if not isinstance(required, list) or not required or not all(
            isinstance(name, str)
            and re.fullmatch(r"[A-Za-z0-9_.-]+", name)
            and name not in {".", ".."}
            for name in required
        ):
            raise PluginInstallError("Modell-Pflichtdateien muessen sichere Dateinamen sein.")
        weight_files = model.get("weight_files")
        if not isinstance(weight_files, list) or not weight_files or not all(
            isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", name)
            for name in weight_files
        ):
            raise PluginInstallError("Modell-Gewichtsdateien fehlen oder sind ungueltig.")
        offline_loader = model.get("offline_loader")
        if offline_loader not in (None, "gliner"):
            raise PluginInstallError("Unbekannter Offline-Modelltest.")

        root = Path(runtime_status["root"])
        python = Path(runtime_status["python"])
        # The GPU-aware GLiNER runtime keeps its modules in a separate
        # packages/ directory, not in the base interpreter's site-packages.
        package_dir = runtime_status.get("packages_path")
        runtime_env = dict(os.environ)
        if runtime_status.get("mode") == "isolated_target" and package_dir:
            runtime_env["PYTHONPATH"] = str(package_dir)
            runtime_env["PYTHONNOUSERSITE"] = "1"
            runtime_env.pop("PYTHONHOME", None)
            runtime_env.pop("PYTHONUSERBASE", None)
        models = root / "models"
        target = models / directory
        stage = models / (directory + "_installing")

        def validate(path: Path) -> bool:
            if not path.is_dir():
                return False
            for name in required:
                candidate = path / name
                if not candidate.is_file() or candidate.stat().st_size <= 0:
                    return False
                if name.endswith(".json"):
                    try:
                        if not isinstance(json.loads(candidate.read_text(encoding="utf-8")), dict):
                            return False
                    except (OSError, UnicodeError, ValueError):
                        return False
            return any(
                (path / name).is_file() and (path / name).stat().st_size > 0
                for name in weight_files
            )

        def offline_check(path: Path) -> None:
            if offline_loader is None:
                return
            script = (
                "import sys\n"
                "from gliner import GLiNER\n"
                "GLiNER.from_pretrained(sys.argv[1], local_files_only=True)\n"
            )
            result = subprocess.run(
                [str(python), "-c", script, str(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                check=False, timeout=600,
                env={**runtime_env, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
            )
            if result.returncode:
                raise PluginInstallError(
                    "Modell kann nicht vollstaendig offline geladen werden "
                    + f"(Exit-Code {result.returncode}). "
                    + "STDOUT: " + (result.stdout or "<leer>")[-3000:]
                    + " STDERR: " + (result.stderr or "<leer>")[-5000:]
                )

        if target.exists():
            if not validate(target):
                raise PluginInstallError(
                    f"Vorhandenes Modell unvollstaendig; keine Ueberschreibung: {target}"
                )
            offline_check(target)
            return {"ready": True, "path": str(target), "reused": True}
        if stage.exists():
            raise PluginInstallError(f"Vorhandenes Modell-Staging bitte pruefen: {stage}")
        models.mkdir(parents=True, exist_ok=True)
        script = (
            "import sys\n"
            "from huggingface_hub import snapshot_download\n"
            "snapshot_download(repo_id=sys.argv[1], local_dir=sys.argv[2], max_workers=2)\n"
        )
        try:
            result = subprocess.run(
                [str(python), "-c", script, repository, str(stage)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                check=False, timeout=3600,
                env={**runtime_env, "HF_HUB_OFFLINE": "0", "TRANSFORMERS_OFFLINE": "0"},
            )
            if result.returncode:
                raise PluginInstallError(
                    "Modell-Download fehlgeschlagen: "
                    + (result.stderr or result.stdout or "Unbekannter Fehler")[-1600:]
                )
            if not validate(stage):
                raise PluginInstallError("Modell heruntergeladen, aber Pflichtdateien fehlen.")
            offline_check(stage)
            stage.rename(target)
            return {"ready": True, "path": str(target), "reused": False}
        except subprocess.TimeoutExpired as exc:
            raise PluginInstallError("Zeitlimit bei Modell-Download oder Offline-Test.") from exc
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

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
        speech_profile: str = "cpu",
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

            if plugin_id == "mediahub.gliner":
                runtime_status = self._prepare_gliner_runtime(manifest, package_root)
            elif plugin_id == "mediahub.smolvlm2":
                runtime_status = self._prepare_smolvlm2_runtime(manifest, package_root)
            else:
                runtime_status = self._prepare_isolated_runtime(manifest)
            if plugin_id == "mediahub.speech_to_text":
                if speech_profile not in {"cpu", "cuda"}:
                    raise PluginInstallError("Ungueltiges Speech-Installationsprofil.")
                if speech_profile == "cuda":
                    if not runtime_status or not runtime_status.get("ready"):
                        raise PluginInstallError("Speech-Python-Runtime ist nicht bereit.")
                    cuda_packages = (manifest.get("runtime") or {}).get("cuda_dependencies")
                    expected = [
                        "nvidia-cublas-cu12==12.6.4.1",
                        "nvidia-cudnn-cu12==9.10.2.21",
                        "nvidia-cuda-runtime-cu12==12.6.77",
                    ]
                    if cuda_packages != expected:
                        raise PluginInstallError("Speech-CUDA-Paketliste ist nicht freigegeben.")
                    module_path = package_root / "runtime.py"
                    spec = importlib.util.spec_from_file_location(
                        "mediahub_speech_cuda_install", module_path
                    )
                    if spec is None or spec.loader is None:
                        raise PluginInstallError("Speech-CUDA-Installer nicht ladbar.")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if tuple(cuda_packages) != tuple(module.CUDA_RUNTIME_PACKAGES):
                        raise PluginInstallError(
                "Speech-CUDA-Paketversionen stimmen nicht ueberein."
            )
                    try:
                        cuda_status = module.inspect_cuda_runtime(Path(runtime_status["root"]))
                        if not cuda_status.get("ready"):
                            cuda_status = module.install_cuda_dependencies(
                                Path(runtime_status["root"])
                            )
                        if not cuda_status.get("ready"):
                            raise RuntimeError("CUDA-DLL-Pruefung fehlgeschlagen")
                    except Exception as exc:
                        raise PluginInstallError(
                            f"Speech-CUDA-Installation fehlgeschlagen: {exc}"
                        ) from exc
                    runtime_status = {
                        **runtime_status, "cuda": cuda_status, "install_profile": "cuda"
                    }
                else:
                    runtime_status = {**(runtime_status or {}), "install_profile": "cpu"}
            if plugin_id == "mediahub.smolvlm2":
                model_status = self._prepare_smolvlm2_model(manifest, package_root, runtime_status)
            else:
                model_status = self._prepare_declared_model(manifest, runtime_status)

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
            "model": model_status,
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
