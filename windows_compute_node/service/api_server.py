"""Minimal HTTP API for the Windows Compute Node."""

from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
import shutil
import threading
import time
import uuid
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any

from shared.node_activity import NodeActivityController
from windows_compute_node.config.node_identity import (
    NodeIdentity,
)
from windows_compute_node.config.settings import (
    NodeSettings,
)
from windows_compute_node.hardware.capabilities import (
    get_capabilities,
)
from windows_compute_node.jobs.input_cleanup import (
    JobInputCleanup,
)
from windows_compute_node.jobs.queue import (
    JobQueue,
)
from windows_compute_node.plugins.dependency_plan import resolve
from windows_compute_node.plugins.installer import (
    ComputePluginInstaller,
    PluginInstallError,
)
from windows_compute_node.plugins.loader import (
    ComputePluginLoader,
)
from windows_compute_node.security.api_token import (
    NodeApiToken,
)
from windows_compute_node.security.pairing import (
    PairingManager,
)
from windows_compute_node.service.runtime_status import (
    ComputeNodeRuntimeStatus,
)
from windows_compute_node.version import WINDOWS_COMPUTE_NODE_VERSION
from windows_compute_node.workers.dispatcher import (
    JobDispatcher,
)
from windows_compute_node.workers.registry import (
    WorkerRegistry,
)


