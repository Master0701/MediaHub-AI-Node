RELATION_ALIASES: dict[str, str] = {
    "spinoff": "spin_off",
    "spin-off": "spin_off",
    "spin_off": "spin_off",
    "spin off": "spin_off",

    "spin-off-sequel": "spin_off_sequel",
    "spin_off_sequel": "spin_off_sequel",
    "spin off sequel": "spin_off_sequel",

    "prequel": "prequel",
    "sequel": "sequel",

    "shared universe": "shared_universe",
    "shared-universe": "shared_universe",
    "shared_universe": "shared_universe",

    "release-order": "release_order",
    "release order": "release_order",
    "release_order": "release_order",

    "chronological-order": "chronological_order",
    "chronological order": "chronological_order",
    "chronological_order": "chronological_order",

    "watch-order": "watch_order",
    "watch order": "watch_order",
    "watch_order": "watch_order",

    "same-franchise": "same_franchise",
    "same franchise": "same_franchise",
    "same_franchise": "same_franchise",

    "same-collection": "same_collection",
    "same collection": "same_collection",
    "same_collection": "same_collection",

    "takes-place-before": "takes_place_before",
    "takes place before": "takes_place_before",
    "takes_place_before": "takes_place_before",

    "takes-place-after": "takes_place_after",
    "takes place after": "takes_place_after",
    "takes_place after": "takes_place_after",
    "takes_place_after": "takes_place_after",

    "parent-series": "parent_series",
    "parent series": "parent_series",
    "parent_series": "parent_series",

    "child-series": "child_series",
    "child series": "child_series",
    "child_series": "child_series",

    "adaptation-of": "adaptation_of",
    "adaptation of": "adaptation_of",
    "adaptation_of": "adaptation_of",

    "based-on": "based_on",
    "based on": "based_on",
    "based_on": "based_on",

    "same-franchise": "same_franchise",
    "same-collection": "same_collection",
}


def normalize_relation_type(
    value: str | None,
) -> str:
    """
    Vereinheitlicht Beziehungstypen aus manuellen Eingaben,
    Importern und externen Metadatenquellen.
    """
    if value is None:
        return ""

    key = str(value).strip().lower()

    if not key:
        return ""

    direct_match = RELATION_ALIASES.get(key)

    if direct_match:
        return direct_match

    normalized = (
        key
        .replace("-", "_")
        .replace(" ", "_")
    )

    while "__" in normalized:
        normalized = normalized.replace(
            "__",
            "_",
        )

    return RELATION_ALIASES.get(
        normalized,
        normalized,
    )
