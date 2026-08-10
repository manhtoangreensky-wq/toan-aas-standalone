"""Focused trust-boundary contracts for Image Operation Asset Export."""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import sqlite3

from PIL import Image

from test_image_operation_asset_export import (
    completed_resize,
    export_operation,
    make_client,
    register_and_login,
)
from test_image_operation_asset_export_source_integrity import (
    ACCOUNT_ID,
    OPERATION_ID,
    load_modules,
    seed_completed_operation,
)


PROJECT_ID = "44444444-4444-4444-8444-444444444444"


def _rgb_png_with_malformed_exif_chunk() -> bytes:
    """Return a valid RGB PNG with an eXIf chunk Pillow parses as empty EXIF."""
    image = Image.new("RGB", (128, 96), (40, 146, 226))
    try:
        stream = BytesIO()
        image.save(
            stream,
            format="PNG",
            # Pillow writes an eXIf chunk but getexif() later treats these
            # deliberately incomplete TIFF bytes as empty metadata.
            exif=b"Exif\x00\x00II*\x00\x08\x00\x00\x00\x00\x00\x00\x00\x00",
        )
        payload = stream.getvalue()
    finally:
        image.close()
    assert b"eXIf" in payload
    return payload


def _operation_project_id(db_path: Path, operation_id: str) -> str | None:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT project_id FROM web_image_operations WHERE id=?",
            (operation_id,),
        ).fetchone()
    assert row is not None
    return str(row[0]) if row[0] else None


def _asset_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM web_asset_files").fetchone()[0])


