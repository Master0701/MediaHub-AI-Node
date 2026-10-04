"""Shared activity/lifecycle state for MediaHub execution nodes."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class NodeActivityController:
    """Tracks MediaHub activity and controls node sleep/wake state."""

    def __init__(
        self,
        *,
        idle_timeout_seconds: float = 900.0,
        sleep_callback: Callable[[], None] | None = None,
        wake_callback: Callable[[], None] | None = None,
    ) -> None:
        self.idle_timeout_seconds = max(
            1.0,
            float(idle_timeout_seconds),
        )
        self.sleep_callback = sleep_callback
        self.wake_callback = wake_callback

        self._lock = threading.RLock()
        self._last_mediahub_activity: float | None = None
        self._active_jobs = 0
        self._sleeping = True
        self._waking = False
        self._last_error = ""

    def note_mediahub_activity(self) -> None:
        with self._lock:
            self._last_mediahub_activity = time.monotonic()

    def mediahub_heartbeat(self) -> None:
        """Record an authenticated MediaHub heartbeat and wake the node."""

        self.note_mediahub_activity()
        self.wake()

    def start_watcher(
        self,
        *,
        interval_seconds: float = 5.0,
    ) -> None:
        """Start the shared idle watcher once."""

        with self._lock:
            watcher = getattr(
                self,
                "_watcher_thread",
                None,
            )

            if (
                watcher is not None
                and watcher.is_alive()
            ):
                return

            stop_event = threading.Event()
            self._watcher_stop_event = stop_event

            watcher = threading.Thread(
                target=self._watch_loop,
                args=(
                    stop_event,
                    max(
                        1.0,
                        float(interval_seconds),
                    ),
                ),
                name="mediahub-node-activity",
                daemon=True,
            )

            self._watcher_thread = watcher

        watcher.start()

    def _watch_loop(
        self,
        stop_event: threading.Event,
        interval_seconds: float,
    ) -> None:
        while not stop_event.wait(
            interval_seconds
        ):
            self.check_idle()

    def stop_watcher(self) -> None:
        with self._lock:
            stop_event = getattr(
                self,
                "_watcher_stop_event",
                None,
            )
            watcher = getattr(
                self,
                "_watcher_thread",
                None,
            )

            self._watcher_stop_event = None
            self._watcher_thread = None

        if stop_event is not None:
            stop_event.set()

        if (
            watcher is not None
            and watcher is not threading.current_thread()
        ):
            watcher.join(timeout=2.0)
    def begin_job(self) -> None:
        self.note_mediahub_activity()
        self.wake()

        with self._lock:
            self._active_jobs += 1

    def end_job(self) -> None:
        with self._lock:
            self._active_jobs = max(
                0,
                self._active_jobs - 1,
            )
            self._last_mediahub_activity = time.monotonic()

    def wake(self) -> None:
        with self._lock:
            if not self._sleeping:
                return

            if self._waking:
                return

            self._waking = True
            self._last_error = ""

        try:
            if callable(self.wake_callback):
                self.wake_callback()

            with self._lock:
                self._sleeping = False

        except Exception as exc:
            with self._lock:
                self._last_error = (
                    f"{type(exc).__name__}: {exc}"
                )
            raise

        finally:
            with self._lock:
                self._waking = False
                self._last_mediahub_activity = time.monotonic()

    def sleep(self) -> bool:
        with self._lock:
            if self._sleeping:
                return True

            if self._active_jobs:
                return False

        try:
            if callable(self.sleep_callback):
                self.sleep_callback()

            with self._lock:
                self._sleeping = True
                self._last_error = ""

            return True

        except Exception as exc:
            with self._lock:
                self._last_error = (
                    f"{type(exc).__name__}: {exc}"
                )

            return False

    def check_idle(self) -> bool:
        with self._lock:
            if self._sleeping:
                return False

            if self._active_jobs:
                return False

            last_activity = self._last_mediahub_activity

        if last_activity is None:
            return False

        idle_for = time.monotonic() - last_activity

        if idle_for < self.idle_timeout_seconds:
            return False

        return self.sleep()

    def status(self) -> dict[str, Any]:
        with self._lock:
            last_activity = self._last_mediahub_activity

            idle_seconds = None

            if last_activity is not None:
                idle_seconds = max(
                    0.0,
                    time.monotonic() - last_activity,
                )

            mediahub_connected = (
                idle_seconds is not None
                and idle_seconds <= 30.0
            )

            state = "ready"

            if self._sleeping:
                state = "sleeping"

            if self._waking:
                state = "waking"

            if self._last_error:
                state = "error"

            return {
                "state": state,
                "sleeping": self._sleeping,
                "waking": self._waking,
                "active_jobs": self._active_jobs,
                "mediahub_connected": mediahub_connected,
                "mediahub_last_seen_seconds": idle_seconds,
                "idle_seconds": idle_seconds,
                "idle_timeout_seconds": (
                    self.idle_timeout_seconds
                ),
                "last_error": self._last_error,
            }


