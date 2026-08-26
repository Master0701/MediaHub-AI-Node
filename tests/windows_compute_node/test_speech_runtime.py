from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

RUNTIME = (
    ROOT
    / "windows_compute_node"
    / "plugin_sources"
    / "speech_to_text"
    / "runtime.py"
)


def load_runtime():
    spec = (
        importlib.util.spec_from_file_location(
            "speech_runtime_test",
            RUNTIME,
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


def test_runtime_paths(
    tmp_path,
):
    module = load_runtime()

    paths = module.runtime_paths(
        tmp_path
    )

    assert paths["root"] == tmp_path

    assert (
        paths["venv"]
        == tmp_path / "venv"
    )

    assert (
        paths["models"]
        == tmp_path / "models"
    )


def test_missing_runtime_without_venv_uses_managed_python(
    tmp_path,
):
    """Managed private Python may replace a plugin venv."""

    module = load_runtime()

    status = module.inspect_runtime(
        tmp_path
    )

    assert status["venv_exists"] is False

    runtime_python = module.venv_python(
        tmp_path
    )

    assert (
        status["python"]
        == str(runtime_python)
    )

    if runtime_python.is_file():
        assert status["python_exists"] is True

        expected_ready = all(
            status["packages"].values()
        )

        assert (
            status["ready"]
            is expected_ready
        )

    else:
        assert status["python_exists"] is False
        assert status["ready"] is False


def test_create_runtime(
    tmp_path,
    monkeypatch,
):
    module = load_runtime()

    # Dieser Test prueft nur die
    # Runtime-/Venv-Erzeugung.
    #
    # Die Auswahl eines kompatiblen
    # produktiven Base-Pythons wird
    # separat getestet.
    monkeypatch.setattr(
        module,
        "runtime_base_python",
        lambda: Path(sys.executable),
    )

    status = module.create_runtime(
        tmp_path
    )

    assert (
        status["venv_exists"]
        is True
    )

    assert (
        status["python_exists"]
        is True
    )

    assert (
        tmp_path / "models"
    ).is_dir()

    assert (
        tmp_path / "cache"
    ).is_dir()

    assert (
        tmp_path / "state.json"
    ).is_file()


def test_created_runtime_not_ready_yet(
    tmp_path,
    monkeypatch,
):
    module = load_runtime()

    monkeypatch.setattr(
        module,
        "runtime_base_python",
        lambda: Path(sys.executable),
    )

    module.create_runtime(
        tmp_path
    )

    status = module.inspect_runtime(
        tmp_path
    )

    # Der Test installiert absichtlich
    # keine Internet-Abhaengigkeiten.
    assert status["ready"] is False



def test_cuda_runtime_paths_are_private(
    tmp_path,
    monkeypatch,
):
    module = load_runtime()

    fake_python = (
        tmp_path
        / "private_python"
        / "python.exe"
    )

    monkeypatch.setattr(
        module,
        "inspect_runtime",
        lambda root=None: {
            "python": str(
                fake_python
            ),
        },
    )

    paths = module.cuda_runtime_paths()

    site = (
        fake_python.parent
        / "Lib"
        / "site-packages"
    )

    assert paths == [
        site
        / "nvidia"
        / "cublas"
        / "bin",

        site
        / "nvidia"
        / "cudnn"
        / "bin",

        site
        / "nvidia"
        / "cuda_runtime"
        / "bin",
    ]


def test_cuda_runtime_not_ready_without_dlls(
    tmp_path,
    monkeypatch,
):
    module = load_runtime()

    fake_python = (
        tmp_path
        / "private_python"
        / "python.exe"
    )

    monkeypatch.setattr(
        module,
        "inspect_runtime",
        lambda root=None: {
            "python": str(
                fake_python
            ),
        },
    )

    status = module.inspect_cuda_runtime()

    assert status["ready"] is False

    assert not any(
        status["dlls"].values()
    )
