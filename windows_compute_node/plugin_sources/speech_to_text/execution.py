"""Execution selection for Speech-to-Text."""

from __future__ import annotations

from typing import Any

SUPPORTED_GPU_BACKENDS = (
    "cuda",
)


def normalize_execution(
    execution: dict[str, Any] | None,
) -> dict[str, Any]:
    """Normalize requested execution settings."""

    value = dict(execution or {})

    mode = str(
        value.get(
            "mode",
            "auto",
        )
    ).strip().lower()

    if mode not in {
        "auto",
        "cpu",
        "gpu",
    }:
        raise ValueError(
            f"Unbekannter Execution-Modus: {mode}"
        )

    cpu_threads = int(
        value.get(
            "cpu_threads",
            4,
        )
    )

    if cpu_threads < 1:
        raise ValueError(
            "cpu_threads muss mindestens 1 sein."
        )

    accelerator = value.get(
        "accelerator"
    )

    return {
        "mode": mode,
        "cpu_threads": cpu_threads,
        "accelerator": accelerator,
    }


def _is_available(
    accelerator: dict[str, Any],
) -> bool:
    """Return whether an accelerator is usable."""

    if accelerator.get(
        "detected"
    ) is False:
        return False

    if accelerator.get(
        "available"
    ) is False:
        return False

    return True


def _is_gpu(
    accelerator: dict[str, Any],
) -> bool:
    """Return whether an accelerator is GPU-like."""

    kind = str(
        accelerator.get(
            "kind",
            "",
        )
    ).strip().lower()

    return kind in {
        "gpu",
        "integrated_gpu",
        "discrete_gpu",
    }


def _backend_families(
    accelerator: dict[str, Any],
) -> list[str]:
    """Return normalized hardware backend families."""

    raw = accelerator.get(
        "backend_family"
    )

    if isinstance(raw, str):
        raw = [raw]

    if isinstance(raw, (list, tuple)):
        return [
            str(item).strip().lower()
            for item in raw
            if str(item).strip()
        ]

    # Compatibility for older capability records.
    vendor = str(
        accelerator.get(
            "vendor",
            "",
        )
    ).strip().lower()

    if "nvidia" in vendor:
        return ["cuda"]

    if (
        "amd" in vendor
        or "ati" in vendor
        or "advanced micro devices" in vendor
    ):
        return [
            "directml",
            "rocm",
        ]

    if "intel" in vendor:
        return [
            "openvino",
            "directml",
        ]

    return []


def _speech_backend(
    accelerator: dict[str, Any],
) -> str | None:
    """Map hardware capabilities to an implemented Speech backend."""

    families = _backend_families(
        accelerator
    )

    if "cuda" in families:
        return "cuda"

    # AMD/Intel hardware remains discoverable, but the
    # current faster-whisper engine has no DirectML,
    # ROCm or OpenVINO execution implementation yet.
    return None


def _is_integrated(
    accelerator: dict[str, Any],
) -> bool:
    kind = str(
        accelerator.get(
            "kind",
            "",
        )
    ).strip().lower()

    if kind == "integrated_gpu":
        return True

    if accelerator.get(
        "integrated"
    ) is True:
        return True

    device_class = str(
        accelerator.get(
            "device_class",
            "",
        )
    ).strip().lower()

    return device_class == "integrated_gpu"


def _gpu_candidates(
    capabilities: dict[str, Any],
) -> list[
    tuple[
        dict[str, Any],
        str,
    ]
]:
    """Return supported Speech GPU candidates in priority order."""

    candidates: list[
        tuple[
            dict[str, Any],
            str,
        ]
    ] = []

    for accelerator in capabilities.get(
        "accelerators",
        [],
    ):
        if not isinstance(
            accelerator,
            dict,
        ):
            continue

        if not _is_available(
            accelerator
        ):
            continue

        if not _is_gpu(
            accelerator
        ):
            continue

        backend = _speech_backend(
            accelerator
        )

        if backend is None:
            continue

        candidates.append(
            (
                accelerator,
                backend,
            )
        )

    # Prefer supported discrete GPUs over supported
    # integrated GPUs. Keep discovery order otherwise.
    candidates.sort(
        key=lambda item: (
            1
            if _is_integrated(item[0])
            else 0
        )
    )

    return candidates


def _specific_accelerator(
    *,
    accelerator_id: str,
    capabilities: dict[str, Any],
) -> dict[str, Any] | None:
    for accelerator in capabilities.get(
        "accelerators",
        [],
    ):
        if not isinstance(
            accelerator,
            dict,
        ):
            continue

        if str(
            accelerator.get(
                "id",
                "",
            )
        ) == accelerator_id:
            return accelerator

    return None


def _cpu_result(
    *,
    cpu_threads: int,
) -> dict[str, Any]:
    return {
        "mode": "cpu",
        "backend": "cpu",
        "cpu_threads": cpu_threads,
        "accelerator": None,
    }


def choose_backend(
    *,
    execution: dict[str, Any] | None,
    capabilities: dict[str, Any],
) -> dict[str, Any]:
    """Choose an actually implemented Speech execution backend."""

    normalized = normalize_execution(
        execution
    )

    mode = normalized["mode"]
    cpu_threads = normalized[
        "cpu_threads"
    ]
    requested_id = normalized[
        "accelerator"
    ]

    if mode == "cpu":
        return _cpu_result(
            cpu_threads=cpu_threads
        )

    if requested_id:
        accelerator = _specific_accelerator(
            accelerator_id=str(
                requested_id
            ),
            capabilities=capabilities,
        )

        if accelerator is None:
            raise RuntimeError(
                "Angeforderter Accelerator "
                f"'{requested_id}' wurde nicht gefunden."
            )

        if not _is_available(
            accelerator
        ):
            raise RuntimeError(
                "Angeforderter Accelerator "
                f"'{requested_id}' ist nicht verfuegbar."
            )

        if not _is_gpu(
            accelerator
        ):
            raise RuntimeError(
                "Angeforderter Accelerator "
                f"'{requested_id}' ist keine GPU."
            )

        backend = _speech_backend(
            accelerator
        )

        if backend is None:
            raise RuntimeError(
                "Der angeforderte Accelerator "
                f"'{requested_id}' wird vom aktuellen "
                "Speech-Backend noch nicht unterstuetzt."
            )

        return {
            "mode": mode,
            "backend": backend,
            "cpu_threads": cpu_threads,
            "accelerator": accelerator,
        }

    candidates = _gpu_candidates(
        capabilities
    )

    if candidates:
        accelerator, backend = candidates[0]

        return {
            "mode": mode,
            "backend": backend,
            "cpu_threads": cpu_threads,
            "accelerator": accelerator,
        }

    if mode == "auto":
        return _cpu_result(
            cpu_threads=cpu_threads
        )

    raise RuntimeError(
        "Keine vom aktuellen Speech-Backend "
        "unterstuetzte GPU verfuegbar."
    )
