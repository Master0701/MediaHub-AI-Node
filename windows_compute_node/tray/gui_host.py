"""Single Tk GUI host for the Windows Compute Node tray UI."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable


class TkGuiHost:
    """Own exactly one Tk interpreter in one dedicated GUI thread."""

    POLL_INTERVAL_MS = 25

    def __init__(self) -> None:
        self._queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._stopping = threading.Event()
        self._stopped = threading.Event()

    @property
    def root(self) -> tk.Tk:
        root = self._root
        if root is None:
            raise RuntimeError("Tk GUI host is not ready.")
        return root

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stopping.clear()
        self._stopped.clear()
        self._ready.clear()

        thread = threading.Thread(
            target=self._run,
            name="compute-node-tk-gui",
            daemon=True,
        )
        self._thread = thread
        thread.start()

        if not self._ready.wait(timeout=5.0):
            raise RuntimeError("Tk GUI host did not start.")

    def submit(self, callback: Callable[[], None]) -> None:
        if self._stopping.is_set():
            return
        self.start()
        self._queue.put(callback)

    def stop(
        self,
        *,
        wait: bool = True,
        timeout: float = 5.0,
    ) -> None:
        thread = self._thread

        if thread is None:
            return

        if not self._stopping.is_set():
            self._stopping.set()
            self._queue.put(self._shutdown)

        if (
            wait
            and threading.current_thread() is not thread
        ):
            self._stopped.wait(timeout=timeout)
            thread.join(timeout=timeout)

    def _shutdown(self) -> None:
        root = self._root
        if root is None:
            return
        try:
            root.quit()
        except tk.TclError:
            pass

    def _drain(self) -> None:
        root = self._root
        if root is None:
            return

        while True:
            try:
                callback = self._queue.get_nowait()
            except queue.Empty:
                break

            try:
                callback()
            except Exception:
                continue

        if not self._stopping.is_set():
            try:
                root.after(self.POLL_INTERVAL_MS, self._drain)
            except tk.TclError:
                pass

    def _run(self) -> None:
        root = tk.Tk()
        self._root = root
        root.withdraw()
        self._ready.set()
        root.after(self.POLL_INTERVAL_MS, self._drain)

        try:
            root.mainloop()
        finally:
            try:
                root.destroy()
            except tk.TclError:
                pass
            self._root = None
            self._ready.clear()
            self._thread = None
            self._stopped.set()
