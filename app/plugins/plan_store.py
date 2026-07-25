"""Persistenter Speicher für bestätigungspflichtige Plugin-Installationspläne."""

from __future__ import annotations

import json
import secrets
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.plugins.install_plan import (
    InstallAction,
    InstallActionType,
    PluginInstallPlan,
)


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


class PluginPlanStore:
    """Speichert Installationspläne auf der Festplatte und im Arbeitsspeicher."""

    metadata_filename = "plan.json"
    archive_filename = "plugin.zip"

    def __init__(
        self,
        *,
        storage_root: Path,
        ttl_minutes: int = 15,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if ttl_minutes <= 0:
            raise ValueError("ttl_minutes muss größer als 0 sein.")

        self.storage_root = storage_root.resolve()
        self.ttl = timedelta(minutes=ttl_minutes)
        self._now = now or (lambda: datetime.now(UTC))
        self._plans: dict[str, StoredPluginPlan] = {}

        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.load()

    def create(
        self,
        *,
        plugin_id: str,
        archive_path: Path,
        sha256: str,
        plan: PluginInstallPlan,
    ) -> StoredPluginPlan:
        """Speichert einen neuen Plan samt Kopie des geprüften ZIP-Pakets."""

        self.cleanup()

        created_at = self._now()
        plan_id = secrets.token_urlsafe(32)
        plan_dir = (self.storage_root / plan_id).resolve()
        self._ensure_inside_root(plan_dir)

        plan_dir.mkdir(parents=True, exist_ok=False)
        persistent_archive = plan_dir / self.archive_filename
        shutil.copy2(archive_path, persistent_archive)

        stored = StoredPluginPlan(
            plan_id=plan_id,
            plugin_id=plugin_id.strip().lower(),
            archive_path=persistent_archive,
            sha256=sha256.strip().lower(),
            plan=plan,
            created_at=created_at,
            expires_at=created_at + self.ttl,
        )

        self._write_metadata(stored)
        self._plans[plan_id] = stored
        return stored

    def load(self) -> int:
        """Lädt gültige Pläne nach einem Dienstneustart wieder ein."""

        self._plans.clear()
        loaded = 0

        for plan_dir in sorted(self.storage_root.iterdir()):
            if not plan_dir.is_dir():
                continue

            metadata_path = plan_dir / self.metadata_filename
            archive_path = plan_dir / self.archive_filename

            if not metadata_path.is_file() or not archive_path.is_file():
                shutil.rmtree(plan_dir, ignore_errors=True)
                continue

            try:
                data = json.loads(metadata_path.read_text(encoding="utf-8"))
                stored = self._stored_from_dict(
                    data=data,
                    archive_path=archive_path,
                )
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                shutil.rmtree(plan_dir, ignore_errors=True)
                continue

            if stored.expires_at <= self._now():
                shutil.rmtree(plan_dir, ignore_errors=True)
                continue

            self._plans[stored.plan_id] = stored
            loaded += 1

        return loaded

    def update_plan(
        self,
        plan_id: str,
        plan: PluginInstallPlan,
    ) -> StoredPluginPlan:
        """Aktualisiert einen gespeicherten Plan nach ausgeführten Schritten."""

        stored = self.get(plan_id)
        if stored is None:
            raise KeyError("Installationsplan nicht gefunden oder abgelaufen.")

        updated = StoredPluginPlan(
            plan_id=stored.plan_id,
            plugin_id=stored.plugin_id,
            archive_path=stored.archive_path,
            sha256=stored.sha256,
            plan=plan,
            created_at=stored.created_at,
            expires_at=stored.expires_at,
        )

        self._plans[plan_id] = updated
        self._write_metadata(updated)
        return updated

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
        """Entfernt einen gültigen Plan einmalig aus dem aktiven Speicher."""

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

    def finalize_consumed(self, stored: StoredPluginPlan) -> None:
        """Löscht die persistenten Dateien eines verbrauchten Plans."""

        plan_dir = stored.archive_path.parent.resolve()
        self._ensure_inside_root(plan_dir)
        shutil.rmtree(plan_dir, ignore_errors=True)

    def delete(self, plan_id: str) -> None:
        """Entfernt einen Plan und seine persistenten Dateien."""

        stored = self._plans.pop(plan_id, None)
        plan_dir = (self.storage_root / plan_id).resolve()
        self._ensure_inside_root(plan_dir)

        if stored is not None:
            plan_dir = stored.archive_path.parent.resolve()
            self._ensure_inside_root(plan_dir)

        shutil.rmtree(plan_dir, ignore_errors=True)

    def cleanup(self) -> int:
        """Entfernt abgelaufene Pläne und beschädigte Reste."""

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

    def _write_metadata(self, stored: StoredPluginPlan) -> None:
        metadata_path = stored.archive_path.parent / self.metadata_filename
        temporary_path = metadata_path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(
                self._stored_to_dict(stored),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(metadata_path)

    def _stored_to_dict(
        self,
        stored: StoredPluginPlan,
    ) -> dict[str, object]:
        return {
            "plan_id": stored.plan_id,
            "plugin_id": stored.plugin_id,
            "sha256": stored.sha256,
            "created_at": stored.created_at.isoformat(),
            "expires_at": stored.expires_at.isoformat(),
            "plan": {
                "plugin_id": stored.plan.plugin_id,
                "ready_without_changes": stored.plan.ready_without_changes,
                "license_present": stored.plan.license_present,
                "warnings": list(stored.plan.warnings),
                "requires_confirmation": stored.plan.requires_confirmation,
                "requires_restart": stored.plan.requires_restart,
                "actions": [
                    {
                        "action_type": action.action_type.value,
                        "name": action.name,
                        "reason": action.reason,
                        "command_preview": action.command_preview,
                        "requires_confirmation": action.requires_confirmation,
                        "requires_restart": action.requires_restart,
                    }
                    for action in stored.plan.actions
                ],
            },
        }

    def _stored_from_dict(
        self,
        *,
        data: dict[str, object],
        archive_path: Path,
    ) -> StoredPluginPlan:
        plan_data = data["plan"]
        if not isinstance(plan_data, dict):
            raise ValueError("Ungültige Plan-Metadaten.")

        actions_data = plan_data.get("actions", [])
        if not isinstance(actions_data, list):
            raise ValueError("Ungültige Aktionsliste.")

        actions = tuple(
            InstallAction(
                action_type=InstallActionType(item["action_type"]),
                name=str(item["name"]),
                reason=str(item["reason"]),
                command_preview=(
                    str(item["command_preview"])
                    if item.get("command_preview") is not None
                    else None
                ),
                requires_confirmation=bool(
                    item.get("requires_confirmation", True)
                ),
                requires_restart=bool(
                    item.get("requires_restart", False)
                ),
            )
            for item in actions_data
            if isinstance(item, dict)
        )

        plan = PluginInstallPlan(
            plugin_id=str(plan_data["plugin_id"]),
            ready_without_changes=bool(
                plan_data["ready_without_changes"]
            ),
            license_present=bool(plan_data["license_present"]),
            actions=actions,
            warnings=tuple(
                str(item)
                for item in plan_data.get("warnings", [])
            ),
            requires_confirmation=bool(
                plan_data["requires_confirmation"]
            ),
            requires_restart=bool(
                plan_data["requires_restart"]
            ),
        )

        return StoredPluginPlan(
            plan_id=str(data["plan_id"]),
            plugin_id=str(data["plugin_id"]),
            archive_path=archive_path.resolve(),
            sha256=str(data["sha256"]),
            plan=plan,
            created_at=datetime.fromisoformat(str(data["created_at"])),
            expires_at=datetime.fromisoformat(str(data["expires_at"])),
        )

    def _ensure_inside_root(self, path: Path) -> None:
        try:
            path.relative_to(self.storage_root)
        except ValueError as exc:
            raise ValueError(
                f"Plan-Pfad liegt außerhalb des Speicherbereichs: {path}"
            ) from exc
