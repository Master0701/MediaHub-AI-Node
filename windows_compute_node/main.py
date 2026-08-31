"""Windows entry point for the MediaHub Compute Node."""

from __future__ import annotations

import logging
import os
import sys
import threading
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
from windows_compute_node.service.api_server import (
    create_server,
)
from windows_compute_node.tray.tray_app import (
    ComputeNodeTray,
    restart_current_process,
)
from windows_compute_node.version import (
    WINDOWS_COMPUTE_NODE_VERSION,
)


def _runtime_dir() -> Path:
    """Return the persistent Windows Compute Node runtime directory."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent / "runtime"

    executable_dir = (
        Path(sys.executable)
        .resolve()
        .parent
    )

    installed_marker = (
        executable_dir
        / "installed.mode"
    )

    if installed_marker.is_file():
        program_data = os.environ.get(
            "PROGRAMDATA",
            "",
        ).strip()

        if program_data:
            return (
                Path(program_data)
                / "MediaHub"
                / "ComputeNode"
            )

    return executable_dir / "runtime"


def _resource_path(
    relative_path: str,
) -> Path:
    """Return a source or PyInstaller bundled resource path."""
    bundle_root = getattr(
        sys,
        "_MEIPASS",
        None,
    )

    if bundle_root:
        return (
            Path(bundle_root)
            / relative_path
        )

    return (
        Path(__file__).resolve().parent
        / relative_path
    )


def _status_text(
    identity: dict[str, Any],
    settings: dict[str, Any],
) -> str:
    return (
        "MediaHub Compute Node läuft\n\n"
        f"Version: {WINDOWS_COMPUTE_NODE_VERSION}\n"
        f"Node-ID: {identity['node_id']}\n"
        f"Name: {settings['node_name']}\n"
        f"Port: {settings['listen_port']}"
    )


def _info_text(
    identity: dict[str, Any],
    settings: dict[str, Any],
    capabilities: dict[str, Any],
) -> str:
    cpu = capabilities["cpu"]

    accelerator_names = []

    for device in capabilities["accelerators"]:
        name = str(
            device.get("name")
            or "Unbekannt"
        )

        accelerator_names.append(name)

    accelerators = (
        ", ".join(accelerator_names)
        if accelerator_names
        else "Keine"
    )

    return (
        "MediaHub Compute Node\n\n"
        f"Version: {WINDOWS_COMPUTE_NODE_VERSION}\n"
        f"Node-ID: {identity['node_id']}\n"
        f"Name: {settings['node_name']}\n"
        f"Platform: {capabilities['platform']} "
        f"{capabilities['machine']}\n"
        f"CPU: {cpu['name']}\n"
        f"Beschleuniger: {accelerators}\n"
        f"API-Port: {settings['listen_port']}"
    )



def _configure_logging(runtime: Path) -> Path:
    """Configure persistent Compute Node logging."""
    log_dir = runtime / "logs"
    log_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_path = log_dir / "compute-node.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        log_path,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Beim normalen Quellstart bleibt die Konsole zusätzlich hilfreich.
    # Eine windowed PyInstaller-EXE besitzt dagegen kein stdout/stderr.
    if (
        not getattr(sys, "frozen", False)
        and sys.stderr is not None
    ):
        console_handler = logging.StreamHandler(
            sys.stderr
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return log_path


def main() -> int:
    runtime = _runtime_dir()
    runtime.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_path = _configure_logging(runtime)
    logger = logging.getLogger(
        "windows_compute_node"
    )

    logger.info(
        "MediaHub Compute Node v%s startet.",
        WINDOWS_COMPUTE_NODE_VERSION,
    )
    logger.info(
        "Runtime-Verzeichnis: %s",
        runtime,
    )
    logger.info(
        "Logdatei: %s",
        log_path,
    )

    identity = NodeIdentity(
        runtime / "node_identity.json"
    ).load_or_create()

    settings = NodeSettings(
        runtime / "settings.json"
    ).load()

    capabilities = get_capabilities()

    host = str(
        settings["listen_host"]
    )

    port = int(
        settings["listen_port"]
    )

    server, api = create_server(
        runtime_dir=runtime,
        host=host,
        port=port,
    )

    server_thread = threading.Thread(
        target=server.serve_forever,
        name="compute-node-api",
        daemon=True,
    )

    server_thread.start()

    logger.info(
        "Compute-Node-API gestartet: %s:%s",
        host,
        port,
    )

    shutdown_lock = threading.Lock()
    shutting_down = False

    def stop_node() -> None:
        nonlocal shutting_down

        with shutdown_lock:
            if shutting_down:
                return

            shutting_down = True

        logger.info(
            "MediaHub Compute Node wird beendet."
        )

        server.shutdown()
        server.server_close()

        logger.info(
            "Compute-Node-API beendet."
        )

    def restart_node() -> None:
        logger.info(
            "Neustart wurde angefordert."
        )
        stop_node()
        restart_current_process()

    tray = ComputeNodeTray(
        icon_path=_resource_path(
            "assets/MediaHub-Compute-Node.ico"
        ),
        runtime_dir=runtime,
        version=WINDOWS_COMPUTE_NODE_VERSION,
        node_id_provider=lambda: str(
            api.identity["node_id"]
        ),
        status_provider=lambda: _status_text(
            identity,
            settings,
        ),
        info_provider=lambda: capabilities,
        runtime_status_provider=lambda: (
            api.runtime_status.snapshot(
                api.jobs.list_jobs()
            )
        ),
        pairing_code_provider=lambda: str(
            api.pairing_code or ""
        ),
        pairing_status_provider=api.pairing.status,
        stop_callback=stop_node,
        restart_callback=restart_node,
        base_url=(
            f"http://127.0.0.1:{port}"
        ),
    )

    try:
        logger.info(
            "Tray-Oberfläche gestartet."
        )
        tray.run()
    except Exception:
        logger.exception(
            "Unbehandelter Fehler im Windows Compute Node."
        )
        raise
    finally:
        stop_node()
        logging.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
