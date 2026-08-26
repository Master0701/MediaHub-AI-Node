"""Tests for automatic CUDA runtime selection."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from windows_compute_node.plugin_sources.speech_to_text import (
    plugin,
)


def _context(
    capabilities: dict,
) -> dict:
    return {
        "capabilities": capabilities,
    }


def _capabilities(
    *,
    vendor: str,
    backend_family: list[str],
) -> dict:
    return {
        "accelerators": [
            {
                "index": 0,
                "kind": "gpu",
                "vendor": vendor,
                "name": "Test GPU",
                "integrated": False,
                "device_class": "discrete_gpu",
                "backend_family": backend_family,
                "available": True,
                "detected": True,
            }
        ]
    }


@pytest.fixture
def runtime_ready(
    monkeypatch,
):
    monkeypatch.setattr(
        plugin,
        "inspect_runtime",
        lambda: {
            "ready": True,
        },
    )

    monkeypatch.setattr(
        plugin,
        "venv_python",
        lambda: plugin.Path(
            "python.exe"
        ),
    )

    monkeypatch.setattr(
        plugin,
        "run_transcription",
        lambda **kwargs: {
            "engine": "mock",
            "text": "ok",
        },
    )


def test_cuda_backend_checks_cuda_runtime(
    monkeypatch,
    runtime_ready,
):
    inspect_cuda = Mock(
        return_value={
            "ready": True,
        }
    )

    install_cuda = Mock()

    monkeypatch.setattr(
        plugin,
        "inspect_cuda_runtime",
        inspect_cuda,
    )

    monkeypatch.setattr(
        plugin,
        "install_cuda_dependencies",
        install_cuda,
    )

    handler = plugin.create_handler(
        _context(
            _capabilities(
                vendor="NVIDIA",
                backend_family=[
                    "cuda",
                    "directml",
                ],
            )
        )
    )

    result = handler(
        {
            "execution": {
                "mode": "gpu",
            },
            "payload": {
                "input": "test.wav",
            },
        }
    )

    assert result["status"] == "completed"
    assert result["execution"]["backend"] == "cuda"

    inspect_cuda.assert_called_once_with()
    install_cuda.assert_not_called()


def test_missing_cuda_runtime_is_installed(
    monkeypatch,
    runtime_ready,
):
    inspect_cuda = Mock(
        return_value={
            "ready": False,
        }
    )

    install_cuda = Mock(
        return_value={
            "ready": True,
        }
    )

    monkeypatch.setattr(
        plugin,
        "inspect_cuda_runtime",
        inspect_cuda,
    )

    monkeypatch.setattr(
        plugin,
        "install_cuda_dependencies",
        install_cuda,
    )

    handler = plugin.create_handler(
        _context(
            _capabilities(
                vendor="NVIDIA",
                backend_family=[
                    "cuda",
                    "directml",
                ],
            )
        )
    )

    result = handler(
        {
            "execution": {
                "mode": "gpu",
            },
            "payload": {
                "input": "test.wav",
            },
        }
    )

    assert result["execution"]["backend"] == "cuda"

    inspect_cuda.assert_called_once_with()
    install_cuda.assert_called_once_with()


def test_cpu_backend_does_not_touch_cuda_runtime(
    monkeypatch,
    runtime_ready,
):
    inspect_cuda = Mock()
    install_cuda = Mock()

    monkeypatch.setattr(
        plugin,
        "inspect_cuda_runtime",
        inspect_cuda,
    )

    monkeypatch.setattr(
        plugin,
        "install_cuda_dependencies",
        install_cuda,
    )

    handler = plugin.create_handler(
        _context(
            _capabilities(
                vendor="NVIDIA",
                backend_family=[
                    "cuda",
                    "directml",
                ],
            )
        )
    )

    result = handler(
        {
            "execution": {
                "mode": "cpu",
            },
            "payload": {
                "input": "test.wav",
            },
        }
    )

    assert result["execution"]["backend"] == "cpu"

    inspect_cuda.assert_not_called()
    install_cuda.assert_not_called()


def test_non_cuda_gpu_does_not_install_nvidia_runtime(
    monkeypatch,
    runtime_ready,
):
    inspect_cuda = Mock()
    install_cuda = Mock()

    monkeypatch.setattr(
        plugin,
        "inspect_cuda_runtime",
        inspect_cuda,
    )

    monkeypatch.setattr(
        plugin,
        "install_cuda_dependencies",
        install_cuda,
    )

    handler = plugin.create_handler(
        _context(
            _capabilities(
                vendor="AMD",
                backend_family=[
                    "directml",
                ],
            )
        )
    )

    result = handler(
        {
            "execution": {
                "mode": "auto",
            },
            "payload": {
                "input": "test.wav",
            },
        }
    )

    assert result["execution"]["backend"] != "cuda"

    inspect_cuda.assert_not_called()
    install_cuda.assert_not_called()
