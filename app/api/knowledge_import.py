from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.knowledge.importer import (
    KnowledgeImporter,
    KnowledgeImportError,
    KnowledgeImportRequest,
)
from app.knowledge.merge import (
    KnowledgeMergeError,
    KnowledgeMergeService,
)
from app.knowledge.relation_importer import (
    KnowledgeItemReference,
    KnowledgeRelationImporter,
    KnowledgeRelationImportError,
    KnowledgeRelationRequest,
)

router = APIRouter(
    prefix="/knowledge/import",
    tags=["knowledge-import"],
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


class AliasInput(BaseModel):
    title: str
    language: str | None = None
    alias_type: str = "alternative"


class ItemImportInput(BaseModel):
    title: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    year: int | None = None
    original_title: str | None = None
    aliases: list[AliasInput | str] = Field(default_factory=list)
    external_ids: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
    dry_run: bool = False
    overwrite_existing: bool = False


class ItemReferenceInput(BaseModel):
    item_id: int | None = None
    title: str | None = None
    media_type: str | None = None
    year: int | None = None
    original_title: str | None = None
    external_ids: dict[str, Any] = Field(default_factory=dict)


class RelationImportInput(BaseModel):
    source: ItemReferenceInput
    target: ItemReferenceInput
    relation_type: str = Field(min_length=1)
    order_type: str | None = None
    position: int | None = None
    notes: str | None = None
    dry_run: bool = False


class MergeInput(BaseModel):
    primary_id: int
    duplicate_id: int
    dry_run: bool = True


@router.post("/item")
def import_item(
    payload: ItemImportInput,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        aliases = []

        for alias in payload.aliases:
            if isinstance(alias, str):
                aliases.append(alias)
            else:
                aliases.append(alias.model_dump())

        importer = KnowledgeImporter(db)

        result = importer.import_item(
            KnowledgeImportRequest(
                title=payload.title,
                media_type=payload.media_type,
                year=payload.year,
                original_title=payload.original_title,
                aliases=aliases,
                external_ids=payload.external_ids,
                metadata=payload.metadata,
                source=payload.source,
            ),
            dry_run=payload.dry_run,
            overwrite_existing=(payload.overwrite_existing),
        )

        return result.to_dict()

    except KnowledgeImportError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.post("/relation")
def import_relation(
    payload: RelationImportInput,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        importer = KnowledgeRelationImporter(db)

        result = importer.import_relation(
            KnowledgeRelationRequest(
                source=_to_reference(payload.source),
                target=_to_reference(payload.target),
                relation_type=(payload.relation_type),
                order_type=payload.order_type,
                position=payload.position,
                notes=payload.notes,
            ),
            dry_run=payload.dry_run,
        )

        return result.to_dict()

    except KnowledgeRelationImportError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.post("/merge")
def merge_items(
    payload: MergeInput,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        service = KnowledgeMergeService(db)

        if payload.dry_run:
            return service.preview_merge(
                primary_id=payload.primary_id,
                duplicate_id=payload.duplicate_id,
            )

        return service.merge_items(
            primary_id=payload.primary_id,
            duplicate_id=payload.duplicate_id,
        )

    except KnowledgeMergeError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


def _to_reference(
    payload: ItemReferenceInput,
) -> KnowledgeItemReference:
    return KnowledgeItemReference(
        item_id=payload.item_id,
        title=payload.title,
        media_type=payload.media_type,
        year=payload.year,
        original_title=payload.original_title,
        external_ids=payload.external_ids,
    )
