from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

ENGINE = (
    ROOT
    / "windows_compute_node"
    / "plugin_sources"
    / "speech_to_text"
    / "engine.py"
)


def load_engine():
    spec = (
        importlib.util.spec_from_file_location(
            "speech_engine_test",
            ENGINE,
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


def test_engine_status():
    module = load_engine()

    status = module.engine_status()

    assert (
        status["engine"]
        == "faster_whisper"
    )

    assert isinstance(
        status["available"],
        bool,
    )


def test_missing_input_fails(
    tmp_path,
):
    module = load_engine()

    with pytest.raises(
        module.SpeechEngineError
    ):
        module.transcribe(
            input_path=(
                tmp_path / "missing.wav"
            ),
            execution={
                "backend": "cpu",
                "cpu_threads": 2,
            },
            options={
                "mock": True,
            },
        )


def test_mock_transcription(
    tmp_path,
):
    module = load_engine()

    media = (
        tmp_path / "test.wav"
    )

    media.write_bytes(
        b"mock-media"
    )

    result = module.transcribe(
        input_path=media,
        execution={
            "backend": "cpu",
            "cpu_threads": 2,
        },
        options={
            "mock": True,
            "mock_text": (
                "NCIS Test Transkript"
            ),
            "language": "de",
        },
    )

    assert result["engine"] == "mock"

    assert (
        result["text"]
        == "NCIS Test Transkript"
    )

    assert result["language"] == "de"

    assert (
        result["execution"][
            "backend"
        ]
        == "cpu"
    )


def test_mock_segments(
    tmp_path,
):
    module = load_engine()

    media = (
        tmp_path / "test.avi"
    )

    media.write_bytes(
        b"mock-video"
    )

    result = module.transcribe(
        input_path=media,
        execution={
            "backend": "cuda",
            "cpu_threads": 4,
        },
        options={
            "mock": True,
            "mock_text": "Hallo MediaHub",
        },
    )

    assert len(
        result["segments"]
    ) == 1

    assert (
        result["segments"][0][
            "text"
        ]
        == "Hallo MediaHub"
    )

    assert (
        result["execution"][
            "backend"
        ]
        == "cuda"
    )
