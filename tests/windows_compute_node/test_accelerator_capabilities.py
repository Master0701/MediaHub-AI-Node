from __future__ import annotations

from windows_compute_node.hardware.capabilities import (
    build_capabilities,
)

SYSTEM = {
    "system": "Windows",
    "machine": "AMD64",
    "cpu": "Test CPU",
    "logical_cpu_count": 16,
}


def test_cpu_only():
    result = build_capabilities(
        system=SYSTEM,
        accelerators=[],
    )

    assert result["execution_modes"] == [
        "auto",
        "cpu",
    ]


def test_nvidia_gpu():
    result = build_capabilities(
        system=SYSTEM,
        accelerators=[
            {
                "kind": "gpu",
                "vendor": "NVIDIA",
                "name": "RTX Test",
                "detected": True,
            }
        ],
    )

    assert "gpu" in result[
        "execution_modes"
    ]


def test_amd_gpu():
    result = build_capabilities(
        system=SYSTEM,
        accelerators=[
            {
                "kind": "gpu",
                "vendor": "AMD",
                "name": "Radeon Test",
                "backend_family": [
                    "directml",
                    "rocm",
                ],
                "detected": True,
            }
        ],
    )

    assert "gpu" in result[
        "execution_modes"
    ]

    assert (
        result["accelerators"][0][
            "vendor"
        ]
        == "AMD"
    )


def test_intel_integrated_gpu():
    result = build_capabilities(
        system=SYSTEM,
        accelerators=[
            {
                "kind": "gpu",
                "vendor": "Intel",
                "name": "Intel Iris Test",
                "integrated": True,
                "backend_family": [
                    "openvino",
                    "directml",
                ],
                "detected": True,
            }
        ],
    )

    assert "gpu" in result[
        "execution_modes"
    ]

    assert (
        result["accelerators"][0][
            "integrated"
        ]
        is True
    )


def test_npu():
    result = build_capabilities(
        system=SYSTEM,
        accelerators=[
            {
                "kind": "npu",
                "vendor": "TestVendor",
                "name": "AI NPU Test",
                "backend_family": [
                    "test_backend",
                ],
                "detected": True,
            }
        ],
    )

    assert "npu" in result[
        "execution_modes"
    ]


def test_multiple_accelerators():
    result = build_capabilities(
        system=SYSTEM,
        accelerators=[
            {
                "kind": "gpu",
                "vendor": "NVIDIA",
                "name": "GPU 0",
                "detected": True,
            },
            {
                "kind": "gpu",
                "vendor": "AMD",
                "name": "GPU 1",
                "detected": True,
            },
            {
                "kind": "npu",
                "vendor": "Intel",
                "name": "NPU 0",
                "detected": True,
            },
        ],
    )

    assert "gpu" in result[
        "execution_modes"
    ]

    assert "npu" in result[
        "execution_modes"
    ]

    assert len(
        result["accelerators"]
    ) == 3


def test_detected_false_does_not_enable_gpu():
    result = build_capabilities(
        system=SYSTEM,
        accelerators=[
            {
                "kind": "gpu",
                "vendor": "AMD",
                "name": "Unavailable GPU",
                "detected": False,
            }
        ],
    )

    assert "gpu" not in result[
        "execution_modes"
    ]
