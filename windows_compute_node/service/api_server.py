"""Minimal HTTP API for the Windows Compute Node."""

from __future__ import annotations

import hashlib
import json
import tempfile
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Any

from windows_compute_node.config.node_identity import (
    NodeIdentity,
)
from windows_compute_node.config.settings import (
    NodeSettings,
)
from windows_compute_node.hardware.capabilities import (
    get_capabilities,
)
from windows_compute_node.jobs.queue import (
    JobQueue,
)
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

        self.identity = NodeIdentity(
            self.runtime_dir
            / "node_identity.json"
        ).load_or_create()

        self.settings = NodeSettings(
            self.runtime_dir
            / "settings.json"
        ).load()

        self.token_store = NodeApiToken(
            self.runtime_dir
            / "security"
            / "api_token.json"
        )

        self.api_token = (
            self.token_store.load_or_create()
        )

        self.pairing = PairingManager(
            lifetime_seconds=600
        )

        self.pairing_code = (
            self.pairing.create_code()
        )

        self.jobs = JobQueue()
        self.runtime_status = ComputeNodeRuntimeStatus()
        self.workers = WorkerRegistry()

        self.dispatcher = JobDispatcher(
            jobs=self.jobs,
            workers=self.workers,
        )

        self.plugin_installer = (
            ComputePluginInstaller(
                plugin_root=(
                    self.runtime_dir
                    / "plugins"
                ),
            )
        )

        self.plugin_loader = (
            ComputePluginLoader(
                plugin_root=(
                    self.runtime_dir
                    / "plugins"
                ),
                workers=self.workers,
                capabilities_provider=(
                    get_capabilities
                ),
            )
        )

        self.plugin_load_results = (
            self.plugin_loader.load_all()
        )

    def reload_plugins(
        self,
    ) -> list[dict[str, Any]]:
        """Lädt Plugin- und Worker-Runtime vollständig neu."""

        self.workers = WorkerRegistry()

        self.dispatcher = JobDispatcher(
            jobs=self.jobs,
            workers=self.workers,
        )

        self.plugin_loader = (
            ComputePluginLoader(
                plugin_root=(
                    self.runtime_dir
                    / "plugins"
                ),
                workers=self.workers,
                capabilities_provider=(
                    get_capabilities
                ),
            )
        )

        self.plugin_load_results = (
            self.plugin_loader.load_all()
        )

        return self.plugin_load_results

    def uninstall_plugin(
        self,
        plugin_id: str,
    ) -> dict[str, Any]:
        result = self.plugin_installer.uninstall(
            plugin_id
        )

        loaded = self.reload_plugins()

        return {
            "uninstalled": True,
            "plugin": result,
            "plugins": loaded,
            "workers": self.workers.list_workers(),
        }

    def install_plugin_package(
        self,
        package_path: Path,
        *,
        expected_sha256: str,
        replace: bool = False,
    ) -> dict[str, Any]:
        package_path = Path(
            package_path
        )

        expected = (
            str(expected_sha256)
            .strip()
            .lower()
        )

        if not expected:
            raise PluginInstallError(
                "SHA-256-Prüfsumme fehlt."
            )

        digest = hashlib.sha256(
            package_path.read_bytes()
        ).hexdigest()

        if digest != expected:
            raise PluginInstallError(
                "SHA-256-Prüfsumme stimmt "
                "nicht mit dem Paket überein."
            )

        result = self.plugin_installer.install(
            package_path,
            replace=replace,
        )

        loaded = self.reload_plugins()

        plugin_id = str(
            result.get("plugin_id")
            or result.get("id")
            or ""
        )

        runtime_result = next(
            (
                item
                for item in loaded
                if isinstance(item, dict)
                and str(
                    item.get("plugin_id")
                    or item.get("id")
                    or ""
                )
                == plugin_id
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
            "node_name": self.settings[
                "node_name"
            ],
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

        if not authorization.startswith(
            prefix
        ):
            return None

        return authorization[
            len(prefix):
        ].strip()

    def _authorized(self) -> bool:
        connection = (
            self.api.settings.get(
                "connection"
            )
            or {}
        )

        if not connection.get(
            "require_authentication",
            True,
        ):
            return True

        return self.api.token_store.validate(
            self._bearer_token()
        )

    def _require_auth(self) -> bool:
        if self._authorized():
            self.api.runtime_status.mark_authenticated_request()
            return True

        self._send_json(
            401,
            {
                "error": "unauthorized",
                "detail": (
                    "Gueltiges Compute-Node-"
                    "API-Token erforderlich."
                ),
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
            data = json.loads(
                raw.decode("utf-8")
            )
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
            raise ValueError(
                "Leerer Request-Body."
            )

        if length > max_bytes:
            raise ValueError(
                "Plugin-Paket ist größer "
                "als 512 MiB."
            )

        body = self.rfile.read(
            length
        )

        if len(body) != length:
            raise ValueError(
                "Plugin-Paket wurde nicht "
                "vollständig übertragen."
            )

        return body

    def do_POST(self) -> None:
        path = self.path.split(
            "?",
            1,
        )[0].rstrip("/")

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
                    {
                        "error": (
                            "X-Plugin-ID fehlt."
                        )
                    },
                )
                return

            try:
                result = (
                    self.api.uninstall_plugin(
                        plugin_id
                    )
                )
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

        if path == "/plugins/install":
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

            replace_value = str(
                self.headers.get(
                    "X-Plugin-Replace",
                    "false",
                )
            ).strip().lower()

            replace = replace_value in {
                "1",
                "true",
                "yes",
                "on",
            }

            safe_name = Path(
                filename
            ).name

            if (
                not safe_name
                or safe_name != filename
                or not safe_name.lower().endswith(
                    ".mhaiplugin"
                )
            ):
                self._send_json(
                    400,
                    {
                        "error": (
                            "invalid_plugin_filename"
                        ),
                        "detail": (
                            "Ungültiger "
                            ".mhaiplugin-Dateiname."
                        ),
                    },
                )
                return

            if not expected_sha256:
                self._send_json(
                    400,
                    {
                        "error": (
                            "missing_sha256"
                        ),
                        "detail": (
                            "X-Plugin-SHA256 fehlt."
                        ),
                    },
                )
                return

            try:
                body = self._read_binary_body()
            except ValueError as error:
                self._send_json(
                    400,
                    {
                        "error": (
                            "invalid_plugin_body"
                        ),
                        "detail": str(error),
                    },
                )
                return

            try:
                with tempfile.TemporaryDirectory(
                    prefix=(
                        "mediahub_compute_upload_"
                    )
                ) as temp_name:
                    package = (
                        Path(temp_name)
                        / safe_name
                    )

                    package.write_bytes(
                        body
                    )

                    result = (
                        self.api
                        .install_plugin_package(
                            package,
                            expected_sha256=(
                                expected_sha256
                            ),
                            replace=replace,
                        )
                    )

            except PluginInstallError as error:
                self._send_json(
                    400,
                    {
                        "error": (
                            "plugin_install_failed"
                        ),
                        "detail": str(error),
                    },
                )
                return

            except OSError as error:
                self._send_json(
                    500,
                    {
                        "error": (
                            "plugin_io_error"
                        ),
                        "detail": str(error),
                    },
                )
                return

            self._send_json(
                201,
                result,
            )
            return

        if path == "/plugins":
            if not self._require_auth():
                return

            self._send_json(
                200,
                {
                    "plugins": (
                        self.api.plugin_load_results
                    )
                },
            )
            return

        if path == "/workers":
            if not self._require_auth():
                return

            self._send_json(
                200,
                {
                    "workers": (
                        self.api.workers.list_workers()
                    )
                },
            )
            return

        if (
            path.startswith("/jobs/")
            and path.endswith("/execute")
        ):
            if not self._require_auth():
                return

            job_id = path[
                len("/jobs/"):
                -len("/execute")
            ].strip("/")

            if not job_id:
                self._send_json(
                    400,
                    {
                        "error": "invalid_job_id",
                    },
                )
                return

            try:
                job = (
                    self.api.dispatcher.execute(
                        job_id
                    )
                )
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

            job_type = str(
                payload.get("job_type")
                or ""
            ).strip()

            if not job_type:
                self._send_json(
                    400,
                    {
                        "error": "invalid_job",
                        "detail": (
                            "job_type ist "
                            "erforderlich."
                        ),
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
                        payload.get(
                            "execution"
                        ),
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

            code = str(
                payload.get("code")
                or ""
            ).strip()

            if not self.api.pairing.validate(
                code
            ):
                self._send_json(
                    403,
                    {
                        "error": "pairing_failed",
                        "detail": (
                            "Pairing-Code ist "
                            "ungueltig oder abgelaufen."
                        ),
                    },
                )
                return

            self._send_json(
                200,
                {
                    "status": "paired",
                    "node_id": (
                        self.api.identity[
                            "node_id"
                        ]
                    ),
                    "node_name": (
                        self.api.settings[
                            "node_name"
                        ]
                    ),
                    "node_type": (
                        "windows_compute"
                    ),
                    "api_token": (
                        self.api.api_token
                    ),
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

        if path.startswith("/jobs/"):
            if not self._require_auth():
                return

            job_id = path[
                len("/jobs/"):
            ].strip()

            job = self.api.jobs.cancel(
                job_id
            )

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
            status = (
                self.api.pairing.status()
            )

            self._send_json(
                200,
                {
                    "pairing": status,
                    "node_id": (
                        self.api.identity[
                            "node_id"
                        ]
                    ),
                },
            )
            return

        if path == "/jobs":
            if not self._require_auth():
                return

            self._send_json(
                200,
                {
                    "jobs": (
                        self.api.jobs.list_jobs()
                    )
                },
            )
            return

        if path.startswith("/jobs/"):
            if not self._require_auth():
                return

            job_id = path[
                len("/jobs/"):
            ].strip()

            job = self.api.jobs.get(
                job_id
            )

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

        accelerators = info.get("accelerators") or []
        gpu_names = ", ".join(
            str(item.get("name", "")).strip()
            for item in accelerators
            if str(item.get("name", "")).strip()
        ) or "Keine GPU erkannt"

        platform_name = str(info.get("platform") or "Windows")
        machine = str(info.get("machine") or "AMD64")
        node_id = str(identity.get("node_id") or "Unbekannt")

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
        <div class="dot"></div>
        <strong>Läuft</strong>
        <span>Compute Node ist betriebsbereit</span>
    </div>

    <div class="details">
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
    api = ComputeNodeAPI(
        runtime_dir
    )

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

    print(
        f"Compute-Node API aktiv: "
        f"http://{host}:{port}"
    )

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
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print(
            "Compute-Node API wird beendet."
        )
    finally:
        server.server_close()
