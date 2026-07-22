import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.knowledge.models import (
    KnowledgeAlias,
    KnowledgeItem,
)
from app.knowledge.service import decode_json


@dataclass(slots=True)
class KnowledgeMatch:
    item: KnowledgeItem
    score: float
    match_type: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item.id,
            "title": self.item.title,
            "original_title": self.item.original_title,
            "year": self.item.year,
            "media_type": self.item.media_type,
            "score": round(self.score, 4),
            "match_type": self.match_type,
            "reasons": self.reasons,
        }


class KnowledgeMatcher:
    """
    Erkennt bereits vorhandene Wissenseinträge.

    Reihenfolge der Erkennung:

    1. Externe IDs wie TMDb, IMDb oder TVDb
    2. Titel, Medientyp und Jahr
    3. Originaltitel und alternative Titel
    4. Unscharfer Titelvergleich
    """

    EXTERNAL_ID_KEYS = {
        "imdb",
        "imdb_id",
        "tmdb",
        "tmdb_id",
        "tvdb",
        "tvdb_id",
        "musicbrainz",
        "musicbrainz_id",
        "audible",
        "audible_id",
        "asin",
    }

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_matches(
        self,
        *,
        title: str,
        media_type: str | None = None,
        year: int | None = None,
        original_title: str | None = None,
        external_ids: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[KnowledgeMatch]:
        normalized_title = normalize_title(title)

        if not normalized_title:
            return []

        normalized_original_title = normalize_title(
            original_title
        )

        normalized_media_type = normalize_media_type(
            media_type
        )

        normalized_external_ids = (
            normalize_external_ids(
                external_ids
            )
        )

        candidates = self._load_candidates(
            title=title,
            original_title=original_title,
            media_type=normalized_media_type,
            year=year,
            limit=max(limit * 5, 100),
        )

        matches: list[KnowledgeMatch] = []

        for item in candidates:
            match = self._compare_item(
                item=item,
                normalized_title=normalized_title,
                normalized_original_title=(
                    normalized_original_title
                ),
                media_type=normalized_media_type,
                year=year,
                external_ids=normalized_external_ids,
            )

            if match is not None:
                matches.append(match)

        matches.sort(
            key=lambda match: (
                -match.score,
                match.item.id,
            )
        )

        return matches[:limit]

    def find_best_match(
        self,
        *,
        title: str,
        media_type: str | None = None,
        year: int | None = None,
        original_title: str | None = None,
        external_ids: dict[str, Any] | None = None,
        minimum_score: float = 0.85,
    ) -> KnowledgeMatch | None:
        matches = self.find_matches(
            title=title,
            media_type=media_type,
            year=year,
            original_title=original_title,
            external_ids=external_ids,
            limit=1,
        )

        if not matches:
            return None

        best_match = matches[0]

        if best_match.score < minimum_score:
            return None

        return best_match

    def find_exact_duplicate(
        self,
        *,
        title: str,
        media_type: str | None = None,
        year: int | None = None,
        original_title: str | None = None,
        external_ids: dict[str, Any] | None = None,
    ) -> KnowledgeMatch | None:
        matches = self.find_matches(
            title=title,
            media_type=media_type,
            year=year,
            original_title=original_title,
            external_ids=external_ids,
            limit=20,
        )

        for match in matches:
            if match.match_type in {
                "external_id",
                "exact_title_year",
                "exact_alias_year",
                "exact_original_title_year",
            }:
                return match

        return None

    def find_database_duplicates(
        self,
    ) -> list[dict[str, Any]]:
        statement = (
            select(KnowledgeItem)
            .options(
                selectinload(
                    KnowledgeItem.aliases
                )
            )
            .order_by(
                KnowledgeItem.id.asc()
            )
        )

        items = list(
            self.db.scalars(statement).all()
        )

        duplicate_groups: list[
            dict[str, Any]
        ] = []

        processed_ids: set[int] = set()

        for item in items:
            if item.id in processed_ids:
                continue

            matches = self.find_matches(
                title=item.title,
                media_type=item.media_type,
                year=item.year,
                original_title=item.original_title,
                external_ids=decode_json(
                    item.external_ids
                ),
                limit=100,
            )

            duplicates = [
                match
                for match in matches
                if (
                    match.item.id != item.id
                    and match.score >= 0.95
                )
            ]

            if not duplicates:
                continue

            group_ids = {
                item.id,
                *(
                    match.item.id
                    for match in duplicates
                ),
            }

            if group_ids & processed_ids:
                continue

            processed_ids.update(group_ids)

            duplicate_groups.append(
                {
                    "primary_item_id": item.id,
                    "primary_title": item.title,
                    "primary_year": item.year,
                    "duplicate_count": len(
                        duplicates
                    ),
                    "duplicates": [
                        match.to_dict()
                        for match in duplicates
                    ],
                }
            )

        return duplicate_groups

    def _load_candidates(
        self,
        *,
        title: str,
        original_title: str | None,
        media_type: str,
        year: int | None,
        limit: int,
    ) -> list[KnowledgeItem]:
        statement = select(
            KnowledgeItem
        ).options(
            selectinload(
                KnowledgeItem.aliases
            )
        )

        if media_type:
            statement = statement.where(
                KnowledgeItem.media_type
                == media_type
            )

        candidate_filters = []

        title_value = title.strip()

        if title_value:
            search_value = (
                f"%{title_value}%"
            )

            alias_item_ids = select(
                KnowledgeAlias.item_id
            ).where(
                KnowledgeAlias.title.ilike(
                    search_value
                )
            )

            candidate_filters.extend(
                [
                    KnowledgeItem.title.ilike(
                        search_value
                    ),
                    KnowledgeItem.original_title.ilike(
                        search_value
                    ),
                    KnowledgeItem.id.in_(
                        alias_item_ids
                    ),
                ]
            )

        if original_title:
            original_search_value = (
                f"%{original_title.strip()}%"
            )

            original_alias_item_ids = select(
                KnowledgeAlias.item_id
            ).where(
                KnowledgeAlias.title.ilike(
                    original_search_value
                )
            )

            candidate_filters.extend(
                [
                    KnowledgeItem.title.ilike(
                        original_search_value
                    ),
                    KnowledgeItem.original_title.ilike(
                        original_search_value
                    ),
                    KnowledgeItem.id.in_(
                        original_alias_item_ids
                    ),
                ]
            )

        if candidate_filters:
            statement = statement.where(
                or_(*candidate_filters)
            )

        if year is not None:
            statement = statement.where(
                or_(
                    KnowledgeItem.year == year,
                    KnowledgeItem.year.is_(None),
                )
            )

        statement = statement.order_by(
            KnowledgeItem.title.asc(),
            KnowledgeItem.year.asc(),
            KnowledgeItem.id.asc(),
        ).limit(limit)

        candidates = list(
            self.db.scalars(statement).unique().all()
        )

        if candidates:
            return candidates

        fallback_statement = select(
            KnowledgeItem
        ).options(
            selectinload(
                KnowledgeItem.aliases
            )
        )

        if media_type:
            fallback_statement = (
                fallback_statement.where(
                    KnowledgeItem.media_type
                    == media_type
                )
            )

        if year is not None:
            fallback_statement = (
                fallback_statement.where(
                    or_(
                        KnowledgeItem.year
                        == year,
                        KnowledgeItem.year.is_(
                            None
                        ),
                    )
                )
            )

        fallback_statement = (
            fallback_statement
            .order_by(
                KnowledgeItem.id.asc()
            )
            .limit(limit)
        )

        return list(
            self.db.scalars(
                fallback_statement
            ).unique().all()
        )

    def _compare_item(
        self,
        *,
        item: KnowledgeItem,
        normalized_title: str,
        normalized_original_title: str,
        media_type: str,
        year: int | None,
        external_ids: dict[str, str],
    ) -> KnowledgeMatch | None:
        reasons: list[str] = []

        item_media_type = (
            normalize_media_type(
                item.media_type
            )
        )

        if (
            media_type
            and item_media_type
            and media_type != item_media_type
        ):
            return None

        item_external_ids = (
            normalize_external_ids(
                decode_json(
                    item.external_ids
                )
            )
        )

        matching_external_ids = []

        for key, value in external_ids.items():
            item_value = (
                item_external_ids.get(key)
            )

            if (
                item_value
                and item_value == value
            ):
                matching_external_ids.append(
                    f"{key}:{value}"
                )

        if matching_external_ids:
            reasons.append(
                "Identische externe ID: "
                + ", ".join(
                    matching_external_ids
                )
            )

            return KnowledgeMatch(
                item=item,
                score=1.0,
                match_type="external_id",
                reasons=reasons,
            )

        item_titles = self._collect_titles(
            item
        )

        exact_title_match = (
            normalized_title
            in item_titles
        )

        exact_original_title_match = (
            bool(normalized_original_title)
            and normalized_original_title
            in item_titles
        )

        year_equal = (
            year is not None
            and item.year is not None
            and year == item.year
        )

        year_unknown = (
            year is None
            or item.year is None
        )

        if exact_title_match and year_equal:
            reasons.extend(
                [
                    "Identischer Titel",
                    "Identisches Jahr",
                ]
            )

            match_type = (
                "exact_title_year"
                if normalize_title(
                    item.title
                )
                == normalized_title
                else "exact_alias_year"
            )

            return KnowledgeMatch(
                item=item,
                score=0.99,
                match_type=match_type,
                reasons=reasons,
            )

        if (
            exact_original_title_match
            and year_equal
        ):
            reasons.extend(
                [
                    "Identischer Originaltitel",
                    "Identisches Jahr",
                ]
            )

            return KnowledgeMatch(
                item=item,
                score=0.985,
                match_type=(
                    "exact_original_title_year"
                ),
                reasons=reasons,
            )

        if exact_title_match and year_unknown:
            reasons.append(
                "Identischer Titel"
            )
            reasons.append(
                "Jahr auf mindestens einer Seite unbekannt"
            )

            return KnowledgeMatch(
                item=item,
                score=0.93,
                match_type="exact_title",
                reasons=reasons,
            )

        best_similarity = 0.0
        best_item_title = ""

        incoming_titles = {
            normalized_title,
        }

        if normalized_original_title:
            incoming_titles.add(
                normalized_original_title
            )

        for incoming_title in incoming_titles:
            for item_title in item_titles:
                similarity = SequenceMatcher(
                    None,
                    incoming_title,
                    item_title,
                ).ratio()

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_item_title = item_title

        if best_similarity < 0.72:
            return None

        score = best_similarity

        reasons.append(
            "Ähnlicher Titel: "
            f"{best_similarity:.3f}"
        )

        if best_item_title:
            reasons.append(
                "Verglichen mit: "
                f"{best_item_title}"
            )

        if year_equal:
            score += 0.08
            reasons.append(
                "Identisches Jahr"
            )
        elif (
            year is not None
            and item.year is not None
        ):
            year_difference = abs(
                year - item.year
            )

            if year_difference == 1:
                score -= 0.04
                reasons.append(
                    "Jahr weicht um 1 ab"
                )
            else:
                score -= min(
                    0.25,
                    year_difference * 0.04,
                )
                reasons.append(
                    "Unterschiedliches Jahr"
                )

        score = max(
            0.0,
            min(score, 0.97),
        )

        if score < 0.72:
            return None

        return KnowledgeMatch(
            item=item,
            score=score,
            match_type="fuzzy_title",
            reasons=reasons,
        )

    @staticmethod
    def _collect_titles(
        item: KnowledgeItem,
    ) -> set[str]:
        titles = {
            normalize_title(item.title),
        }

        if item.original_title:
            titles.add(
                normalize_title(
                    item.original_title
                )
            )

        for alias in item.aliases:
            normalized_alias = (
                normalize_title(
                    alias.title
                )
            )

            if normalized_alias:
                titles.add(
                    normalized_alias
                )

        return {
            title
            for title in titles
            if title
        }


def normalize_media_type(
    value: str | None,
) -> str:
    if not value:
        return ""

    normalized = (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    aliases = {
        "movie": "movie",
        "film": "movie",
        "movies": "movie",
        "serie": "series",
        "series": "series",
        "tv": "series",
        "tv_series": "series",
        "show": "series",
        "episode": "episode",
        "season": "season",
        "audiobook": "audiobook",
        "hörbuch": "audiobook",
        "audio_book": "audiobook",
    }

    return aliases.get(
        normalized,
        normalized,
    )


def normalize_external_ids(
    values: dict[str, Any] | None,
) -> dict[str, str]:
    if not values:
        return {}

    normalized: dict[str, str] = {}

    key_aliases = {
        "imdb": "imdb",
        "imdb_id": "imdb",
        "tmdb": "tmdb",
        "tmdb_id": "tmdb",
        "tvdb": "tvdb",
        "tvdb_id": "tvdb",
        "musicbrainz": "musicbrainz",
        "musicbrainz_id": "musicbrainz",
        "audible": "audible",
        "audible_id": "audible",
        "asin": "asin",
    }

    for raw_key, raw_value in values.items():
        if raw_value is None:
            continue

        key = (
            str(raw_key)
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        canonical_key = key_aliases.get(
            key,
            key,
        )

        value = str(
            raw_value
        ).strip().lower()

        if not value:
            continue

        normalized[canonical_key] = value

    return normalized


def normalize_title(
    value: str | None,
) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize(
        "NFKD",
        str(value),
    )

    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(
            character
        )
    )

    normalized = normalized.lower()

    normalized = normalized.replace(
        "&",
        " and ",
    )

    normalized = re.sub(
        r"['’`´]",
        "",
        normalized,
    )

    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()
