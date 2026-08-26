from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

FILE = (
    ROOT
    / "windows_compute_node"
    / "plugin_sources"
    / "speech_to_text"
    / "pip_bootstrap.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "speech_pip_bootstrap_test",
        FILE,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    assert spec.loader is not None

    spec.loader.exec_module(module)

    return module


def test_official_bootstrap_url():
    module = load_module()

    module.validate_bootstrap_url()


def test_http_bootstrap_rejected():
    module = load_module()

    with pytest.raises(
        module.PipBootstrapError
    ):
        module.validate_bootstrap_url(
            "http://bootstrap.pypa.io/get-pip.py"
        )


def test_wrong_domain_rejected():
    module = load_module()

    with pytest.raises(
        module.PipBootstrapError
    ):
        module.validate_bootstrap_url(
            "https://example.com/get-pip.py"
        )


def test_wrong_path_rejected():
    module = load_module()

    with pytest.raises(
        module.PipBootstrapError
    ):
        module.validate_bootstrap_url(
            "https://bootstrap.pypa.io/other.py"
        )


def test_missing_python():
    module = load_module()

    result = module.inspect_pip(
        Path("definitely_missing_python.exe")
    )

    assert result["available"] is False
    assert result["pip"] is False
