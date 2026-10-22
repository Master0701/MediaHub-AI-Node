from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

RUNTIME_FILE = (
    ROOT
    / "windows_compute_node"
    / "plugin_sources"
    / "speech_to_text"
    / "runtime.py"
)


def load_runtime():
    spec = (
        importlib.util.spec_from_file_location(
            "speech_runtime_provider_test",
            RUNTIME_FILE,
        )
    )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    assert spec.loader is not None

    spec.loader.exec_module(
        module
    )

    return module


def test_provider_loader():
    runtime = load_runtime()

    provider = (
        runtime
        ._load_python_runtime_provider()
    )

    assert (
        provider.PREFERRED_MINOR
        == 12
    )


def test_runtime_base_python_rejects_unsupported_host(monkeypatch):
    runtime = load_runtime()
    provider = runtime._load_python_runtime_provider()

    monkeypatch.setattr(
        provider,
        "inspect_managed_python",
        lambda: {
            "executable": "missing-python.exe",
            "available": False,
            "ready": False,
        },
    )

    with pytest.raises(RuntimeError, match="nicht bereit"):
        runtime.runtime_base_python()


def test_create_runtime_does_not_fallback_to_host_python(
    tmp_path, monkeypatch,
):
    runtime = load_runtime()
    provider = runtime._load_python_runtime_provider()

    monkeypatch.setattr(
        provider,
        "inspect_managed_python",
        lambda: {
            "executable": "missing-python.exe",
            "available": False,
            "ready": False,
        },
    )

    with pytest.raises(RuntimeError, match="nicht bereit"):
        runtime.create_runtime(tmp_path)

    assert not (
        tmp_path / "venv" / "Scripts" / "python.exe"
    ).is_file()



def test_speech_requires_managed_python(monkeypatch):
    runtime = load_runtime()
    provider = runtime._load_python_runtime_provider()

    def missing_managed_python():
        return {
            "executable": "missing-python.exe",
            "available": False,
            "ready": False,
        }

    def forbidden_fallback():
        raise AssertionError(
            "Speech darf nicht auf require_python zurueckfallen."
        )

    monkeypatch.setattr(
        provider,
        "inspect_managed_python",
        missing_managed_python,
    )
    monkeypatch.setattr(
        provider,
        "require_python",
        forbidden_fallback,
    )

    with pytest.raises(RuntimeError):
        runtime.runtime_base_python()
