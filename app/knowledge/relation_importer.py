from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.constants import normalize_relation_type
from app.knowledge.matcher import KnowledgeMatcher
from app.knowledge.models import (
    KnowledgeItem,
    KnowledgeRelation,
)
from app.knowledge.service import relation_to_dict


@dataclass(slots=True)
class KnowledgeItemReference:
    item_id: int | None = None
    title: str | None = None
    media_type: str | None = None
    year: int | None = None
    original_title: str | None = None
    external_ids: dict[str, Any] | None = None


@dataclass(slots=True)
class KnowledgeRelationRequest:
    source: KnowledgeItemReference
    target: KnowledgeItemReference
    relation_type: str
    order_type: str | None = None
    position: int | None = None
    notes: str | None = None


@dataclass(slots=True)
class KnowledgeRelationImportResult:
    status: str
    relation_id: int | None
    relation: dict[str, Any] | None
    source_id: int | None
    target_id: int | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "relation_id": self.relation_id,
            "relation": self.relation,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "message": self.message,
        }


class KnowledgeRelationImportError(ValueError):
    pass


class KnowledgeRelationImporter:
    """
    Erstellt Beziehungen zwischen vorhandenen
    Wissenseinträgen.

    Bereits vorhandene identische Beziehungen
    werden nicht doppelt angelegt.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.matcher = KnowledgeMatcher(db)

    def import_relation(
        self,
        request: KnowledgeRelationRequest,
        *,
        commit: bool = True,
        dry_run: bool = False,
    ) -> KnowledgeRelationImportResult:
        source = self._resolve_reference(
            request.source,
            role="Quelle",
        )

        target = self._resolve_reference(
            request.target,
            role="Ziel",
        )

        if source.id == target.id:
            raise KnowledgeRelationImportError(
                "Quelle und Ziel dürfen nicht "
                "derselbe Wissenseintrag sein."
            )

        relation_type = normalize_relation_type(
            request.relation_type
        )

        if not relation_type:
            raise KnowledgeRelationImportError(
                "Ein Beziehungstyp ist erforderlich."
            )

        order_type = (
            normalize_relation_type(
                request.order_type
            )
            if request.order_type
            else None
        )

        position = self._normalize_position(
            request.position
        )

        notes = (
            request.notes.strip()
            if request.notes
            else None
        )

        existing = self._find_existing_relation(
            source_id=source.id,
            target_id=target.id,
            relation_type=relation_type,
            order_type=order_type,
        )

        if existing is not None:
            changed = False

            if (
                existing.position is None
                and position is not None
            ):
                existing.position = position
                changed = True

            if notes:
                merged_notes = self._merge_notes(
                    existing.notes,
                    notes,
                )

                if merged_notes != existing.notes:
                    existing.notes = merged_notes
                    changed = True

            if dry_run:
                return KnowledgeRelationImportResult(
                    status=(
                        "would_update"
                        if changed
                        else "unchanged"
                    ),
                    relation_id=existing.id,
                    relation=relation_to_dict(
                        existing
                    ),
                    source_id=source.id,
                    target_id=target.id,
                    message=(
                        "Die vorhandene Beziehung "
                        "würde ergänzt."
                        if changed
                        else
                        "Die Beziehung ist bereits "
                        "vollständig vorhanden."
                    ),
                )

            try:
                if changed:
                    self.db.flush()

                    if commit:
                        self.db.commit()
                        self.db.refresh(existing)

                return KnowledgeRelationImportResult(
                    status=(
                        "updated"
                        if changed
                        else "unchanged"
                    ),
                    relation_id=existing.id,
                    relation=relation_to_dict(
                        existing
                    ),
                    source_id=source.id,
                    target_id=target.id,
                    message=(
                        "Vorhandene Beziehung wurde "
                        "ergänzt."
                        if changed
                        else
                        "Die Beziehung war bereits "
                        "vorhanden."
                    ),
                )

            except Exception:
                self.db.rollback()
                raise

        if dry_run:
            return KnowledgeRelationImportResult(
                status="would_create",
                relation_id=None,
                relation={
                    "source_id": source.id,
                    "target_id": target.id,
                    "relation_type": relation_type,
                    "order_type": order_type,
                    "position": position,
                    "notes": notes,
                },
                source_id=source.id,
                target_id=target.id,
                message=(
                    "Die Beziehung würde neu "
                    "angelegt."
                ),
            )

        relation = KnowledgeRelation(
            source_id=source.id,
            target_id=target.id,
            relation_type=relation_type,
            order_type=order_type,
            position=position,
            notes=notes,
        )

        try:
            self.db.add(relation)
            self.db.flush()

            if commit:
                self.db.commit()
                self.db.refresh(relation)

            return KnowledgeRelationImportResult(
                status="created",
                relation_id=relation.id,
                relation=relation_to_dict(
                    relation
                ),
                source_id=source.id,
                target_id=target.id,
                message=(
                    "Neue Beziehung wurde erstellt."
                ),
            )

        except Exception:
            self.db.rollback()
            raise

    def _resolve_reference(
        self,
        reference: KnowledgeItemReference,
        *,
        role: str,
    ) -> KnowledgeItem:
        if reference.item_id is not None:
            item = self.db.get(
                KnowledgeItem,
                reference.item_id,
            )

            if item is None:
                raise KnowledgeRelationImportError(
                    f"{role} wurde nicht gefunden: "
                    f"ID {reference.item_id}"
                )

            return item

        title = (
            reference.title.strip()
            if reference.title
            else ""
        )

        if not title:
            raise KnowledgeRelationImportError(
                f"{role}: Titel oder ID ist "
                "erforderlich."
            )

        matches = self.matcher.find_matches(
            title=title,
            media_type=reference.media_type,
            year=reference.year,
            original_title=(
                reference.original_title
            ),
            external_ids=(
                reference.external_ids
                or {}
            ),
            limit=10,
        )

        strong_matches = [
            match
            for match in matches
            if match.score >= 0.95
        ]

        if not strong_matches:
            raise KnowledgeRelationImportError(
                f"{role} konnte nicht eindeutig "
                f"gefunden werden: {title!r}"
            )

        if len(strong_matches) > 1:
            ids = [
                match.item.id
                for match in strong_matches
            ]

            raise KnowledgeRelationImportError(
                f"{role} ist nicht eindeutig: "
                f"{title!r}, Treffer-IDs: {ids}"
            )

        return strong_matches[0].item

    def _find_existing_relation(
        self,
        *,
        source_id: int,
        target_id: int,
        relation_type: str,
        order_type: str | None,
    ) -> KnowledgeRelation | None:
        statement = select(
            KnowledgeRelation
        ).where(
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
    def _normalize_position(
        value: int | None,
    ) -> int | None:
        if value is None:
            return None

        try:
            position = int(value)
        except (
            TypeError,
            ValueError,
        ) as error:
            raise KnowledgeRelationImportError(
                "Die Position muss eine Zahl sein."
            ) from error

        if position < 0:
            raise KnowledgeRelationImportError(
                "Die Position darf nicht negativ "
                "sein."
            )

        return position

    @staticmethod
    def _merge_notes(
        current: str | None,
        incoming: str | None,
    ) -> str | None:
        current_value = (
            current.strip()
            if current
            else ""
        )

        incoming_value = (
            incoming.strip()
            if incoming
            else ""
        )

        if not current_value:
            return incoming_value or None

        if not incoming_value:
            return current_value

        if incoming_value in current_value:
            return current_value

        return (
            current_value
            + "\n\n"
            + incoming_value
        )
