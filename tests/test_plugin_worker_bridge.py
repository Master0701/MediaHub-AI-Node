from __future__ import annotations

from typing import Any

from app.plugins.worker_bridge import PluginWorkerJobHandler


def test_plugin_worker_handler_wraps_plain_job_payload() -> None:
    received: list[dict[str, Any]] = []

    def handler(
        request: dict[str, Any],
    ) -> dict[str, Any]:
        received.append(request)
        return {
            "status": "completed",
        }

    adapter = PluginWorkerJobHandler(
        job_type="speech_to_text",
        handler=handler,
    )

    result = adapter.execute(
        db=None,
        payload={
            "input": "/tmp/test.wav",
            "options": {
                "language": "de",
            },
        },
        progress_callback=lambda *_args, **_kwargs: None,
    )

    assert result == {
        "status": "completed",
    }

    assert received == [
        {
            "payload": {
                "input": "/tmp/test.wav",
                "options": {
                    "language": "de",
                },
            },
        }
    ]


def test_plugin_worker_handler_preserves_shared_request() -> None:
    received: list[dict[str, Any]] = []

    def handler(
        request: dict[str, Any],
    ) -> dict[str, Any]:
        received.append(request)
        return request

    adapter = PluginWorkerJobHandler(
        job_type="speech_to_text",
        handler=handler,
    )

    request = {
        "execution": {
            "mode": "cpu",
            "cpu_threads": 3,
        },
        "payload": {
            "input": "/tmp/test.wav",
        },
    }

    result = adapter.execute(
        db=None,
        payload=request,
        progress_callback=lambda *_args, **_kwargs: None,
    )

    assert received == [request]
    assert result == request


def test_plugin_worker_handler_does_not_swallow_type_error() -> None:
    def handler(
        request: dict[str, Any],
    ) -> dict[str, Any]:
        del request
        raise TypeError("echter Plugin-Fehler")

    adapter = PluginWorkerJobHandler(
        job_type="speech_to_text",
        handler=handler,
    )

    try:
        adapter.execute(
            db=None,
            payload={
                "input": "/tmp/test.wav",
            },
            progress_callback=lambda *_args, **_kwargs: None,
        )
    except TypeError as exc:
        assert str(exc) == "echter Plugin-Fehler"
    else:
        raise AssertionError(
            "TypeError des Plugins wurde verschluckt."
        )
