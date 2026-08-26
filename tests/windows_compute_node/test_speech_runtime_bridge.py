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

PLUGIN = (
    ROOT
    / "windows_compute_node"
    / "plugin_sources"
    / "speech_to_text"
)

BRIDGE_FILE = (
    PLUGIN / "runtime_bridge.py"
)

RUNNER_FILE = (
    PLUGIN / "runtime_runner.py"
)


def load_bridge():
    spec = importlib.util.spec_from_file_location(
        "speech_bridge_test",
        BRIDGE_FILE,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    assert spec.loader is not None

    spec.loader.exec_module(
        module
    )

    return module


def test_mock_through_subprocess(
    tmp_path,
):
    bridge = load_bridge()

    media = (
        tmp_path / "test.avi"
    )

    media.write_bytes(
        b"mock-video"
    )

    result = bridge.run_transcription(
        runtime_python=sys.executable,
        runner_path=RUNNER_FILE,
        input_path=media,
        execution={
            "backend": "cpu",
            "cpu_threads": 3,
        },
        options={
            "mock": True,
            "mock_text": (
                "NCIS ueber Prozessbruecke"
            ),
            "language": "de",
        },
    )

    assert result["engine"] == "mock"

    assert (
        result["text"]
        == "NCIS ueber Prozessbruecke"
    )

    assert (
        result["execution"][
            "cpu_threads"
        ]
        == 3
    )


def test_cuda_mock_through_subprocess(
    tmp_path,
):
    bridge = load_bridge()

    media = (
        tmp_path / "test.avi"
    )

    media.write_bytes(
        b"mock-video"
    )

    result = bridge.run_transcription(
        runtime_python=sys.executable,
        runner_path=RUNNER_FILE,
        input_path=media,
        execution={
            "backend": "cuda",
            "cpu_threads": 4,
        },
        options={
            "mock": True,
            "mock_text": "CUDA Mock",
        },
    )

    assert result["engine"] == "mock"

    assert (
        result["execution"][
            "backend"
        ]
        == "cuda"
    )


def test_missing_python_fails(
    tmp_path,
):
    bridge = load_bridge()

    with pytest.raises(
        bridge.SpeechRuntimeBridgeError
    ):
        bridge.run_transcription(
            runtime_python=(
                tmp_path
                / "missing-python.exe"
            ),
            runner_path=RUNNER_FILE,
            input_path=(
                tmp_path / "test.avi"
            ),
            execution={
                "backend": "cpu"
            },
        )


def test_missing_runner_fails(
    tmp_path,
):
    bridge = load_bridge()

    with pytest.raises(
        bridge.SpeechRuntimeBridgeError
    ):
        bridge.run_transcription(
            runtime_python=sys.executable,
            runner_path=(
                tmp_path / "missing.py"
            ),
            input_path=(
                tmp_path / "test.avi"
            ),
            execution={
                "backend": "cpu"
            },
        )



def test_cuda_environment_adds_private_dll_paths(
    tmp_path,
):
    bridge = load_bridge()

    runtime_python = (
        tmp_path
        / "private_python"
        / "python.exe"
    )

    site = (
        runtime_python.parent
        / "Lib"
        / "site-packages"
    )

    expected = [
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

    for directory in expected:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    environment = (
        bridge._subprocess_environment(
            runtime_python=runtime_python,
            execution={
                "backend": "cuda",
            },
        )
    )

    parts = environment[
        "PATH"
    ].split(
        bridge.os.pathsep
    )

    assert parts[:3] == [
        str(directory)
        for directory in expected
    ]


def test_cpu_environment_does_not_add_cuda_paths(
    tmp_path,
):
    bridge = load_bridge()

    runtime_python = (
        tmp_path
        / "private_python"
        / "python.exe"
    )

    environment = (
        bridge._subprocess_environment(
            runtime_python=runtime_python,
            execution={
                "backend": "cpu",
            },
        )
    )

    nvidia_root = str(
        runtime_python.parent
        / "Lib"
        / "site-packages"
        / "nvidia"
    )

    assert (
        nvidia_root
        not in environment.get(
            "PATH",
            "",
        )
    )