def test_export_source_rejects_png_exif_chunk_even_when_pillow_reports_empty_exif(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    payload = _rgb_png_with_malformed_exif_chunk()
    seed_completed_operation(db, root=db.image_operations_directory(), payload=payload)

    result = operations.open_image_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    try:
        assert result.source is None
        assert result.failure is not None
        assert result.failure.domain is operations.ImageOperationExportFailureDomain.SOURCE_INTEGRITY
    finally:
        result.close()


def test_export_source_exposes_only_db_derived_project_id(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    payload = Image.new("RGB", (128, 96), (40, 146, 226))
    try:
        stream = BytesIO()
        payload.save(stream, format="PNG")
        body = stream.getvalue()
    finally:
        payload.close()
    seed_completed_operation(db, root=db.image_operations_directory(), payload=body)
    with db.transaction() as conn:
        now = db.utc_now()
        conn.execute(
            """INSERT INTO web_projects
               (id, account_id, title, summary, objective, state, created_at, updated_at)
               VALUES (?, ?, 'Source export project', '', '', 'active', ?, ?)""",
            (PROJECT_ID, ACCOUNT_ID, now, now),
        )
        conn.execute(
            "UPDATE web_image_operations SET project_id=? WHERE id=? AND account_id=?",
            (PROJECT_ID, OPERATION_ID, ACCOUNT_ID),
        )

    result = operations.open_image_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    try:
        assert result.failure is None
        assert result.source is not None
        assert result.source.project_id == PROJECT_ID
    finally:
        result.close()


def test_endpoint_propagates_active_operation_project_to_private_vault_asset(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        email = "export-project-owner@example.com"
        csrf = register_and_login(client, email)
        _, operation = completed_resize(
            client,
            csrf,
            source_key="export-project-source-0001",
            operation_key="export-project-operation-0001",
        )
        db_path = tmp_path / "image-operation-asset-export.db"
        with sqlite3.connect(db_path) as conn:
            account_id = str(conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0])
            now = importlib.import_module("copyfast_db").utc_now()
            conn.execute(
                """INSERT INTO web_projects
                   (id, account_id, title, summary, objective, state, created_at, updated_at)
                   VALUES (?, ?, 'Export project', '', '', 'active', ?, ?)""",
                (PROJECT_ID, account_id, now, now),
            )
            conn.execute(
                "UPDATE web_image_operations SET project_id=? WHERE id=? AND account_id=?",
                (PROJECT_ID, operation["id"], account_id),
            )
            conn.commit()

        exported = export_operation(client, csrf, operation["id"], "export-project-copy-0001")

        assert exported.status_code == 200, exported.text
        assert exported.json()["data"]["asset"]["project_id"] == PROJECT_ID
        assert _operation_project_id(db_path, operation["id"]) == PROJECT_ID


def test_endpoint_returns_fresh_owner_receipt_after_finalizer_state_changes(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "export-fresh-receipt@example.com")
        _, operation = completed_resize(
            client,
            csrf,
            source_key="export-fresh-receipt-source-0001",
            operation_key="export-fresh-receipt-operation-0001",
        )
        assets = importlib.import_module("copyfast_assets")
        db = importlib.import_module("copyfast_db")
        original_finalize = assets.finalize_image_operation_asset_export

        def finalize_then_archive(*, lease, source, request_id):
            finalized = original_finalize(lease=lease, source=source, request_id=request_id)
            with db.transaction() as conn:
                now = db.utc_now()
                conn.execute(
                    """UPDATE web_asset_files
                       SET state='archived', archived_at=?, updated_at=?
                       WHERE id=? AND account_id=?""",
                    (now, now, finalized.asset["id"], lease.account_id),
                )
            return finalized

        monkeypatch.setattr(assets, "finalize_image_operation_asset_export", finalize_then_archive)
        exported = export_operation(client, csrf, operation["id"], "export-fresh-receipt-copy-0001")

        assert exported.status_code == 200, exported.text
        assert exported.json()["data"]["asset"]["state"] == "archived"


def test_endpoint_replay_reports_the_current_archived_asset_lifecycle(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "export-replay-lifecycle@example.com")
        _, operation = completed_resize(
            client,
            csrf,
            source_key="export-replay-lifecycle-source-0001",
            operation_key="export-replay-lifecycle-operation-0001",
        )
        db_path = tmp_path / "image-operation-asset-export.db"
        first = export_operation(client, csrf, operation["id"], "export-replay-lifecycle-copy-0001")
        assert first.status_code == 200, first.text
        asset_id = first.json()["data"]["asset"]["id"]
        db = importlib.import_module("copyfast_db")
        with db.transaction() as conn:
            now = db.utc_now()
            conn.execute(
                "UPDATE web_asset_files SET state='archived', archived_at=?, updated_at=? WHERE id=?",
                (now, now, asset_id),
            )

        replay = export_operation(client, csrf, operation["id"], "export-replay-lifecycle-new-key-0001")

        assert replay.status_code == 200, replay.text
        assert replay.json()["data"]["asset"] == {
            **first.json()["data"]["asset"],
            "state": "archived",
            "archived_at": replay.json()["data"]["asset"]["archived_at"],
            "updated_at": replay.json()["data"]["asset"]["updated_at"],
        }
        assert replay.json()["data"]["asset"]["archived_at"]
        assert _asset_count(db_path) == 2


def test_endpoint_reclaims_an_expired_export_lease_instead_of_replaying_pending(tmp_path, monkeypatch) -> None:
    """A retry must fence and finish an expired copy rather than remain pending."""

    with make_client(tmp_path, monkeypatch) as client:
        email = "export-expired-lease-owner@example.com"
        csrf = register_and_login(client, email)
        _, operation = completed_resize(
            client,
            csrf,
            source_key="export-expired-lease-source-0001",
            operation_key="export-expired-lease-operation-0001",
        )
        db = importlib.import_module("copyfast_db")
        assets = importlib.import_module("copyfast_assets")
        db_path = tmp_path / "image-operation-asset-export.db"
        with sqlite3.connect(db_path) as conn:
            account_id = str(conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0])
            output_sha256, output_bytes = conn.execute(
                "SELECT sha256, byte_size FROM web_image_operations WHERE id=? AND account_id=?",
                (operation["id"], account_id),
            ).fetchone()

        reservation = assets.reserve_image_operation_asset_export(
            account_id=account_id,
            operation_id=operation["id"],
            idempotency_key="export-expired-lease-primary-0001",
            request_fingerprint=str(output_sha256),
            expected_bytes=int(output_bytes),
        )
        assert reservation.lease is not None
        with db.transaction() as conn:
            conn.execute(
                "UPDATE web_image_operation_asset_exports SET lease_expires_at=? WHERE operation_id=? AND account_id=?",
                ("1970-01-01T00:00:00+00:00", operation["id"], account_id),
            )

        retry = export_operation(client, csrf, operation["id"], "export-expired-lease-retry-0001")

        assert retry.status_code == 200, retry.text
        assert retry.json()["ok"] is True
        assert retry.json()["status"] == "completed"
        assert retry.json()["data"]["asset"]["id"]
        with sqlite3.connect(db_path) as conn:
            state, generation = conn.execute(
                "SELECT state, lease_generation FROM web_image_operation_asset_exports WHERE operation_id=? AND account_id=?",
                (operation["id"], account_id),
            ).fetchone()
        assert (state, generation) == ("completed", 2)
