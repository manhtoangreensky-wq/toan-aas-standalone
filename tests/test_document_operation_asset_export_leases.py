"""Fenced lease contracts for Document Operation → Asset Vault export."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

import pytest
from fastapi import HTTPException


ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ASSET_ID = "22222222-2222-4222-8222-222222222222"
DOCUMENT_OPERATION_ID = "33333333-3333-4333-8333-333333333333"
SECOND_DOCUMENT_OPERATION_ID = "44444444-4444-4444-8444-444444444444"
IMAGE_OPERATION_ID = "55555555-5555-4555-8555-555555555555"
EXPORTED_ASSET_ID = "66666666-6666-4666-8666-666666666666"


def load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-export-leases.db"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED", "true")
    for name in ("copyfast_db", "copyfast_auth", "copyfast_assets"):
        sys.modules.pop(name, None)
    db = importlib.import_module("copyfast_db")
    assets = importlib.import_module("copyfast_assets")
    db.ensure_copyfast_schema()
    return db, assets


def seed_account_and_source(db) -> None:
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache,
                is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
            (ACCOUNT_ID, "document-export-lease@example.com", "not-a-login-hash", "Document lease", now, now),
        )
        conn.execute(
            """INSERT OR IGNORE INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension,
                content_type, byte_size, sha256, storage_key, state, lifecycle_revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.pdf', 'application/pdf', 512, ?, ?, 'active', 1, ?, ?, NULL)""",
            (
                SOURCE_ASSET_ID,
                ACCOUNT_ID,
                "Nguồn PDF",
                "source.pdf",
                "a" * 64,
                "objects/" + "1" * 32 + ".blob",
                now,
                now,
            ),
        )


def seed_completed_document_operation(
    db,
    *,
    operation_id: str = DOCUMENT_OPERATION_ID,
    idempotency_key: str = "document-operation-seed-0001",
    output_byte_size: int = 512,
) -> None:
    seed_account_and_source(db)
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_document_operations
               (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                request_fingerprint, source_sha256, source_byte_size, source_count,
                requested_page_range, selected_start_page, selected_end_page, source_page_count,
                output_page_count, storage_key, original_filename, content_type, byte_size,
                sha256, failure_code, created_at, queued_at, started_at, completed_at, updated_at)
               VALUES (?, ?, ?, NULL, 'pdf_split', 'completed', ?, ?, ?, 512, 1,
                       '1-2', 1, 2, 2, 2, ?, 'toan-aas-pdf-pages-1-2.pdf', 'application/pdf', ?,
                       ?, NULL, ?, ?, ?, ?, ?)""",
            (
                operation_id,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                idempotency_key,
                "b" * 64,
                "c" * 64,
                "outputs/" + operation_id.replace("-", "") + ".pdf",
                output_byte_size,
                "d" * 64,
                now,
                now,
                now,
                now,
                now,
            ),
        )


def seed_completed_image_operation(db) -> None:
    seed_account_and_source(db)
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_image_operations
               (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                request_fingerprint, source_sha256, source_byte_size, target_width, target_height,
                preset, fit_mode, created_at, queued_at, updated_at, settings_json)
               VALUES (?, ?, ?, NULL, 'image_resize', 'completed', ?, ?, ?, 512, 128, 128,
                       'custom', 'crop', ?, ?, ?, '{}')""",
            (
                IMAGE_OPERATION_ID,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                "image-operation-seed-0001",
                "e" * 64,
                "f" * 64,
                now,
                now,
                now,
            ),
        )


