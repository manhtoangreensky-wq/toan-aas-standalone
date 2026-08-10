"""Persistence contracts for Image Operation → Asset Vault finalization."""

from __future__ import annotations

from io import BytesIO
import hashlib
import importlib
import os
from pathlib import Path
import sqlite3
import sys
import time

from PIL import Image
import pytest


ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ASSET_ID = "22222222-2222-4222-8222-222222222222"
OPERATION_ID = "33333333-3333-4333-8333-333333333333"


def load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "export-finalization.db"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED", "true")
    for name in ("copyfast_db", "copyfast_auth", "copyfast_assets", "copyfast_image_operations"):
        sys.modules.pop(name, None)
    db = importlib.import_module("copyfast_db")
    assets = importlib.import_module("copyfast_assets")
    db.ensure_copyfast_schema()
    return db, assets


def rgb_png() -> bytes:
    image = Image.new("RGB", (128, 128), (32, 136, 232))
    try:
        stream = BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()
    finally:
        image.close()


def rgba_png() -> bytes:
    image = Image.new("RGBA", (128, 128), (32, 136, 232, 255))
    try:
        stream = BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()
    finally:
        image.close()


def rgb_png_with_malformed_exif_chunk() -> bytes:
    """Return a valid RGB PNG whose eXIf payload Pillow reports as empty."""

    image = Image.new("RGB", (128, 128), (32, 136, 232))
    try:
        stream = BytesIO()
        image.save(
            stream,
            format="PNG",
            exif=b"Exif\x00\x00II*\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00",
        )
        payload = stream.getvalue()
    finally:
        image.close()
    assert b"eXIf" in payload
    return payload


def seed_completed_operation(db, *, byte_size: int, digest: str) -> None:
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache,
                is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
            (ACCOUNT_ID, "finalization-export@example.com", "not-a-login-hash", "Finalization Export", now, now),
        )
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension,
                content_type, byte_size, sha256, storage_key, state, lifecycle_revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.png', 'image/png', ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (SOURCE_ASSET_ID, ACCOUNT_ID, "Nguồn", "source.png", byte_size, digest, "objects/" + "1" * 32 + ".blob", now, now),
        )
        conn.execute(
            """INSERT INTO web_image_operations
               (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                request_fingerprint, source_sha256, source_byte_size, source_width, source_height,
                target_width, target_height, preset, fit_mode, storage_key, original_filename,
                content_type, byte_size, sha256, failure_code, created_at, queued_at, started_at,
                completed_at, updated_at, settings_json)
               VALUES (?, ?, ?, NULL, 'image_resize', 'completed', ?, ?, ?, ?, 128, 128,
                       128, 128, 'custom', 'crop', ?, 'resized.png', 'image/png', ?, ?, NULL,
                       ?, ?, ?, ?, ?, '{}')""",
            (
                OPERATION_ID,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                "export-finalization-operation-0001",
                digest,
                digest,
                byte_size,
                "outputs/" + "2" * 32 + ".png",
                byte_size,
                digest,
                now,
                now,
                now,
                now,
                now,
            ),
        )


