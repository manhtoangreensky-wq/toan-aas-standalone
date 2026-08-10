"""Fenced lease contracts for Image Operation → Asset Vault export."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sqlite3
import sys
import time

import pytest
from fastapi import HTTPException


ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ASSET_ID = "22222222-2222-4222-8222-222222222222"
OPERATION_ID = "33333333-3333-4333-8333-333333333333"
SECOND_OPERATION_ID = "44444444-4444-4444-8444-444444444444"
THIRD_OPERATION_ID = "55555555-5555-4555-8555-555555555555"


def load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "export-leases.db"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED", "true")
    for name in ("copyfast_db", "copyfast_auth", "copyfast_assets"):
        sys.modules.pop(name, None)
    db = importlib.import_module("copyfast_db")
    assets = importlib.import_module("copyfast_assets")
    db.ensure_copyfast_schema()
    return db, assets


def seed_completed_operation(
    db,
    *,
    operation_id: str = OPERATION_ID,
    idempotency_key: str = "operation-seed-key-0001",
    storage_key: str = "outputs/22222222222222222222222222222222.png",
) -> None:
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache,
                is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
            (ACCOUNT_ID, "lease-export@example.com", "not-a-login-hash", "Lease Export", now, now),
        )
        conn.execute(
            """INSERT OR IGNORE INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension,
                content_type, byte_size, sha256, storage_key, state, lifecycle_revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.png', 'image/png', 512, ?, ?, 'active', 1, ?, ?, NULL)""",
            (SOURCE_ASSET_ID, ACCOUNT_ID, "Nguồn", "source.png", "a" * 64, "objects/" + "1" * 32 + ".blob", now, now),
        )
        conn.execute(
            """INSERT INTO web_image_operations
               (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                request_fingerprint, source_sha256, source_byte_size, source_width, source_height,
                target_width, target_height, preset, fit_mode, storage_key, original_filename,
                content_type, byte_size, sha256, failure_code, created_at, queued_at, started_at,
                completed_at, updated_at, settings_json)
               VALUES (?, ?, ?, NULL, 'image_resize', 'completed', ?, ?, ?, 512, 128, 128,
                       128, 128, 'custom', 'crop', ?, 'resized.png', 'image/png', 512, ?, NULL,
                       ?, ?, ?, ?, ?, '{}')""",
            (
                operation_id,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                idempotency_key,
                "b" * 64,
                "a" * 64,
                storage_key,
                "c" * 64,
                now,
                now,
                now,
                now,
                now,
            ),
        )


def test_export_reservation_fences_stale_lease_and_preserves_one_quota_reservation(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_operation(db)

    first = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-lease-primary-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )
    assert first.state == "leased"
    assert first.lease is not None
    assert first.lease.generation == 1

    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_image_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", OPERATION_ID),
        )

    reclaimed = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-lease-reclaim-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )
    assert reclaimed.state == "leased"
    assert reclaimed.lease is not None
    assert reclaimed.lease.generation == 2
    assert reclaimed.lease.token != first.lease.token

    assets.release_image_operation_asset_export_lease(first.lease)
    with sqlite3.connect(tmp_path / "export-leases.db") as conn:
        row = conn.execute(
            "SELECT state, lease_generation, lease_token, reserved_bytes FROM web_image_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()
    assert row == ("copying", 2, reclaimed.lease.token, 512)


def test_current_export_lease_release_removes_its_request_mapping_and_reservation(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_operation(db)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-lease-release-0001",
        request_fingerprint="e" * 64,
        expected_bytes=512,
    )
    assert reservation.lease is not None

    assert assets.release_image_operation_asset_export_lease(reservation.lease) is True
    with sqlite3.connect(tmp_path / "export-leases.db") as conn:
        relation_count = conn.execute("SELECT COUNT(*) FROM web_image_operation_asset_exports").fetchone()[0]
        request_count = conn.execute("SELECT COUNT(*) FROM web_image_operation_asset_export_requests").fetchone()[0]
    assert relation_count == 0
    assert request_count == 0


def test_expired_export_lease_cannot_release_its_request_mapping_or_reservation(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_operation(db)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-lease-expired-release-0001",
        request_fingerprint="f" * 64,
        expected_bytes=512,
    )
    assert reservation.lease is not None

    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_image_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", OPERATION_ID),
        )

    assert assets.release_image_operation_asset_export_lease(reservation.lease) is False
    with sqlite3.connect(tmp_path / "export-leases.db") as conn:
        relation_count = conn.execute("SELECT COUNT(*) FROM web_image_operation_asset_exports").fetchone()[0]
        request_count = conn.execute("SELECT COUNT(*) FROM web_image_operation_asset_export_requests").fetchone()[0]
    assert relation_count == 1
    assert request_count == 1


def test_expired_export_lease_releases_quota_but_current_lease_keeps_it_reserved(tmp_path, monkeypatch) -> None:
    """Only a live fenced lease may reserve a Web account's Asset Vault quota."""

    db, assets = load_modules(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "1")
    seed_completed_operation(db)
    seed_completed_operation(
        db,
        operation_id=SECOND_OPERATION_ID,
        idempotency_key="operation-seed-key-0002",
        storage_key="outputs/33333333333333333333333333333333.png",
    )
    seed_completed_operation(
        db,
        operation_id=THIRD_OPERATION_ID,
        idempotency_key="operation-seed-key-0003",
        storage_key="outputs/44444444444444444444444444444444.png",
    )
    reserved_bytes = 700 * 1024
    stale = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-lease-stale-quota-0001",
        request_fingerprint="a" * 64,
        expected_bytes=reserved_bytes,
    )
    assert stale.lease is not None
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_image_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", OPERATION_ID),
        )

    current = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=SECOND_OPERATION_ID,
        idempotency_key="export-lease-current-quota-0001",
        request_fingerprint="b" * 64,
        expected_bytes=reserved_bytes,
    )
    assert current.state == "leased"
    assert current.lease is not None

    with pytest.raises(HTTPException) as blocked:
        assets.reserve_image_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=THIRD_OPERATION_ID,
            idempotency_key="export-lease-live-quota-0001",
            request_fingerprint="c" * 64,
            expected_bytes=reserved_bytes,
        )
    assert blocked.value.status_code == 413


def test_expired_export_lease_pending_object_is_not_reconciler_protected(tmp_path, monkeypatch) -> None:
    """An expired attempt's private key follows normal orphan-retention cleanup."""

    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_operation(db)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-lease-expired-orphan-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )
    assert reservation.lease is not None
    pending_object = tmp_path / "private-web-assets" / reservation.lease.pending_storage_key
    pending_object.parent.mkdir(parents=True, exist_ok=True)
    pending_object.write_bytes(b"expired export object")
    old_timestamp = time.time() - assets.ORPHAN_RETENTION_SECONDS - 2
    os.utime(pending_object, (old_timestamp, old_timestamp))
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_image_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", OPERATION_ID),
        )

    assets.reconcile_asset_vault_storage()

    assert not pending_object.exists()
