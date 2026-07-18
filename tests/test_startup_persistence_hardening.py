"""Focused Railway startup and persistent-session safety contracts.

These tests deliberately exercise only Web-owned startup decisions.  They do
not start a provider, Bot, payment path or a production deployment.
"""

from __future__ import annotations

import asyncio
import importlib
import threading

import pytest
from fastapi import FastAPI

import copyfast_auth
import copyfast_autopilot
import copyfast_db


ENVIRONMENT_NAMES = ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT")


def _clear_deployment_environment(monkeypatch) -> None:
    for name in (
        *ENVIRONMENT_NAMES,
        "RAILWAY_VOLUME_MOUNT_PATH",
        "WEBAPP_SESSION_DB_PATH",
        "RAILWAY_REPLICA_COUNT",
        "RAILWAY_REPLICAS",
        "WEBAPP_REPLICA_COUNT",
        "CORS_ALLOW_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("environment_name", ENVIRONMENT_NAMES)
def test_live_uses_one_production_policy_for_cors_auth_and_autopilot(monkeypatch, environment_name: str) -> None:
    """A Railway ``live`` label cannot weaken one subsystem selectively."""
    _clear_deployment_environment(monkeypatch)
    monkeypatch.setenv(environment_name, " LiVe ")
    monkeypatch.setenv("WEBAPP_AUTOPILOT_TOPOLOGY", "sqlite_single_replica")

    application_module = importlib.import_module("app")
    assert copyfast_db.is_production_like_environment() is True
    assert copyfast_auth._is_production() is True
    assert copyfast_auth._cookie_secure() is True
    assert copyfast_autopilot._topology_guarded_code() == "OPS_REPLICA_COUNT_UNVERIFIED"

    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:8877")
    with pytest.raises(RuntimeError, match="HTTPS"):
        application_module._origins()

    monkeypatch.setenv("RAILWAY_REPLICA_COUNT", "1")
    assert copyfast_autopilot._topology_guarded_code() is None


def test_production_session_database_rejects_absolute_path_outside_verified_volume(tmp_path, monkeypatch) -> None:
    _clear_deployment_environment(monkeypatch)
    volume = tmp_path / "railway-volume"
    volume.mkdir()
    outside_database = tmp_path / "ephemeral-app" / "web.db"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(outside_database))

    with pytest.raises(RuntimeError, match="persistent volume"):
        copyfast_db.session_database_path()
    with pytest.raises(RuntimeError, match="persistent volume"):
        copyfast_db.ensure_copyfast_persistence()


def test_production_session_database_resolves_only_a_file_below_verified_volume(tmp_path, monkeypatch) -> None:
    _clear_deployment_environment(monkeypatch)
    volume = tmp_path / "railway-volume"
    volume.mkdir()
    nested_database = volume / "state" / ".." / "sessions.db"
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(nested_database))

    expected = (volume / "sessions.db").resolve()
    assert copyfast_db.session_database_path() == str(expected)
    copyfast_db.ensure_copyfast_persistence()

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(volume))
    with pytest.raises(RuntimeError, match="persistent volume"):
        copyfast_db.session_database_path()


def test_lifespan_makes_critical_readiness_available_before_private_reconciliation(monkeypatch) -> None:
    """A slow volume scan may run later, but cannot hold the health path up."""
    application_module = importlib.import_module("app")
    critical_checks: list[str] = []
    for name in (
        "ensure_auth_configuration",
        "ensure_oauth_configuration",
        "ensure_copyfast_persistence",
        "ensure_copyfast_schema",
        "ensure_admin_document_archive_persistence",
        "ensure_asset_vault_persistence",
        "ensure_project_package_persistence",
        "ensure_document_operations_persistence",
        "ensure_image_operations_persistence",
    ):
        monkeypatch.setattr(application_module, name, lambda name=name: critical_checks.append(name))
    monkeypatch.setattr(
        application_module.copyfast_document_operations,
        "ensure_document_operations_runtime",
        lambda: critical_checks.append("document_runtime"),
    )
    monkeypatch.setattr(
        application_module.copyfast_image_operations,
        "ensure_image_operations_runtime",
        lambda: critical_checks.append("image_runtime"),
    )

    started = threading.Event()
    release = threading.Event()
    reconciled: list[str] = []
    image_reconciliation_fences: list[str | None] = []

    def slow_asset_reconcile() -> None:
        started.set()
        assert release.wait(timeout=3)
        reconciled.append("asset_vault")

    def package_reconcile() -> None:
        reconciled.append("project_packages")

    def failed_document_reconcile() -> None:
        reconciled.append("document_operations")
        raise RuntimeError("private filesystem failure")

    def image_reconcile(*, interrupted_before: str | None = None) -> None:
        reconciled.append("image_operations")
        image_reconciliation_fences.append(interrupted_before)

    monkeypatch.setattr(
        application_module,
        "STARTUP_RECONCILIATION_STEPS",
        (
            ("asset_vault", slow_asset_reconcile),
            ("project_packages", package_reconcile),
            ("document_operations", failed_document_reconcile),
            ("image_operations", image_reconcile),
        ),
    )

    async def exercise_lifespan() -> None:
        application = FastAPI()
        async with application_module.lifespan(application):
            # Reaching this line is the readiness boundary: all required
            # auth/persistence/schema/runtime checks completed, while the
            # slow reconciliation is still deliberately in the background.
            assert critical_checks == [
                "ensure_auth_configuration",
                "ensure_oauth_configuration",
                "ensure_copyfast_persistence",
                "ensure_copyfast_schema",
                "ensure_admin_document_archive_persistence",
                "ensure_asset_vault_persistence",
                "ensure_project_package_persistence",
                "ensure_document_operations_persistence",
                "ensure_image_operations_persistence",
                "document_runtime",
                "image_runtime",
            ]
            assert application.state.copyfast_startup_reconciliation["status"] in {"scheduled", "running"}
            assert application.state.copyfast_startup_reconciliation["interrupted_before"]
            assert await asyncio.to_thread(started.wait, 1.0)
            assert application.state.copyfast_startup_reconciliation["status"] == "running"
            release.set()
            await asyncio.wait_for(application.state.copyfast_startup_reconciliation_task, timeout=1.0)
            assert application.state.copyfast_startup_reconciliation["status"] == "completed_with_errors"
            assert application.state.copyfast_startup_reconciliation["failed_steps"] == ["document_operations"]

    asyncio.run(exercise_lifespan())
    assert reconciled == ["asset_vault", "project_packages", "document_operations", "image_operations"]
    assert len(image_reconciliation_fences) == 1
    assert image_reconciliation_fences[0]
