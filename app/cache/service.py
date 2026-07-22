import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.cache.models import CacheEntry


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def encode_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def decode_json(value: str | None) -> Any:
    if not value:
        return {}

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {
            "raw": value,
        }


def normalize_namespace(namespace: str) -> str:
    return namespace.strip().lower()


def normalize_key(cache_key: str) -> str:
    return cache_key.strip()


def is_expired(entry: CacheEntry) -> bool:
    if entry.expires is None:
        return False

    expires = entry.expires

    if expires.tzinfo is None:
        expires = expires.replace(
            tzinfo=timezone.utc
        )

    return expires <= utc_now()


def get_cache_entry(
    db: Session,
    namespace: str,
    cache_key: str,
    include_expired: bool = False,
) -> CacheEntry | None:
    statement = select(CacheEntry).where(
        CacheEntry.namespace
        == normalize_namespace(namespace),
        CacheEntry.cache_key
        == normalize_key(cache_key),
    )

    entry = db.scalar(statement)

    if entry is None:
        return None

    if is_expired(entry) and not include_expired:
        return None

    entry.last_accessed = utc_now()
    entry.access_count += 1

    db.commit()
    db.refresh(entry)

    return entry


def set_cache_entry(
    db: Session,
    namespace: str,
    cache_key: str,
    value: Any,
    source: str | None = None,
    content_type: str = "application/json",
    file_path: str | None = None,
    checksum: str | None = None,
    ttl_seconds: int | None = None,
) -> CacheEntry:
    normalized_namespace = normalize_namespace(
        namespace
    )
    normalized_key = normalize_key(cache_key)

    statement = select(CacheEntry).where(
        CacheEntry.namespace
        == normalized_namespace,
        CacheEntry.cache_key
        == normalized_key,
    )

    entry = db.scalar(statement)

    expires = None

    if ttl_seconds is not None:
        expires = utc_now() + timedelta(
            seconds=ttl_seconds
        )

    if entry is None:
        entry = CacheEntry(
            namespace=normalized_namespace,
            cache_key=normalized_key,
        )

        db.add(entry)

    entry.value_json = encode_json(value)
    entry.source = (
        source.strip().lower()
        if source
        else None
    )
    entry.content_type = content_type
    entry.file_path = file_path
    entry.checksum = checksum
    entry.expires = expires
    entry.updated = utc_now()
    entry.last_accessed = utc_now()

    db.commit()
    db.refresh(entry)

    return entry


def delete_cache_entry(
    db: Session,
    namespace: str,
    cache_key: str,
) -> bool:
    entry = db.scalar(
        select(CacheEntry).where(
            CacheEntry.namespace
            == normalize_namespace(namespace),
            CacheEntry.cache_key
            == normalize_key(cache_key),
        )
    )

    if entry is None:
        return False

    db.delete(entry)
    db.commit()

    return True


def list_cache_entries(
    db: Session,
    namespace: str | None = None,
    include_expired: bool = False,
    limit: int = 100,
) -> list[CacheEntry]:
    statement = select(CacheEntry)

    if namespace:
        statement = statement.where(
            CacheEntry.namespace
            == normalize_namespace(namespace)
        )

    statement = statement.order_by(
        CacheEntry.updated.desc()
    ).limit(limit)

    entries = list(
        db.scalars(statement).all()
    )

    if include_expired:
        return entries

    return [
        entry
        for entry in entries
        if not is_expired(entry)
    ]


def purge_expired_entries(
    db: Session,
) -> int:
    now = utc_now()

    result = db.execute(
        delete(CacheEntry).where(
            CacheEntry.expires.is_not(None),
            CacheEntry.expires <= now,
        )
    )

    db.commit()

    return int(result.rowcount or 0)


def cache_entry_to_dict(
    entry: CacheEntry,
) -> dict[str, Any]:
    return {
        "id": entry.id,
        "namespace": entry.namespace,
        "cache_key": entry.cache_key,
        "value": decode_json(
            entry.value_json
        ),
        "source": entry.source,
        "content_type": entry.content_type,
        "file_path": entry.file_path,
        "checksum": entry.checksum,
        "created": entry.created,
        "updated": entry.updated,
        "expires": entry.expires,
        "expired": is_expired(entry),
        "last_accessed": entry.last_accessed,
        "access_count": entry.access_count,
    }
