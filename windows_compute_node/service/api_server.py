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


def run_server(
    runtime_dir: Path,
    host: str,
    port: int,
) -> None:
    api = ComputeNodeAPI(
        runtime_dir
    )

    RequestHandler.api = api

    server = ThreadingHTTPServer(
        (host, port),
        RequestHandler,
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
