from datetime import datetime, timezone

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
    return datetime.now(timezone.utc)


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    namespace: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    cache_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    value_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/json",
    )

    file_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    checksum: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
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

    expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    __table_args__ = (
        UniqueConstraint(
            "namespace",
            "cache_key",
            name="uq_cache_namespace_key",
        ),
    )