class ComputeNodeAPI:
    def __init__(
        self,
        runtime_dir: Path,
    ) -> None:
        self.runtime_dir = Path(runtime_dir)

        self.input_cleanup = JobInputCleanup(self.runtime_dir)
        self.orphan_inputs_removed = self.input_cleanup.cleanup_orphans()

        self.identity = NodeIdentity(self.runtime_dir / "node_identity.json").load_or_create()

        self.settings = NodeSettings(self.runtime_dir / "settings.json").load()

        self.token_store = NodeApiToken(self.runtime_dir / "security" / "api_token.json")

        self.api_token = self.token_store.load_or_create()

        self.pairing = PairingManager(lifetime_seconds=600)

        self.pairing_code = self.pairing.create_code()

        self.jobs = JobQueue()
        self.runtime_status = ComputeNodeRuntimeStatus()
        self.workers = WorkerRegistry()

        self.dispatcher = JobDispatcher(
            jobs=self.jobs,
            workers=self.workers,
            runtime_dir=self.runtime_dir,
        )

        self._install_plans = {}
        self._install_plan_lock = threading.RLock()
        self._install_plan_dir = self.runtime_dir / "plugin_install_plans"

        self.plugin_installer = ComputePluginInstaller(
            plugin_root=(self.runtime_dir / "plugins"),
        )

        self.plugin_loader = ComputePluginLoader(
            plugin_root=(self.runtime_dir / "plugins"),
            workers=self.workers,
            capabilities_provider=(get_capabilities),
        )

        self.plugin_load_results = self.plugin_loader.load_all()

        self.activity = NodeActivityController(
            idle_timeout_seconds=900.0,
            sleep_callback=(self.plugin_loader.sleep_all),
            wake_callback=(self.plugin_loader.wake_all),
        )

        self.dispatcher.activity = self.activity

    def reload_plugins(
        self,
    ) -> list[dict[str, Any]]:
        """Lädt Plugin- und Worker-Runtime vollständig neu."""

        self.workers = WorkerRegistry()

        self.dispatcher = JobDispatcher(
            jobs=self.jobs,
            workers=self.workers,
            runtime_dir=self.runtime_dir,
        )

        self.plugin_loader = ComputePluginLoader(
            plugin_root=(self.runtime_dir / "plugins"),
            workers=self.workers,
            capabilities_provider=(get_capabilities),
        )

        self.plugin_load_results = self.plugin_loader.load_all()

        self.activity.sleep_callback = self.plugin_loader.sleep_all
        self.activity.wake_callback = self.plugin_loader.wake_all

        self.dispatcher.activity = self.activity

        return self.plugin_load_results

    def uninstall_plugin(
        self,
        plugin_id: str,
    ) -> dict[str, Any]:
        result = self.plugin_installer.uninstall(plugin_id)

        loaded = self.reload_plugins()

        return {
            "uninstalled": True,
            "plugin": result,
            "plugins": loaded,
            "workers": self.workers.list_workers(),
        }

    def _cleanup_install_plans(self) -> None:
        now = time.monotonic()
        for plan_id, entry in list(self._install_plans.items()):
            if entry["expires"] <= now:
                self._install_plans.pop(plan_id, None)
                shutil.rmtree(entry["directory"], ignore_errors=True)

    def create_install_plan(
        self, filename: str, body: bytes, sha256: str, replace: bool, speech_profile: str = "cpu"
    ) -> dict[str, Any]:
        expected = sha256.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise PluginInstallError("Ungueltige SHA-256-Pruefsumme.")
        if hashlib.sha256(body).hexdigest() != expected:
            raise PluginInstallError("SHA-256-Pruefsumme stimmt nicht ueberein.")
        with self._install_plan_lock:
            self._cleanup_install_plans()
            plan_id = uuid.uuid4().hex
            directory = self._install_plan_dir / plan_id
            directory.mkdir(parents=True, exist_ok=False)
            package = directory / filename
            try:
                package.write_bytes(body)
                manifest = self.plugin_installer.inspect_package(package)
                plugin_id = str(manifest["id"])
                if (self.plugin_installer.plugin_root / plugin_id).exists() and not replace:
                    raise PluginInstallError(
                        "Plugin ist bereits installiert; Ersetzen muss bestaetigt werden."
                    )
                runtime = manifest.get("runtime") or {}
                if not isinstance(runtime, dict):
                    raise PluginInstallError("Ungueltige Runtime-Deklaration.")
                python_packages = runtime.get("dependencies", [])
                if not isinstance(python_packages, list) or any(
                    not isinstance(x, str) for x in python_packages
                ):
                    raise PluginInstallError("Ungueltige Python-Abhaengigkeiten.")
                if speech_profile not in {"cpu", "cuda"}:
                    raise PluginInstallError("Ungueltiges Speech-Installationsprofil.")
                if speech_profile != "cpu" and manifest.get("id") != "mediahub.speech_to_text":
                    raise PluginInstallError("CUDA-Profil ist nur fuer Speech-to-Text zulaessig.")
                cuda_packages = []
                if manifest.get("id") == "mediahub.speech_to_text" and speech_profile == "cuda":
                    cuda_packages = runtime.get("cuda_dependencies", [])
                    expected_cuda = [
                        "nvidia-cublas-cu12==12.6.4.1",
                        "nvidia-cudnn-cu12==9.10.2.21",
                        "nvidia-cuda-runtime-cu12==12.6.77",
                    ]
                    if cuda_packages != expected_cuda:
                        raise PluginInstallError(
                            "Speech-CUDA-Abhaengigkeiten fehlen oder weichen "
                            "von den freigegebenen Versionen ab."
                        )
                dependencies = manifest.get("dependencies", [])
                if not isinstance(dependencies, list):
                    raise PluginInstallError("Ungueltige Plugin-Abhaengigkeiten.")
                # Resolve the entire dependency chain before the single approval.
                # Packages are staged by the MediaHub client or operator; no
                # arbitrary network downloads are performed while planning.
                catalog = self.runtime_dir / "plugin_package_catalog"
                steps = resolve(self.plugin_installer, package, catalog)
                # Snapshot the exact bytes and hashes of every dependency.
                # Confirmation must not trust mutable catalog files.
                staged_steps = []
                for index, step in enumerate(steps):
                    source = Path(step["package_path"])
                    staged = directory / f"step_{index}.mhaiplugin"
                    if source != package:
                        shutil.copyfile(source, staged)
                    else:
                        staged = package
                    if hashlib.sha256(staged.read_bytes()).hexdigest() != step["sha256"]:
                        raise PluginInstallError(
                            "Abhaengigkeitspaket hat sich waehrend der Planung geaendert."
                        )
                    staged_steps.append({**step, "package_path": str(staged)})
                from windows_compute_node.plugins.dependency_plan import (
                    dependencies as get_plugin_dependencies,
                )
                from windows_compute_node.runtime_support import python_runtime
                needs_managed_python = any(
                    dep_id == "mediahub.python_runtime"
                    for step in staged_steps
                    for dep_id, _ in get_plugin_dependencies(
                        self.plugin_installer.inspect_package(Path(step["package_path"]))
                    )
                )
                if needs_managed_python:
                    needs_managed_python = not python_runtime.inspect_managed_python().get(
                        "ready", False
                    )
                response = {
                    "status": "plan_created",
                    "plan_id": plan_id,
                    "package": {
                        "plugin_id": plugin_id,
                        "name": str(manifest.get("name") or plugin_id),
                        "version": str(manifest.get("version") or ""),
                        "sha256": expected,
                    },
                    "plan": {
                        "replace": replace,
                        "python_packages": python_packages,
                        "speech_install_profile": (
                            speech_profile if plugin_id == "mediahub.speech_to_text" else None
                        ),
                        "speech_cuda_packages": cuda_packages,
                        "plugin_dependencies": [
                            x
                            for x in dependencies
                            if isinstance(x, dict)
                            and (not x.get("targets") or "windows_compute" in x.get("targets", []))
                        ],
                        "runtime_isolated": runtime.get("isolated") is True,
                        "installation_steps": [
                            {key: value for key, value in step.items() if key != "package_path"}
                            for step in staged_steps
                        ],
                        "managed_python_download": (
                            "MediaHub_Tools CPython 3.12.10 x64 (HTTPS, verified SHA256)"
                            if needs_managed_python else None
                        ),
                        "confirmation_count": 1,
                    },
                }
                self._install_plans[plan_id] = {
                    "directory": directory,
                    "package": package,
                    "sha256": expected,
                    "replace": replace,
                    "steps": staged_steps,
                    "needs_managed_python": needs_managed_python,
                    "speech_profile": (
                        speech_profile if plugin_id == "mediahub.speech_to_text" else "cpu"
                    ),
                    "expires": time.monotonic() + 900,
                }
                return response
            except Exception:
                shutil.rmtree(directory, ignore_errors=True)
                raise

    def cancel_install_plan(self, plan_id: str) -> dict[str, Any]:
        with self._install_plan_lock:
            entry = self._install_plans.pop(plan_id, None)
            if entry:
                shutil.rmtree(entry["directory"], ignore_errors=True)
        return {"cancelled": True}

    def confirm_install_plan(self, plan_id: str, sha256: str) -> dict[str, Any]:
        with self._install_plan_lock:
            self._cleanup_install_plans()
            entry = self._install_plans.get(plan_id)
            if entry is None:
                raise PluginInstallError("Installationsplan nicht vorhanden oder abgelaufen.")
            if sha256.strip().lower() != entry["sha256"]:
                raise PluginInstallError("SHA-256 stimmt nicht mit dem Installationsplan ueberein.")
            self._install_plans.pop(plan_id)
            try:
                results = []
                for step in entry["steps"]:
                    package = Path(step["package_path"])
                    if hashlib.sha256(package.read_bytes()).hexdigest() != step["sha256"]:
                        raise PluginInstallError("Installationspaket nach Freigabe veraendert.")
                    from windows_compute_node.plugins.dependency_plan import (
                        dependencies as get_plugin_dependencies,
                    )
                    manifest = self.plugin_installer.inspect_package(package)
                    if any(
                        key == "mediahub.python_runtime"
                        for key, _ in get_plugin_dependencies(manifest)
                    ):
                        self._ensure_managed_python_after_approval()
                    result = self.install_plugin_package(
                        package, expected_sha256=step["sha256"], replace=step["replace"],
                        speech_profile=(
                            entry["speech_profile"]
                            if step["plugin_id"] == "mediahub.speech_to_text"
                            else "cpu"
                        )
                    )
                    results.append(result)
                    if step["plugin_id"] == "mediahub.python_runtime":
                        self._ensure_managed_python_after_approval()
                return {
                    "installed": True, "installation_steps": results,
                    "plugins": self.plugin_load_results,
                }
            finally:
                shutil.rmtree(entry["directory"], ignore_errors=True)

    def _ensure_managed_python_after_approval(self) -> None:
        """Provision managed Python only after the single plan confirmation."""
        from windows_compute_node.runtime_support import python_runtime
        if python_runtime.inspect_managed_python().get("ready", False):
            return
        import importlib.util
        plugin = self.plugin_installer.plugin_root / "mediahub.python_runtime" / "plugin.py"
        if not plugin.is_file():
            raise PluginInstallError("Python-Runtime-Plugin nicht installiert.")
        spec = importlib.util.spec_from_file_location("mediahub_managed_python_install", plugin)
        if spec is None or spec.loader is None:
            raise PluginInstallError("Python-Runtime-Installer nicht ladbar.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.install_from_tools_repo(confirmed=True)
        if not result.get("ready"):
            raise PluginInstallError("Python Runtime wurde nicht betriebsbereit installiert.")
        if not python_runtime.inspect_managed_python().get("ready", False):
            raise PluginInstallError(
                "Verwaltete Python 3.12.10 Runtime nach Installation nicht bereit."
            )

    def install_plugin_package(
        self,
        package_path: Path,
        *,
        expected_sha256: str,
        replace: bool = False,
        speech_profile: str = "cpu",
    ) -> dict[str, Any]:
        package_path = Path(package_path)

        expected = str(expected_sha256).strip().lower()

        if not expected:
            raise PluginInstallError("SHA-256-Prüfsumme fehlt.")

        digest = hashlib.sha256(package_path.read_bytes()).hexdigest()

        if digest != expected:
            raise PluginInstallError("SHA-256-Prüfsumme stimmt nicht mit dem Paket überein.")

        result = self.plugin_installer.install(
            package_path,
            replace=replace,
            speech_profile=speech_profile,
        )

        loaded = self.reload_plugins()

        plugin_id = str(result.get("plugin_id") or result.get("id") or "")

        runtime_result = next(
            (
                item
                for item in loaded
                if isinstance(item, dict)
                and str(item.get("plugin_id") or item.get("id") or "") == plugin_id
            ),
            None,
        )

        return {
            "installed": True,
            "plugin": result,
            "runtime": runtime_result,
            "plugins": loaded,
            "workers": self.workers.list_workers(),
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "mediahub-compute-node",
            "node_id": self.identity["node_id"],
        }

    def identity_info(
        self,
    ) -> dict[str, Any]:
        return {
            "node_id": self.identity["node_id"],
            "node_name": self.settings["node_name"],
            "node_type": "windows_compute",
        }

    def capabilities_info(
        self,
    ) -> dict[str, Any]:
        return get_capabilities()


class RequestHandler(
    BaseHTTPRequestHandler,
):
    api: ComputeNodeAPI

    def _send_json(
        self,
        status: int,
        payload: dict[str, Any],
    ) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def _bearer_token(
        self,
    ) -> str | None:
        authorization = str(
            self.headers.get(
                "Authorization",
                "",
            )
        ).strip()

        prefix = "Bearer "

        if not authorization.startswith(prefix):
            return None

        return authorization[len(prefix) :].strip()

    def _authorized(self) -> bool:
        connection = self.api.settings.get("connection") or {}

        if not connection.get(
            "require_authentication",
            True,
        ):
            return True

        return self.api.token_store.validate(self._bearer_token())

    def _require_auth(self) -> bool:
        if self._authorized():
            self.api.runtime_status.mark_authenticated_request()
            return True

        self._send_json(
            401,
            {
                "error": "unauthorized",
                "detail": ("Gueltiges Compute-Node-API-Token erforderlich."),
            },
        )

        return False

    def _read_json(
        self,
    ) -> dict[str, Any]:
        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )
        except ValueError:
            length = 0

        if length <= 0:
            return {}

        raw = self.rfile.read(length)

        try:
            data = json.loads(raw.decode("utf-8"))
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return {}

        if not isinstance(data, dict):
            return {}

        return data

    def _read_binary_body(
        self,
        *,
        max_bytes: int = 512 * 1024 * 1024,
    ) -> bytes:
        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )
        except ValueError:
            length = 0

        if length <= 0:
            raise ValueError("Leerer Request-Body.")

        if length > max_bytes:
            raise ValueError("Plugin-Paket ist größer als 512 MiB.")

        body = self.rfile.read(length)

        if len(body) != length:
            raise ValueError("Plugin-Paket wurde nicht vollständig übertragen.")

        return body

    def do_POST(self) -> None:
        path = self.path.split(
            "?",
            1,
        )[0].rstrip("/")

        if path == "/activity/heartbeat":
            if not self._require_auth():
                return

            self.api.activity.mediahub_heartbeat()

            self._send_json(
                200,
                {
                    "ok": True,
                    "activity": (self.api.activity.status()),
                },
            )
            return

        if path == "/plugins/uninstall":
            if not self._require_auth():
                return

            plugin_id = str(
                self.headers.get(
                    "X-Plugin-ID",
                    "",
                )
            ).strip()

            if not plugin_id:
                self._send_json(
                    400,
                    {"error": ("X-Plugin-ID fehlt.")},
                )
                return

            try:
                result = self.api.uninstall_plugin(plugin_id)
            except PluginInstallError as exc:
                self._send_json(
                    400,
                    {"error": str(exc)},
                )
                return
            except OSError as exc:
                self._send_json(
                    500,
                    {"error": str(exc)},
                )
                return

            self._send_json(
                200,
                result,
            )
            return

        if path.startswith("/plugins/plan/") and path.endswith("/confirm"):
            if not self._require_auth():
                return
            plan_id = path[len("/plugins/plan/") : -len("/confirm")].strip("/")
            if not re.fullmatch(r"[0-9a-f]{32}", plan_id):
                self._send_json(400, {"error": "invalid_plan_id"})
                return
            try:
                result = self.api.confirm_install_plan(
                    plan_id, self.headers.get("X-Plugin-SHA256", "")
                )
            except PluginInstallError as error:
                self._send_json(400, {"error": "plan_confirmation_failed", "detail": str(error)})
                return
            except OSError as error:
                self._send_json(500, {"error": "plugin_io_error", "detail": str(error)})
                return
            self._send_json(201, result)
            return

        if path == "/plugins/install":
            if not self._require_auth():
                return
            self._send_json(
                409,
                {
                    "error": "install_plan_required",
                    "detail": (
                        "Direkte Installation deaktiviert. "
                        "/plugins/plan und /confirm verwenden."
                    ),
                },
            )
            return

        if path == "/plugins/plan":
            if not self._require_auth():
                return

            filename = str(
                self.headers.get(
                    "X-Plugin-Filename",
                    "",
                )
            ).strip()

            expected_sha256 = str(
                self.headers.get(
                    "X-Plugin-SHA256",
                    "",
                )
            ).strip()

            replace_value = (
                str(
                    self.headers.get(
                        "X-Plugin-Replace",
                        "false",
                    )
                )
                .strip()
                .lower()
            )

            replace = replace_value in {
                "1",
                "true",
                "yes",
                "on",
            }

            safe_name = Path(filename).name

            if (
                not safe_name
                or safe_name != filename
                or not safe_name.lower().endswith(".mhaiplugin")
            ):
                self._send_json(
                    400,
                    {
                        "error": ("invalid_plugin_filename"),
                        "detail": ("Ungültiger .mhaiplugin-Dateiname."),
                    },
                )
                return

            if not expected_sha256:
                self._send_json(
                    400,
                    {
                        "error": ("missing_sha256"),
                        "detail": ("X-Plugin-SHA256 fehlt."),
                    },
                )
                return

            try:
                body = self._read_binary_body()
            except ValueError as error:
                self._send_json(
                    400,
                    {
                        "error": ("invalid_plugin_body"),
                        "detail": str(error),
                    },
                )
                return

            try:
                result = self.api.create_install_plan(
                    safe_name, body, expected_sha256, replace,
                    str(self.headers.get("X-Speech-Install-Profile", "cpu")).strip().lower(),
                )

            except PluginInstallError as error:
                self._send_json(
                    400,
                    {
                        "error": ("plugin_install_failed"),
                        "detail": str(error),
                    },
                )
                return

            except OSError as error:
                self._send_json(
                    500,
                    {
                        "error": ("plugin_io_error"),
                        "detail": str(error),
                    },
                )
                return

            self._send_json(
                200,
                result,
            )
            return

        if path == "/plugins":
            if not self._require_auth():
                return

            self._send_json(
                200,
                {"plugins": (self.api.plugin_load_results)},
            )
            return

        if path == "/workers":
            if not self._require_auth():
                return

            self._send_json(
                200,
                {"workers": (self.api.workers.list_workers())},
            )
            return

        if path.startswith("/jobs/") and path.endswith("/input"):
            if not self._require_auth():
                return

            job_id = path[len("/jobs/") : -len("/input")].strip("/")

            if not job_id:
                self._send_json(
                    400,
                    {
                        "error": "invalid_job_id",
                    },
                )
                return

            job = self.api.jobs.get(job_id)

            if job is None:
                self._send_json(
                    404,
                    {
                        "error": "job_not_found",
                        "job_id": job_id,
                    },
                )
                return

            if job.get("status") != "queued":
                self._send_json(
                    409,
                    {
                        "error": "job_not_queued",
                        "job_id": job_id,
                    },
                )
                return

            filename = str(
                self.headers.get(
                    "X-Input-Filename",
                    "",
                )
            ).strip()

            safe_name = Path(filename).name

            if not safe_name or safe_name != filename:
                self._send_json(
                    400,
                    {
                        "error": "invalid_input_filename",
                    },
                )
                return

            try:
                content_length = int(
                    self.headers.get(
                        "Content-Length",
                        "0",
                    )
                )
            except ValueError:
                content_length = 0

            if content_length <= 0:
                self._send_json(
                    400,
                    {
                        "error": "empty_input",
                    },
                )
                return

            upload_dir = self.api.runtime_dir / "job_inputs" / job_id

            upload_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            target = upload_dir / safe_name

            temporary = target.with_suffix(target.suffix + ".part")

            if temporary.exists():
                temporary.unlink()

            remaining = content_length

            try:
                with temporary.open("wb") as handle:
                    while remaining > 0:
                        chunk = self.rfile.read(
                            min(
                                remaining,
                                1024 * 1024,
                            )
                        )

                        if not chunk:
                            raise ValueError("Eingabedatei wurde nicht vollständig übertragen.")

                        handle.write(chunk)
                        remaining -= len(chunk)

                temporary.replace(target)

                updated = self.api.jobs.update_payload(
                    job_id,
                    {
                        "input": str(target),
                        "input_info": {
                            "filename": safe_name,
                            "size": content_length,
                        },
                    },
                )

            except Exception as error:
                if temporary.exists():
                    temporary.unlink()

                if target.exists():
                    target.unlink()

                self._send_json(
                    400,
                    {
                        "error": "input_upload_failed",
                        "detail": str(error),
                    },
                )
                return

            self._send_json(
                200,
                {
                    "job": updated,
                    "input": (updated.get("payload", {}).get("input", {})),
                },
            )
            return

        if path.startswith("/jobs/") and path.endswith("/execute"):
            if not self._require_auth():
                return

            job_id = path[len("/jobs/") : -len("/execute")].strip("/")

            if not job_id:
                self._send_json(
                    400,
                    {
                        "error": "invalid_job_id",
                    },
                )
                return

            try:
                job = self.api.dispatcher.execute(job_id)
            except KeyError:
                self._send_json(
                    404,
                    {
                        "error": "job_not_found",
                        "job_id": job_id,
                    },
                )
                return

            self._send_json(
                200,
                job,
            )
            return

        if path == "/jobs":
            if not self._require_auth():
                return

            payload = self._read_json()

            job_type = str(payload.get("job_type") or "").strip()

            if not job_type:
                self._send_json(
                    400,
                    {
                        "error": "invalid_job",
                        "detail": ("job_type ist erforderlich."),
                    },
                )
                return

            job = self.api.jobs.create(
                job_type=job_type,
                payload=(
                    payload.get("payload")
                    if isinstance(
                        payload.get("payload"),
                        dict,
                    )
                    else {}
                ),
                execution=(
                    payload.get("execution")
                    if isinstance(
                        payload.get("execution"),
                        dict,
                    )
                    else {}
                ),
            )

            self._send_json(
                201,
                job,
            )
            return

        if path == "/pair":
            payload = self._read_json()

            code = str(payload.get("code") or "").strip()

            if not self.api.pairing.validate(code):
                self._send_json(
                    403,
                    {
                        "error": "pairing_failed",
                        "detail": ("Pairing-Code ist ungueltig oder abgelaufen."),
                    },
                )
                return

            self._send_json(
                200,
                {
                    "status": "paired",
                    "node_id": (self.api.identity["node_id"]),
                    "node_name": (self.api.settings["node_name"]),
                    "node_type": ("windows_compute"),
                    "api_token": (self.api.api_token),
                },
            )
            return

        self._send_json(
            404,
            {
                "error": "not_found",
                "path": path or "/",
            },
        )

    def do_DELETE(self) -> None:
        path = self.path.split(
            "?",
            1,
        )[0].rstrip("/")

        if path.startswith("/plugins/plan/"):
            if not self._require_auth():
                return
            plan_id = path[len("/plugins/plan/") :]
            if not re.fullmatch(r"[0-9a-f]{32}", plan_id):
                self._send_json(400, {"error": "invalid_plan_id"})
                return
            self._send_json(200, self.api.cancel_install_plan(plan_id))
            return

        if path.startswith("/jobs/"):
            if not self._require_auth():
                return

            job_id = path[len("/jobs/") :].strip()

            job = self.api.jobs.cancel(job_id)

            if job is not None:
                self.api.dispatcher._cleanup_input(job_id)

            if job is None:
                self._send_json(
                    404,
                    {
                        "error": "job_not_found",
                        "job_id": job_id,
                    },
                )
                return

            self._send_json(
                200,
                job,
            )
            return

        self._send_json(
            404,
            {
                "error": "not_found",
                "path": path or "/",
            },
        )

    def do_GET(self) -> None:
        path = self.path.split(
            "?",
            1,
        )[0].rstrip("/")

        if path == "/status":
            self._send_status_page()
            return

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if path == "/health":
            self._send_json(
                200,
                self.api.health(),
            )
            return

        if path == "/pair/status":
            status = self.api.pairing.status()

            self._send_json(
                200,
                {
                    "pairing": status,
                    "node_id": (self.api.identity["node_id"]),
                },
            )
            return

        if path == "/plugins":
            if not self._require_auth():
                return

            self._send_json(
                200,
                {"plugins": (self.api.plugin_load_results)},
            )
            return

        if path == "/workers":
            if not self._require_auth():
                return

            self._send_json(
                200,
                {"workers": (self.api.workers.list_workers())},
            )
            return

        if path == "/jobs":
            if not self._require_auth():
                return

            self._send_json(
                200,
                {"jobs": (self.api.jobs.list_jobs())},
            )
            return

        if path.startswith("/jobs/"):
            if not self._require_auth():
                return

            job_id = path[len("/jobs/") :].strip()

            job = self.api.jobs.get(job_id)

            if job is None:
                self._send_json(
                    404,
                    {
                        "error": "job_not_found",
                        "job_id": job_id,
                    },
                )
                return

            self._send_json(
                200,
                job,
            )
            return

        if path == "/identity":
            if not self._require_auth():
                return

            self._send_json(
                200,
                self.api.identity_info(),
            )
            return

        if path == "/capabilities":
            if not self._require_auth():
                return

            self._send_json(
                200,
                self.api.capabilities_info(),
            )
            return

        self._send_json(
            404,
            {
                "error": "not_found",
                "path": path or "/",
            },
        )

    def _send_status_page(self) -> None:
        """Serve the local browser status page."""
        client_ip = str(self.client_address[0])

        if client_ip not in {"127.0.0.1", "::1"}:
            self._send_json(
                403,
                {
                    "error": "local_status_only",
                    "detail": "Die Statusseite ist nur lokal verfügbar.",
                },
            )
            return

        info = self.api.capabilities_info()
        identity = self.api.identity_info()

        plugin_results = list(getattr(self.api, "plugin_load_results", []) or [])
        plugin_rows = []

        for plugin in plugin_results:
            name = str(plugin.get("name") or plugin.get("plugin_id") or "Unbekannt")
            version = str(plugin.get("version") or "-")
            loaded = plugin.get("loaded")
            error = str(plugin.get("error") or plugin.get("detail") or "").strip()
            workers = plugin.get("workers") or []

            state_class = "starting"
            state_text = "Wird geprüft"

            if loaded is True:
                state_class = "ready"
                state_text = "Bereit"

            if error:
                state_class = "error"
                state_text = "Fehler"

            worker_text = ", ".join(str(item) for item in workers) or "Keine"

            error_html = ""

            if error:
                error_html = '<div class="plugin-error">' + html_lib.escape(error) + "</div>"

            plugin_rows.append(
                '<div class="plugin-row">'
                f'<span class="plugin-dot {state_class}"></span>'
                '<div class="plugin-info">'
                f"<strong>{html_lib.escape(name)}</strong>"
                f"<span>v{html_lib.escape(version)} · {state_text}</span>"
                f"<small>Worker: {html_lib.escape(worker_text)}</small>"
                f"{error_html}"
                "</div>"
                "</div>"
            )

        plugins_html = "".join(plugin_rows)

        if not plugins_html:
            plugins_html = '<div class="plugin-empty">Keine Plugins installiert oder geladen.</div>'

        accelerators = info.get("accelerators") or []
        gpu_names = (
            ", ".join(
                str(item.get("name", "")).strip()
                for item in accelerators
                if str(item.get("name", "")).strip()
            )
            or "Keine GPU erkannt"
        )

        platform_name = str(info.get("platform") or "Windows")
        machine = str(info.get("machine") or "AMD64")
        node_id = str(identity.get("node_id") or "Unbekannt")

        activity_status = self.api.activity.status()

        node_state = str(activity_status.get("state") or "ready")

        node_state_class = "ready"
        node_state_text = "Aktiv"
        node_state_detail = "Compute Node ist betriebsbereit"

        if node_state == "sleeping":
            node_state_class = "offline"
            node_state_text = "Ruhemodus"
            node_state_detail = "Plugins befinden sich im Ruhemodus"

        if node_state == "waking":
            node_state_class = "starting"
            node_state_text = "Wird aktiviert"
            node_state_detail = "Plugins werden aufgeweckt"

        if node_state == "error":
            node_state_class = "error"
            node_state_text = "Fehler"
            node_state_detail = str(activity_status.get("last_error") or "Lifecycle-Fehler")

        mediahub_connected = bool(activity_status.get("mediahub_connected"))

        mediahub_state_class = "offline"
        mediahub_state_text = "Nicht verbunden"

        if mediahub_connected:
            mediahub_state_class = "ready"
            mediahub_state_text = "Verbunden"

        active_jobs = int(activity_status.get("active_jobs") or 0)

        idle_seconds = activity_status.get("idle_seconds")
        idle_timeout = float(activity_status.get("idle_timeout_seconds") or 0.0)

        last_seen_text = "Noch kein Heartbeat"

        if idle_seconds is not None:
            last_seen_text = f"Vor {int(idle_seconds)} Sekunden"

        sleep_text = "Wartet auf MediaHub"

        if idle_seconds is not None:
            remaining = max(
                0,
                int(idle_timeout - float(idle_seconds)),
            )
            remaining_minutes = remaining // 60
            remaining_seconds = remaining % 60
            sleep_text = f"{remaining_minutes:02d}:{remaining_seconds:02d} Minuten"

        if node_state == "sleeping":
            sleep_text = "Aktiv"

        html = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MediaHub Compute Node</title>
