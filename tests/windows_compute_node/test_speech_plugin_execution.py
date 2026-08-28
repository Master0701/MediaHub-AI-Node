from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

EXECUTION = (
    ROOT
    / "windows_compute_node"
    / "plugin_sources"
    / "speech_to_text"
    / "execution.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "speech_execution_test",
        EXECUTION,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    assert spec.loader is not None

    spec.loader.exec_module(
        module
    )

    return module


def caps(*items):
    return {
        "accelerators": list(items)
    }


def test_cpu_mode():
    module = load_module()

    result = module.choose_backend(
        execution={
            "mode": "cpu",
            "cpu_threads": 4,
        },
        capabilities=caps(),
    )

    assert result["backend"] == "cpu"
    assert result["cpu_threads"] == 4


def test_auto_without_gpu_uses_cpu():
    module = load_module()

    result = module.choose_backend(
        execution={
            "mode": "auto",
            "cpu_threads": 2,
        },
        capabilities=caps(),
    )

    assert result["backend"] == "cpu"


def test_nvidia_gpu_uses_cuda():
    module = load_module()

    result = module.choose_backend(
        execution={"mode": "gpu"},
        capabilities=caps(
            {
                "id": "gpu0",
                "vendor": "NVIDIA",
                "kind": "gpu",
                "backend_family": [
                    "cuda",
                    "directml",
                ],
                "available": True,
            }
        ),
    )

    assert result["backend"] == "cuda"

    assert (
        result["accelerator"]["id"]
        == "gpu0"
    )


def test_amd_gpu_not_yet_supported_for_speech():
    module = load_module()

    with pytest.raises(
        RuntimeError
    ):
        module.choose_backend(
            execution={"mode": "gpu"},
            capabilities=caps(
                {
                    "id": "gpu0",
                    "vendor": "AMD",
                    "kind": "gpu",
                    "backend_family": [
                        "directml",
                        "rocm",
                    ],
                    "available": True,
                }
            ),
        )


def test_ati_alias_not_yet_supported_for_speech():
    module = load_module()

    with pytest.raises(
        RuntimeError
    ):
        module.choose_backend(
            execution={"mode": "gpu"},
            capabilities=caps(
                {
                    "id": "gpu0",
                    "vendor": "ATI",
                    "kind": "gpu",
                    "available": True,
                }
            ),
        )


def test_intel_integrated_not_yet_supported_for_speech():
    module = load_module()

    with pytest.raises(
        RuntimeError
    ):
        module.choose_backend(
            execution={"mode": "gpu"},
            capabilities=caps(
                {
                    "id": "igpu0",
                    "vendor": "Intel",
                    "kind": "integrated_gpu",
                    "integrated": True,
                    "backend_family": [
                        "openvino",
                        "directml",
                    ],
                    "available": True,
                }
            ),
        )


def test_gpu_without_accelerator_fails():
    module = load_module()

    with pytest.raises(
        RuntimeError
    ):
        module.choose_backend(
            execution={"mode": "gpu"},
            capabilities=caps(),
        )


def test_amd_igpu_before_nvidia_selects_nvidia():
    """Regression test for real hybrid AMD APU + NVIDIA systems."""

    module = load_module()

    result = module.choose_backend(
        execution={"mode": "gpu"},
        capabilities=caps(
            {
                "id": "gpu0",
                "vendor": "AMD",
                "name": "AMD Radeon Graphics",
                "kind": "integrated_gpu",
                "device_class": "integrated_gpu",
                "integrated": True,
                "backend_family": [
                    "directml",
                    "rocm",
                ],
                "available": True,
            },
            {
                "id": "gpu1",
                "vendor": "NVIDIA",
                "name": "NVIDIA GeForce RTX Test",
                "kind": "discrete_gpu",
                "device_class": "discrete_gpu",
                "integrated": False,
                "backend_family": [
                    "cuda",
                    "directml",
                ],
                "available": True,
            },
        ),
    )

    assert result["backend"] == "cuda"

    assert (
        result["accelerator"]["id"]
        == "gpu1"
    )

    assert (
        result["accelerator"]["vendor"]
        == "NVIDIA"
    )


def test_auto_amd_igpu_before_nvidia_selects_nvidia():
    module = load_module()

    result = module.choose_backend(
        execution={"mode": "auto"},
        capabilities=caps(
            {
                "id": "gpu0",
                "vendor": "AMD",
                "kind": "integrated_gpu",
                "integrated": True,
                "backend_family": [
                    "directml",
                    "rocm",
                ],
                "available": True,
            },
            {
                "id": "gpu1",
                "vendor": "NVIDIA",
                "kind": "discrete_gpu",
                "integrated": False,
                "backend_family": [
                    "cuda",
                ],
                "available": True,
            },
        ),
    )

    assert result["backend"] == "cuda"

    assert (
        result["accelerator"]["id"]
        == "gpu1"
    )


def test_auto_unsupported_amd_gpu_falls_back_cpu():
    module = load_module()

    result = module.choose_backend(
        execution={
            "mode": "auto",
            "cpu_threads": 6,
        },
        capabilities=caps(
            {
                "id": "gpu0",
                "vendor": "AMD",
                "kind": "gpu",
                "backend_family": [
                    "directml",
                    "rocm",
                ],
                "available": True,
            }
        ),
    )

    assert result["backend"] == "cpu"
    assert result["cpu_threads"] == 6


def test_specific_supported_accelerator():
    module = load_module()

    result = module.choose_backend(
        execution={
            "mode": "gpu",
            "accelerator": "gpu1",
        },
        capabilities=caps(
            {
                "id": "gpu0",
                "vendor": "AMD",
                "available": True,
            },
            {
                "id": "gpu1",
                "vendor": "NVIDIA",
                "kind": "gpu",
                "backend_family": [
                    "cuda",
                ],
                "available": True,
            },
        ),
    )

    assert result["backend"] == "cuda"

    assert (
        result["accelerator"]["id"]
        == "gpu1"
    )


def test_specific_unsupported_accelerator_fails():
    module = load_module()

    with pytest.raises(
        RuntimeError
    ):
        module.choose_backend(
            execution={
                "mode": "gpu",
                "accelerator": "gpu0",
            },
            capabilities=caps(
                {
                    "id": "gpu0",
                    "vendor": "AMD",
                    "kind": "integrated_gpu",
                    "backend_family": [
                        "directml",
                        "rocm",
                    ],
                    "available": True,
                },
                {
                    "id": "gpu1",
                    "vendor": "NVIDIA",
                    "kind": "gpu",
                    "backend_family": [
                        "cuda",
                    ],
                    "available": True,
                },
            ),
        )


def test_unavailable_accelerator_ignored():
    module = load_module()

    result = module.choose_backend(
        execution={"mode": "auto"},
        capabilities=caps(
            {
                "id": "gpu0",
                "vendor": "NVIDIA",
                "kind": "gpu",
                "backend_family": [
                    "cuda",
                ],
                "available": False,
            }
        ),
    )

    assert result["backend"] == "cpu"



@pytest.mark.parametrize(
    ("requested", "expected_name"),
    [
        ("1", "NVIDIA GeForce RTX 3070 Laptop GPU"),
        (
            "NVIDIA GeForce RTX 3070 Laptop GPU",
            "NVIDIA GeForce RTX 3070 Laptop GPU",
        ),
        (
            r"PCI\VEN_10DE&DEV_249D&SUBSYS_106C1043"
            r"&REV_A1\4&1BA6DC09&0&0009",
            "NVIDIA GeForce RTX 3070 Laptop GPU",
        ),
    ],
)
def test_specific_real_accelerator_identifiers(
    requested,
    expected_name,
):
    module = load_module()

    result = module.choose_backend(
        execution={
            "mode": "gpu",
            "accelerator": requested,
        },
        capabilities=caps(
            {
                "index": 0,
                "vendor": "AMD",
                "name": "AMD Radeon(TM) Graphics",
                "kind": "gpu",
                "device_class": "integrated_gpu",
                "integrated": True,
                "backend_family": [
                    "directml",
                    "rocm",
                ],
                "available": True,
            },
            {
                "index": 1,
                "vendor": "NVIDIA",
                "name": "NVIDIA GeForce RTX 3070 Laptop GPU",
                "kind": "gpu",
                "device_class": "discrete_gpu",
                "integrated": False,
                "backend_family": [
                    "cuda",
                    "directml",
                ],
                "available": True,
                "pnp_device_id": (
                    r"PCI\VEN_10DE&DEV_249D&SUBSYS_106C1043"
                    r"&REV_A1\4&1BA6DC09&0&0009"
                ),
            },
        ),
    )

    assert result["backend"] == "cuda"
    assert result["accelerator"]["index"] == 1
    assert (
        result["accelerator"]["name"]
        == expected_name
    )

def test_invalid_cpu_threads():
    module = load_module()

    with pytest.raises(
        ValueError
    ):
        module.normalize_execution(
            {
                "cpu_threads": 0
            }
        )
