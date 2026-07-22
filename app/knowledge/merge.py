from copy import deepcopy
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.knowledge.constants import (
    normalize_relation_type,
)
from app.knowledge.models import (
    KnowledgeAlias,
    KnowledgeItem,
    KnowledgeRelation,
)
from app.knowledge.service import (
    decode_json,
    encode_json,
    item_to_dict,
    relation_to_dict,
)


class KnowledgeMergeError(ValueError):
    """Fehler beim Zusammenführen von Wissenseinträgen."""


class KnowledgeMergeService:
    """
    Führt doppelte Wissenseinträge sicher zusammen.

    Der Haupteintrag bleibt erhalten.
    Der Dubletteneintrag wird nach erfolgreicher
    Übernahme aller Daten gelöscht.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def preview_merge(
        self,
        *,
        primary_id: int,
        duplicate_id: int,
    ) -> dict[str, Any]:
        primary = self._require_item(primary_id)
        duplicate = self._require_item(duplicate_id)

        self._validate_items(
            primary=primary,
            duplicate=duplicate,
        )

        alias_preview = self._preview_aliases(
            primary=primary,
            duplicate=duplicate,
        )

        relation_preview = (
            self._preview_relations(
                primary=primary,
                duplicate=duplicate,
            )
        )

        merged_external_ids = merge_dicts(
            decode_json(primary.external_ids),
            decode_json(duplicate.external_ids),
        )

        merged_metadata = merge_dicts(
            decode_json(primary.metadata_json),
            decode_json(duplicate.metadata_json),
        )

        return {
            "primary": item_to_dict(primary),
            "duplicate": item_to_dict(duplicate),
            "result": {
                "title": (
                    primary.title
                    or duplicate.title
                ),
                "original_title": (
                    primary.original_title
                    or duplicate.original_title
                ),
                "media_type": (
                    primary.media_type
                    or duplicate.media_type
                ),
                "year": (
                    primary.year
                    if primary.year is not None
                    else duplicate.year
                ),
                "external_ids": (
                    merged_external_ids
                ),
                "metadata": merged_metadata,
            },
            "aliases": alias_preview,
            "relations": relation_preview,
            "duplicate_will_be_deleted": True,
        }

    def merge_items(
        self,
        *,
        primary_id: int,
        duplicate_id: int,
        commit: bool = True,
    ) -> dict[str, Any]:
        primary = self._require_item(primary_id)
        duplicate = self._require_item(duplicate_id)

        self._validate_items(
            primary=primary,
            duplicate=duplicate,
        )

        preview = self.preview_merge(
            primary_id=primary_id,
            duplicate_id=duplicate_id,
        )

        statistics = {
            "aliases_added": 0,
            "aliases_skipped": 0,
            "relations_moved": 0,
            "relations_merged": 0,
            "relations_removed": 0,
        }

        try:
            self._merge_basic_fields(
                primary=primary,
                duplicate=duplicate,
            )

            alias_statistics = self._merge_aliases(
                primary=primary,
                duplicate=duplicate,
            )

            statistics.update(
                alias_statistics
            )

            relation_statistics = (
                self._merge_relations(
                    primary=primary,
                    duplicate=duplicate,
                )
            )

            statistics.update(
                relation_statistics
            )

            self.db.flush()

            self.db.delete(duplicate)
            self.db.flush()

            if commit:
                self.db.commit()
                self.db.refresh(primary)

            return {
                "status": "merged",
                "primary_id": primary.id,
                "deleted_duplicate_id": (
                    duplicate_id
                ),
                "statistics": statistics,
                "preview": preview,
                "result": item_to_dict(primary),
            }

        except Exception:
            self.db.rollback()
            raise

    def _merge_basic_fields(
        self,
        *,
        primary: KnowledgeItem,
        duplicate: KnowledgeItem,
    ) -> None:
        if (
            not primary.original_title
            and duplicate.original_title
        ):
            primary.original_title = (
                duplicate.original_title
            )

        if (
            primary.year is None
            and duplicate.year is not None
        ):
            primary.year = duplicate.year

        if (
            not primary.media_type
            and duplicate.media_type
        ):
            primary.media_type = (
                duplicate.media_type
            )

        primary.external_ids = encode_json(
            merge_dicts(
                decode_json(
                    primary.external_ids
                ),
                decode_json(
                    duplicate.external_ids
                ),
            )
        )

        primary.metadata_json = encode_json(
            merge_dicts(
                decode_json(
                    primary.metadata_json
                ),
                decode_json(
                    duplicate.metadata_json
                ),
            )
        )

    def _merge_aliases(
        self,
        *,
        primary: KnowledgeItem,
        duplicate: KnowledgeItem,
    ) -> dict[str, int]:
        existing_alias_keys = {
            self._alias_key(
                title=alias.title,
                language=alias.language,
            )
            for alias in primary.aliases
        }

        added = 0
        skipped = 0

        possible_aliases: list[
            tuple[str, str | None, str]
        ] = []

        possible_aliases.append(
            (
                duplicate.title,
                None,
                "merged_title",
            )
        )

        if duplicate.original_title:
            possible_aliases.append(
                (
                    duplicate.original_title,
                    None,
                    "merged_original_title",
                )
            )

        for alias in duplicate.aliases:
            possible_aliases.append(
                (
                    alias.title,
                    alias.language,
                    alias.alias_type,
                )
            )

        primary_title_key = normalize_text(
            primary.title
        )

        primary_original_key = normalize_text(
            primary.original_title
        )

        for (
            title,
            language,
            alias_type,
        ) in possible_aliases:
            alias_key = self._alias_key(
                title=title,
                language=language,
            )

            normalized_title = normalize_text(
                title
            )

            if not normalized_title:
                skipped += 1
                continue

            if normalized_title in {
                primary_title_key,
                primary_original_key,
            }:
                skipped += 1
                continue

            if alias_key in existing_alias_keys:
                skipped += 1
                continue

            new_alias = KnowledgeAlias(
                item_id=primary.id,
                title=title.strip(),
                language=(
                    language.strip().lower()
                    if language
                    else None
                ),
                alias_type=(
                    alias_type.strip().lower()
                    if alias_type
                    else "alternative"
                ),
            )

            self.db.add(new_alias)

            existing_alias_keys.add(
                alias_key
            )

            added += 1

        return {
            "aliases_added": added,
            "aliases_skipped": skipped,
        }

    def _merge_relations(
        self,
        *,
        primary: KnowledgeItem,
        duplicate: KnowledgeItem,
    ) -> dict[str, int]:
        statement = (
            select(KnowledgeRelation)
            .where(
                or_(
                    KnowledgeRelation.source_id
                    == duplicate.id,
                    KnowledgeRelation.target_id
                    == duplicate.id,
                )
            )
            .order_by(
                KnowledgeRelation.id.asc()
            )
        )

        duplicate_relations = list(
            self.db.scalars(statement).all()
        )

        moved = 0
        merged = 0
        removed = 0

        for relation in duplicate_relations:
            new_source_id = (
                primary.id
                if relation.source_id
                == duplicate.id
                else relation.source_id
            )

            new_target_id = (
                primary.id
                if relation.target_id
                == duplicate.id
                else relation.target_id
            )

            if new_source_id == new_target_id:
                self.db.delete(relation)
                removed += 1
                continue

            relation_type = (
                normalize_relation_type(
                    relation.relation_type
                )
            )

            order_type = (
                normalize_relation_type(
                    relation.order_type
                )
                if relation.order_type
                else None
            )

            existing = (
                self._find_existing_relation(
                    source_id=new_source_id,
                    target_id=new_target_id,
                    relation_type=relation_type,
                    order_type=order_type,
                    exclude_relation_id=(
                        relation.id
                    ),
                )
            )

            if existing is not None:
                self._merge_relation_data(
                    target=existing,
                    source=relation,
                )

                self.db.delete(relation)
                merged += 1
                continue

            relation.source_id = (
                new_source_id
            )
            relation.target_id = (
                new_target_id
            )
            relation.relation_type = (
                relation_type
            )
            relation.order_type = (
                order_type
            )

            moved += 1

        return {
            "relations_moved": moved,
            "relations_merged": merged,
            "relations_removed": removed,
        }

    def _find_existing_relation(
        self,
        *,
        source_id: int,
        target_id: int,
        relation_type: str,
        order_type: str | None,
        exclude_relation_id: int,
    ) -> KnowledgeRelation | None:
        statement = select(
            KnowledgeRelation
        ).where(
            KnowledgeRelation.id
            != exclude_relation_id,
            KnowledgeRelation.source_id
            == source_id,
            KnowledgeRelation.target_id
            == target_id,
            KnowledgeRelation.relation_type
            == relation_type,
        )

        if order_type is None:
            statement = statement.where(
                KnowledgeRelation.order_type.is_(
                    None
                )
            )
        else:
            statement = statement.where(
                KnowledgeRelation.order_type
                == order_type
            )

        return self.db.scalar(statement)

    @staticmethod
    def _merge_relation_data(
        *,
        target: KnowledgeRelation,
        source: KnowledgeRelation,
    ) -> None:
        if (
            target.position is None
            and source.position is not None
        ):
            target.position = source.position

        elif (
            target.position is not None
            and source.position is not None
        ):
            target.position = min(
                target.position,
                source.position,
            )

        target.notes = merge_notes(
            target.notes,
            source.notes,
        )

    def _preview_aliases(
        self,
        *,
        primary: KnowledgeItem,
        duplicate: KnowledgeItem,
    ) -> dict[str, Any]:
        existing_keys = {
            self._alias_key(
                title=alias.title,
                language=alias.language,
            )
            for alias in primary.aliases
        }

        candidates = []

        values: list[
            tuple[str, str | None, str]
        ] = [
            (
                duplicate.title,
                None,
                "merged_title",
            )
        ]

        if duplicate.original_title:
            values.append(
                (
                    duplicate.original_title,
                    None,
                    "merged_original_title",
                )
            )

        values.extend(
            (
                alias.title,
                alias.language,
                alias.alias_type,
            )
            for alias in duplicate.aliases
        )

        primary_titles = {
            normalize_text(primary.title),
            normalize_text(
                primary.original_title
            ),
        }

        for title, language, alias_type in values:
            key = self._alias_key(
                title=title,
                language=language,
            )

            normalized_title = normalize_text(
                title
            )

            will_add = (
                bool(normalized_title)
                and normalized_title
                not in primary_titles
                and key not in existing_keys
            )

            candidates.append(
                {
                    "title": title,
                    "language": language,
                    "alias_type": alias_type,
                    "will_add": will_add,
                }
            )

            if will_add:
                existing_keys.add(key)

        return {
            "candidates": candidates,
            "add_count": sum(
                1
                for candidate in candidates
                if candidate["will_add"]
            ),
        }

    def _preview_relations(
        self,
        *,
        primary: KnowledgeItem,
        duplicate: KnowledgeItem,
    ) -> dict[str, Any]:
        statement = (
            select(KnowledgeRelation)
            .where(
                or_(
                    KnowledgeRelation.source_id
                    == duplicate.id,
                    KnowledgeRelation.target_id
                    == duplicate.id,
                )
            )
            .order_by(
                KnowledgeRelation.id.asc()
            )
        )

        relations = list(
            self.db.scalars(statement).all()
        )

        results = []

        for relation in relations:
            new_source_id = (
                primary.id
                if relation.source_id
                == duplicate.id
                else relation.source_id
            )

            new_target_id = (
                primary.id
                if relation.target_id
                == duplicate.id
                else relation.target_id
            )

            if new_source_id == new_target_id:
                action = "remove_self_relation"
            else:
                existing = (
                    self._find_existing_relation(
                        source_id=new_source_id,
                        target_id=new_target_id,
                        relation_type=(
                            normalize_relation_type(
                                relation.relation_type
                            )
                        ),
                        order_type=(
                            normalize_relation_type(
                                relation.order_type
                            )
                            if relation.order_type
                            else None
                        ),
                        exclude_relation_id=(
                            relation.id
                        ),
                    )
                )

                action = (
                    "merge_with_existing"
                    if existing is not None
                    else "move_to_primary"
                )

            results.append(
                {
                    "relation": (
                        relation_to_dict(
                            relation
                        )
                    ),
                    "new_source_id": (
                        new_source_id
                    ),
                    "new_target_id": (
                        new_target_id
                    ),
                    "action": action,
                }
            )

        return {
            "count": len(results),
            "items": results,
        }

    def _require_item(
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
            raise KnowledgeMergeError(
                "Wissenseintrag wurde nicht "
                f"gefunden: {item_id}"
            )

        return item

    @staticmethod
    def _validate_items(
        *,
        primary: KnowledgeItem,
        duplicate: KnowledgeItem,
    ) -> None:
        if primary.id == duplicate.id:
            raise KnowledgeMergeError(
                "Haupteintrag und Dublette "
                "dürfen nicht identisch sein."
            )

        primary_type = normalize_text(
            primary.media_type
        )

        duplicate_type = normalize_text(
            duplicate.media_type
        )

        if (
            primary_type
            and duplicate_type
            and primary_type != duplicate_type
        ):
            raise KnowledgeMergeError(
                "Die Medientypen stimmen "
                "nicht überein: "
                f"{primary.media_type!r} und "
                f"{duplicate.media_type!r}"
            )

    @staticmethod
    def _alias_key(
        *,
        title: str,
        language: str | None,
    ) -> tuple[str, str]:
        return (
            normalize_text(title),
            normalize_text(language),
        )


def normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


def merge_notes(
    primary: str | None,
    duplicate: str | None,
) -> str | None:
    primary_value = (
        primary.strip()
        if primary
        else ""
    )

    duplicate_value = (
        duplicate.strip()
        if duplicate
        else ""
    )

    if not primary_value:
        return duplicate_value or None

    if not duplicate_value:
        return primary_value

    if duplicate_value in primary_value:
        return primary_value

    if primary_value in duplicate_value:
        return duplicate_value

    return (
        primary_value
        + "\n\n"
        + duplicate_value
    )


def merge_dicts(
    primary: dict[str, Any],
    duplicate: dict[str, Any],
) -> dict[str, Any]:
    """
    Vereinigt zwei Wörterbücher rekursiv.

    Bereits vorhandene Werte des Haupteintrags
    haben Vorrang. Fehlende Werte werden aus
    der Dublette übernommen.
    """
    result = deepcopy(primary)

    for key, duplicate_value in duplicate.items():
        if key not in result:
            result[key] = deepcopy(
                duplicate_value
            )
            continue

        primary_value = result[key]

        if (
            isinstance(primary_value, dict)
            and isinstance(
                duplicate_value,
                dict,
            )
        ):
            result[key] = merge_dicts(
                primary_value,
                duplicate_value,
            )
            continue

        if is_empty_value(primary_value):
            result[key] = deepcopy(
                duplicate_value
            )

    return result


def is_empty_value(
    value: Any,
) -> bool:
    """
    Prüft sicher, ob ein Wert als leer gilt.

    Unterstützt auch Listen, Wörterbücher,
    Mengen und andere Container.
    """
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(
        value,
        (list, tuple, set, dict),
    ):
        return len(value) == 0

    return False
