from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_reference_uuid() -> str:
    return str(uuid4())


class ReferenceProfile(Base):
    __tablename__ = "reference_profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    reference_uuid: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        default=new_reference_uuid,
        index=True,
    )

    reference_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_file_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_file_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    quality_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    quality_profile: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    created_with_pipeline: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_with_profile: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    analysis_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    quality_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    comparison_settings_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    enabled: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        index=True,
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

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="uq_reference_profile_name",
        ),
    )