def test_finalizing_current_lease_creates_one_independent_private_asset(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = rgb_png()
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-finalization-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reservation.lease is not None

    source = assets.ImageOperationAssetExportSource(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        kind="image_resize",
        project_id=None,
        original_filename="resized.png",
        byte_size=len(payload),
        sha256=digest,
        width=128,
        height=128,
        stream=BytesIO(payload),
    )
    finalized = assets.finalize_image_operation_asset_export(
        lease=reservation.lease,
        source=source,
        request_id="test-export-finalization-request",
    )

    assert finalized.state == "completed"
    assert finalized.asset["state"] == "active"
    assert finalized.asset["content_type"] == "image/png"
    assert finalized.asset["original_filename"] == "resized.png"
    with sqlite3.connect(tmp_path / "export-finalization.db") as conn:
        relation = conn.execute(
            "SELECT asset_id, state, lease_token, reserved_bytes, pending_storage_key FROM web_image_operation_asset_exports"
        ).fetchone()
        asset = conn.execute(
            "SELECT account_id, extension, content_type, byte_size, sha256, storage_key, state FROM web_asset_files WHERE id=?",
            (finalized.asset["id"],),
        ).fetchone()
    assert relation == (finalized.asset["id"], "completed", None, 0, None)
    assert asset[:5] == (ACCOUNT_ID, ".png", "image/png", len(payload), digest)
    assert asset[5].startswith("objects/")
    assert asset[6] == "active"
    copied = tmp_path / "private-web-assets" / asset[5]
    assert copied.read_bytes() == payload


def test_export_receipt_replays_the_asset_current_lifecycle_not_a_stale_snapshot(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = rgb_png()
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-finalization-lifecycle-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reservation.lease is not None
    finalized = assets.finalize_image_operation_asset_export(
        lease=reservation.lease,
        source=assets.ImageOperationAssetExportSource(
            account_id=ACCOUNT_ID,
            operation_id=OPERATION_ID,
            kind="image_resize",
            project_id=None,
            original_filename="resized.png",
            byte_size=len(payload),
            sha256=digest,
            width=128,
            height=128,
            stream=BytesIO(payload),
        ),
        request_id="test-export-lifecycle-request",
    )
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_asset_files SET state='archived', archived_at=?, updated_at=? WHERE id=?",
            (db.utc_now(), db.utc_now(), finalized.asset["id"]),
        )

    receipt = assets.get_image_operation_asset_export_receipt(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
    )

    assert receipt is not None
    assert receipt.state == "completed"
    assert receipt.asset["id"] == finalized.asset["id"]
    assert receipt.asset["state"] == "archived"


def test_finalizer_rejects_a_destination_blob_that_only_matches_the_digest(tmp_path, monkeypatch) -> None:
    """A private blob must parse as the exact final PNG, not merely rehash."""

    db, assets = load_modules(tmp_path, monkeypatch)
    payload = b"\x89PNG\r\n\x1a\nnot-a-complete-png"
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-finalization-invalid-png-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reservation.lease is not None

    with pytest.raises(RuntimeError, match="PNG"):
        assets.finalize_image_operation_asset_export(
            lease=reservation.lease,
            source=assets.ImageOperationAssetExportSource(
                account_id=ACCOUNT_ID,
                operation_id=OPERATION_ID,
                kind="image_resize",
                project_id=None,
                original_filename="resized.png",
                byte_size=len(payload),
                sha256=digest,
                width=128,
                height=128,
                stream=BytesIO(payload),
            ),
            request_id="test-export-invalid-destination-png",
        )

    with sqlite3.connect(tmp_path / "export-finalization.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
        relation_state = conn.execute(
            "SELECT state FROM web_image_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()[0]
    assert copied_asset_count == 0
    assert relation_state == "copying"
    assert not list((tmp_path / "private-web-assets" / "objects").glob("*.blob"))


def test_finalizer_enforces_the_final_rgb_pixel_contract(tmp_path, monkeypatch) -> None:
    """A resize export cannot persist an RGBA PNG under its RGB contract."""

    db, assets = load_modules(tmp_path, monkeypatch)
    payload = rgba_png()
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-finalization-rgba-contract-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reservation.lease is not None

    with pytest.raises(RuntimeError, match="PNG"):
        assets.finalize_image_operation_asset_export(
            lease=reservation.lease,
            source=assets.ImageOperationAssetExportSource(
                account_id=ACCOUNT_ID,
                operation_id=OPERATION_ID,
                kind="image_resize",
                project_id=None,
                original_filename="resized.png",
                byte_size=len(payload),
                sha256=digest,
                width=128,
                height=128,
                stream=BytesIO(payload),
            ),
            request_id="test-export-rgba-destination-png",
        )


def test_finalizer_rejects_a_destination_png_with_an_exif_chunk(tmp_path, monkeypatch) -> None:
    """Destination validation must reject eXIf even if Pillow returns no EXIF map."""

    db, assets = load_modules(tmp_path, monkeypatch)
    payload = rgb_png_with_malformed_exif_chunk()
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-finalization-exif-contract-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reservation.lease is not None

    with pytest.raises(RuntimeError, match="PNG"):
        assets.finalize_image_operation_asset_export(
            lease=reservation.lease,
            source=assets.ImageOperationAssetExportSource(
                account_id=ACCOUNT_ID,
                operation_id=OPERATION_ID,
                kind="image_resize",
                project_id=None,
                original_filename="resized.png",
                byte_size=len(payload),
                sha256=digest,
                width=128,
                height=128,
                stream=BytesIO(payload),
            ),
            request_id="test-export-exif-destination-png",
        )


def test_stale_finalizer_cannot_replace_a_reclaimed_completed_export(tmp_path, monkeypatch) -> None:
    """A fenced stale writer leaves only the reclaimed attempt's Asset Vault row."""

    db, assets = load_modules(tmp_path, monkeypatch)
    payload = rgb_png()
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    first = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-finalization-stale-first-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert first.lease is not None
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_image_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", OPERATION_ID),
        )
    reclaimed = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-finalization-stale-reclaimed-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reclaimed.lease is not None
    completed = assets.finalize_image_operation_asset_export(
        lease=reclaimed.lease,
        source=assets.ImageOperationAssetExportSource(
            account_id=ACCOUNT_ID,
            operation_id=OPERATION_ID,
            kind="image_resize",
            project_id=None,
            original_filename="resized.png",
            byte_size=len(payload),
            sha256=digest,
            width=128,
            height=128,
            stream=BytesIO(payload),
        ),
        request_id="test-export-stale-reclaimed-complete",
    )

    with pytest.raises(RuntimeError, match="lease"):
        assets.finalize_image_operation_asset_export(
            lease=first.lease,
            source=assets.ImageOperationAssetExportSource(
                account_id=ACCOUNT_ID,
                operation_id=OPERATION_ID,
                kind="image_resize",
                project_id=None,
                original_filename="resized.png",
                byte_size=len(payload),
                sha256=digest,
                width=128,
                height=128,
                stream=BytesIO(payload),
            ),
            request_id="test-export-stale-reclaimed-late",
        )

    with sqlite3.connect(tmp_path / "export-finalization.db") as conn:
        relation = conn.execute(
            "SELECT asset_id, state FROM web_image_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()
        asset_count = conn.execute("SELECT COUNT(*) FROM web_asset_files").fetchone()[0]
    assert relation == (completed.asset["id"], "completed")
    assert asset_count == 2


def test_reconciler_keeps_the_private_object_owned_by_a_live_pending_export(tmp_path, monkeypatch) -> None:
    """An object reserved by a current export is not an orphan yet."""

    db, assets = load_modules(tmp_path, monkeypatch)
    payload = rgb_png()
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-reconciler-pending-key-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reservation.lease is not None
    pending_object = tmp_path / "private-web-assets" / reservation.lease.pending_storage_key
    pending_object.parent.mkdir(parents=True, exist_ok=True)
    pending_object.write_bytes(payload)
    old_timestamp = time.time() - assets.ORPHAN_RETENTION_SECONDS - 2
    os.utime(pending_object, (old_timestamp, old_timestamp))

    assets.reconcile_asset_vault_storage()

    assert pending_object.is_file()


def test_lifecycle_reference_summary_reports_a_redacted_image_operation_export(tmp_path, monkeypatch) -> None:
    """The independent asset exposes only a reason/count, never export internals."""

    db, assets = load_modules(tmp_path, monkeypatch)
    payload = rgb_png()
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-lifecycle-reference-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reservation.lease is not None
    finalized = assets.finalize_image_operation_asset_export(
        lease=reservation.lease,
        source=assets.ImageOperationAssetExportSource(
            account_id=ACCOUNT_ID,
            operation_id=OPERATION_ID,
            kind="image_resize",
            project_id=None,
            original_filename="resized.png",
            byte_size=len(payload),
            sha256=digest,
            width=128,
            height=128,
            stream=BytesIO(payload),
        ),
        request_id="test-export-lifecycle-reference",
    )

    with db.transaction() as conn:
        summary = assets._lifecycle_reference_summary(
            conn,
            asset_id=finalized.asset["id"],
            account_id=ACCOUNT_ID,
        )

    assert summary == {
        "total_count": 1,
        "hard_blocker_count": 0,
        "references": [{
            "reason": "image_operation_export",
            "count": 1,
            "hard_blocker": False,
        }],
    }
    assert OPERATION_ID not in repr(summary)
    assert finalized.asset["id"] not in repr(summary)


@pytest.mark.parametrize(
    ("project_state", "project_owner"),
    (("archived", ACCOUNT_ID), ("active", "55555555-5555-4555-8555-555555555555")),
    ids=("archived", "foreign"),
)
def test_finalizer_drops_an_archived_or_foreign_source_project_during_copy(
    tmp_path,
    monkeypatch,
    project_state: str,
    project_owner: str,
) -> None:
    """Only a current, owner-scoped Project may remain attached to the copy."""

    db, assets = load_modules(tmp_path, monkeypatch)
    payload = rgb_png()
    digest = hashlib.sha256(payload).hexdigest()
    project_id = "44444444-4444-4444-8444-444444444444"
    seed_completed_operation(db, byte_size=len(payload), digest=digest)
    with db.transaction() as conn:
        now = db.utc_now()
        if project_owner != ACCOUNT_ID:
            conn.execute(
                """INSERT INTO web_accounts
                   (id, email, password_hash, display_name, canonical_user_id, role_cache,
                    is_active, password_login_enabled, created_at, updated_at)
                   VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
                (project_owner, "foreign-project@example.com", "not-a-login-hash", "Foreign Project", now, now),
            )
        conn.execute(
            """INSERT INTO web_projects
               (id, account_id, title, summary, objective, state, created_at, updated_at)
               VALUES (?, ?, 'Project source', '', '', ?, ?, ?)""",
            (project_id, project_owner, project_state, now, now),
        )
    reservation = assets.reserve_image_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key="export-archived-project-0001",
        request_fingerprint=digest,
        expected_bytes=len(payload),
    )
    assert reservation.lease is not None
    finalized = assets.finalize_image_operation_asset_export(
        lease=reservation.lease,
        source=assets.ImageOperationAssetExportSource(
            account_id=ACCOUNT_ID,
            operation_id=OPERATION_ID,
            kind="image_resize",
            project_id=project_id,
            original_filename="resized.png",
            byte_size=len(payload),
            sha256=digest,
            width=128,
            height=128,
            stream=BytesIO(payload),
        ),
        request_id="test-export-archived-project",
    )

    assert finalized.asset["project_id"] is None
    with sqlite3.connect(tmp_path / "export-finalization.db") as conn:
        stored_project_id = conn.execute(
            "SELECT project_id FROM web_asset_files WHERE id=?",
            (finalized.asset["id"],),
        ).fetchone()[0]
    assert stored_project_id is None
