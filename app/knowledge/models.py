from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    media_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    original_title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    external_ids: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    metadata_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    aliases: Mapped[list["KnowledgeAlias"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
    )


class KnowledgeAlias(Base):
    __tablename__ = "knowledge_aliases"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey(
            "knowledge_items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    alias_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="alternative",
    )

    item: Mapped[KnowledgeItem] = relationship(
        back_populates="aliases",
    )

    __table_args__ = (
        UniqueConstraint(
            "item_id",
            "title",
            "language",
            name="uq_knowledge_alias",
        ),
    )


class KnowledgeRelation(Base):
    __tablename__ = "knowledge_relations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey(
            "knowledge_items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_id: Mapped[int] = mapped_column(
        ForeignKey(
            "knowledge_items.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    relation_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    order_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    position: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "target_id",
            "relation_type",
            "order_type",
            name="uq_knowledge_relation",
        ),
    )
