"""Capability discovery for the Windows Compute Node."""

from __future__ import annotations

from typing import Any

from windows_compute_node.hardware.accelerators import (
    get_accelerators,
)
from windows_compute_node.hardware.system_info import (
    get_system_info,
)


def build_capabilities(
    *,
    system: dict[str, Any],
    accelerators: list[dict[str, Any]],
) -> dict[str, Any]:
    has_gpu = any(
        item.get("kind") == "gpu"
        and item.get("detected") is True
        for item in accelerators
    )

    has_npu = any(
        item.get("kind") == "npu"
        and item.get("detected") is True
        for item in accelerators
    )

    modes = [
        "auto",
        "cpu",
    ]

    if has_gpu:
        modes.append("gpu")

    if has_npu:
        modes.append("npu")

    return {
        "node_type": "windows_compute",
        "platform": system["system"],
        "machine": system["machine"],
        "cpu": {
            "name": system["cpu"],
            "logical_threads": system[
                "logical_cpu_count"
            ],
            "available": True,
        },
        "accelerators": accelerators,
        "execution_modes": modes,
    }


def get_capabilities() -> dict[str, Any]:
    return build_capabilities(
        system=get_system_info(),
        accelerators=get_accelerators(),
    )