<style>
:root {{
    color-scheme: dark;
    font-family: "Segoe UI", system-ui, sans-serif;
}}
* {{
    box-sizing: border-box;
}}
body {{
    margin: 0;
    min-height: 100vh;
    background: #0d1117;
    color: #f4f7fb;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
}}
.panel {{
    width: min(820px, 100%);
    background: #11151d;
    border: 1px solid #202938;
    border-radius: 18px;
    padding: 30px;
    box-shadow: 0 22px 70px rgba(0, 0, 0, .38);
}}
.header {{
    display: flex;
    gap: 18px;
    align-items: center;
}}
.logo {{
    width: 62px;
    height: 62px;
    border-radius: 16px;
    display: grid;
    place-items: center;
    font-size: 34px;
    font-weight: 800;
    color: #48c7ff;
    background: #17202c;
    box-shadow: 0 0 26px rgba(72, 199, 255, .18);
}}
h1 {{
    margin: 0;
    font-size: 27px;
}}
.version {{
    margin-top: 5px;
    color: #8e9aaa;
}}
.status {{
    margin-top: 28px;
    background: #19212c;
    border-radius: 14px;
    padding: 18px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #43d17b;
    box-shadow: 0 0 16px rgba(67, 209, 123, .6);
}}
.status strong {{
    font-size: 18px;
}}
.details {{
    margin-top: 18px;
    background: #151b24;
    border-radius: 14px;
    overflow: hidden;
}}
.row {{
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 24px;
    padding: 15px 20px;
    border-bottom: 1px solid #212a36;
}}
.row:last-child {{
    border-bottom: 0;
}}
.label {{
    color: #7f8b99;
}}
.value {{
    font-weight: 600;
    overflow-wrap: anywhere;
}}
.plugin-status-section {{
    margin-top: 22px;
    background: #151b24;
    border-radius: 14px;
    overflow: hidden;
}}

