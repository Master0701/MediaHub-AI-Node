"""Tests für den persistenten Installationsplan-Speicher."""

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
    archive = tmp_path / "source.zip"
    archive.write_bytes(b"zip")

    store = PluginPlanStore(
        storage_root=tmp_path / "plans",
        ttl_minutes=15,
    )
    stored = store.create(
        plugin_id="provider.test",
        archive_path=archive,
        sha256="a" * 64,
        plan=create_plan(),
    )

    assert store.get(stored.plan_id) is not None
    assert stored.archive_path.is_file()
    assert len(store) == 1


def test_plan_survives_store_restart(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    archive.write_bytes(b"zip")
    storage_root = tmp_path / "plans"

    first_store = PluginPlanStore(
        storage_root=storage_root,
        ttl_minutes=15,
    )
    stored = first_store.create(
        plugin_id="provider.test",
        archive_path=archive,
        sha256="a" * 64,
        plan=create_plan(),
    )

    second_store = PluginPlanStore(
        storage_root=storage_root,
        ttl_minutes=15,
    )
    restored = second_store.get(stored.plan_id)

    assert restored is not None
    assert restored.plugin_id == "provider.test"
    assert restored.archive_path.is_file()


def test_consume_and_finalize_are_one_time(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    archive.write_bytes(b"zip")

    store = PluginPlanStore(
        storage_root=tmp_path / "plans",
        ttl_minutes=15,
    )
    stored = store.create(
        plugin_id="provider.test",
        archive_path=archive,
        sha256="a" * 64,
        plan=create_plan(),
    )

    consumed = store.consume(stored.plan_id)
    store.finalize_consumed(consumed)

    assert consumed.consumed is True
    assert store.get(stored.plan_id) is None
    assert consumed.archive_path.exists() is False


def test_cleanup_removes_expired_archive(tmp_path: Path) -> None:
    current = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)

    def now() -> datetime:
        return current

    archive = tmp_path / "source.zip"
    archive.write_bytes(b"zip")

    store = PluginPlanStore(
        storage_root=tmp_path / "plans",
        ttl_minutes=1,
        now=now,
    )
    stored = store.create(
        plugin_id="provider.test",
        archive_path=archive,
        sha256="a" * 64,
        plan=create_plan(),
    )

    current += timedelta(minutes=2)

    assert store.get(stored.plan_id) is None
    assert stored.archive_path.exists() is False
