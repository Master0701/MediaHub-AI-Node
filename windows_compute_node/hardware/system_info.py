"""Basic platform-neutral hardware information."""

from __future__ import annotations

import os
import platform
from typing import Any


def get_system_info() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "cpu": platform.processor() or "unknown",
        "logical_cpu_count": os.cpu_count() or 1,
    }
