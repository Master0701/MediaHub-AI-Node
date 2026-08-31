"""Native status window for MediaHub Compute Node."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image, ImageTk

from windows_compute_node.tray.gui_host import TkGuiHost


class ComputeNodeStatusWindow:
    """Dark status window for the Windows Compute Node."""

    REFRESH_INTERVAL_MS = 1000

    def __init__(
        self,
        *,
        gui_host: TkGuiHost,
        version: str,
        node_id_provider: Callable[[], str],
        info_provider: Callable[[], dict[str, Any]],
        runtime_status_provider: Callable[[], dict[str, Any]],
        pairing_code_provider: Callable[[], str],
        pairing_status_provider: Callable[[], dict[str, Any]],
        icon_path: Path,
        open_browser_callback: Callable[[], None],
        open_console_callback: Callable[[], None],
    ) -> None:
        self.gui_host = gui_host
        self.version = str(version)
        self.node_id_provider = node_id_provider
        self.info_provider = info_provider
        self.runtime_status_provider = runtime_status_provider
        self.pairing_code_provider = pairing_code_provider
        self.pairing_status_provider = pairing_status_provider
        self.icon_path = Path(icon_path)
        self.open_browser_callback = open_browser_callback
        self.open_console_callback = open_console_callback

        self._root: tk.Toplevel | None = None
        self._logo_image: ImageTk.PhotoImage | None = None

        self._status_label: tk.Label | None = None
        self._status_detail_label: tk.Label | None = None
        self._connection_value: tk.Label | None = None
        self._work_value: tk.Label | None = None
        self._pairing_value: tk.Label | None = None
        self._pairing_status_value: tk.Label | None = None

    def show(self) -> None:
        """Show the status window through the shared Tk GUI host."""
        self.gui_host.submit(self._show_on_gui_thread)

    def _show_on_gui_thread(self) -> None:
        root = self._root
        if root is not None:
            try:
                if root.winfo_exists():
                    self._bring_to_front()
                    return
            except tk.TclError:
                pass
        self._root = None
        self._run()

    def _close_window(self) -> None:
        root = self._root
        self._root = None
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass
        self._logo_image = None
        self._status_label = None
        self._status_detail_label = None
        self._connection_value = None
        self._work_value = None
        self._pairing_value = None
        self._pairing_status_value = None

    def _bring_to_front(self) -> None:
        root = self._root

        if root is None:
            return

        try:
            root.deiconify()
            root.lift()
            root.focus_force()
        except tk.TclError:
            pass

    def _load_logo(self) -> ImageTk.PhotoImage | None:
        try:
            with Image.open(self.icon_path) as image:
                rgba = image.convert("RGBA")
                rgba.thumbnail((76, 76))
                return ImageTk.PhotoImage(rgba)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _gpu_text(info: dict[str, Any]) -> str:
        accelerators = info.get("accelerators") or []

        names = [
            str(item.get("name", "")).strip()
            for item in accelerators
            if str(item.get("name", "")).strip()
        ]

        return ", ".join(names) or "Keine GPU erkannt"

    @staticmethod
    def _platform_text(info: dict[str, Any]) -> str:
        platform_name = str(
            info.get("platform") or "Windows"
        )

        machine = str(
            info.get("machine") or "AMD64"
        )

        return f"{platform_name} ({machine})"

    def _runtime_values(
        self,
    ) -> tuple[str, str, str, str]:
        status = self.runtime_status_provider()

        label = str(
            status.get("label") or "Läuft"
        )

        connected = bool(
            status.get("connected")
        )

        working = bool(
            status.get("working")
        )

        active_job_type = str(
            status.get("active_job_type") or ""
        ).strip()

        connection_text = (
            "Verbunden"
            if connected
            else "Nicht verbunden"
        )

        if working:
            if active_job_type:
                work_text = f"Arbeitet: {active_job_type}"
            else:
                work_text = "Arbeitet"

            detail = "Ein Compute-Auftrag wird ausgeführt."
        elif connected:
            work_text = "Bereit"
            detail = "Verbunden und bereit für Aufgaben."
        else:
            work_text = "Leerlauf"
            detail = "Compute Node läuft und wartet auf MediaHub."

        return (
            label,
            detail,
            connection_text,
            work_text,
        )

    def _refresh_runtime_status(self) -> None:
        root = self._root

        if root is None:
            return

        try:
            (
                label,
                detail,
                connection_text,
                work_text,
            ) = self._runtime_values()

            if self._status_label is not None:
                self._status_label.configure(
                    text=label,
                )

            if self._status_detail_label is not None:
                self._status_detail_label.configure(
                    text=detail,
                )

            if self._connection_value is not None:
                self._connection_value.configure(
                    text=connection_text,
                )

            if self._work_value is not None:
                self._work_value.configure(
                    text=work_text,
                )

            pairing_status = self.pairing_status_provider()
            pairing_active = bool(
                pairing_status.get("active", False)
            )
            pairing_used = bool(
                pairing_status.get("used", False)
            )
            expires = max(
                0,
                int(
                    pairing_status.get(
                        "expires_in_seconds",
                        0,
                    )
                    or 0
                ),
            )

            code = str(
                self.pairing_code_provider() or ""
            ).strip()

            if pairing_used:
                pairing_text = "Bereits verwendet"
                pairing_state_text = "MediaHub gekoppelt"
            elif pairing_active and code:
                pairing_text = code
                minutes, seconds = divmod(
                    expires,
                    60,
                )
                pairing_state_text = (
                    f"Gültig: {minutes:02d}:{seconds:02d}"
                )
            elif code:
                pairing_text = "Abgelaufen"
                pairing_state_text = (
                    "Neustart erzeugt einen neuen Code"
                )
            else:
                pairing_text = "Nicht verfügbar"
                pairing_state_text = "Kein aktiver Pairing-Code"

            if self._pairing_value is not None:
                self._pairing_value.configure(
                    text=pairing_text,
                )

            if self._pairing_status_value is not None:
                self._pairing_status_value.configure(
                    text=pairing_state_text,
                )

            root.after(
                self.REFRESH_INTERVAL_MS,
                self._refresh_runtime_status,
            )
        except tk.TclError:
            return

    def _add_detail_row(
        self,
        parent: tk.Frame,
        *,
        row: int,
        name: str,
        value: str,
    ) -> tk.Label:
        tk.Label(
            parent,
            text=name,
            font=("Segoe UI", 10),
            fg="#8e9aaa",
            bg="#171d26",
            anchor="w",
        ).grid(
            row=row,
            column=0,
            sticky="nw",
            padx=(0, 24),
            pady=7,
        )

        value_label = tk.Label(
            parent,
            text=value,
            font=("Segoe UI", 10, "bold"),
            fg="#f4f7fb",
            bg="#171d26",
            anchor="w",
            justify="left",
            wraplength=430,
        )

        value_label.grid(
            row=row,
            column=1,
            sticky="nw",
            pady=7,
        )

        return value_label

    def _run(self) -> None:
        root = tk.Toplevel(self.gui_host.root)
        self._root = root

        root.title("MediaHub Compute Node – Status")
        root.geometry("720x570")
        root.minsize(680, 520)
        root.configure(bg="#11151d")
        root.protocol(
            "WM_DELETE_WINDOW",
            self._close_window,
        )

        try:
            root.iconbitmap(
                default=str(self.icon_path),
            )
        except tk.TclError:
            pass

        outer = tk.Frame(
            root,
            bg="#11151d",
            padx=28,
            pady=26,
        )
        outer.pack(
            fill="both",
            expand=True,
        )

        header = tk.Frame(
            outer,
            bg="#11151d",
        )
        header.pack(
            fill="x",
            pady=(0, 22),
        )

        self._logo_image = self._load_logo()

        if self._logo_image is not None:
            logo = tk.Label(
                header,
                image=self._logo_image,
                bg="#11151d",
            )
        else:
            logo = tk.Label(
                header,
                text="M",
                font=("Segoe UI", 34, "bold"),
                fg="#48c7ff",
                bg="#17202c",
                width=2,
            )

        logo.pack(
            side="left",
            padx=(0, 18),
        )

        title_area = tk.Frame(
            header,
            bg="#11151d",
        )
        title_area.pack(
            side="left",
            fill="x",
            expand=True,
        )

        tk.Label(
            title_area,
            text="MediaHub Compute Node",
            font=("Segoe UI", 21, "bold"),
            fg="#f4f7fb",
            bg="#11151d",
            anchor="w",
        ).pack(
            fill="x",
        )

        tk.Label(
            title_area,
            text=f"Version {self.version}",
            font=("Segoe UI", 10),
            fg="#8e9aaa",
            bg="#11151d",
            anchor="w",
        ).pack(
            fill="x",
            pady=(5, 0),
        )

        status_card = tk.Frame(
            outer,
            bg="#171d26",
            padx=22,
            pady=18,
        )
        status_card.pack(
            fill="x",
            pady=(0, 16),
        )

        status_line = tk.Frame(
            status_card,
            bg="#171d26",
        )
        status_line.pack(
            fill="x",
        )

        tk.Label(
            status_line,
            text="●",
            font=("Segoe UI", 16, "bold"),
            fg="#55d98b",
            bg="#171d26",
        ).pack(
            side="left",
            padx=(0, 10),
        )

        self._status_label = tk.Label(
            status_line,
            text="Läuft",
            font=("Segoe UI", 15, "bold"),
            fg="#f4f7fb",
            bg="#171d26",
            anchor="w",
        )
        self._status_label.pack(
            side="left",
        )

        self._status_detail_label = tk.Label(
            status_card,
            text="Compute Node läuft.",
            font=("Segoe UI", 10),
            fg="#9ba7b8",
            bg="#171d26",
            anchor="w",
        )
        self._status_detail_label.pack(
            fill="x",
            pady=(8, 0),
        )

        info = self.info_provider()

        details = tk.Frame(
            outer,
            bg="#171d26",
            padx=22,
            pady=16,
        )
        details.pack(
            fill="both",
            expand=True,
        )
        details.grid_columnconfigure(
            1,
            weight=1,
        )

        self._add_detail_row(
            details,
            row=0,
            name="Node-ID",
            value=self.node_id_provider(),
        )

        self._add_detail_row(
            details,
            row=1,
            name="Port",
            value="8766",
        )

        self._add_detail_row(
            details,
            row=2,
            name="Plattform",
            value=self._platform_text(info),
        )

        self._add_detail_row(
            details,
            row=3,
            name="Hardware",
            value=self._gpu_text(info),
        )

        self._connection_value = self._add_detail_row(
            details,
            row=4,
            name="Verbindung",
            value="Nicht verbunden",
        )

        self._work_value = self._add_detail_row(
            details,
            row=5,
            name="Auslastung",
            value="Leerlauf",
        )

        self._pairing_value = self._add_detail_row(
            details,
            row=6,
            name="Pairing-Code",
            value="Wird geladen …",
        )

        self._pairing_status_value = self._add_detail_row(
            details,
            row=7,
            name="Pairing",
            value="Wird geprüft …",
        )

        def copy_pairing_code() -> None:
            status = self.pairing_status_provider()

            if not bool(status.get("active", False)):
                return

            code = str(
                self.pairing_code_provider() or ""
            ).strip()

            if not code:
                return

            root.clipboard_clear()
            root.clipboard_append(code)
            root.update()

        copy_button = tk.Button(
            details,
            text="Kopieren",
            command=copy_pairing_code,
            bg="#1d2838",
            fg="#e8f4ff",
            activebackground="#26374c",
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=5,
            cursor="hand2",
        )
        copy_button.grid(
            row=6,
            column=2,
            padx=(8, 16),
            pady=5,
            sticky="e",
        )

        buttons = tk.Frame(
            outer,
            bg="#11151d",
        )
        buttons.pack(
            fill="x",
            pady=(20, 0),
        )

        browser_button = tk.Button(
            buttons,
            text="Im Browser öffnen",
            command=self.open_browser_callback,
            font=("Segoe UI", 10, "bold"),
            fg="#f4f7fb",
            bg="#1c6ea4",
            activeforeground="#ffffff",
            activebackground="#2788c5",
            relief="flat",
            padx=18,
            pady=9,
            cursor="hand2",
        )
        browser_button.pack(
            side="left",
        )

        console_button = tk.Button(
            buttons,
            text="Diagnosekonsole",
            command=self.open_console_callback,
            font=("Segoe UI", 10, "bold"),
            fg="#f4f7fb",
            bg="#273142",
            activeforeground="#ffffff",
            activebackground="#344156",
            relief="flat",
            padx=18,
            pady=9,
            cursor="hand2",
        )
        console_button.pack(
            side="left",
            padx=(10, 0),
        )

        close_button = tk.Button(
            buttons,
            text="Schließen",
            command=self._close_window,
            font=("Segoe UI", 10, "bold"),
            fg="#f4f7fb",
            bg="#273142",
            activeforeground="#ffffff",
            activebackground="#344156",
            relief="flat",
            padx=22,
            pady=9,
            cursor="hand2",
        )
        close_button.pack(
            side="right",
        )

        self._refresh_runtime_status()
