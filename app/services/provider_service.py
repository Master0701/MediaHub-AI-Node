import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Provider
from app.providers.registry import provider_registry


def serialize_config(
    config: dict[str, Any] | None,
) -> str:
    return json.dumps(
        config or {},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def deserialize_config(
    config: str | None,
) -> dict[str, Any]:
    if not config:
        return {}

    try:
        value = json.loads(config)
    except json.JSONDecodeError:
        return {"raw": config}

    if isinstance(value, dict):
        return value

    return {"value": value}


def ensure_default_providers(
    db: Session,
) -> None:
    for provider_name in provider_registry.list_names():
        existing = db.scalar(select(Provider).where(Provider.name == provider_name))

        if existing is not None:
            continue

        db.add(
            Provider(
                name=provider_name,
                enabled=1,
                config=serialize_config({}),
            )
        )

    db.commit()


def list_providers(
    db: Session,
) -> list[Provider]:
    query = select(Provider).order_by(Provider.name.asc())

    return list(db.scalars(query).all())


def get_provider(
    db: Session,
    provider_name: str,
) -> Provider | None:
    query = select(Provider).where(Provider.name == provider_name)

    return db.scalar(query)


def set_provider_enabled(
    db: Session,
    provider: Provider,
    enabled: bool,
) -> Provider:
    provider.enabled = 1 if enabled else 0

    db.commit()
    db.refresh(provider)

    return provider


def provider_to_dict(
    provider: Provider,
) -> dict[str, Any]:
    implementation = provider_registry.get(provider.name)

    return {
        "id": provider.id,
        "name": provider.name,
        "enabled": bool(provider.enabled),
        "registered": implementation is not None,
        "config": deserialize_config(provider.config),
    }
