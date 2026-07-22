from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.knowledge.matcher import (
    KnowledgeMatch,
    KnowledgeMatcher,
    normalize_external_ids,
    normalize_media_type,
    normalize_title,
)
from app.knowledge.merge import merge_dicts
from app.knowledge.models import (
    KnowledgeAlias,
    KnowledgeItem,
)
from app.knowledge.service import (
    decode_json,
    encode_json,
    item_to_dict,
)


@dataclass(slots=True)
class KnowledgeImportRequest:
    title: str
    media_type: str
    year: int | None = None
    original_title: str | None = None
    aliases: list[dict[str, Any] | str] = field(
        default_factory=list
    )
    external_ids: dict[str, Any] = field(
        default_factory=dict
    )
    metadata: dict[str, Any] = field(
        default_factory=dict
    )
    source: str | None = None


@dataclass(slots=True)
class KnowledgeImportResult:
    status: str
    item_id: int | None
    item: dict[str, Any] | None
    match: dict[str, Any] | None
    candidates: list[dict[str, Any]]
    changes: dict[str, Any]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "item_id": self.item_id,
            "item": self.item,
            "match": self.match,
            "candidates": self.candidates,
            "changes": self.changes,
            "message": self.message,
        }


class KnowledgeImportError(ValueError):
    """Ungültige Daten beim Wissensimport."""


