from __future__ import annotations

import re
from collections.abc import Iterable


def normalize_identifier(value: str | None) -> str:
    if value is None:
        return ""
    normalized = str(value).strip().lower()
    if not normalized:
        return ""
    normalized = normalized.replace("’", "'").replace("'", "")
    normalized = re.sub(r"[^a-z0-9äöüß]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


MEDIA_TYPE_ALIASES: dict[str, str] = {
    "movie": "movie", "film": "movie", "movies": "movie",
    "feature_film": "movie", "feature": "movie",
    "series": "series", "serie": "series", "tv": "series",
    "tv_series": "series", "show": "series",
    "season": "season", "staffel": "season",
    "episode": "episode", "folge": "episode",
    "special": "special", "short": "short", "short_film": "short",
    "documentary": "documentary", "dokumentation": "documentary",
    "music_video": "music_video", "video": "video",
    "audiobook": "audiobook", "audio_book": "audiobook",
    "hörbuch": "audiobook", "hoerbuch": "audiobook",
    "podcast": "podcast", "music": "music", "album": "album",
    "track": "track", "book": "book", "unknown": "unknown",
}

SUPPORTED_MEDIA_TYPES: tuple[str, ...] = tuple(dict.fromkeys(MEDIA_TYPE_ALIASES.values()))


def normalize_media_type(value: str | None) -> str:
    normalized = normalize_identifier(value)
    if not normalized:
        return ""
    return MEDIA_TYPE_ALIASES.get(normalized, normalized)


RELATION_ALIASES: dict[str, str] = {
    "spinoff": "spin_off", "spin_off": "spin_off",
    "spin_off_sequel": "spin_off_sequel", "prequel": "prequel",
    "sequel": "sequel", "shared_universe": "shared_universe",
    "release_order": "release_order", "chronological_order": "chronological_order",
    "watch_order": "watch_order", "same_franchise": "same_franchise",
    "same_collection": "same_collection", "takes_place_before": "takes_place_before",
    "takes_place_after": "takes_place_after", "parent_series": "parent_series",
    "child_series": "child_series", "adaptation_of": "adaptation_of",
    "based_on": "based_on", "remake": "remake", "reboot": "reboot",
    "continues": "continues", "crossover": "crossover", "related": "related",
}

DIRECTED_RELATION_TYPES = frozenset({
    "prequel", "sequel", "spin_off", "spin_off_sequel", "remake", "reboot",
    "takes_place_before", "takes_place_after", "continues", "adaptation_of",
    "based_on", "parent_series", "child_series",
})
SYMMETRIC_RELATION_TYPES = frozenset({
    "crossover", "shared_universe", "same_franchise", "same_collection", "related",
})
ORDER_TYPES = frozenset({"chronological_order", "release_order", "watch_order"})
SUPPORTED_RELATION_TYPES = tuple(
    sorted(
        DIRECTED_RELATION_TYPES
        | SYMMETRIC_RELATION_TYPES
        | ORDER_TYPES
    )
)
INVERSE_RELATION_TYPES = {
    "prequel": "sequel", "sequel": "prequel",
    "takes_place_before": "takes_place_after",
    "takes_place_after": "takes_place_before",
    "parent_series": "child_series", "child_series": "parent_series",
}


def normalize_relation_type(value: str | None) -> str:
    normalized = normalize_identifier(value)
    if not normalized:
        return ""
    return RELATION_ALIASES.get(normalized, normalized)


EDITION_ALIASES: dict[str, str] = {
    "uncut": "uncut", "un_cut": "uncut", "extended": "extended",
    "extended_cut": "extended", "directors_cut": "directors_cut",
    "director_cut": "directors_cut", "theatrical": "theatrical_cut",
    "theatrical_cut": "theatrical_cut", "remaster": "remastered",
    "remastered": "remastered", "special_edition": "special_edition",
    "anniversary_edition": "anniversary_edition",
    "ultimate_edition": "ultimate_edition", "final_cut": "final_cut",
    "unrated": "unrated", "unrated_cut": "unrated",
    "restored": "restored", "restoration": "restored",
}
SUPPORTED_EDITION_TYPES = tuple(dict.fromkeys(EDITION_ALIASES.values()))
EDITION_PATTERNS: dict[str, str] = {
    "uncut": r"\buncut\b",
    "extended": r"\bextended(?:[ ._-]*cut)?\b",
    "directors_cut": r"\bdirector(?:'s|s)?[ ._-]*cut\b",
    "theatrical_cut": r"\btheatrical(?:[ ._-]*cut)?\b",
    "remastered": r"\bremaster(?:ed)?\b",
    "special_edition": r"\bspecial[ ._-]*edition\b",
    "anniversary_edition": r"\banniversary[ ._-]*edition\b",
    "ultimate_edition": r"\bultimate[ ._-]*edition\b",
    "final_cut": r"\bfinal[ ._-]*cut\b",
    "unrated": r"\bunrated(?:[ ._-]*cut)?\b",
    "restored": r"\brestor(?:ed|ation)\b",
}


def normalize_edition_type(value: str | None) -> str:
    normalized = normalize_identifier(value)
    if not normalized:
        return ""
    return EDITION_ALIASES.get(normalized, normalized)


def normalize_edition_types(values: Iterable[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        normalized = normalize_edition_type(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
