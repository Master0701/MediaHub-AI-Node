"""Custom dark tray popup for MediaHub Compute Node."""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageTk

from windows_compute_node.tray.gui_host import TkGuiHost

BG = "#101722"
CARD = "#151f2d"
HOVER = "#203149"
TEXT = "#edf5ff"
MUTED = "#8fa4bd"
ACCENT = "#45a8ff"
GREEN = "#4bd28b"
RED = "#ff6b72"
DIVIDER = "#26364a"

WIDTH = 330
ROW_HEIGHT = 42


class ComputeNodeTrayMenu:
    """Dark MediaHub popup menu shown from the notification icon."""

    def __init__(
        self,
        *,
        gui_host: TkGuiHost,
        icon_path: Path,
        version: str,
        runtime_status_provider: Callable[[], dict[str, Any]],
        show_status_callback: Callable[[], None],
        open_console_callback: Callable[[], None],
        open_browser_callback: Callable[[], None],
        restart_callback: Callable[[], None],
        exit_callback: Callable[[], None],
        info_callback: Callable[[], None],
        about_callback: Callable[[], None],
    ) -> None:
        self.gui_host = gui_host
        self.icon_path = Path(icon_path)
        self.version = str(version)
        self.runtime_status_provider = runtime_status_provider

        self.show_status_callback = show_status_callback
        self.open_console_callback = open_console_callback
        self.open_browser_callback = open_browser_callback
        self.restart_callback = restart_callback
        self.exit_callback = exit_callback
        self.info_callback = info_callback
        self.about_callback = about_callback

        self._root: tk.Tk | None = None
        self._status_label: tk.Label | None = None
        self._status_dot: tk.Label | None = None
        self._images: list[ImageTk.PhotoImage] = []
        self._lock = threading.RLock()

    @staticmethod
    def _draw_icon(kind: str, size: int = 22) -> Image.Image:
        scale = 3
        canvas_size = size * scale

        image = Image.new(
            "RGBA",
            (canvas_size, canvas_size),
            (0, 0, 0, 0),
        )
        draw = ImageDraw.Draw(image)

        def p(value: float) -> int:
            return int(value * scale)

        line = p(1.7)
        fg = (187, 218, 245, 255)
        blue = (69, 168, 255, 255)
        danger = (255, 107, 114, 255)

        if kind == "status":
            draw.ellipse(
                (p(4), p(4), p(18), p(18)),
                outline=blue,
                width=line,
            )
            draw.ellipse(
                (p(9), p(9), p(13), p(13)),
                fill=blue,
            )

        elif kind == "console":
            draw.rounded_rectangle(
                (p(2), p(4), p(20), p(18)),
                radius=p(2),
                outline=fg,
                width=line,
            )
            draw.line(
                (p(6), p(8), p(9), p(11), p(6), p(14)),
                fill=blue,
                width=line,
                joint="curve",
            )
            draw.line(
                (p(11), p(14), p(16), p(14)),
                fill=fg,
                width=line,
            )

        elif kind == "browser":
            draw.ellipse(
                (p(3), p(3), p(19), p(19)),
                outline=blue,
                width=line,
            )
            draw.line(
                (p(3), p(11), p(19), p(11)),
                fill=fg,
                width=line,
            )
            draw.arc(
                (p(7), p(3), p(15), p(19)),
                90,
                270,
                fill=fg,
                width=line,
            )
            draw.arc(
                (p(7), p(3), p(15), p(19)),
                270,
                90,
                fill=fg,
                width=line,
            )

        elif kind == "restart":
            draw.arc(
                (p(3), p(3), p(19), p(19)),
                35,
                315,
                fill=blue,
                width=line,
            )
            draw.polygon(
                [
                    (p(17), p(3)),
                    (p(20), p(7)),
                    (p(15), p(7)),
                ],
                fill=blue,
            )

        elif kind == "exit":
            draw.arc(
                (p(4), p(5), p(18), p(20)),
                135,
                405,
                fill=danger,
                width=line,
            )
            draw.line(
                (p(11), p(2), p(11), p(11)),
                fill=danger,
                width=line,
            )

        elif kind == "info":
            draw.ellipse(
                (p(4), p(4), p(18), p(18)),
                outline=fg,
                width=line,
            )
            draw.ellipse(
                (p(10), p(7), p(12), p(9)),
                fill=blue,
            )
            draw.line(
                (p(11), p(11), p(11), p(15)),
                fill=blue,
                width=line,
            )

        elif kind == "mediahub":
            draw.rounded_rectangle(
                (p(3), p(3), p(19), p(19)),
                radius=p(4),
                outline=blue,
                width=line,
            )
            draw.line(
                (
                    p(7),
                    p(15),
                    p(7),
                    p(8),
                    p(11),
                    p(13),
                    p(15),
                    p(8),
                    p(15),
                    p(15),
                ),
                fill=fg,
                width=line,
                joint="curve",
            )

        return image.resize(
            (size, size),
            Image.Resampling.LANCZOS,
        )

    def _photo_icon(self, kind: str) -> ImageTk.PhotoImage:
        photo = ImageTk.PhotoImage(self._draw_icon(kind))
        self._images.append(photo)
        return photo

    def _close(self) -> None:
        root = self._root
        self._root = None

        # Widget-Referenzen zuerst lösen. Besonders PhotoImage-Objekte
        # dürfen nicht erst später auf einem fremden Thread freigegeben
        # werden, nachdem der gemeinsame Tk-Interpreter beendet wurde.
        self._status_label = None
        self._status_dot = None

        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass

        self._images.clear()

    def _invoke(self, callback: Callable[[], None]) -> None:
        self._close()
        callback()

    def _divider(self, parent: tk.Widget) -> None:
        tk.Frame(
            parent,
            bg=DIVIDER,
            height=1,
        ).pack(
            fill="x",
            padx=14,
            pady=5,
        )

    def _menu_row(
        self,
        parent: tk.Widget,
        *,
        text: str,
        icon: str,
        callback: Callable[[], None],
        danger: bool = False,
    ) -> None:
        row = tk.Frame(
            parent,
            bg=BG,
            height=ROW_HEIGHT,
            cursor="hand2",
        )
        row.pack(fill="x", padx=7)
        row.pack_propagate(False)

        photo = self._photo_icon(icon)

        icon_label = tk.Label(
            row,
            image=photo,
            bg=BG,
            borderwidth=0,
        )
        icon_label.pack(side="left", padx=(12, 11))

        label = tk.Label(
            row,
            text=text,
            bg=BG,
            fg=RED if danger else TEXT,
            font=("Segoe UI", 10),
            anchor="w",
        )
        label.pack(
            side="left",
            fill="both",
            expand=True,
        )

        widgets = (row, icon_label, label)

        def enter(_event: object) -> None:
            for widget in widgets:
                widget.configure(bg=HOVER)

        def leave(_event: object) -> None:
            for widget in widgets:
                widget.configure(bg=BG)

        def click(_event: object) -> None:
            self._invoke(callback)

        for widget in widgets:
            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)
            widget.bind("<ButtonRelease-1>", click)

    def _refresh_status(self) -> None:
        root = self._root

        if root is None:
            return

        try:
            status = self.runtime_status_provider()
            label = str(status.get("label") or "Läuft")
            working = bool(status.get("working", False))
            connected = bool(status.get("connected", False))

            if working:
                job_type = str(
                    status.get("active_job_type") or ""
                ).strip()
                label = (
                    f"Arbeitet: {job_type}"
                    if job_type
                    else "Arbeitet"
                )
            elif connected:
                label = "Verbunden"

            if self._status_label is not None:
                self._status_label.configure(text=label)

            if self._status_dot is not None:
                self._status_dot.configure(
                    fg=GREEN if connected or working else ACCENT
                )

            root.after(750, self._refresh_status)
        except tk.TclError:
            return

    def _build(self, x: int, y: int) -> None:
        with self._lock:
            self._close()

            root = tk.Toplevel(self.gui_host.root)
            self._root = root
            self._images.clear()

            root.withdraw()
            root.overrideredirect(True)
            root.configure(bg=BG)

            try:
                root.attributes("-topmost", True)
            except tk.TclError:
                pass

            outer = tk.Frame(
                root,
                bg=BG,
                highlightbackground=DIVIDER,
                highlightthickness=1,
            )
            outer.pack(fill="both", expand=True)

            header = tk.Frame(
                outer,
                bg=CARD,
                height=78,
            )
            header.pack(fill="x")
            header.pack_propagate(False)

            try:
                logo_image = Image.open(
                    self.icon_path
                ).convert("RGBA")
                logo_image.thumbnail((46, 46))

                logo = ImageTk.PhotoImage(logo_image)
                self._images.append(logo)

                tk.Label(
                    header,
                    image=logo,
                    bg=CARD,
                ).pack(
                    side="left",
                    padx=(15, 11),
                )
            except Exception:
                pass

            title_area = tk.Frame(header, bg=CARD)
            title_area.pack(
                side="left",
                fill="both",
                expand=True,
                pady=12,
            )

            tk.Label(
                title_area,
                text="MediaHub Compute Node",
                bg=CARD,
                fg=TEXT,
                font=("Segoe UI Semibold", 11),
                anchor="w",
            ).pack(fill="x")

            status_line = tk.Frame(
                title_area,
                bg=CARD,
            )
            status_line.pack(
                fill="x",
                pady=(4, 0),
            )

            self._status_dot = tk.Label(
                status_line,
                text="●",
                bg=CARD,
                fg=GREEN,
                font=("Segoe UI", 9),
            )
            self._status_dot.pack(side="left")

            self._status_label = tk.Label(
                status_line,
                text="Läuft",
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 9),
                anchor="w",
            )
            self._status_label.pack(
                side="left",
                padx=(5, 0),
            )

            version = tk.Label(
                header,
                text=f"v{self.version}",
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 8),
            )
            version.pack(
                side="right",
                anchor="n",
                padx=12,
                pady=13,
            )

            self._menu_row(
                outer,
                text="Status anzeigen",
                icon="status",
                callback=self.show_status_callback,
            )
            self._menu_row(
                outer,
                text="Diagnosekonsole",
                icon="console",
                callback=self.open_console_callback,
            )
            self._menu_row(
                outer,
                text="Im Browser öffnen",
                icon="browser",
                callback=self.open_browser_callback,
            )

            self._divider(outer)

            self._menu_row(
                outer,
                text="Neustart",
                icon="restart",
                callback=self.restart_callback,
            )
            self._menu_row(
                outer,
                text="Beenden",
                icon="exit",
                callback=self.exit_callback,
                danger=True,
            )

            self._divider(outer)

            self._menu_row(
                outer,
                text="Info",
                icon="info",
                callback=self.info_callback,
            )
            self._menu_row(
                outer,
                text="Über MediaHub",
                icon="mediahub",
                callback=self.about_callback,
            )

            root.update_idletasks()

            width = WIDTH
            height = root.winfo_reqheight()

            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()

            left = max(
                6,
                min(x - width, screen_width - width - 6),
            )
            top = max(
                6,
                min(y - height, screen_height - height - 6),
            )

            root.geometry(
                f"{width}x{height}+{left}+{top}"
            )

            def close_if_focus_lost(_event: object) -> None:
                root.after(100, self._check_focus)

            root.bind("<FocusOut>", close_if_focus_lost)
            root.bind("<Escape>", lambda _event: self._close())

            root.deiconify()
            root.lift()
            root.focus_force()

            self._refresh_status()

    def _check_focus(self) -> None:
        root = self._root

        if root is None:
            return

        try:
            if root.focus_displayof() is None:
                self._close()
        except tk.TclError:
            pass

    def show(self, x: int, y: int) -> None:
        """Schedule the custom popup on the single Tk GUI host."""
        left = int(x)
        top = int(y)
        self.gui_host.submit(lambda: self._build(left, top))
