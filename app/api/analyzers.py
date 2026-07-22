from typing import Any

from fastapi import APIRouter

from app.analyzer.manager import (
    analyzer_manager,
)


router = APIRouter(
    prefix="/analyzers",
    tags=["Analyzers"],
)


@router.get("")
def list_analyzers_endpoint(
) -> dict[str, Any]:
    analyzers = (
        analyzer_manager.list_analyzers()
    )

    return {
        "count": len(analyzers),
        "analyzers": analyzers,
    }


@router.get("/{analyzer_name}")
def get_analyzer_endpoint(
    analyzer_name: str,
) -> dict[str, Any]:
    normalized_name = (
        analyzer_name.strip().lower()
    )

    analyzers = (
        analyzer_manager.list_analyzers()
    )

    for analyzer in analyzers:
        if (
            analyzer["name"]
            == normalized_name
        ):
            return analyzer

    return {
        "found": False,
        "name": normalized_name,
    }
