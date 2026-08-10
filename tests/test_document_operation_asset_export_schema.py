"""Closed capability, schema and edge-rate contracts for document export."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def load_db(tmp_path: Path, monkeypatch, *, export_enabled: str | None):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-export-schema.db"))
    if export_enabled is None:
        monkeypatch.delenv("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", raising=False)
    else:
        monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", export_enabled)
    sys.modules.pop("copyfast_db", None)
    return importlib.import_module("copyfast_db")


def test_document_operation_export_capability_is_closed_and_status_requires_all_private_gates(tmp_path, monkeypatch) -> None:
    db = load_db(tmp_path, monkeypatch, export_enabled=None)
    assert db.document_operation_export_enabled() is False

    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", "on")
    api = importlib.import_module("copyfast_api")
    assert api._flags()["document_operation_export_enabled"] is True

    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "false")
    assert api._flags()["document_operation_export_enabled"] is False
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "false")
    assert api._flags()["document_operation_export_enabled"] is False
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", "enabled")
    assert api._flags()["document_operation_export_enabled"] is False


def test_document_export_relation_schema_is_distinct_and_has_only_lookup_indexes(tmp_path, monkeypatch) -> None:
    db = load_db(tmp_path, monkeypatch, export_enabled="true")
    db.ensure_copyfast_schema()

    with sqlite3.connect(tmp_path / "document-export-schema.db") as conn:
        table_names = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "web_document_operation_asset_exports" in table_names
        assert "web_document_operation_asset_export_requests" in table_names
        assert "web_image_operation_asset_exports" in table_names

        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(web_document_operation_asset_exports)").fetchall()
        }
        assert {
            "operation_id",
            "account_id",
            "asset_id",
            "state",
            "request_fingerprint",
            "lease_generation",
            "lease_token",
            "lease_expires_at",
            "reserved_bytes",
            "pending_storage_key",
            "created_at",
            "updated_at",
            "completed_at",
        }.issubset(columns)

        request_sql = str(
            conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='web_document_operation_asset_export_requests'"
            ).fetchone()[0]
        )
        assert "PRIMARY KEY (account_id, idempotency_key)" in request_sql

        indexes = {
            str(row[1])
            for row in conn.execute("PRAGMA index_list(web_document_operation_asset_exports)").fetchall()
        }
        assert "idx_web_document_operation_asset_exports_account_state_updated" in indexes
        assert "idx_web_document_operation_asset_exports_expiry" in indexes


def test_document_export_has_its_own_canonical_post_rate_bucket_outside_the_parser_gate() -> None:
    predicate_start = APP.index("document_export_parts = request.url.path.split(\"/\")")
    predicate_end = APP.index("# Subtitle Asset Operations", predicate_start)
    predicate = APP[predicate_start:predicate_end]

    assert 'request.method == "POST"' in predicate
    assert '"/api/v1/document-operations/"' in predicate
    assert '"/export-to-asset-vault"' in predicate
    assert "len(document_export_parts) == 6" in predicate
    assert "document_export_canonical_id == document_export_operation_id.lower()" in predicate
    assert "if document_operation_asset_export:" in APP
    assert 'else "document-operation-asset-export" if document_operation_asset_export' in APP

    run_start = APP.index("document_operation_run = (")
    run_end = APP.index("image_export_parts", run_start)
    assert "export-to-asset-vault" not in APP[run_start:run_end]
