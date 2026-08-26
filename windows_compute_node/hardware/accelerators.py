"""Generic accelerator discovery for the Windows Compute Node."""

from __future__ import annotations

from typing import Any

from windows_compute_node.hardware.gpu_info import (
    get_windows_gpus,
)


def get_accelerators() -> list[dict[str, Any]]:
    accelerators: list[
        dict[str, Any]
    ] = []

    accelerators.extend(
        get_windows_gpus()
    )

    # Weitere echte Hardware-Detectoren
    # werden später hier ergänzt:
    #
    # - AMD GPU / iGPU
    # - Intel GPU / iGPU
    # - NPU / AI Accelerator
    #
    # Wichtig:
    # Nicht erkannte Hardware darf niemals
    # künstlich als verfügbar gemeldet werden.

    return accelerators