def seed_completed_export_relation(db) -> None:
    seed_completed_document_operation(db)
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension,
                content_type, byte_size, sha256, storage_key, state, lifecycle_revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.pdf', 'application/pdf', 512, ?, ?, 'active', 1, ?, ?, NULL)""",
            (
                EXPORTED_ASSET_ID,
                ACCOUNT_ID,
                "PDF đã lưu",
                "toan-aas-pdf-split.pdf",
                "d" * 64,
                "objects/" + "2" * 32 + ".blob",
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO web_document_operation_asset_exports
               (operation_id, account_id, asset_id, state, request_fingerprint,
                lease_generation, lease_token, lease_expires_at, reserved_bytes,
                pending_storage_key, created_at, updated_at, completed_at)
               VALUES (?, ?, ?, 'completed', ?, 1, NULL, NULL, 0, NULL, ?, ?, ?)""",
            (DOCUMENT_OPERATION_ID, ACCOUNT_ID, EXPORTED_ASSET_ID, "d" * 64, now, now, now),
        )


@pytest.mark.parametrize(
    ("request_fingerprint", "expected_bytes"),
    (
        ("e" * 64, 512),
        ("d" * 64, 513),
    ),
)
def test_document_export_initial_reservation_rejects_unverified_completed_output(
    tmp_path,
    monkeypatch,
    request_fingerprint: str,
    expected_bytes: int,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db)

    with pytest.raises(HTTPException) as rejected:
        assets.reserve_document_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=DOCUMENT_OPERATION_ID,
            idempotency_key="document-export-unverified-output-0001",
            request_fingerprint=request_fingerprint,
            expected_bytes=expected_bytes,
        )
    assert rejected.value.status_code == 409

    with sqlite3.connect(tmp_path / "document-export-leases.db") as conn:
        relation_count = conn.execute("SELECT COUNT(*) FROM web_document_operation_asset_exports").fetchone()[0]
        request_count = conn.execute("SELECT COUNT(*) FROM web_document_operation_asset_export_requests").fetchone()[0]
    assert relation_count == 0
    assert request_count == 0


def test_document_export_reservation_creates_an_owner_scoped_fenced_lease(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db)

    reservation = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID.upper(),
        operation_id=DOCUMENT_OPERATION_ID.upper(),
        idempotency_key="document-export-lease-primary-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )

    assert reservation.state == "leased"
    assert reservation.lease is not None
    assert reservation.lease.account_id == ACCOUNT_ID
    assert reservation.lease.operation_id == DOCUMENT_OPERATION_ID
    assert reservation.lease.generation == 1
    assert reservation.lease.reserved_bytes == 512
    assert reservation.lease.request_fingerprint == "d" * 64
    assert reservation.lease.token
    assert reservation.lease.pending_storage_key.startswith("objects/")
    with sqlite3.connect(tmp_path / "document-export-leases.db") as conn:
        relation = conn.execute(
            """SELECT state, lease_generation, lease_token, reserved_bytes, pending_storage_key
               FROM web_document_operation_asset_exports WHERE operation_id=? AND account_id=?""",
            (DOCUMENT_OPERATION_ID, ACCOUNT_ID),
        ).fetchone()
        request = conn.execute(
            """SELECT operation_id, request_fingerprint
               FROM web_document_operation_asset_export_requests
               WHERE account_id=? AND idempotency_key=?""",
            (ACCOUNT_ID, "document-export-lease-primary-0001"),
        ).fetchone()
    assert relation == ("copying", 1, reservation.lease.token, 512, reservation.lease.pending_storage_key)
    assert request == (DOCUMENT_OPERATION_ID, "d" * 64)


def test_document_export_replay_keeps_live_lease_pending_and_rejects_rebound_idempotency(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db)
    seed_completed_document_operation(
        db,
        operation_id=SECOND_DOCUMENT_OPERATION_ID,
        idempotency_key="document-operation-seed-0002",
    )
    first = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-replay-key-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )
    assert first.lease is not None

    replay = assets.replay_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-replay-key-0001",
    )
    assert replay is not None
    assert replay.state == "copying"
    assert replay.asset is None

    with pytest.raises(HTTPException) as different_operation:
        assets.replay_document_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=SECOND_DOCUMENT_OPERATION_ID,
            idempotency_key="document-export-replay-key-0001",
        )
    assert different_operation.value.status_code == 409

    with pytest.raises(HTTPException) as different_fingerprint:
        assets.reserve_document_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=DOCUMENT_OPERATION_ID,
            idempotency_key="document-export-replay-key-0002",
            request_fingerprint="e" * 64,
            expected_bytes=512,
        )
    assert different_fingerprint.value.status_code == 409

    with pytest.raises(HTTPException) as different_bytes:
        assets.reserve_document_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=DOCUMENT_OPERATION_ID,
            idempotency_key="document-export-replay-key-0003",
            request_fingerprint="d" * 64,
            expected_bytes=513,
        )
    assert different_bytes.value.status_code == 409


def test_document_export_reclaims_only_expired_lease_with_a_new_fence(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db)
    seed_completed_document_operation(
        db,
        operation_id=SECOND_DOCUMENT_OPERATION_ID,
        idempotency_key="document-operation-seed-0002",
    )
    first = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-stale-first-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )
    assert first.lease is not None
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_document_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", DOCUMENT_OPERATION_ID),
        )

    reclaimed = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-stale-reclaim-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )

    assert reclaimed.state == "leased"
    assert reclaimed.lease is not None
    assert reclaimed.lease.generation == 2
    assert reclaimed.lease.token != first.lease.token
    assert reclaimed.lease.pending_storage_key != first.lease.pending_storage_key
    assert assets.release_document_operation_asset_export_lease(first.lease) is False
    with sqlite3.connect(tmp_path / "document-export-leases.db") as conn:
        relation = conn.execute(
            """SELECT state, lease_generation, lease_token, reserved_bytes, pending_storage_key
               FROM web_document_operation_asset_exports WHERE operation_id=?""",
            (DOCUMENT_OPERATION_ID,),
        ).fetchone()
    assert relation == (
        "copying",
        2,
        reclaimed.lease.token,
        512,
        reclaimed.lease.pending_storage_key,
    )
    assert assets.release_document_operation_asset_export_lease(reclaimed.lease) is True

    with pytest.raises(HTTPException) as rebound:
        assets.reserve_document_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=SECOND_DOCUMENT_OPERATION_ID,
            idempotency_key="document-export-stale-reclaim-0001",
            request_fingerprint="d" * 64,
            expected_bytes=512,
        )
    assert rebound.value.status_code == 409

    reclaimed_after_release = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-stale-reclaim-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )
    assert reclaimed_after_release.state == "leased"
    assert reclaimed_after_release.lease is not None
    assert reclaimed_after_release.lease.generation == 3
    assert reclaimed_after_release.lease.token != reclaimed.lease.token
    assert reclaimed_after_release.lease.pending_storage_key != reclaimed.lease.pending_storage_key
    with sqlite3.connect(tmp_path / "document-export-leases.db") as conn:
        relation = conn.execute(
            """SELECT state, lease_generation, lease_token, reserved_bytes, pending_storage_key
               FROM web_document_operation_asset_exports WHERE operation_id=?""",
            (DOCUMENT_OPERATION_ID,),
        ).fetchone()
        request_count = conn.execute("SELECT COUNT(*) FROM web_document_operation_asset_export_requests").fetchone()[0]
    assert relation == (
        "copying",
        3,
        reclaimed_after_release.lease.token,
        512,
        reclaimed_after_release.lease.pending_storage_key,
    )
    assert request_count == 2


def test_document_export_receipt_reads_current_asset_state_and_guards_missing_asset(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_export_relation(db)

    repeated = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-completed-reserve-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )
    assert repeated.state == "completed"
    assert repeated.lease is None
    with pytest.raises(HTTPException) as different_completed_bytes:
        assets.reserve_document_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=DOCUMENT_OPERATION_ID,
            idempotency_key="document-export-completed-reserve-0002",
            request_fingerprint="d" * 64,
            expected_bytes=513,
        )
    assert different_completed_bytes.value.status_code == 409
    replay = assets.replay_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-completed-replay-0001",
    )
    assert replay is not None
    assert replay.state == "completed"
    assert replay.asset is not None
    assert replay.asset["id"] == EXPORTED_ASSET_ID

    active = assets.get_document_operation_asset_export_receipt(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
    )
    assert active is not None
    assert active.state == "completed"
    assert active.asset is not None
    assert active.asset["id"] == EXPORTED_ASSET_ID
    assert active.asset["state"] == "active"

    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_asset_files SET state='archived', archived_at=?, updated_at=? WHERE id=?",
            (db.utc_now(), db.utc_now(), EXPORTED_ASSET_ID),
        )
    archived = assets.get_document_operation_asset_export_receipt(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
    )
    assert archived is not None
    assert archived.state == "guarded"
    assert archived.asset is None

    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_asset_files SET state='unavailable', archived_at=NULL, updated_at=? WHERE id=?",
            (db.utc_now(), EXPORTED_ASSET_ID),
        )
    unavailable = assets.get_document_operation_asset_export_receipt(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
    )
    assert unavailable is not None
    assert unavailable.state == "guarded"
    assert unavailable.asset is None

    with sqlite3.connect(tmp_path / "document-export-leases.db") as conn:
        conn.execute("DELETE FROM web_asset_files WHERE id=?", (EXPORTED_ASSET_ID,))
        conn.commit()
    missing = assets.get_document_operation_asset_export_receipt(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
    )
    assert missing is not None
    assert missing.state == "guarded"
    assert missing.asset is None


@pytest.mark.parametrize(
    ("asset_sha256", "asset_byte_size"),
    (
        ("e" * 64, 512),
        ("d" * 64, 513),
    ),
)
def test_document_export_receipt_guards_active_asset_with_tampered_integrity_metadata(
    tmp_path,
    monkeypatch,
    asset_sha256: str,
    asset_byte_size: int,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_export_relation(db)

    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_asset_files SET sha256=?, byte_size=?, updated_at=? WHERE id=?",
            (asset_sha256, asset_byte_size, db.utc_now(), EXPORTED_ASSET_ID),
        )

    receipt = assets.get_document_operation_asset_export_receipt(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
    )

    assert receipt is not None
    assert receipt.state == "guarded"
    assert receipt.asset is None


@pytest.mark.parametrize(
    ("case_name", "asset_state", "asset_sha256", "asset_byte_size"),
    (
        ("archived", "archived", "d" * 64, 512),
        ("unavailable", "unavailable", "d" * 64, 512),
        ("digest-mismatch", "active", "e" * 64, 512),
        ("byte-size-mismatch", "active", "d" * 64, 513),
        ("missing", None, None, None),
    ),
)
def test_document_export_completed_reservation_guards_invalid_copied_asset(
    tmp_path,
    monkeypatch,
    case_name: str,
    asset_state: str | None,
    asset_sha256: str | None,
    asset_byte_size: int | None,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_export_relation(db)

    if asset_state is None:
        with sqlite3.connect(tmp_path / "document-export-leases.db") as conn:
            conn.execute("DELETE FROM web_asset_files WHERE id=?", (EXPORTED_ASSET_ID,))
            conn.commit()
    else:
        with db.transaction() as conn:
            conn.execute(
                """UPDATE web_asset_files
                   SET state=?, sha256=?, byte_size=?, archived_at=?, updated_at=?
                   WHERE id=?""",
                (
                    asset_state,
                    asset_sha256,
                    asset_byte_size,
                    db.utc_now() if asset_state == "archived" else None,
                    db.utc_now(),
                    EXPORTED_ASSET_ID,
                ),
            )

    reservation = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key=f"document-export-{case_name}-guarded-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )

    assert reservation.state == "guarded"
    assert reservation.lease is None


@pytest.mark.parametrize(
    ("column", "invalid_value"),
    (
        ("extension", ".txt"),
        ("content_type", "text/plain"),
        ("original_filename", "renamed.pdf"),
        ("storage_key", "objects/not-a-vault-key.blob"),
    ),
)
def test_document_export_completed_asset_metadata_tampering_guards_receipt_reserve_and_replay(
    tmp_path,
    monkeypatch,
    column: str,
    invalid_value: str,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_export_relation(db)

    with db.transaction() as conn:
        conn.execute(
            f"UPDATE web_asset_files SET {column}=?, updated_at=? WHERE id=?",
            (invalid_value, db.utc_now(), EXPORTED_ASSET_ID),
        )

    receipt = assets.get_document_operation_asset_export_receipt(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
    )
    assert receipt is not None
    assert receipt.state == "guarded"
    assert receipt.asset is None

    reservation = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key=f"document-export-{column}-metadata-reserve-0001",
        request_fingerprint="d" * 64,
        expected_bytes=512,
    )
    assert reservation.state == "guarded"
    assert reservation.lease is None

    replay = assets.replay_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key=f"document-export-{column}-metadata-replay-0001",
    )
    assert replay is not None
    assert replay.state == "guarded"
    assert replay.asset is None

    with sqlite3.connect(tmp_path / "document-export-leases.db") as conn:
        request_count = conn.execute(
            "SELECT COUNT(*) FROM web_document_operation_asset_export_requests"
        ).fetchone()[0]
    assert request_count == 0


def test_document_reservation_counts_live_image_reservations_against_the_shared_quota(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "1")
    reserved_bytes = 700 * 1024
    seed_completed_document_operation(db, output_byte_size=reserved_bytes)
    seed_completed_image_operation(db)
    image = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=IMAGE_OPERATION_ID,
        idempotency_key="image-export-shared-quota-0001",
        request_fingerprint="f" * 64,
        expected_bytes=reserved_bytes,
    )
    assert image.lease is not None

    with pytest.raises(HTTPException) as blocked:
        assets.reserve_document_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=DOCUMENT_OPERATION_ID,
            idempotency_key="document-export-shared-quota-0001",
            request_fingerprint="d" * 64,
            expected_bytes=reserved_bytes,
        )
    assert blocked.value.status_code == 413

    assert assets.release_image_operation_asset_export_lease(image.lease) is True
    document = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-shared-quota-0002",
        request_fingerprint="d" * 64,
        expected_bytes=reserved_bytes,
    )
    assert document.lease is not None
    with pytest.raises(HTTPException) as image_blocked:
        assets.reserve_image_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=IMAGE_OPERATION_ID,
            idempotency_key="image-export-shared-quota-0002",
            request_fingerprint="f" * 64,
            expected_bytes=reserved_bytes,
        )
    assert image_blocked.value.status_code == 413


def test_image_reclaim_rechecks_shared_quota_after_expired_lease(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "1")
    reserved_bytes = 700 * 1024
    seed_completed_image_operation(db)
    seed_completed_document_operation(db, output_byte_size=reserved_bytes)
    first = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=IMAGE_OPERATION_ID,
        idempotency_key="image-export-expired-shared-quota-0001",
        request_fingerprint="f" * 64,
        expected_bytes=reserved_bytes,
    )
    assert first.lease is not None
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_image_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", IMAGE_OPERATION_ID),
        )

    document = assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=DOCUMENT_OPERATION_ID,
        idempotency_key="document-export-expired-image-quota-0001",
        request_fingerprint="d" * 64,
        expected_bytes=reserved_bytes,
    )
    assert document.lease is not None

    with pytest.raises(HTTPException) as blocked:
        assets.reserve_image_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=IMAGE_OPERATION_ID,
            idempotency_key="image-export-expired-shared-quota-0002",
            request_fingerprint="f" * 64,
            expected_bytes=reserved_bytes,
        )
    assert blocked.value.status_code == 413

    with sqlite3.connect(tmp_path / "document-export-leases.db") as conn:
        generation = conn.execute(
            "SELECT lease_generation FROM web_image_operation_asset_exports WHERE operation_id=?",
            (IMAGE_OPERATION_ID,),
        ).fetchone()[0]
    assert generation == 1


@pytest.mark.parametrize(
    "flag_name",
    (
        "WEBAPP_ASSET_VAULT_ENABLED",
        "WEBAPP_DOCUMENT_OPERATIONS_ENABLED",
        "WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED",
    ),
)
def test_document_export_reservation_requires_every_effective_capability_gate(tmp_path, monkeypatch, flag_name: str) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db)
    monkeypatch.setenv(flag_name, "false")

    with pytest.raises(HTTPException) as blocked:
        assets.reserve_document_operation_asset_export(
            account_id=ACCOUNT_ID,
            operation_id=DOCUMENT_OPERATION_ID,
            idempotency_key="document-export-capability-gate-0001",
            request_fingerprint="d" * 64,
            expected_bytes=512,
        )
    assert blocked.value.status_code == 503
