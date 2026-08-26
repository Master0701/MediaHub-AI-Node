"""Runtime management for the Speech plugin."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import Any

RUNTIME_NAME = "speech_to_text"

REQUIRED_PACKAGES = {
    "faster-whisper": "faster_whisper",
}


def _load_python_runtime_provider():
    provider_file = (
        Path(__file__).resolve().parent
        / "python_runtime.py"
    )

    spec = importlib.util.spec_from_file_location(
        "mediahub_speech_python_runtime",
        provider_file,
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "Speech Python-Runtime-Provider "
            "konnte nicht geladen werden."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def runtime_base_python() -> Path:
    provider = (
        _load_python_runtime_provider()
    )

    return Path(
        provider.require_python()
    )


def default_runtime_root() -> Path:
    override = os.environ.get(
        "MEDIAHUB_COMPUTE_RUNTIME"
    )

    if override:
        return (
            Path(override)
            / RUNTIME_NAME
        )

    return (
        Path.home()
        / ".mediahub"
        / "compute_node"
        / "plugin_runtimes"
        / RUNTIME_NAME
    )


def runtime_paths(
    root: Path | None = None,
) -> dict[str, Path]:
    root = Path(
        root or default_runtime_root()
    )

    return {
        "root": root,
        "venv": root / "venv",
        "state": root / "state.json",
        "models": root / "models",
        "cache": root / "cache",
    }


def _python_has_module(
    python_path: Path,
    module: str,
) -> bool:
    """Return whether a Python interpreter provides a module."""

    if not python_path.is_file():
        return False

    result = subprocess.run(
        [
            str(python_path),
            "-c",
            (
                "import importlib.util,sys;"
                "sys.exit("
                f"0 if importlib.util.find_spec({module!r}) "
                "else 1)"
            ),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0


def _venv_python_path(
    root: Path | None = None,
) -> Path:
    """Return the traditional Speech venv interpreter path."""

    paths = runtime_paths(root)

    if os.name == "nt":
        return (
            paths["venv"]
            / "Scripts"
            / "python.exe"
        )

    return (
        paths["venv"]
        / "bin"
        / "python"
    )


def venv_python(
    root: Path | None = None,
) -> Path:
    """Return the interpreter used by the Speech runtime.

    A traditional per-plugin venv remains preferred when it
    already exists.  MediaHub's managed private Python can be
    used directly when it intentionally has no venv module.
    """

    venv_path = _venv_python_path(root)

    if venv_path.is_file():
        return venv_path

    base_python = runtime_base_python()

    if (
        base_python.is_file()
        and not _python_has_module(
            base_python,
            "venv",
        )
    ):
        return base_python

    return venv_path

def inspect_runtime(
    root: Path | None = None,
) -> dict[str, Any]:
    paths = runtime_paths(root)

    python_path = venv_python(root)

    result = {
        "runtime": RUNTIME_NAME,
        "root": str(paths["root"]),
        "venv_exists": (
            paths["venv"].is_dir()
        ),
        "python_exists": (
            python_path.is_file()
        ),
        "python": str(python_path),
        "packages": {},
        "ready": False,
    }

    if not python_path.is_file():
        for package in REQUIRED_PACKAGES:
            result["packages"][
                package
            ] = False

        return result

    all_available = True

    for package, module in (
        REQUIRED_PACKAGES.items()
    ):
        available = _module_available(
            python_path,
            module,
        )

        result["packages"][
            package
        ] = available

        if not available:
            all_available = False

    result["ready"] = all_available

    return result


def create_runtime(
    root: Path | None = None,
) -> dict[str, Any]:
    paths = runtime_paths(root)

    paths["root"].mkdir(
        parents=True,
        exist_ok=True,
    )
    paths["models"].mkdir(
        parents=True,
        exist_ok=True,
    )
    paths["cache"].mkdir(
        parents=True,
        exist_ok=True,
    )

    base_python = runtime_base_python()

    if not base_python.is_file():
        raise RuntimeError(
            "Kein kompatibles Runtime-Python vorhanden."
        )

    traditional_venv_python = (
        _venv_python_path(root)
    )

    runtime_mode: str

    if traditional_venv_python.is_file():
        python_path = traditional_venv_python
        runtime_mode = "venv"

    elif _python_has_module(
        base_python,
        "venv",
    ):
        subprocess.run(
            [
                str(base_python),
                "-m",
                "venv",
                str(paths["venv"]),
            ],
            check=True,
        )

        python_path = traditional_venv_python
        runtime_mode = "venv"

    else:
        # MediaHub managed/private Python distributions may
        # intentionally omit the stdlib venv package.
        # They are already isolated from the host Python and
        # can therefore act as the plugin runtime directly.
        python_path = base_python
        runtime_mode = "managed_private_python"

    if not python_path.is_file():
        raise RuntimeError(
            "Speech-Runtime-Python wurde nicht erstellt."
        )

    state = {
        "runtime": RUNTIME_NAME,
        "mode": runtime_mode,
        "created_with": str(base_python),
        "python": str(python_path),
    }

    paths["state"].write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return inspect_runtime(root)

def install_dependencies(
    root: Path | None = None,
) -> dict[str, Any]:
    status = create_runtime(root)

    python_path = Path(
        status["python"]
    )

    subprocess.run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
        ],
        check=True,
    )

    subprocess.run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            "faster-whisper",
        ],
        check=True,
    )

    status = inspect_runtime(root)

    if not status["ready"]:
        raise RuntimeError(
            "Speech-Runtime wurde "
            "installiert, ist aber "
            "nicht bereit."
        )

    return status


def _module_available(
    python_path: Path,
    module: str,
) -> bool:
    result = subprocess.run(
        [
            str(python_path),
            "-c",
            (
                "import importlib.util,sys;"
                "sys.exit("
                "0 if importlib.util.find_spec("
                f"{module!r}"
                ") else 1)"
            ),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0



# --------------------------------------------------
# Managed NVIDIA CUDA runtime for Speech-to-Text
# --------------------------------------------------

CUDA_RUNTIME_PACKAGES = (
    "nvidia-cublas-cu12==12.6.4.1",
    "nvidia-cudnn-cu12==9.10.2.21",
    "nvidia-cuda-runtime-cu12==12.6.77",
)


def runtime_site_packages(
    root: Path | None = None,
) -> Path:
    """Return site-packages of managed Speech Python."""

    status = inspect_runtime(
        root
    )

    python_path = Path(
        status["python"]
    )

    return (
        python_path.parent
        / "Lib"
        / "site-packages"
    )


def cuda_runtime_paths(
    root: Path | None = None,
) -> list[Path]:
    """Return managed NVIDIA DLL directories."""

    site = runtime_site_packages(
        root
    )

    return [
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


def inspect_cuda_runtime(
    root: Path | None = None,
) -> dict[str, Any]:
    """Inspect required CUDA DLLs."""

    paths = cuda_runtime_paths(
        root
    )

    dlls = {
        "cublas64_12.dll": False,
        "cublasLt64_12.dll": False,
        "cudnn64_9.dll": False,
    }

    for directory in paths:

        if not directory.is_dir():
            continue

        for name in dlls:

            if (
                directory
                / name
            ).is_file():

                dlls[name] = True

    return {
        "paths": [
            str(path)
            for path in paths
        ],
        "dlls": dlls,
        "ready": all(
            dlls.values()
        ),
    }


def install_cuda_dependencies(
    root: Path | None = None,
) -> dict[str, Any]:
    """Install pinned CUDA libraries into Speech runtime."""

    status = create_runtime(
        root
    )

    python_path = Path(
        status["python"]
    )

    subprocess.run(
        [
            str(python_path),
            "-m",
            "pip",
            "install",
            *CUDA_RUNTIME_PACKAGES,
        ],
        check=True,
    )

    cuda_status = inspect_cuda_runtime(
        root
    )

    if not cuda_status["ready"]:
        raise RuntimeError(
            "CUDA-Runtime wurde installiert, "
            "aber erforderliche DLLs fehlen."
        )

    return cuda_status
