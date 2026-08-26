from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

MODULE_FILE = (
    ROOT
    / "windows_compute_node"
    / "plugin_sources"
    / "speech_to_text"
    / "python_runtime.py"
)


def load_module():
    spec = (
        importlib.util.spec_from_file_location(
            "speech_python_runtime_test",
            MODULE_FILE,
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


def test_missing_python():
    module = load_module()

    result = module.inspect_python(
        Path("Z:/definitely/missing/python.exe")
    )

    assert result["available"] is False
    assert result["supported"] is False


def test_current_python_is_inspectable():
    module = load_module()

    result = module.inspect_python(
        sys.executable
    )

    assert result["available"] is True
    assert result["major"] == 3
    assert result["bits"] == "64bit"


def test_python_314_not_supported():
    module = load_module()

    if sys.version_info[:2] != (3, 14):
        pytest.skip(
            "Dieser Entwicklungstest "
            "ist fuer Python 3.14 gedacht."
        )

    result = module.inspect_python(
        sys.executable
    )

    assert result["supported"] is False


def test_supported_minor_contract():
    module = load_module()

    assert (
        module.PREFERRED_MINOR
        == 12
    )

    assert (
        module.SUPPORTED_MINORS
        == (12, 11, 10, 9)
    )


def test_discovery_contract():
    module = load_module()

    result = module.discover_python()

    assert "found" in result
    assert "checked" in result

    if result["found"]:
        assert (
            result["python"]["supported"]
            is True
        )
    else:
        assert (
            result["required"][
                "preferred_minor"
            ]
            == 12
        )