.plugin-status-title {{
    padding: 16px 20px;
    font-size: 18px;
    font-weight: 700;
    border-bottom: 1px solid #212a36;
}}

.plugin-row {{
    display: flex;
    gap: 14px;
    align-items: flex-start;
    padding: 15px 20px;
    border-bottom: 1px solid #212a36;
}}

.plugin-row:last-child {{
    border-bottom: 0;
}}

.plugin-dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-top: 5px;
    flex: 0 0 auto;
}}

.plugin-dot.ready {{
    background: #43d17b;
    box-shadow: 0 0 14px rgba(67, 209, 123, 0.6);
}}

.plugin-dot.starting {{
    background: #e8bd45;
    box-shadow: 0 0 14px rgba(232, 189, 69, 0.5);
}}

.plugin-dot.offline {{
    background: #697687;
    box-shadow: 0 0 10px rgba(105, 118, 135, 0.35);
}}

.plugin-dot.error {{
    background: #ef5b5b;
    box-shadow: 0 0 14px rgba(239, 91, 91, 0.55);
}}

.plugin-info {{
    display: flex;
    flex-direction: column;
    gap: 3px;
}}

.plugin-info span,
.plugin-info small {{
    color: #8e9aaa;
}}

.plugin-error {{
    color: #ff8080;
    margin-top: 4px;
    overflow-wrap: anywhere;
}}

