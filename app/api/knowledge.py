from collections.abc import Generator
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.knowledge.service import (
    add_alias,
    create_item,
    create_relation,
    get_item,
    item_to_dict,
    list_relations,
    relation_to_dict,
    search_items,
)


router = APIRouter(
    prefix="/knowledge",
    tags=["Knowledge"],
)


class KnowledgeItemCreate(BaseModel):
    media_type: str = Field(
        min_length=1,
        max_length=50,
    )
    title: str = Field(
        min_length=1,
        max_length=500,
    )
    original_title: str | None = None
    year: int | None = Field(
        default=None,
        ge=1,
        le=9999,
    )
    external_ids: dict[str, Any] = Field(
        default_factory=dict
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class KnowledgeAliasCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=500,
    )
    language: str | None = Field(
        default=None,
        max_length=20,
    )
    alias_type: str = Field(
        default="alternative",
        min_length=1,
        max_length=50,
    )


class KnowledgeRelationCreate(BaseModel):
    source_id: int
    target_id: int
    relation_type: str = Field(
        min_length=1,
        max_length=100,
    )
    order_type: str | None = Field(
        default=None,
        max_length=50,
    )
    position: int | None = Field(
        default=None,
        ge=0,
    )
    notes: str | None = None


def get_database() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/items",
    status_code=status.HTTP_201_CREATED,
)
def create_item_endpoint(
    request: KnowledgeItemCreate,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    item = create_item(
        db=db,
        media_type=request.media_type,
        title=request.title,
        original_title=request.original_title,
        year=request.year,
        external_ids=request.external_ids,
        metadata=request.metadata,
    )

    return item_to_dict(item)


@router.get("/items")
def search_items_endpoint(
    q: str | None = None,
    media_type: str | None = None,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_database),
) -> list[dict[str, Any]]:
    items = search_items(
        db=db,
        query=q,
        media_type=media_type,
        limit=limit,
    )

    return [
        item_to_dict(item)
        for item in items
    ]


@router.get("/items/{item_id}")
def get_item_endpoint(
    item_id: int,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    item = get_item(db, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wissenseintrag nicht gefunden.",
        )

    result = item_to_dict(item)

    result["relations"] = [
        relation_to_dict(relation)
        for relation in list_relations(
            db,
            item_id,
        )
    ]

    return result


@router.post(
    "/items/{item_id}/aliases",
    status_code=status.HTTP_201_CREATED,
)
def add_alias_endpoint(
    item_id: int,
    request: KnowledgeAliasCreate,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    item = get_item(db, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wissenseintrag nicht gefunden.",
        )

    try:
        alias = add_alias(
            db=db,
            item=item,
            title=request.title,
            language=request.language,
            alias_type=request.alias_type,
        )
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dieser alternative Titel existiert bereits.",
        ) from exc

    return {
        "id": alias.id,
        "item_id": alias.item_id,
        "title": alias.title,
        "language": alias.language,
        "alias_type": alias.alias_type,
    }


@router.post(
    "/relations",
    status_code=status.HTTP_201_CREATED,
)
def create_relation_endpoint(
    request: KnowledgeRelationCreate,
    db: Session = Depends(get_database),
) -> dict[str, Any]:
    if request.source_id == request.target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Quelle und Ziel dürfen nicht "
                "identisch sein."
            ),
        )

    source = get_item(
        db,
        request.source_id,
    )
    target = get_item(
        db,
        request.target_id,
    )

    if source is None or target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Quell- oder Zieleintrag "
                "wurde nicht gefunden."
            ),
        )

    try:
        relation = create_relation(
            db=db,
            source_id=request.source_id,
            target_id=request.target_id,
            relation_type=request.relation_type,
            order_type=request.order_type,
            position=request.position,
            notes=request.notes,
        )
    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Diese Beziehung existiert bereits.",
        ) from exc

    return relation_to_dict(relation)


@router.get("/items/{item_id}/relations")
def list_relations_endpoint(
    item_id: int,
    db: Session = Depends(get_database),
) -> list[dict[str, Any]]:
    item = get_item(db, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wissenseintrag nicht gefunden.",
        )

    return [
        relation_to_dict(relation)
        for relation in list_relations(
            db,
            item_id,
        )
    ]
