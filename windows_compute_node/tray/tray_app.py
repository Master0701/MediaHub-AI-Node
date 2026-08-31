"""Windows system-tray integration for MediaHub Compute Node."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pystray
from PIL import Image

from windows_compute_node.tray.custom_menu import ComputeNodeTrayMenu
from windows_compute_node.tray.gui_host import TkGuiHost
from windows_compute_node.tray.info_window import ComputeNodeInfoWindow
from windows_compute_node.tray.status_window import ComputeNodeStatusWindow
from windows_compute_node.tray.windows_tray_icon import MediaHubWindowsIcon


class ComputeNodeTray:
    """Small Windows tray shell around the running Compute Node."""

    def __init__(
        self,
        *,
        icon_path: Path,
        runtime_dir: Path,
        version: str,
        node_id_provider: Callable[[], str],
        status_provider: Callable[[], str],
        info_provider: Callable[[], dict[str, Any]],
        runtime_status_provider: Callable[[], dict[str, Any]],
        pairing_code_provider: Callable[[], str],
        pairing_status_provider: Callable[[], dict[str, Any]],
        stop_callback: Callable[[], None],
        restart_callback: Callable[[], None],
        base_url: str = "http://127.0.0.1:8766",
    ) -> None:
        self.icon_path = Path(icon_path)
        self.runtime_dir = Path(runtime_dir)
        self.version = str(version)
        self.node_id_provider = node_id_provider
        self.status_provider = status_provider
        self.info_provider = info_provider
        self.runtime_status_provider = runtime_status_provider
        self.pairing_code_provider = pairing_code_provider
        self.pairing_status_provider = pairing_status_provider
        self.stop_callback = stop_callback
        self.restart_callback = restart_callback
        self.base_url = base_url.rstrip("/")
        self._icon: pystray.Icon | None = None
        self._gui_host = TkGuiHost()
        self._gui_host.start()
        self._status_window = ComputeNodeStatusWindow(
            gui_host=self._gui_host,
            version=self.version,
            node_id_provider=self.node_id_provider,
            info_provider=self.info_provider,
            runtime_status_provider=self.runtime_status_provider,
            pairing_code_provider=self.pairing_code_provider,
            pairing_status_provider=self.pairing_status_provider,
            icon_path=self.icon_path,
            open_browser_callback=self._open_browser,
            open_console_callback=self._open_console,
        )

        self._info_window = ComputeNodeInfoWindow(
            gui_host=self._gui_host,
            title="MediaHub Compute Node – Info",
            heading="MediaHub Compute Node",
            version=self.version,
            body_provider=self._info_body,
            icon_path=self.icon_path,
        )

        self._about_window = ComputeNodeInfoWindow(
            gui_host=self._gui_host,
            title="Über MediaHub",
            heading="Über MediaHub",
            version=self.version,
            body_provider=self._about_body,
            icon_path=self.icon_path,
        )

        self._custom_menu = ComputeNodeTrayMenu(
            gui_host=self._gui_host,
            icon_path=self.icon_path,
            version=self.version,
            runtime_status_provider=self.runtime_status_provider,
            show_status_callback=self._show_status,
            open_console_callback=self._open_console,
            open_browser_callback=self._open_browser,
            restart_callback=self._restart,
            exit_callback=self._exit,
            info_callback=self._show_info,
            about_callback=self._about_mediahub,
        )

    @property
    def log_path(self) -> Path:
        return self.runtime_dir / "logs" / "compute-node.log"

    def _image(self) -> Image.Image:
        return Image.open(self.icon_path).convert("RGBA")

    def _tooltip(self) -> str:
        status = self.runtime_status_provider()
        label = str(status.get("label") or "Läuft")
        return f"MediaHub Compute Node v{self.version} – {label}"

    def _show_status(self, _icon: object = None, _item: object = None) -> None:
        self._status_window.show()
    def _info_body(self) -> str:
        return (
            "Lokaler Windows-Ausführungsknoten für MediaHub.\\n\\n"
            f"Version: {self.version}\\n"
            f"Node-ID: {self.node_id_provider()}\\n"
            f"API: {self.base_url}\\n\\n"
            "Der Compute Node stellt Rechenleistung und installierte "
            "Worker für MediaHub bereit.\\n\\n"
            "Der API-Token wird aus Sicherheitsgründen nicht angezeigt."
        )

    def _show_info(self, *_args: object) -> None:
        self._info_window.show()

    def _about_body(self) -> str:
        return (
            "MediaHub Compute Node ist Teil des MediaHub-Ökosystems.\\n\\n"
            "Der Compute Node verarbeitet lokale Aufgaben für MediaHub "
            "und kann über installierbare Worker und Plugins erweitert "
            "werden.\\n\\n"
            "Windows Compute Node und Raspberry-Pi-AI-Node bleiben "
            "getrennte Ausführungsknoten und können je nach verfügbarer "
            "Hardware und installierten Fähigkeiten eingesetzt werden."
        )

    def _about_mediahub(self, *_args: object) -> None:
        self._about_window.show()

    def _open_console(self, _icon: object = None, _item: object = None) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.touch(exist_ok=True)

        escaped = str(self.log_path).replace("'", "''")
        command = (
            "$Host.UI.RawUI.WindowTitle='MediaHub Compute Node - Diagnose'; "
            f"Write-Host 'Log: {escaped}'; "
            "Write-Host ''; "
            f"Get-Content -LiteralPath '{escaped}' -Tail 100 -Wait"
        )
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoExit",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )

    def _open_browser(self, _icon: object = None, _item: object = None) -> None:
        webbrowser.open(f"{self.base_url}/status")

    def _restart(self, _icon: object = None, _item: object = None) -> None:
        threading.Thread(
            target=self.restart_callback,
            name="compute-node-restart",
            daemon=True,
        ).start()

    def _exit(
        self,
        _icon: object = None,
        _item: object = None,
    ) -> None:
        # Zuerst den API-Server kontrolliert herunterfahren.
        # stop_callback verweist in main.py auf stop_node().
        self.stop_callback()

        # Danach den gemeinsamen Tk-GUI-Host vollständig beenden.
        self._gui_host.stop(
            wait=True,
        )

        # Zuletzt die Tray-Schleife beenden, damit run() zurückkehrt
        # und der Hauptprozess regulär beendet werden kann.
        if self._icon is not None:
            self._icon.stop()

    def run(self) -> None:
        """Run the tray loop in the current thread."""
        self._icon = MediaHubWindowsIcon(
            "mediahub_compute_node",
            self._image(),
            self._tooltip(),
            menu=None,
            custom_menu_callback=self._custom_menu.show,
        )
        self._icon.run()

    def run_detached(self) -> threading.Thread:
        """Run the tray loop in a daemon thread."""
        thread = threading.Thread(
            target=self.run,
            name="compute-node-tray",
            daemon=True,
        )
        thread.start()
        return thread

    def notify_ready(self) -> None:
        if self._icon is None:
            return

        try:
            self._icon.notify(
                "Gestartet und bereit.",
                "MediaHub Compute Node",
            )
        except Exception:
            # Notifications are optional; the tray itself must keep working.
            pass


def frozen_executable() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(__file__).resolve()


def restart_current_process() -> None:
    """Start a fresh Compute Node process and exit this process."""
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()

        subprocess.Popen(
            [str(executable)],
            cwd=str(executable.parent),
            creationflags=(
                getattr(
                    subprocess,
                    "CREATE_NEW_PROCESS_GROUP",
                    0,
                )
                | getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                )
            ),
            close_fds=True,
        )
    else:
        python_executable = Path(
            sys.executable
        ).resolve()

        pythonw_executable = (
            python_executable.parent
            / "pythonw.exe"
        )

        if pythonw_executable.exists():
            launcher = pythonw_executable
        else:
            launcher = python_executable

        repository_root = Path(
            __file__
        ).resolve().parents[2]

        subprocess.Popen(
            [
                str(launcher),
                "-m",
                "windows_compute_node.main",
            ],
            cwd=str(repository_root),
            creationflags=(
                getattr(
                    subprocess,
                    "CREATE_NEW_PROCESS_GROUP",
                    0,
                )
                | getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                )
            ),
            close_fds=True,
        )

    os._exit(0)
