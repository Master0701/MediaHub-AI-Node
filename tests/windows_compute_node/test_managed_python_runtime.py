from __future__ import annotations

from pathlib import Path

from windows_compute_node.runtime_support import python_runtime


def test_managed_python_inspection_exists():
    assert callable(
        getattr(python_runtime, "inspect_managed_python", None)
    )



def test_managed_python_missing(tmp_path):
    executable = tmp_path / "missing" / "python.exe"

    result = python_runtime.inspect_managed_python(executable)

    assert result["available"] is False
    assert result["ready"] is False
    assert result["executable"] == str(executable)



def test_managed_python_rejects_wrong_version():
    import sys

    if sys.version_info[:3] == (3, 12, 10):
        import pytest
        pytest.skip("Test-Python hat bereits die Zielversion.")

    result = python_runtime.inspect_managed_python(sys.executable)

    assert result["available"] is True
    assert result["ready"] is False
    assert "error" in result



def test_managed_python_accepts_portable_runtime():
    import os

    import pytest

    executable = (
        Path(os.environ["TEMP"])
        / "MediaHub-Python-Portable-Test"
        / "python.exe"
    )

    if not executable.is_file():
        pytest.skip("Portable Python-Testkopie nicht vorhanden.")

    result = python_runtime.inspect_managed_python(executable)

    assert result["available"] is True
    assert result["ready"] is True
