from typing import Any

import pytest

from app.references.compare import ReferenceCompareService


REFERENCE_QUALITY = {
    "score": 52,
    "width": 1280,
    "height": 720,
    "resolution_class": "HD",
    "video_codec": "h264",
    "video_bitrate_bps": 1_500_000,
    "frame_rate": 25.0,
    "bit_depth": 8,
    "hdr": False,
    "audio_channels": 2,
    "audio_quality": "standard",
    "scan_type": "progressive",
    "profile": {
        "name": "HD-Referenz",
    },
}


def make_reference() -> dict[str, Any]:
    return {
        "id": 3,
        "reference_uuid": "test-reference-uuid",
        "reference_version": 1,
        "name": "MediaHub Testreferenz",
        "quality_profile": "HD-Referenz",
        "quality_score": 52,
        "quality": dict(REFERENCE_QUALITY),
        "comparison_settings": {
            "allowed_score_difference": 5,
        },
        "analysis": {
            "media": {
                "quality_fingerprint": {
                    "test": "reference",
                },
            },
        },
    }


def make_candidate(
    *,
    score: int,
    width: int,
    height: int,
    bitrate: int,
) -> dict[str, Any]:
    quality = dict(REFERENCE_QUALITY)

    quality.update(
        {
            "score": score,
            "width": width,
            "height": height,
            "video_bitrate_bps": bitrate,
        }
    )

    if width <= 640 or height <= 360:
        quality["resolution_class"] = (
            "Low Resolution"
        )

    return {
        "file_path": "/tmp/test-video.mkv",
        "pipeline_version": "test",
        "media": {
            "quality": quality,
            "quality_fingerprint": {
                "test": "candidate",
            },
        },
    }


def install_visual_result(
    monkeypatch: pytest.MonkeyPatch,
    *,
    verdict: str,
    difference: float,
    similarity: float,
    events: list[str],
) -> None:
    result = {
        "available": True,
        "version": "2",
        "verdict": verdict,
        "visual_difference_percent": difference,
        "similarity_percent": similarity,
        "quality_events": events,
    }

    def fake_compare(
        self: Any,
        *,
        reference_fingerprint: dict[str, Any],
        candidate_fingerprint: dict[str, Any],
    ) -> dict[str, Any]:
        assert reference_fingerprint
        assert candidate_fingerprint

        return dict(result)

    monkeypatch.setattr(
        "app.references.compare."
        "FingerprintCompareService.compare",
        fake_compare,
    )


def test_identical_reference_is_similar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_visual_result(
        monkeypatch,
        verdict="similar",
        difference=0.0,
        similarity=100.0,
        events=[],
    )

    candidate = make_candidate(
        score=52,
        width=1280,
        height=720,
        bitrate=1_500_000,
    )

    result = ReferenceCompareService().compare(
        reference=make_reference(),
        candidate_analysis=candidate,
        allowed_score_difference=5,
    )

    assert result["verdict"] == "similar"
    assert result["reference_score"] == 52
    assert result["candidate_score"] == 52
    assert result["score_difference"] == 0

    categories = result["category_comparison"]

    assert categories["resolution"] == "equal"
    assert categories["video_bitrate"] == "equal"
    assert categories["visual_quality"] == "similar"

    summary = result["category_summary"]

    assert summary["worse"] == []
    assert result["visual_comparison"]["version"] == "2"
    assert (
        result["visual_comparison"][
            "similarity_percent"
        ]
        == 100.0
    )


def test_low_quality_video_is_worse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_visual_result(
        monkeypatch,
        verdict="similar",
        difference=-5.9,
        similarity=93.47,
        events=[],
    )

    candidate = make_candidate(
        score=35,
        width=640,
        height=360,
        bitrate=650_000,
    )

    result = ReferenceCompareService().compare(
        reference=make_reference(),
        candidate_analysis=candidate,
        allowed_score_difference=5,
    )

    assert result["verdict"] == "worse"
    assert result["score_difference"] == -17

    categories = result["category_comparison"]

    assert categories["resolution"] == "worse"
    assert categories["video_bitrate"] == "worse"
    assert categories["visual_quality"] == "similar"

    summary = result["category_summary"]

    assert summary["worse"] == [
        "resolution",
        "video_bitrate",
    ]

    assert result["visual_comparison"][
        "quality_events"
    ] == []


def test_damaged_blurred_video_is_worse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quality_events = [
        "detail_loss",
        "severe_detail_loss",
        "blur_detected",
    ]

    install_visual_result(
        monkeypatch,
        verdict="worse",
        difference=-33.33,
        similarity=47.67,
        events=quality_events,
    )

    candidate = make_candidate(
        score=35,
        width=640,
        height=360,
        bitrate=500_000,
    )

    result = ReferenceCompareService().compare(
        reference=make_reference(),
        candidate_analysis=candidate,
        allowed_score_difference=5,
    )

    assert result["verdict"] == "worse"
    assert result["score_difference"] == -17

    categories = result["category_comparison"]

    assert categories["resolution"] == "worse"
    assert categories["video_bitrate"] == "worse"
    assert categories["visual_quality"] == "worse"

    summary = result["category_summary"]

    assert summary["worse"] == [
        "resolution",
        "video_bitrate",
        "visual_quality",
    ]

    visual = result["visual_comparison"]

    assert visual["version"] == "2"
    assert visual["verdict"] == "worse"
    assert (
        visual["visual_difference_percent"]
        == -33.33
    )
    assert visual["similarity_percent"] == 47.67
    assert visual["quality_events"] == quality_events


def test_resolution_uses_pixel_count() -> None:
    service = ReferenceCompareService()

    result = service._compare_resolution(
        reference_quality={
            "width": 1280,
            "height": 720,
            "resolution_class": "HD",
        },
        candidate_quality={
            "width": 640,
            "height": 360,
            "resolution_class": (
                "Low Resolution"
            ),
        },
    )

    assert result == "worse"


def test_resolution_fallback_handles_low_resolution() -> None:
    service = ReferenceCompareService()

    result = service._compare_resolution(
        reference_quality={
            "resolution_class": "HD",
        },
        candidate_quality={
            "resolution_class": (
                "Low Resolution"
            ),
        },
    )

    assert result == "worse"


def test_resolution_tolerance_accepts_small_difference() -> None:
    service = ReferenceCompareService()

    result = service._compare_resolution(
        reference_quality={
            "width": 1280,
            "height": 720,
        },
        candidate_quality={
            "width": 1270,
            "height": 720,
        },
    )

    assert result == "equal"
