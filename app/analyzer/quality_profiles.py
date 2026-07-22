from copy import deepcopy
from typing import Any

DEFAULT_PROFILE_NAME = "balanced"


QUALITY_PROFILES: dict[str, dict[str, Any]] = {
    "permissive": {
        "name": "permissive",
        "label": "Großzügig",
        "description": ("Geeignet für ältere Aufnahmen, seltene Inhalte und kleine Dateien."),
        "thresholds": {
            "excellent": 85,
            "very_good": 70,
            "good": 55,
            "acceptable": 35,
            "improvable": 20,
        },
        "minimums": {
            "height": 480,
            "bitrate_bps": 400_000,
            "audio_channels": 1,
        },
    },
    "balanced": {
        "name": "balanced",
        "label": "Ausgewogen",
        "description": ("Standardprofil für Filme, Serien und gewöhnliche Medienbibliotheken."),
        "thresholds": {
            "excellent": 90,
            "very_good": 75,
            "good": 60,
            "acceptable": 45,
            "improvable": 30,
        },
        "minimums": {
            "height": 720,
            "bitrate_bps": 1_500_000,
            "audio_channels": 2,
        },
    },
    "archive": {
        "name": "archive",
        "label": "Archivqualität",
        "description": ("Strenge Bewertung für hochwertige Archiv- und Hauptfassungen."),
        "thresholds": {
            "excellent": 95,
            "very_good": 85,
            "good": 70,
            "acceptable": 55,
            "improvable": 40,
        },
        "minimums": {
            "height": 1080,
            "bitrate_bps": 4_000_000,
            "audio_channels": 2,
        },
    },
}


def get_quality_profile(
    profile_name: str | None,
) -> dict[str, Any]:
    normalized_name = str(profile_name or DEFAULT_PROFILE_NAME).strip().lower()

    profile = QUALITY_PROFILES.get(normalized_name)

    if profile is None:
        profile = QUALITY_PROFILES[DEFAULT_PROFILE_NAME]

    return deepcopy(profile)


def list_quality_profiles() -> list[dict[str, Any]]:
    return [deepcopy(profile) for profile in QUALITY_PROFILES.values()]
