"""Schema and closed-enable contracts for Image Operation Asset Vault export."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys


def load_db(tmp_path: Path, monkeypatch, *, export_enabled: str | None):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "export-schema.db"))
    if export_enabled is None:
        monkeypatch.delenv("WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED", raising=False)
    else:
        monkeypatch.setenv("WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED", export_enabled)
    sys.modules.pop("copyfast_db", None)
    return importlib.import_module("copyfast_db")


def test_image_operation_export_flag_is_closed_by_default_and_accepts_explicit_true_values(tmp_path, monkeypatch) -> None:
    assert load_db(tmp_path, monkeypatch, export_enabled=None).image_operation_export_enabled() is False
    assert load_db(tmp_path, monkeypatch, export_enabled="true").image_operation_export_enabled() is True
    assert load_db(tmp_path, monkeypatch, export_enabled="on").image_operation_export_enabled() is True
    assert load_db(tmp_path, monkeypatch, export_enabled="enabled").image_operation_export_enabled() is False


def test_export_relation_schema_has_fenced_state_invariants_and_request_map(tmp_path, monkeypatch) -> None:
    db = load_db(tmp_path, monkeypatch, export_enabled="true")
    db.ensure_copyfast_schema()
    database = tmp_path / "export-schema.db"
    with sqlite3.connect(database) as conn:
        table_names = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "web_image_operation_asset_exports" in table_names
        assert "web_image_operation_asset_export_requests" in table_names
        conn.execute("PRAGMA foreign_keys=OFF")
        with __import__("pytest").raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO web_image_operation_asset_exports
                   (operation_id, account_id, asset_id, state, request_fingerprint,
                    lease_generation, lease_token, lease_expires_at, reserved_bytes,
                    pending_storage_key, created_at, updated_at, completed_at)
                   VALUES (?, ?, NULL, 'copying', ?, 1, NULL, NULL, 0, NULL, ?, ?, NULL)""",
                ("00000000-0000-4000-8000-000000000001", "account-test", "a" * 64, db.utc_now(), db.utc_now()),
            )
        with __import__("pytest").raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO web_image_operation_asset_exports
                   (operation_id, account_id, asset_id, state, request_fingerprint,
                    lease_generation, lease_token, lease_expires_at, reserved_bytes,
                    pending_storage_key, created_at, updated_at, completed_at)
                   VALUES (?, ?, NULL, 'completed', ?, 1, NULL, NULL, 0, NULL, ?, ?, ?)""",
                ("00000000-0000-4000-8000-000000000002", "account-test", "b" * 64, db.utc_now(), db.utc_now(), db.utc_now()),
            )
        indexes = {str(row[1]) for row in conn.execute("PRAGMA index_list(web_image_operation_asset_exports)").fetchall()}
        assert "idx_web_image_operation_asset_exports_account_state_updated" in indexes
        assert "idx_web_image_operation_asset_exports_expiry" in indexes