.plugin-empty {{
    padding: 18px 20px;
    color: #8e9aaa;
}}
.footer {{
    margin-top: 20px;
    color: #697687;
    font-size: 13px;
}}
</style>
</head>
<body>
<main class="panel">
    <div class="header">
        <div class="logo">M</div>
        <div>
            <h1>MediaHub Compute Node</h1>
            <div class="version">Version {WINDOWS_COMPUTE_NODE_VERSION}</div>
        </div>
    </div>

    <div class="status">
        <span class="plugin-dot {node_state_class}"></span>
        <strong>{node_state_text}</strong>
        <span>{html_lib.escape(node_state_detail)}</span>
    </div>

    <div class="details">
        <div class="row">
            <div class="label">MediaHub</div>
            <div class="value">
                <span class="plugin-dot {mediahub_state_class}"></span>
                {mediahub_state_text}
            </div>
        </div>
        <div class="row">
            <div class="label">Letzte Aktivität</div>
            <div class="value">{last_seen_text}</div>
        </div>
        <div class="row">
            <div class="label">Aktive Jobs</div>
            <div class="value">{active_jobs}</div>
        </div>
        <div class="row">
            <div class="label">Ruhemodus</div>
            <div class="value">{sleep_text}</div>
        </div>
        <div class="row">
            <div class="label">Node-ID</div>
            <div class="value">{node_id}</div>
        </div>
        <div class="row">
            <div class="label">Port</div>
            <div class="value">8766</div>
        </div>
        <div class="row">
            <div class="label">Plattform</div>
            <div class="value">{platform_name} ({machine})</div>
        </div>
        <div class="row">
            <div class="label">Hardware</div>
            <div class="value">{gpu_names}</div>
        </div>
    </div>

    <section class="plugin-status-section">
        <div class="plugin-status-title">
            Installierte Plugins
        </div>
        {plugins_html}
    </section>
    <div class="footer">
        Lokale Statusseite · API-Token wird nicht angezeigt.
    </div>
