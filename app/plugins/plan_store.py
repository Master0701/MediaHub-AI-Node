"""Kurzlebiger Speicher für bestätigungspflichtige Plugin-Installationspläne."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from app.plugins.install_plan import PluginInstallPlan


@dataclass(frozen=True, slots=True)
class StoredPluginPlan:
    """Ein gespeicherter und noch nicht bestätigter Installationsplan."""

    plan_id: str
    plugin_id: str
    archive_path: Path
    sha256: str
    plan: PluginInstallPlan
    created_at: datetime
    expires_at: datetime
    consumed: bool = False

    @property
    def expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at


class PluginPlanStore:
    """Speichert Installationspläne nur für kurze Zeit im Arbeitsspeicher."""

    def __init__(
        self,
        *,
        ttl_minutes: int = 15,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if ttl_minutes <= 0:
            raise ValueError("ttl_minutes muss größer als 0 sein.")

        self.ttl = timedelta(minutes=ttl_minutes)
        self._now = now or (lambda: datetime.now(UTC))
        self._plans: dict[str, StoredPluginPlan] = {}

    def create(
        self,
        *,
        plugin_id: str,
        archive_path: Path,
        sha256: str,
        plan: PluginInstallPlan,
    ) -> StoredPluginPlan:
        """Erzeugt eine neue einmalig bestätigbare Plan-ID."""

        self.cleanup()

        created_at = self._now()
        plan_id = secrets.token_urlsafe(32)

        stored = StoredPluginPlan(
            plan_id=plan_id,
            plugin_id=plugin_id.strip().lower(),
            archive_path=archive_path.resolve(),
            sha256=sha256.strip().lower(),
            plan=plan,
            created_at=created_at,
            expires_at=created_at + self.ttl,
        )
        self._plans[plan_id] = stored
        return stored

    def get(self, plan_id: str) -> StoredPluginPlan | None:
        """Liefert einen gültigen Plan oder `None`."""

        stored = self._plans.get(plan_id)
        if stored is None:
            return None

        if stored.consumed or stored.expires_at <= self._now():
            self.delete(plan_id)
            return None

        return stored

    def consume(self, plan_id: str) -> StoredPluginPlan:
        """Entfernt einen gültigen Plan und gibt ihn einmalig zurück."""

        stored = self.get(plan_id)
        if stored is None:
            raise KeyError("Installationsplan nicht gefunden oder abgelaufen.")

        self._plans.pop(plan_id, None)

        return StoredPluginPlan(
            plan_id=stored.plan_id,
            plugin_id=stored.plugin_id,
            archive_path=stored.archive_path,
            sha256=stored.sha256,
            plan=stored.plan,
            created_at=stored.created_at,
            expires_at=stored.expires_at,
            consumed=True,
        )

    def delete(self, plan_id: str) -> None:
        """Entfernt einen Plan und seine temporäre Paketdatei."""

        stored = self._plans.pop(plan_id, None)
        if stored is not None:
            stored.archive_path.unlink(missing_ok=True)

    def cleanup(self) -> int:
        """Entfernt abgelaufene Pläne und deren temporäre Pakete."""

        expired_ids = [
            plan_id
            for plan_id, stored in self._plans.items()
            if stored.expires_at <= self._now()
        ]

        for plan_id in expired_ids:
            self.delete(plan_id)

        return len(expired_ids)

    def __len__(self) -> int:
        self.cleanup()
        return len(self._plans)
