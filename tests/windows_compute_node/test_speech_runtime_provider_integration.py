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


def test_runtime_base_python_rejects_unsupported_host():
    runtime = load_runtime()

    provider = (
        runtime
        ._load_python_runtime_provider()
    )

    discovery = (
        provider.discover_python()
    )

    if discovery["found"]:
        pytest.skip(
            "Kompatibler Runtime-Python "
            "ist auf diesem Rechner vorhanden."
        )

    with pytest.raises(provider.RuntimePythonError):
        runtime.runtime_base_python()


def test_create_runtime_does_not_fallback_to_host_python(
    tmp_path,
):
    runtime = load_runtime()

    provider = (
        runtime
        ._load_python_runtime_provider()
    )

    discovery = (
        provider.discover_python()
    )

    if discovery["found"]:
        pytest.skip(
            "Kompatibler Runtime-Python "
            "ist auf diesem Rechner vorhanden."
        )

    with pytest.raises(provider.RuntimePythonError):
        runtime.create_runtime(
            tmp_path
        )

    assert not (
        tmp_path
        / "venv"
        / "Scripts"
        / "python.exe"
    ).is_file()