</main>
</body>
</html>
"""

        payload = html.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(payload)),
        )
        self.send_header(
            "Cache-Control",
            "no-store",
        )
        self.end_headers()
        self.wfile.write(payload)

    def log_message(
        self,
        format: str,
        *args: object,
    ) -> None:
        print(
            "[HTTP]",
            self.address_string(),
            "-",
            format % args,
        )


def create_server(
    runtime_dir: Path,
    host: str,
    port: int,
) -> tuple[ThreadingHTTPServer, ComputeNodeAPI]:
    """Create the Compute Node API without starting its serve loop."""
    api = ComputeNodeAPI(runtime_dir)

    RequestHandler.api = api

    server = ThreadingHTTPServer(
        (host, port),
        RequestHandler,
    )

    return server, api


def run_server(
    runtime_dir: Path,
    host: str,
    port: int,
) -> None:
    server, api = create_server(
        runtime_dir=runtime_dir,
        host=host,
        port=port,
    )

    print(f"Compute-Node API aktiv: http://{host}:{port}")

    print(
        "Endpunkte: "
        "/health, /pair, /pair/status, "
        "/identity, /capabilities, "
        "/plugins, /workers, "
        "/jobs, /jobs/{id}, "
        "/jobs/{id}/execute"
    )

    print()
    print(
        "PAIRING-CODE:",
        api.pairing_code,
    )

    print(
        "Gueltig fuer:",
        api.pairing.lifetime_seconds,
        "Sekunden",
    )

    try:
        api.activity.start_watcher()
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("Compute-Node API wird beendet.")
    finally:
        api.activity.stop_watcher()
        server.server_close()
