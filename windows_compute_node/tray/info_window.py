"""Dark information windows for the Windows Compute Node."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageTk

from windows_compute_node.tray.gui_host import TkGuiHost


class ComputeNodeInfoWindow:
    """Reusable dark information window."""

    def __init__(
        self,
        *,
        gui_host: TkGuiHost,
        title: str,
        heading: str,
        version: str,
        body_provider: Callable[[], str],
        icon_path: Path,
    ) -> None:
        self.gui_host = gui_host
        self.title = title
        self.heading = heading
        self.version = version
        self.body_provider = body_provider
        self.icon_path = icon_path

        self._root: tk.Toplevel | None = None
        self._logo_image: ImageTk.PhotoImage | None = None

    def show(self) -> None:
        """Show the information window through the shared Tk GUI host."""
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
                rgba.thumbnail((72, 72))
                return ImageTk.PhotoImage(rgba)
        except (OSError, ValueError):
            return None

    def _run(self) -> None:
        root = tk.Toplevel(self.gui_host.root)
        self._root = root

        root.title(self.title)
        root.geometry("680x470")
        root.minsize(620, 430)
        root.configure(bg="#11151d")
        root.protocol("WM_DELETE_WINDOW", self._close_window)

        try:
            root.iconbitmap(default=str(self.icon_path))
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
            pady=(0, 24),
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
            text=self.heading,
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

        card = tk.Frame(
            outer,
            bg="#171d26",
            padx=22,
            pady=20,
        )
        card.pack(
            fill="both",
            expand=True,
        )

        body = self.body_provider()

        tk.Label(
            card,
            text=body,
            font=("Segoe UI", 11),
            fg="#d8dee9",
            bg="#171d26",
            justify="left",
            anchor="nw",
            wraplength=570,
        ).pack(
            fill="both",
            expand=True,
        )

        button_area = tk.Frame(
            outer,
            bg="#11151d",
        )
        button_area.pack(
            fill="x",
            pady=(20, 0),
        )

        close_button = tk.Button(
            button_area,
            text="Schließen",
            command=self._close_window,
            font=("Segoe UI", 10, "bold"),
            fg="#f4f7fb",
            bg="#273142",
            activeforeground="#ffffff",
            activebackground="#344156",
            relief="flat",
            padx=24,
            pady=9,
            cursor="hand2",
        )
        close_button.pack(
            side="right",
        )
