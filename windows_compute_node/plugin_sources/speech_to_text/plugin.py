"""MediaHub Speech-to-Text Compute plugin."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from windows_compute_node.plugin_sources.speech_to_text.runtime import (
    inspect_cuda_runtime,
    inspect_runtime,
    install_cuda_dependencies,
    install_dependencies,
    venv_python,
)
from windows_compute_node.plugin_sources.speech_to_text.runtime_bridge import (
    run_transcription,
)

_PLUGIN_DIR = Path(__file__).resolve().parent

_EXECUTION_FILE = (
    _PLUGIN_DIR / "execution.py"
)

_SPEC = importlib.util.spec_from_file_location(
    "mediahub_speech_execution",
    _EXECUTION_FILE,
)

if (
    _SPEC is None
    or _SPEC.loader is None
):
    raise RuntimeError(
        "Speech execution module "
        "kann nicht geladen werden."
    )

_EXECUTION_MODULE = (
    importlib.util.module_from_spec(
        _SPEC
    )
)

sys.modules[
    _SPEC.name
] = _EXECUTION_MODULE

_SPEC.loader.exec_module(
    _EXECUTION_MODULE
)

choose_backend = (
    _EXECUTION_MODULE.choose_backend
)


_ENGINE_FILE = (
    _PLUGIN_DIR / "engine.py"
)

_ENGINE_SPEC = (
    importlib.util.spec_from_file_location(
        "mediahub_speech_engine",
        _ENGINE_FILE,
    )
)

if (
    _ENGINE_SPEC is None
    or _ENGINE_SPEC.loader is None
):
    raise RuntimeError(
        "Speech engine module "
        "kann nicht geladen werden."
    )

_ENGINE_MODULE = (
    importlib.util.module_from_spec(
        _ENGINE_SPEC
    )
)

sys.modules[
    _ENGINE_SPEC.name
] = _ENGINE_MODULE

_ENGINE_SPEC.loader.exec_module(
    _ENGINE_MODULE
)

transcribe = _ENGINE_MODULE.transcribe
engine_status = _ENGINE_MODULE.engine_status


def _capabilities(
    context: dict[str, Any],
) -> dict[str, Any]:
    provider = context.get(
        "capabilities_provider"
    )

    if callable(provider):
        value = provider()

        if isinstance(value, dict):
            return value

    value = context.get(
        "capabilities"
    )

    if isinstance(value, dict):
        return value

    return {}


def create_handler(
    context: dict[str, Any],
):
    def handler(
        request: dict[str, Any],
    ) -> dict[str, Any]:
        execution = request.get(
            "execution"
        )

        selected = choose_backend(
            execution=execution,
            capabilities=_capabilities(
                context
            ),
        )

        payload = dict(
            request.get("payload")
            or {}
        )

        input_path = payload.get(
            "input"
        )

        if not input_path:
            raise ValueError(
                "Speech-Job benoetigt "
                "payload.input."
            )

        options = dict(
            payload.get(
                "options"
            )
            or {}
        )

        runtime_status = inspect_runtime()

        if not runtime_status["ready"]:
            runtime_status = install_dependencies()

        backend = str(
            selected.get(
                "backend",
                "cpu",
            )
        ).strip().lower()

        if backend == "cuda":
            cuda_status = inspect_cuda_runtime()

            if not cuda_status["ready"]:
                cuda_status = install_cuda_dependencies()

        runtime_python = venv_python()

        runner_path = (
            Path(__file__).resolve().parent
            / "runtime_runner.py"
        )

        result = run_transcription(
            runtime_python=runtime_python,
            runner_path=runner_path,
            input_path=input_path,
            execution=selected,
            options=options,
        )

        return {
            "status": "completed",
            "engine": result[
                "engine"
            ],
            "execution": selected,
            "transcription": result,
            "input": input_path,
        }

    return handler


def register(
    context: dict[str, Any],
) -> None:
    workers = context["workers"]

    workers.register(
        worker_id=(
            "mediahub.speech_to_text.worker"
        ),
        name=(
            "MediaHub Speech-to-Text Worker"
        ),
        job_types=[
            "speech_to_text"
        ],
        handler=create_handler(
            context
        ),
        metadata={
            "plugin_id": context[
                "plugin_id"
            ],
            "plugin_version": context[
                "plugin_version"
            ],
            "execution_modes": [
                "auto",
                "cpu",
                "gpu"
            ],
            "engine": (
                engine_status()
            ),
        },
    )
