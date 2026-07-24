from app.knowledge.types import (
    normalize_edition_type,
    normalize_edition_types,
    normalize_media_type,
    normalize_relation_type,
)


def test_normalize_media_type_aliases() -> None:
    assert normalize_media_type("Film") == "movie"
    assert normalize_media_type("TV Series") == "series"
    assert normalize_media_type("Hörbuch") == "audiobook"
    assert normalize_media_type("Staffel") == "season"


def test_normalize_relation_type_aliases() -> None:
    assert normalize_relation_type("spin-off") == "spin_off"
    assert normalize_relation_type("shared universe") == "shared_universe"
    assert normalize_relation_type("takes place after") == "takes_place_after"


def test_normalize_edition_type_aliases() -> None:
    assert normalize_edition_type("Director's Cut") == "directors_cut"
    assert normalize_edition_type("Extended Cut") == "extended"
    assert normalize_edition_type("Remaster") == "remastered"


def test_normalize_edition_types_removes_duplicates() -> None:
    assert normalize_edition_types(["Extended", "extended cut", "Director's Cut", ""]) == [
        "extended", "directors_cut"
    ]
