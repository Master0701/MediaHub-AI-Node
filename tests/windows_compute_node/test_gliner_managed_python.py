from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

RUNTIME_FILE = (
    ROOT / "windows_compute_node" / "runtime"
    / "plugins" / "mediahub.gliner" / "runtime_manager.py"
)


def test_gliner_requires_managed_python(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "gliner_managed_python_test",
        RUNTIME_FILE,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    provider = module._load_python_runtime_provider()

    monkeypatch.setattr(
        provider,
        "inspect_managed_python",
        lambda: {
            "executable": "missing-python.exe",
            "available": False,
            "ready": False,
        },
    )

    def forbidden_fallback():
        raise AssertionError(
            "GLiNER darf nicht auf require_python zurueckfallen."
        )

    monkeypatch.setattr(
        provider,
        "require_python",
        forbidden_fallback,
    )

    with pytest.raises(RuntimeError):
        module.runtime_base_python()



def test_gliner_rejects_packages_from_other_directories(
    monkeypatch, tmp_path
):
    import subprocess
    import sys

    spec = importlib.util.spec_from_file_location(
        "gliner_package_origin_test",
        RUNTIME_FILE,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    packages = tmp_path / "gliner_packages"
    packages.mkdir()

    foreign = tmp_path / "foreign_packages"
    foreign.mkdir()

    (foreign / "gliner.py").write_text(
        "__version__ = 'test'\n",
        encoding="utf-8",
    )
    (foreign / "torch.py").write_text(
        "\n".join([
            "__version__ = 'test'",
            "class version:",
            "    cuda = None",
            "class cuda:",
            "    @staticmethod",
            "    def is_available(): return False",
            "    @staticmethod",
            "    def device_count(): return 0",
            "",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        module,
        "runtime_base_python",
        lambda: Path(sys.executable),
    )

    real_run = subprocess.run

    def run_with_foreign_packages(command, **kwargs):
        import os

        env = os.environ.copy()
        env["PYTHONPATH"] = str(foreign)
        kwargs["env"] = env
        return real_run(command, **kwargs)

    monkeypatch.setattr(
        module.subprocess,
        "run",
        run_with_foreign_packages,
    )

    result = module.inspect_package_runtime(packages)

    print("GLiNER-Pruefergebnis:", result)
    assert result["ready"] is False



def test_gliner_accepts_packages_from_own_directory(
    monkeypatch, tmp_path
):
    import sys

    spec = importlib.util.spec_from_file_location(
        "gliner_valid_package_origin_test",
        RUNTIME_FILE,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    packages = tmp_path / "gliner_packages"
    packages.mkdir()

    (packages / "gliner.py").write_text(
        "__version__ = 'test'",
        encoding="utf-8",
    )

    (packages / "torch.py").write_text(
        chr(10).join([
            "__version__ = 'test'",
            "class version:",
            "    cuda = None",
            "class cuda:",
            "    @staticmethod",
            "    def is_available(): return False",
            "    @staticmethod",
            "    def device_count(): return 0",
            "",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        module,
        "runtime_base_python",
        lambda: Path(sys.executable),
    )

    result = module.inspect_package_runtime(packages)

    print("GLiNER-Positivtest:", result)

    assert result["ready"] is True
    assert result["gliner_available"] is True
    assert result["torch_available"] is True
    assert result["error"] is None
