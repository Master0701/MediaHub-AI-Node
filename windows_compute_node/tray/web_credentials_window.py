"""Web credential editor on the shared Tk GUI thread."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from windows_compute_node.security.web_credentials import NodeWebCredentials
from windows_compute_node.tray.gui_host import TkGuiHost


class WebCredentialsWindow:
    def __init__(self, *, gui_host: TkGuiHost, credentials_path: Path, on_saved=None) -> None:
        self.gui_host = gui_host
        self.credentials = NodeWebCredentials(credentials_path)
        self.on_saved = on_saved
        self._window: tk.Toplevel | None = None

    def show(self) -> None:
        self.gui_host.submit(self._show)

    def _show(self) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.lift()
            self._window.focus_force()
            return
        window = tk.Toplevel(self.gui_host.root)
        self._window = window
        window.title(
            "MediaHub – Webzugang verwalten"
            if self.credentials.configured()
            else "MediaHub – Webzugang einrichten"
        )
        window.geometry("440x410")
        window.resizable(False, False)
        window.configure(bg="#151f2d")
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        frame = tk.Frame(window, bg="#151f2d", padx=24, pady=16)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame, text="HTTPS-Webzugang", font=("Segoe UI", 15, "bold"), fg="#edf5ff", bg="#151f2d"
        ).pack(anchor="w", pady=(0, 12))
        configured = self.credentials.configured()
        entries: dict[str, tk.Entry] = {}
        fields = ([("old", "Bisheriges Passwort")] if configured else []) + [
            ("user", "Benutzername"),
            ("new", "Neues Passwort (1 bis 1024 Zeichen)"),
            ("confirm", "Passwort wiederholen"),
        ]
        for key, label in fields:
            tk.Label(frame, text=label, fg="#edf5ff", bg="#151f2d").pack(anchor="w")
            entry = tk.Entry(frame, show="•" if key != "user" else "", width=48)
            entry.pack(fill="x", pady=(2, 8))
            entries[key] = entry
        entries["user"].insert(0, "mediahub")

        def save() -> None:
            user = entries["user"].get().strip()
            new = entries["new"].get()
            if new != entries["confirm"].get():
                messagebox.showerror(
                    "Webzugang", "Passwörter stimmen nicht überein.", parent=window
                )
                return
            if configured:
                # Existing username is stored in the credential record.
                try:
                    import json

                    current_user = str(
                        json.loads(self.credentials.path.read_text(encoding="utf-8"))["username"]
                    )
                except (OSError, ValueError, KeyError, TypeError):
                    messagebox.showerror(
                        "Webzugang",
                        "Zugangsdaten beschädigt. Keine Änderung vorgenommen.",
                        parent=window,
                    )
                    return
                if not self.credentials.verify(current_user, entries["old"].get()):
                    messagebox.showerror(
                        "Webzugang", "Bisheriges Passwort ist falsch.", parent=window
                    )
                    return
            try:
                self.credentials.set_credentials(user, new)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Webzugang", str(exc), parent=window)
                return
            window.destroy()
            if self.on_saved is not None:
                try:
                    self.on_saved()
                except Exception:
                    import logging

                    logging.getLogger(__name__).exception(
                        "HTTPS-Start nach Einrichtung fehlgeschlagen"
                    )
            messagebox.showinfo(
                "Webzugang",
                "Zugangsdaten sicher gespeichert. Falls HTTPS konfiguriert ist, "
                "wird der Webzugang jetzt aktiviert.",
            )

        tk.Button(frame, text="Speichern", command=save, bg="#45a8ff", fg="#101722").pack(
            anchor="e", pady=(6, 0)
        )
        entries["user"].focus_set()
