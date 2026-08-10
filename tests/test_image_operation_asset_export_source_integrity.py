"""Integrity contracts for Image Operation → Asset Vault source opening."""

from __future__ import annotations

from io import BytesIO
import hashlib
import importlib
from pathlib import Path
import sqlite3
import sys

import pytest
from PIL import Image


ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ASSET_ID = "22222222-2222-4222-8222-222222222222"
OPERATION_ID = "33333333-3333-4333-8333-333333333333"


def load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "export-source.db"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ROOT", str(tmp_path / "private-image-outputs"))
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "100")
    for name in ("copyfast_db", "copyfast_auth", "copyfast_image_operations"):
        sys.modules.pop(name, None)
    db = importlib.import_module("copyfast_db")
    operations = importlib.import_module("copyfast_image_operations")
    db.ensure_copyfast_schema()
    return db, operations


def png_bytes(*, mode: str, transparent: bool = False) -> bytes:
    image = Image.new(mode, (128, 96), (40, 146, 226, 255) if mode == "RGBA" else (40, 146, 226))
    try:
        if transparent:
            image.putpixel((0, 0), (40, 146, 226, 0))
        stream = BytesIO()
        image.save(stream, format="PNG")
        return stream.getvalue()
    finally:
        image.close()


def seed_completed_operation(
    db,
    *,
    root: Path,
    kind: str = "image_resize",
    payload: bytes,
    digest: str | None = None,
    storage_key: str | None = None,
) -> tuple[str, Path]:
    now = db.utc_now()
    key = storage_key or ("outputs/" + "2" * 32 + ".png")
    output = root / key
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    expected_digest = digest or hashlib.sha256(payload).hexdigest()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache,
                is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
            (ACCOUNT_ID, "export-source@example.com", "not-a-login-hash", "Export Source", now, now),
        )
        conn.execute(
            """INSERT INTO web_asset_files
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
               VALUES (?, ?, ?, NULL, ?, 'completed', ?, ?, ?, 512, 128, 96,
                       128, 96, 'custom', 'crop', ?, 'operation.png', 'image/png', ?, ?, NULL,
                       ?, ?, ?, ?, ?, '{}')""",
            (
                OPERATION_ID,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                kind,
                "operation-export-source-key-0001",
                "b" * 64,
                "c" * 64,
                key,
                len(payload),
                expected_digest,
                now,
                now,
                now,
                now,
                now,
            ),
        )
    return key, output


def operation_state(tmp_path: Path) -> str:
    with sqlite3.connect(tmp_path / "export-source.db") as conn:
        return str(conn.execute("SELECT state FROM web_image_operations WHERE id=?", (OPERATION_ID,)).fetchone()[0])


def test_export_source_opener_uses_completed_db_metadata_and_keeps_verified_fd_open(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    root = db.image_operations_directory()
    payload = png_bytes(mode="RGB")
    seed_completed_operation(db, root=root, payload=payload)

    result = operations.open_image_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.failure is None
    assert result.source is not None
    assert result.source.contract.kind == "image_resize"
    assert result.source.contract.expected_mode == "RGB"
    assert result.source.byte_size == len(payload)
    try:
        assert result.source.stream.read() == payload
    finally:
        result.close()


def test_export_source_integrity_failure_is_typed_and_never_marks_output_without_explicit_action(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    root = db.image_operations_directory()
    payload = png_bytes(mode="RGB")
    storage_key, _ = seed_completed_operation(db, root=root, payload=payload, digest="0" * 64)

    result = operations.open_image_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.ImageOperationExportFailureDomain.SOURCE_INTEGRITY
    assert result.failure.should_mark_output_unavailable is True
    safe_failure = repr(result.failure).lower()
    for private_value in (storage_key.lower(), hashlib.sha256(payload).hexdigest(), "private-image-outputs"):
        assert private_value not in safe_failure
    assert operation_state(tmp_path) == "completed"

    assert operations.mark_image_operation_export_source_unavailable(result) is True
    assert operation_state(tmp_path) == "unavailable"


def test_export_source_opener_requires_cleanup_rgba_png_with_transparent_alpha(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    root = db.image_operations_directory()
    payload = png_bytes(mode="RGBA", transparent=False)
    seed_completed_operation(db, root=root, kind="image_background_cleanup", payload=payload)

    result = operations.open_image_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.ImageOperationExportFailureDomain.SOURCE_INTEGRITY
    assert operation_state(tmp_path) == "completed"


def test_export_source_runtime_boundary_is_destination_failure_and_keeps_completed_output(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    root = db.image_operations_directory()
    seed_completed_operation(db, root=root, payload=png_bytes(mode="RGB"))

    def unavailable_root():
        raise RuntimeError("private root unavailable")

    monkeypatch.setattr(operations, "image_operations_directory", unavailable_root)
    result = operations.open_image_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.ImageOperationExportFailureDomain.DESTINATION
    assert result.failure.should_mark_output_unavailable is False
    assert operations.mark_image_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path) == "completed"


def test_export_source_opener_rejects_final_or_output_directory_symlink_without_leaking_key(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    root = db.image_operations_directory()
    payload = png_bytes(mode="RGB")
    storage_key, output = seed_completed_operation(db, root=root, payload=payload)
    external = tmp_path / "external.png"
    external.write_bytes(payload)
    try:
        output.unlink()
        output.symlink_to(external)
    except (NotImplementedError, OSError):
        pytest.skip("filesystem does not permit a symlink integrity contract")

    result = operations.open_image_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.ImageOperationExportFailureDomain.SOURCE_INTEGRITY
    assert storage_key not in repr(result.failure)
    assert operation_state(tmp_path) == "completed"


def test_export_source_opener_allows_only_the_four_export_kinds(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    root = db.image_operations_directory()
    payload = png_bytes(mode="RGB")
    seed_completed_operation(db, root=root, kind="image_future_kind", payload=payload)

    result = operations.open_image_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.ImageOperationExportFailureDomain.PRECONDITION
    assert result.failure.should_mark_output_unavailable is False
    assert operations.mark_image_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path) == "completed"
