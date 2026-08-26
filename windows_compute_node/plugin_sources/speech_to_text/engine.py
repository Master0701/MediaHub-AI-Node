"""Speech-to-Text engine abstraction."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


class SpeechEngineError(RuntimeError):
    pass


def faster_whisper_available() -> bool:
    return (
        importlib.util.find_spec(
            "faster_whisper"
        )
        is not None
    )


def engine_status() -> dict[str, Any]:
    available = (
        faster_whisper_available()
    )

    return {
        "engine": "faster_whisper",
        "available": available,
    }


def transcribe(
    *,
    input_path: str | Path,
    execution: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(input_path)

    if not path.is_file():
        raise SpeechEngineError(
            f"Eingabedatei nicht gefunden: "
            f"{path}"
        )

    options = dict(
        options or {}
    )

    if options.get(
        "mock",
        False,
    ):
        return _mock_transcribe(
            path=path,
            execution=execution,
            options=options,
        )

    if not faster_whisper_available():
        raise SpeechEngineError(
            "faster-whisper ist fuer dieses "
            "Speech-Plugin noch nicht "
            "installiert."
        )

    return _faster_whisper_transcribe(
        path=path,
        execution=execution,
        options=options,
    )


def _mock_transcribe(
    *,
    path: Path,
    execution: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    text = str(
        options.get(
            "mock_text",
            "MediaHub Speech Mock",
        )
    )

    language = str(
        options.get(
            "language",
            "de",
        )
    )

    return {
        "engine": "mock",
        "text": text,
        "language": language,
        "segments": [
            {
                "start": 0.0,
                "end": 1.0,
                "text": text,
            }
        ],
        "execution": execution,
        "input": str(path),
    }


def _faster_whisper_transcribe(
    *,
    path: Path,
    execution: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    from faster_whisper import (
        WhisperModel,
    )

    backend = str(
        execution.get(
            "backend",
            "cpu",
        )
    )

    if backend == "cuda":
        device = "cuda"
        compute_type = str(
            options.get(
                "compute_type",
                "float16",
            )
        )

    elif backend == "cpu":
        device = "cpu"
        compute_type = str(
            options.get(
                "compute_type",
                "int8",
            )
        )

    else:
        raise SpeechEngineError(
            "Das aktuell installierte "
            "faster-whisper-Backend "
            f"unterstuetzt '{backend}' "
            "noch nicht direkt."
        )

    model_name = str(
        options.get(
            "model",
            "small",
        )
    )

    cpu_threads = int(
        execution.get(
            "cpu_threads",
            4,
        )
    )

    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
    )

    language = options.get(
        "language"
    )

    segments_iter, info = (
        model.transcribe(
            str(path),
            language=language,
            beam_size=int(
                options.get(
                    "beam_size",
                    5,
                )
            ),
            vad_filter=bool(
                options.get(
                    "vad_filter",
                    True,
                )
            ),
        )
    )

    segments = []

    text_parts = []

    for segment in segments_iter:
        text = str(
            segment.text
        ).strip()

        segments.append(
            {
                "start": float(
                    segment.start
                ),
                "end": float(
                    segment.end
                ),
                "text": text,
            }
        )

        if text:
            text_parts.append(text)

    detected_language = getattr(
        info,
        "language",
        language,
    )

    probability = getattr(
        info,
        "language_probability",
        None,
    )

    return {
        "engine": "faster_whisper",
        "model": model_name,
        "text": " ".join(
            text_parts
        ).strip(),
        "language": (
            detected_language
        ),
        "language_probability": (
            probability
        ),
        "segments": segments,
        "execution": execution,
        "input": str(path),
    }