class KnowledgeImporter:
    """
    Importiert oder aktualisiert Wissenseinträge.

    Entscheidungen:

    - Kein passender Treffer:
      Neuer Eintrag wird erstellt.

    - Ein eindeutiger Treffer:
      Bestehender Eintrag wird ergänzt.

    - Mehrere gleichwertige Treffer:
      Konflikt wird zurückgegeben.

    Vorhandene Werte werden nicht ohne ausdrückliche
    Erlaubnis überschrieben.
    """

    EXACT_MATCH_TYPES = {
        "external_id",
        "exact_title_year",
        "exact_alias_year",
        "exact_original_title_year",
    }

    def __init__(
        self,
        db: Session,
        *,
        automatic_match_score: float = 0.95,
        conflict_score: float = 0.90,
    ) -> None:
        self.db = db
        self.matcher = KnowledgeMatcher(db)
        self.automatic_match_score = (
            automatic_match_score
        )
        self.conflict_score = conflict_score

    def import_item(
        self,
        request: KnowledgeImportRequest,
        *,
        commit: bool = True,
        dry_run: bool = False,
        overwrite_existing: bool = False,
    ) -> KnowledgeImportResult:
        request = self._normalize_request(request)

        matches = self.matcher.find_matches(
            title=request.title,
            media_type=request.media_type,
            year=request.year,
            original_title=request.original_title,
            external_ids=request.external_ids,
            limit=20,
        )

        decision = self._decide_match(matches)

        if decision["status"] == "conflict":
            return KnowledgeImportResult(
                status="conflict",
                item_id=None,
                item=None,
                match=None,
                candidates=[
                    match.to_dict()
                    for match in decision["matches"]
                ],
                changes={},
                message=(
                    "Mehrere mögliche Wissenseinträge "
                    "wurden gefunden. Es wurde nichts "
                    "verändert."
                ),
            )

        if decision["status"] == "create":
            if dry_run:
                return KnowledgeImportResult(
                    status="would_create",
                    item_id=None,
                    item=self._request_to_dict(
                        request
                    ),
                    match=None,
                    candidates=[
                        match.to_dict()
                        for match in matches
                    ],
                    changes={
                        "create_item": True,
                    },
                    message=(
                        "Es wurde kein eindeutiger "
                        "Treffer gefunden. Der Eintrag "
                        "würde neu angelegt."
                    ),
                )

            return self._create_item(
                request=request,
                commit=commit,
            )

        match: KnowledgeMatch = decision["match"]

        if dry_run:
            item = self._load_item(match.item.id)

            changes = self._calculate_changes(
                item=item,
                request=request,
                overwrite_existing=(
                    overwrite_existing
                ),
            )

            return KnowledgeImportResult(
                status="would_update",
                item_id=item.id,
                item=item_to_dict(item),
                match=match.to_dict(),
                candidates=[
                    candidate.to_dict()
                    for candidate in matches
                ],
                changes=changes,
                message=(
                    "Ein eindeutiger Treffer wurde "
                    "gefunden. Der vorhandene Eintrag "
                    "würde aktualisiert."
                ),
            )

        return self._update_item(
            item_id=match.item.id,
            request=request,
            match=match,
            commit=commit,
            overwrite_existing=(
                overwrite_existing
            ),
            candidates=matches,
        )

    def _decide_match(
        self,
        matches: list[KnowledgeMatch],
    ) -> dict[str, Any]:
        if not matches:
            return {
                "status": "create",
            }

        strong_matches = [
            match
            for match in matches
            if (
                match.score
                >= self.conflict_score
            )
        ]

        exact_matches = [
            match
            for match in strong_matches
            if match.match_type
            in self.EXACT_MATCH_TYPES
        ]

        if len(exact_matches) == 1:
            return {
                "status": "update",
                "match": exact_matches[0],
            }

        if len(exact_matches) > 1:
            external_id_matches = [
                match
                for match in exact_matches
                if match.match_type
                == "external_id"
            ]

            if len(external_id_matches) == 1:
                return {
                    "status": "update",
                    "match": (
                        external_id_matches[0]
                    ),
                }

            return {
                "status": "conflict",
                "matches": exact_matches,
            }

        best_match = matches[0]

        if (
            best_match.score
            < self.automatic_match_score
        ):
            return {
                "status": "create",
            }

        nearly_equal_matches = [
            match
            for match in strong_matches
            if abs(
                best_match.score
                - match.score
            ) <= 0.02
        ]

        if len(nearly_equal_matches) > 1:
            return {
                "status": "conflict",
                "matches": (
                    nearly_equal_matches
                ),
            }

        return {
            "status": "update",
            "match": best_match,
        }

    def _create_item(
        self,
        *,
        request: KnowledgeImportRequest,
        commit: bool,
    ) -> KnowledgeImportResult:
        item = KnowledgeItem(
            title=request.title,
            original_title=(
                request.original_title
            ),
            media_type=request.media_type,
            year=request.year,
            external_ids=encode_json(
                request.external_ids
            ),
            metadata_json=encode_json(
                self._metadata_with_source(
                    request.metadata,
                    request.source,
                )
            ),
        )

        try:
            self.db.add(item)
            self.db.flush()

            alias_changes = self._add_aliases(
                item=item,
                aliases=request.aliases,
            )

            self.db.flush()

            if commit:
                self.db.commit()

            item = self._load_item(item.id)

            return KnowledgeImportResult(
                status="created",
                item_id=item.id,
                item=item_to_dict(item),
                match=None,
                candidates=[],
                changes={
                    "created": True,
                    **alias_changes,
                },
                message=(
                    "Neuer Wissenseintrag wurde "
                    "erstellt."
                ),
            )

        except Exception:
            self.db.rollback()
            raise

    def _update_item(
        self,
        *,
        item_id: int,
        request: KnowledgeImportRequest,
        match: KnowledgeMatch,
        commit: bool,
        overwrite_existing: bool,
        candidates: list[KnowledgeMatch],
    ) -> KnowledgeImportResult:
        item = self._load_item(item_id)

        try:
            changes = self._apply_changes(
                item=item,
                request=request,
                overwrite_existing=(
                    overwrite_existing
                ),
            )

            self.db.flush()

            if commit:
                self.db.commit()

            item = self._load_item(item.id)

            changed = self._has_changes(
                changes
            )

            return KnowledgeImportResult(
                status=(
                    "updated"
                    if changed
                    else "unchanged"
                ),
                item_id=item.id,
                item=item_to_dict(item),
                match=match.to_dict(),
                candidates=[
                    candidate.to_dict()
                    for candidate in candidates
                ],
                changes=changes,
                message=(
                    "Vorhandener Wissenseintrag "
                    "wurde ergänzt."
                    if changed
                    else
                    "Der Wissenseintrag war bereits "
                    "vollständig. Es wurde nichts "
                    "verändert."
                ),
            )

        except Exception:
            self.db.rollback()
            raise

    def _apply_changes(
        self,
        *,
        item: KnowledgeItem,
        request: KnowledgeImportRequest,
        overwrite_existing: bool,
    ) -> dict[str, Any]:
        changes = self._calculate_changes(
            item=item,
            request=request,
            overwrite_existing=(
                overwrite_existing
            ),
        )

        field_changes = changes[
            "fields"
        ]

        for field_name, change in (
            field_changes.items()
        ):
            setattr(
                item,
                field_name,
                change["new"],
            )

        if changes["external_ids_changed"]:
            item.external_ids = encode_json(
                changes["external_ids"]
            )

        if changes["metadata_changed"]:
            item.metadata_json = encode_json(
                changes["metadata"]
            )

        alias_changes = self._add_aliases(
            item=item,
            aliases=request.aliases,
        )

        changes.update(alias_changes)

        return changes

    def _calculate_changes(
        self,
        *,
        item: KnowledgeItem,
        request: KnowledgeImportRequest,
        overwrite_existing: bool,
    ) -> dict[str, Any]:
        field_changes: dict[
            str,
            dict[str, Any]
        ] = {}

        incoming_fields = {
            "title": request.title,
            "original_title": (
                request.original_title
            ),
            "media_type": (
                request.media_type
            ),
            "year": request.year,
        }

        for field_name, incoming_value in (
            incoming_fields.items()
        ):
            current_value = getattr(
                item,
                field_name,
            )

            should_change = False

            if self._is_empty(current_value):
                should_change = not self._is_empty(
                    incoming_value
                )

            elif (
                overwrite_existing
                and not self._is_empty(
                    incoming_value
                )
                and current_value
                != incoming_value
            ):
                should_change = True

            if should_change:
                field_changes[field_name] = {
                    "old": current_value,
                    "new": incoming_value,
                }

        current_external_ids = (
            normalize_external_ids(
                decode_json(
                    item.external_ids
                )
            )
        )

        incoming_external_ids = (
            normalize_external_ids(
                request.external_ids
            )
        )

        if overwrite_existing:
            merged_external_ids = {
                **current_external_ids,
                **incoming_external_ids,
            }
        else:
            merged_external_ids = merge_dicts(
                current_external_ids,
                incoming_external_ids,
            )

        current_metadata = decode_json(
            item.metadata_json
        )

        incoming_metadata = (
            self._metadata_with_source(
                request.metadata,
                request.source,
            )
        )

        if overwrite_existing:
            merged_metadata = self._overwrite_dicts(
                current_metadata,
                incoming_metadata,
            )
        else:
            merged_metadata = merge_dicts(
                current_metadata,
                incoming_metadata,
            )

        alias_preview = self._preview_aliases(
            item=item,
            aliases=request.aliases,
        )

        return {
            "fields": field_changes,
            "external_ids": (
                merged_external_ids
            ),
            "external_ids_changed": (
                merged_external_ids
                != current_external_ids
            ),
            "metadata": merged_metadata,
            "metadata_changed": (
                merged_metadata
                != current_metadata
            ),
            "aliases_to_add": (
                alias_preview
            ),
        }

    def _add_aliases(
        self,
        *,
        item: KnowledgeItem,
        aliases: list[
            dict[str, Any] | str
        ],
    ) -> dict[str, Any]:
        existing_keys = {
            self._alias_key(
                alias.title,
                alias.language,
            )
            for alias in item.aliases
        }

        primary_titles = {
            normalize_title(item.title),
            normalize_title(
                item.original_title
            ),
        }

        added: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []

        for alias_data in aliases:
            parsed = self._parse_alias(
                alias_data
            )

            title = parsed["title"]
            language = parsed["language"]
            alias_type = parsed[
                "alias_type"
            ]

            normalized = normalize_title(
                title
            )

            alias_key = self._alias_key(
                title,
                language,
            )

            if not normalized:
                skipped.append({
                    **parsed,
                    "reason": "empty_title",
                })
                continue

            if normalized in primary_titles:
                skipped.append({
                    **parsed,
                    "reason": "primary_title",
                })
                continue

            if alias_key in existing_keys:
                skipped.append({
                    **parsed,
                    "reason": "already_exists",
                })
                continue

            alias = KnowledgeAlias(
                item_id=item.id,
                title=title,
                language=language,
                alias_type=alias_type,
            )

            self.db.add(alias)

            existing_keys.add(alias_key)
            added.append(parsed)

        return {
            "aliases_added": added,
            "aliases_skipped": skipped,
        }

    def _preview_aliases(
        self,
        *,
        item: KnowledgeItem,
        aliases: list[
            dict[str, Any] | str
        ],
    ) -> list[dict[str, Any]]:
        existing_keys = {
            self._alias_key(
                alias.title,
                alias.language,
            )
            for alias in item.aliases
        }

        primary_titles = {
            normalize_title(item.title),
            normalize_title(
                item.original_title
            ),
        }

        result = []

        for alias_data in aliases:
            parsed = self._parse_alias(
                alias_data
            )

            normalized = normalize_title(
                parsed["title"]
            )

            key = self._alias_key(
                parsed["title"],
                parsed["language"],
            )

            will_add = (
                bool(normalized)
                and normalized
                not in primary_titles
                and key not in existing_keys
            )

            result.append({
                **parsed,
                "will_add": will_add,
            })

            if will_add:
                existing_keys.add(key)

        return result

    def _load_item(
        self,
        item_id: int,
    ) -> KnowledgeItem:
        statement = (
            select(KnowledgeItem)
            .options(
                selectinload(
                    KnowledgeItem.aliases
                )
            )
            .where(
                KnowledgeItem.id == item_id
            )
        )

        item = self.db.scalar(statement)

        if item is None:
            raise KnowledgeImportError(
                "Wissenseintrag wurde nicht "
                f"gefunden: {item_id}"
            )

        return item

    @staticmethod
    def _normalize_request(
        request: KnowledgeImportRequest,
    ) -> KnowledgeImportRequest:
        title = str(
            request.title or ""
        ).strip()

        if not title:
            raise KnowledgeImportError(
                "Ein Titel ist erforderlich."
            )

        media_type = normalize_media_type(
            request.media_type
        )

        if not media_type:
            raise KnowledgeImportError(
                "Ein Medientyp ist erforderlich."
            )

        year = request.year

        if year is not None:
            try:
                year = int(year)
            except (
                TypeError,
                ValueError,
            ) as error:
                raise KnowledgeImportError(
                    "Das Jahr muss eine Zahl sein."
                ) from error

            if year < 1800 or year > 2200:
                raise KnowledgeImportError(
                    "Das Jahr liegt außerhalb "
                    "des erlaubten Bereichs."
                )

        original_title = (
            str(request.original_title).strip()
            if request.original_title
            else None
        )

        return KnowledgeImportRequest(
            title=title,
            media_type=media_type,
            year=year,
            original_title=original_title,
            aliases=list(
                request.aliases or []
            ),
            external_ids=(
                normalize_external_ids(
                    request.external_ids
                )
            ),
            metadata=dict(
                request.metadata or {}
            ),
            source=(
                str(request.source).strip()
                if request.source
                else None
            ),
        )

    @staticmethod
    def _parse_alias(
        alias: dict[str, Any] | str,
    ) -> dict[str, Any]:
        if isinstance(alias, str):
            return {
                "title": alias.strip(),
                "language": None,
                "alias_type": "alternative",
            }

        title = str(
            alias.get("title") or ""
        ).strip()

        language_value = alias.get(
            "language"
        )

        alias_type_value = alias.get(
            "alias_type",
            alias.get(
                "type",
                "alternative",
            ),
        )

        return {
            "title": title,
            "language": (
                str(language_value)
                .strip()
                .lower()
                if language_value
                else None
            ),
            "alias_type": (
                str(alias_type_value)
                .strip()
                .lower()
                if alias_type_value
                else "alternative"
            ),
        }

    @staticmethod
    def _alias_key(
        title: str,
        language: str | None,
    ) -> tuple[str, str]:
        return (
            normalize_title(title),
            (
                str(language)
                .strip()
                .lower()
                if language
                else ""
            ),
        )

    @staticmethod
    def _metadata_with_source(
        metadata: dict[str, Any],
        source: str | None,
    ) -> dict[str, Any]:
        result = dict(metadata)

        if source:
            existing_sources = result.get(
                "sources"
            )

            if isinstance(
                existing_sources,
                list,
            ):
                sources = [
                    str(value)
                    for value
                    in existing_sources
                    if value
                ]
            elif existing_sources:
                sources = [
                    str(existing_sources)
                ]
            else:
                sources = []

            if source not in sources:
                sources.append(source)

            result["sources"] = sources

        return result

    @classmethod
    def _overwrite_dicts(
        cls,
        primary: dict[str, Any],
        incoming: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(primary)

        for key, incoming_value in (
            incoming.items()
        ):
            current_value = result.get(key)

            if (
                isinstance(current_value, dict)
                and isinstance(
                    incoming_value,
                    dict,
                )
            ):
                result[key] = (
                    cls._overwrite_dicts(
                        current_value,
                        incoming_value,
                    )
                )
            else:
                result[key] = incoming_value

        return result

    @staticmethod
    def _request_to_dict(
        request: KnowledgeImportRequest,
    ) -> dict[str, Any]:
        return {
            "title": request.title,
            "original_title": (
                request.original_title
            ),
            "media_type": (
                request.media_type
            ),
            "year": request.year,
            "aliases": request.aliases,
            "external_ids": (
                request.external_ids
            ),
            "metadata": request.metadata,
            "source": request.source,
        }

    @staticmethod
    def _has_changes(
        changes: dict[str, Any],
    ) -> bool:
        return any([
            bool(changes.get("fields")),
            bool(
                changes.get(
                    "external_ids_changed"
                )
            ),
            bool(
                changes.get(
                    "metadata_changed"
                )
            ),
            bool(
                changes.get(
                    "aliases_added"
                )
            ),
        ])

    @staticmethod
    def _is_empty(
        value: Any,
    ) -> bool:
        return (
            value is None
            or value == ""
        )
