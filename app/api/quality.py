from fastapi import APIRouter, HTTPException

from app.analyzer.quality_profiles import (
    DEFAULT_PROFILE_NAME,
    get_quality_profile,
    list_quality_profiles,
)


router = APIRouter(
    prefix="/quality",
    tags=["quality"],
)


@router.get("/profiles")
def get_profiles() -> dict:
    profiles = list_quality_profiles()

    return {
        "count": len(profiles),
        "default_profile": DEFAULT_PROFILE_NAME,
        "profiles": profiles,
    }


@router.get("/profiles/{profile_name}")
def get_profile(
    profile_name: str,
) -> dict:
    normalized_name = profile_name.strip().lower()

    profiles = {
        profile["name"]: profile
        for profile in list_quality_profiles()
    }

    profile = profiles.get(
        normalized_name
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Unbekanntes Qualitätsprofil: "
                f"{profile_name}"
            ),
        )

    return profile
