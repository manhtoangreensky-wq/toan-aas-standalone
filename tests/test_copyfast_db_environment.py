"""Focused production-like persistence contracts for the Web database."""

from __future__ import annotations

import pytest

import copyfast_db


ENVIRONMENT_NAMES = ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT")


def _clear_environment(monkeypatch) -> None:
    for name in (*ENVIRONMENT_NAMES, "RAILWAY_VOLUME_MOUNT_PATH", "WEBAPP_SESSION_DB_PATH"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("environment_name", ENVIRONMENT_NAMES)
def test_live_label_is_production_like_for_every_deployment_environment_name(monkeypatch, environment_name: str) -> None:
    """Keep DB persistence policy aligned with notification preflight labels."""
    _clear_environment(monkeypatch)
    monkeypatch.setenv(environment_name, " LiVe ")

    assert copyfast_db._is_production() is True


@pytest.mark.parametrize("environment", ("", "local", "test"))
def test_local_and_test_environment_keep_development_scheduler_behavior(monkeypatch, environment: str) -> None:
    _clear_environment(monkeypatch)
    if environment:
        monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setattr(copyfast_db, "_persistent_session_directory", lambda: None)

    copyfast_db.ensure_copyfast_persistence()
    assert copyfast_db.web_scheduler_persistence_ready() is True


@pytest.mark.parametrize("environment", ("production", "live"))
def test_production_like_environment_fails_closed_without_persistent_scheduler_storage(monkeypatch, environment: str) -> None:
    _clear_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setattr(copyfast_db, "_persistent_session_directory", lambda: None)

    with pytest.raises(RuntimeError, match="Production cần WEBAPP_SESSION_DB_PATH"):
        copyfast_db.ensure_copyfast_persistence()
    assert copyfast_db.web_scheduler_persistence_ready() is False


def test_live_scheduler_accepts_database_inside_declared_persistent_volume(tmp_path, monkeypatch) -> None:
    _clear_environment(monkeypatch)
    volume = tmp_path / "persistent-volume"
    volume.mkdir()
    monkeypatch.setenv("APP_ENV", "live")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(volume / "web-session.db"))

    copyfast_db.ensure_copyfast_persistence()
    assert copyfast_db.web_scheduler_persistence_ready() is True
