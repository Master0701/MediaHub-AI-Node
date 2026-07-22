import json
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.references.models import ReferenceProfile


class ReferenceProfileNotFoundError(Exception):
    pass


class ReferenceProfileNameExistsError(Exception):
    pass


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, set):
        return sorted(value)

    raise TypeError(f"Nicht JSON-serialisierbarer Typ: {type(value).__name__}")


def json_dumps(value: Any) -> str:
    return json.dumps(
        value if value is not None else {},
        ensure_ascii=False,
        default=json_default,
        separators=(",", ":"),
    )


def json_loads(
    value: str | None,
    fallback: Any = None,
) -> Any:
    if not value:
        return {} if fallback is None else fallback

    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {} if fallback is None else fallback


class ReferenceService:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def create(
        self,
        *,
        name: str,
        description: str | None = None,
        source_file_path: str | None = None,
        source_file_name: str | None = None,
        quality_score: int | None = None,
        quality_profile: str | None = None,
        analysis: dict[str, Any] | None = None,
        quality: dict[str, Any] | None = None,
        comparison_settings: (dict[str, Any] | None) = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        normalized_name = self._normalize_name(name)

        analysis_data = analysis if isinstance(analysis, dict) else {}

        pipeline_version = analysis_data.get("pipeline_version")

        profile = ReferenceProfile(
            name=normalized_name,
            reference_version=1,
            created_with_pipeline=(str(pipeline_version) if pipeline_version is not None else None),
            created_with_profile=(self._normalize_optional_text(quality_profile)),
            description=self._normalize_optional_text(description),
            source_file_path=(self._normalize_optional_text(source_file_path)),
            source_file_name=(self._normalize_optional_text(source_file_name)),
            quality_score=quality_score,
            quality_profile=(self._normalize_optional_text(quality_profile)),
            analysis_json=json_dumps(analysis_data),
            quality_json=json_dumps(quality),
            comparison_settings_json=json_dumps(comparison_settings),
            enabled=1 if enabled else 0,
        )

        self.session.add(profile)

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()

            raise (ReferenceProfileNameExistsError(normalized_name)) from exc

        self.session.refresh(profile)

        return self.to_dict(profile)

    def list(
        self,
        *,
        enabled_only: bool = False,
    ) -> list[dict[str, Any]]:
        statement = select(ReferenceProfile).order_by(ReferenceProfile.name.asc())

        if enabled_only:
            statement = statement.where(ReferenceProfile.enabled == 1)

        profiles = self.session.scalars(statement).all()

        return [self.to_dict(profile) for profile in profiles]

    def get(
        self,
        profile_id: int,
    ) -> dict[str, Any]:
        profile = self._get_model(profile_id)

        return self.to_dict(profile)

    def get_by_name(
        self,
        name: str,
    ) -> dict[str, Any]:
        normalized_name = self._normalize_name(name)

        statement = select(ReferenceProfile).where(ReferenceProfile.name == normalized_name)

        profile = self.session.scalar(statement)

        if profile is None:
            raise ReferenceProfileNotFoundError(normalized_name)

        return self.to_dict(profile)

    def update(
        self,
        profile_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        source_file_path: str | None = None,
        source_file_name: str | None = None,
        quality_score: int | None = None,
        quality_profile: str | None = None,
        analysis: dict[str, Any] | None = None,
        quality: dict[str, Any] | None = None,
        comparison_settings: (dict[str, Any] | None) = None,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        profile = self._get_model(profile_id)

        if name is not None:
            profile.name = self._normalize_name(name)

        if description is not None:
            profile.description = self._normalize_optional_text(description)

        if source_file_path is not None:
            profile.source_file_path = self._normalize_optional_text(source_file_path)

        if source_file_name is not None:
            profile.source_file_name = self._normalize_optional_text(source_file_name)

        if quality_score is not None:
            profile.quality_score = quality_score

        if quality_profile is not None:
            profile.quality_profile = self._normalize_optional_text(quality_profile)

        if analysis is not None:
            profile.analysis_json = json_dumps(analysis)

        if quality is not None:
            profile.quality_json = json_dumps(quality)

        if comparison_settings is not None:
            profile.comparison_settings_json = json_dumps(comparison_settings)

        if enabled is not None:
            profile.enabled = 1 if enabled else 0

        profile.reference_version = max(
            int(profile.reference_version or 0) + 1,
            2,
        )

        if analysis is not None:
            pipeline_version = analysis.get("pipeline_version")

            if pipeline_version is not None:
                profile.created_with_pipeline = str(pipeline_version)

        if quality_profile is not None:
            profile.created_with_profile = self._normalize_optional_text(quality_profile)

        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()

            raise (ReferenceProfileNameExistsError(profile.name)) from exc

        self.session.refresh(profile)

        return self.to_dict(profile)

    def delete(
        self,
        profile_id: int,
    ) -> dict[str, Any]:
        profile = self._get_model(profile_id)

        result = self.to_dict(profile)

        self.session.delete(profile)
        self.session.commit()

        return result

    def _get_model(
        self,
        profile_id: int,
    ) -> ReferenceProfile:
        profile = self.session.get(
            ReferenceProfile,
            profile_id,
        )

        if profile is None:
            raise ReferenceProfileNotFoundError(profile_id)

        return profile

    @staticmethod
    def to_dict(
        profile: ReferenceProfile,
    ) -> dict[str, Any]:
        return {
            "id": profile.id,
            "reference_uuid": (profile.reference_uuid),
            "reference_version": (profile.reference_version),
            "name": profile.name,
            "description": (profile.description),
            "source": {
                "file_path": (profile.source_file_path),
                "file_name": (profile.source_file_name),
            },
            "quality_score": (profile.quality_score),
            "quality_profile": (profile.quality_profile),
            "created_with": {
                "pipeline": (profile.created_with_pipeline),
                "quality_profile": (profile.created_with_profile),
            },
            "analysis": json_loads(profile.analysis_json),
            "quality": json_loads(profile.quality_json),
            "comparison_settings": (json_loads(profile.comparison_settings_json)),
            "enabled": bool(profile.enabled),
            "created": (profile.created.isoformat() if profile.created else None),
            "updated": (profile.updated.isoformat() if profile.updated else None),
        }

    @staticmethod
    def _normalize_name(
        name: str,
    ) -> str:
        normalized = str(name).strip()

        if not normalized:
            raise ValueError("Der Profilname darf nicht leer sein.")

        if len(normalized) > 200:
            raise ValueError("Der Profilname darf höchstens 200 Zeichen lang sein.")

        return normalized

    @staticmethod
    def _normalize_optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()

        return normalized or None
