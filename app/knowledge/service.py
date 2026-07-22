import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.knowledge.constants import (
    normalize_relation_type,
)
from app.knowledge.models import (
    KnowledgeAlias,
    KnowledgeItem,
    KnowledgeRelation,
)


def encode_json(value: dict[str, Any] | None) -> str:
    return json.dumps(
        value or {},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def decode_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {"raw": value}

    if isinstance(decoded, dict):
        return decoded

    return {"value": decoded}


def create_item(
    db: Session,
    media_type: str,
    title: str,
    original_title: str | None = None,
    year: int | None = None,
    external_ids: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeItem:
    item = KnowledgeItem(
        media_type=media_type.strip().lower(),
        title=title.strip(),
        original_title=(
            original_title.strip()
            if original_title
            else None
        ),
        year=year,
        external_ids=encode_json(external_ids),
        metadata_json=encode_json(metadata),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def get_item(
    db: Session,
    item_id: int,
) -> KnowledgeItem | None:
    return db.get(KnowledgeItem, item_id)


def search_items(
    db: Session,
    query: str | None = None,
    media_type: str | None = None,
    limit: int = 100,
) -> list[KnowledgeItem]:
    statement = select(KnowledgeItem)

    if media_type:
        statement = statement.where(
            KnowledgeItem.media_type
            == media_type.strip().lower()
        )

    if query:
        search_value = f"%{query.strip()}%"

        alias_item_ids = select(
            KnowledgeAlias.item_id
        ).where(
            KnowledgeAlias.title.ilike(search_value)
        )

        statement = statement.where(
            or_(
                KnowledgeItem.title.ilike(search_value),
                KnowledgeItem.original_title.ilike(
                    search_value
                ),
                KnowledgeItem.id.in_(alias_item_ids),
            )
        )

    statement = statement.order_by(
        KnowledgeItem.title.asc(),
        KnowledgeItem.year.asc(),
    ).limit(limit)

    return list(db.scalars(statement).all())


def add_alias(
    db: Session,
    item: KnowledgeItem,
    title: str,
    language: str | None = None,
    alias_type: str = "alternative",
) -> KnowledgeAlias:
    alias = KnowledgeAlias(
        item_id=item.id,
        title=title.strip(),
        language=(
            language.strip().lower()
            if language
            else None
        ),
        alias_type=alias_type.strip().lower(),
    )

    db.add(alias)
    db.commit()
    db.refresh(alias)

    return alias


def create_relation(
    db: Session,
    source_id: int,
    target_id: int,
    relation_type: str,
    order_type: str | None = None,
    position: int | None = None,
    notes: str | None = None,
) -> KnowledgeRelation:
    relation = KnowledgeRelation(
        source_id=source_id,
        target_id=target_id,
        relation_type=normalize_relation_type(
            relation_type
        ),
        order_type=(
            normalize_relation_type(
                order_type
            )
            if order_type
            else None
        ),
        position=position,
        notes=notes.strip() if notes else None,
    )

    db.add(relation)
    db.commit()
    db.refresh(relation)

    return relation


def list_relations(
    db: Session,
    item_id: int,
) -> list[KnowledgeRelation]:
    statement = (
        select(KnowledgeRelation)
        .where(
            or_(
                KnowledgeRelation.source_id == item_id,
                KnowledgeRelation.target_id == item_id,
            )
        )
        .order_by(
            KnowledgeRelation.relation_type.asc(),
            KnowledgeRelation.position.asc(),
        )
    )

    return list(db.scalars(statement).all())


def item_to_dict(
    item: KnowledgeItem,
) -> dict[str, Any]:
    return {
        "id": item.id,
        "media_type": item.media_type,
        "title": item.title,
        "original_title": item.original_title,
        "year": item.year,
        "external_ids": decode_json(
            item.external_ids
        ),
        "metadata": decode_json(
            item.metadata_json
        ),
        "aliases": [
            {
                "id": alias.id,
                "title": alias.title,
                "language": alias.language,
                "alias_type": alias.alias_type,
            }
            for alias in item.aliases
        ],
        "created": item.created,
        "updated": item.updated,
    }


def relation_to_dict(
    relation: KnowledgeRelation,
) -> dict[str, Any]:
    return {
        "id": relation.id,
        "source_id": relation.source_id,
        "target_id": relation.target_id,
        "relation_type": relation.relation_type,
        "order_type": relation.order_type,
        "position": relation.position,
        "notes": relation.notes,
        "created": relation.created,
    }
