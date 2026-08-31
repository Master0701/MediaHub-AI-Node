"""Windows pystray integration for the custom MediaHub tray menu."""

from __future__ import annotations

import ctypes
from collections.abc import Callable

import pystray._win32 as pystray_win32
from pystray._util import win32
from pystray._util.win32 import wintypes


class MediaHubWindowsIcon(pystray_win32.Icon):
    """Windows tray icon that opens our own popup on right click."""

    def __init__(
        self,
        *args: object,
        custom_menu_callback: Callable[[int, int], None],
        **kwargs: object,
    ) -> None:
        self._custom_menu_callback = custom_menu_callback
        super().__init__(*args, **kwargs)

    def _on_notify(self, wparam: int, lparam: int) -> None:
        if lparam == win32.WM_LBUTTONUP:
            self()
            return

        if lparam == win32.WM_RBUTTONUP:
            win32.SetForegroundWindow(self._hwnd)

            point = wintypes.POINT()
            win32.GetCursorPos(ctypes.byref(point))

            self._custom_menu_callback(
                int(point.x),
                int(point.y),
            )
