"""Tests für kurzlebige und einmalige Installationspläne."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.plugins.install_plan import PluginInstallPlan
from app.plugins.plan_store import PluginPlanStore


def create_plan() -> PluginInstallPlan:
    return PluginInstallPlan(
        plugin_id="provider.test",
        ready_without_changes=True,
        license_present=True,
        actions=(),
        warnings=(),
        requires_confirmation=False,
        requires_restart=False,
    )


def test_create_and_get_plan(tmp_path: Path) -> None:
    archive = tmp_path / "plugin.zip"
    archive.write_bytes(b"zip")

    store = PluginPlanStore(ttl_minutes=15)
    stored = store.create(
        plugin_id="provider.test",
        archive_path=archive,
        sha256="a" * 64,
        plan=create_plan(),
    )

    assert store.get(stored.plan_id) is not None
    assert len(store) == 1


def test_consume_is_one_time(tmp_path: Path) -> None:
    archive = tmp_path / "plugin.zip"
    archive.write_bytes(b"zip")

    store = PluginPlanStore(ttl_minutes=15)
    stored = store.create(
        plugin_id="provider.test",
        archive_path=archive,
        sha256="a" * 64,
        plan=create_plan(),
    )

    consumed = store.consume(stored.plan_id)

    assert consumed.consumed is True
    assert store.get(stored.plan_id) is None


def test_cleanup_removes_expired_archive(tmp_path: Path) -> None:
    current = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)

    def now() -> datetime:
        return current

    archive = tmp_path / "plugin.zip"
    archive.write_bytes(b"zip")

    store = PluginPlanStore(ttl_minutes=1, now=now)
    stored = store.create(
        plugin_id="provider.test",
        archive_path=archive,
        sha256="a" * 64,
        plan=create_plan(),
    )

    current += timedelta(minutes=2)

    assert store.get(stored.plan_id) is None
    assert archive.exists() is False
