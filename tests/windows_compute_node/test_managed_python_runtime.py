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
    import sys

    import pytest

    if sys.platform != "win32":
        pytest.skip("Portable Python-Runtime ist nur unter Windows verfÃ¼gbar.")

    # Use a real isolated test runtime, never the obsolete TEMP location.
    # A custom path may be supplied without changing any runtime files.
    configured = os.environ.get("MEDIAHUB_TEST_PORTABLE_PYTHON")
    executable = (
        Path(configured)
        if configured
        else (
            Path(__file__).resolve().parents[2]
            / "windows_compute_node"
            / "runtime"
            / "private_python"
            / "cpython-3.12.10-x64-astral-20250409"
            / "python.exe"
        )
    )

    if not executable.is_file():
        pytest.skip(f"Isolierte portable Python-Testkopie nicht vorhanden: {executable}")

    result = python_runtime.inspect_managed_python(executable)

    assert result["available"] is True
    assert result["ready"] is True
