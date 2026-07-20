"""High-risk contracts for the query-only Web-native Jobs / Assets model."""

from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3

import copyfast_native_read_models as models
import pytest


OWNER = "account-owner"
OTHER_OWNER = "account-other"
NOW = "2026-07-17T10:00:00+00:00"
VALID_PACKAGE_KEY = "packages/" + ("a" * 32) + ".zip"
VALID_DOCUMENT_KEY = "outputs/" + ("b" * 32) + ".pdf"
VALID_IMAGE_KEY = "outputs/" + ("c" * 32) + ".png"
VALID_SUBTITLE_KEY = "outputs/" + ("e" * 32) + ".vtt"
VALID_AUDIO_KEY = "outputs/" + ("f" * 32) + ".m4a"
VALID_VIDEO_KEY = "outputs/" + ("e" * 32) + ".jpg"
VALID_SHA256 = "d" * 64
SECRET = "provider-token-ultra-secret"


def _database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.executescript(
        """
        CREATE TABLE web_asset_files (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            extension TEXT NOT NULL,
            content_type TEXT NOT NULL,
            byte_size INTEGER NOT NULL,
            sha256 TEXT,
            storage_key TEXT,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT
        );
        CREATE TABLE web_project_packages (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            state TEXT NOT NULL,
            document_count INTEGER NOT NULL,
            asset_reference_count INTEGER NOT NULL,
            storage_key TEXT,
            original_filename TEXT,
            content_type TEXT,
            byte_size INTEGER,
            sha256 TEXT,
            created_at TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL,
            request_fingerprint TEXT,
            source_snapshot_json TEXT,
            failure_code TEXT
        );
        CREATE TABLE web_document_operations (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            source_asset_id TEXT,
            kind TEXT NOT NULL,
            state TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            selected_start_page INTEGER,
            selected_end_page INTEGER,
            source_page_count INTEGER,
            output_page_count INTEGER,
            storage_key TEXT,
            original_filename TEXT,
            content_type TEXT,
            byte_size INTEGER,
            sha256 TEXT,
            created_at TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL,
            idempotency_key TEXT,
            request_fingerprint TEXT,
            source_sha256 TEXT,
            failure_code TEXT
        );
        CREATE TABLE web_image_operations (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            source_asset_id TEXT,
            kind TEXT NOT NULL,
            state TEXT NOT NULL,
            target_width INTEGER NOT NULL,
            target_height INTEGER NOT NULL,
            preset TEXT NOT NULL,
            fit_mode TEXT NOT NULL,
            source_width INTEGER,
            source_height INTEGER,
            storage_key TEXT,
            original_filename TEXT,
            content_type TEXT,
            byte_size INTEGER,
            sha256 TEXT,
            created_at TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL,
            idempotency_key TEXT,
            request_fingerprint TEXT,
            settings_json TEXT,
            failure_code TEXT
        );
        CREATE TABLE web_video_operations (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            source_asset_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            state TEXT NOT NULL,
            idempotency_key TEXT,
            request_fingerprint TEXT,
            source_sha256 TEXT,
            source_byte_size INTEGER,
            source_extension TEXT,
            source_content_type TEXT,
            poster_position TEXT NOT NULL,
            source_duration_ms INTEGER,
            source_width INTEGER,
            source_height INTEGER,
            frame_timestamp_ms INTEGER,
            output_width INTEGER,
            output_height INTEGER,
            storage_key TEXT,
            original_filename TEXT,
            content_type TEXT,
            byte_size INTEGER,
            sha256 TEXT,
            failure_code TEXT,
            created_at TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    connection.executemany(
        """INSERT INTO web_asset_files
           (id, account_id, display_name, original_filename, extension,
            content_type, byte_size, sha256, storage_key, state, created_at,
            updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "asset-owner",
                OWNER,
                r"C:\private\brief.pdf",
                r"C:\private\brief.pdf",
                ".pdf",
                "application/pdf",
                40,
                VALID_SHA256,
                "objects/private-storage-hidden-owner.blob",
                "active",
                NOW,
                NOW,
                None,
            ),
            (
                "asset-other",
                OTHER_OWNER,
                "other-private.pdf",
                "other-private.pdf",
                ".pdf",
                "application/pdf",
                41,
                VALID_SHA256,
                "objects/private-storage-hidden-other.blob",
                "active",
                NOW,
                NOW,
                None,
            ),
        ],
    )
    connection.executemany(
        """INSERT INTO web_project_packages
           (id, account_id, state, document_count, asset_reference_count,
            storage_key, original_filename, content_type, byte_size, sha256,
            created_at, queued_at, started_at, completed_at, updated_at,
            request_fingerprint, source_snapshot_json, failure_code)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "package-owner",
                OWNER,
                "completed",
                2,
                1,
                VALID_PACKAGE_KEY,
                r"D:\private\owner-package.zip",
                "application/zip",
                512,
                VALID_SHA256,
                NOW,
                NOW,
                NOW,
                NOW,
                "2026-07-17T10:01:00+00:00",
                SECRET,
                '{"snapshot":"' + SECRET + '"}',
                SECRET,
            ),
            (
                "package-other",
                OTHER_OWNER,
                "completed",
                1,
                0,
                VALID_PACKAGE_KEY,
                "other-package.zip",
                "application/zip",
                512,
                VALID_SHA256,
                NOW,
                NOW,
                NOW,
                NOW,
                "2026-07-17T10:02:00+00:00",
                SECRET,
                SECRET,
                SECRET,
            ),
        ],
    )
    connection.executemany(
        """INSERT INTO web_document_operations
           (id, account_id, source_asset_id, kind, state, source_count,
            selected_start_page, selected_end_page, source_page_count,
            output_page_count, storage_key, original_filename, content_type,
            byte_size, sha256, created_at, queued_at, started_at, completed_at,
            updated_at, idempotency_key, request_fingerprint, source_sha256,
            failure_code)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "document-incomplete",
                OWNER,
                "asset-owner",
                "pdf_split",
                "completed",
                1,
                1,
                1,
                1,
                1,
                None,
                "incomplete.pdf",
                "application/pdf",
                128,
                VALID_SHA256,
                NOW,
                NOW,
                NOW,
                NOW,
                "2026-07-17T10:03:00+00:00",
                SECRET,
                SECRET,
                VALID_SHA256,
                SECRET,
            ),
            (
                "document-other",
                OTHER_OWNER,
                "asset-other",
                "pdf_split",
                "completed",
                1,
                1,
                1,
                1,
                1,
                VALID_DOCUMENT_KEY,
                "other.pdf",
                "application/pdf",
                128,
                VALID_SHA256,
                NOW,
                NOW,
                NOW,
                NOW,
                "2026-07-17T10:04:00+00:00",
                SECRET,
                SECRET,
                VALID_SHA256,
                SECRET,
            ),
        ],
    )
    connection.executemany(
        """INSERT INTO web_image_operations
           (id, account_id, source_asset_id, kind, state, target_width,
            target_height, preset, fit_mode, source_width, source_height,
            storage_key, original_filename, content_type, byte_size, sha256,
            created_at, queued_at, started_at, completed_at, updated_at,
            idempotency_key, request_fingerprint, settings_json, failure_code)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "image-complete",
                OWNER,
                "asset-owner",
                "image_resize",
                "completed",
                1024,
                1024,
                "1:1",
                "crop",
                1600,
                1200,
                VALID_IMAGE_KEY,
                "owner-image.png",
                "image/png",
                256,
                VALID_SHA256,
                NOW,
                NOW,
                NOW,
                NOW,
                "2026-07-17T10:05:00+00:00",
                SECRET,
                SECRET,
                '{"provider":"' + SECRET + '"}',
                SECRET,
            ),
            (
                "image-queued",
                OWNER,
                "asset-owner",
                "image_resize",
                "queued",
                1024,
                1024,
                "1:1",
                "crop",
                1600,
                1200,
                VALID_IMAGE_KEY,
                "queued-image.png",
                "image/png",
                256,
                VALID_SHA256,
                NOW,
                NOW,
                None,
                NOW,
                "2026-07-17T10:06:00+00:00",
                SECRET,
                SECRET,
                '{"provider":"' + SECRET + '"}',
                SECRET,
            ),
            (
                "image-other",
                OTHER_OWNER,
                "asset-other",
                "image_resize",
                "completed",
                1024,
                1024,
                "1:1",
                "crop",
                1600,
                1200,
                VALID_IMAGE_KEY,
                "other-image.png",
                "image/png",
                256,
                VALID_SHA256,
                NOW,
                NOW,
                NOW,
                NOW,
                "2026-07-17T10:07:00+00:00",
                SECRET,
                SECRET,
                SECRET,
                SECRET,
            ),
        ],
    )
    connection.executemany(
        """INSERT INTO web_video_operations
           (id, account_id, source_asset_id, kind, state, idempotency_key,
            request_fingerprint, source_sha256, source_byte_size,
            source_extension, source_content_type, poster_position,
            source_duration_ms, source_width, source_height,
            frame_timestamp_ms, output_width, output_height, storage_key,
            original_filename, content_type, byte_size, sha256, failure_code,
            created_at, queued_at, started_at, completed_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "video-complete", OWNER, "asset-owner", "video_poster", "completed",
                SECRET, SECRET, VALID_SHA256, 1_024, ".mp4", "video/mp4", "middle",
                9_000, 1_920, 1_080, 4_500, 1_280, 720, VALID_VIDEO_KEY,
                "owner-poster.jpg", "image/jpeg", 384, VALID_SHA256, SECRET,
                NOW, NOW, NOW, NOW, "2026-07-17T10:08:00+00:00",
            ),
            (
                "video-queued", OWNER, "asset-owner", "video_poster", "queued",
                SECRET, SECRET, VALID_SHA256, 1_024, ".mp4", "video/mp4", "start",
                None, None, None, None, None, None, None,
                None, None, None, None, SECRET,
                NOW, NOW, None, None, "2026-07-17T10:09:00+00:00",
            ),
            (
                "video-other", OTHER_OWNER, "asset-other", "video_poster", "completed",
                SECRET, SECRET, VALID_SHA256, 1_024, ".mp4", "video/mp4", "end",
                9_000, 1_920, 1_080, 8_500, 1_280, 720, VALID_VIDEO_KEY,
                "other-poster.jpg", "image/jpeg", 384, VALID_SHA256, SECRET,
                NOW, NOW, NOW, NOW, "2026-07-17T10:10:00+00:00",
            ),
        ],
    )
    return connection


def _install_read_transaction(monkeypatch, connection: sqlite3.Connection) -> None:
    @contextmanager
    def read_transaction():
        yield connection

    monkeypatch.setattr(models, "read_transaction", read_transaction)


def _insert_document_operation(
    connection: sqlite3.Connection,
    record_id: str,
    *,
    kind: str,
    content_type: str,
    storage_key: str,
    output_page_count: int | None,
) -> None:
    connection.execute(
        """INSERT INTO web_document_operations
           (id, account_id, source_asset_id, kind, state, source_count,
            selected_start_page, selected_end_page, source_page_count,
            output_page_count, storage_key, original_filename, content_type,
            byte_size, sha256, created_at, queued_at, started_at, completed_at,
            updated_at, idempotency_key, request_fingerprint, source_sha256,
            failure_code)
           VALUES (?, ?, ?, ?, 'completed', 1, 1, 1, 1, ?, ?, ?, ?, 128, ?,
                   ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record_id,
            OWNER,
            "asset-owner",
            kind,
            output_page_count,
            storage_key,
            "untrusted-row-name.bin",
            content_type,
            VALID_SHA256,
            NOW,
            NOW,
            NOW,
            NOW,
            "2026-07-17T11:00:00+00:00",
            SECRET,
            SECRET,
            VALID_SHA256,
            SECRET,
        ),
    )


def test_native_read_models_keep_jobs_and_assets_owner_scoped(monkeypatch) -> None:
    connection = _database()
    _install_read_transaction(monkeypatch, connection)
    changes_before = connection.total_changes

    jobs = models.list_native_jobs(OWNER)
    assets = models.list_native_assets(OWNER)

    assert {models.parse_native_job_id(job["id"])[1] for job in jobs} == {
        "package-owner",
        "document-incomplete",
        "image-complete",
        "image-queued",
        "video-complete",
        "video-queued",
    }
    assert {models.parse_native_asset_id(asset["id"]) for asset in assets} == {"asset-owner"}
    assert models.get_native_job(OWNER, models.encode_native_job_id("project-package", "package-other")) is None
    assert models.get_native_job(OTHER_OWNER, models.encode_native_job_id("project-package", "package-owner")) is None
    assert connection.total_changes == changes_before


def test_native_resolvers_keep_owner_scope_inside_callers_transaction(monkeypatch) -> None:
    """Write-side modules can validate an opaque reference without a second read."""

    connection = _database()
    _install_read_transaction(monkeypatch, connection)
    job_id = models.encode_native_job_id("image-operation", "image-complete")
    asset_id = models.encode_native_asset_id("asset-owner")
    changes_before = connection.total_changes

    own_job = models.resolve_native_job(connection, OWNER, job_id)
    own_asset = models.resolve_native_asset(connection, OWNER, asset_id)
    foreign_job = models.resolve_native_job(connection, OTHER_OWNER, job_id)
    foreign_asset = models.resolve_native_asset(connection, OTHER_OWNER, asset_id)

    assert own_job and own_job["id"] == job_id and own_job["output"] is not None
    assert own_asset and own_asset["id"] == asset_id and own_asset["status"] == "active"
    assert foreign_job is None
    assert foreign_asset is None
    assert connection.total_changes == changes_before


def test_native_read_models_redact_private_metadata_and_paths(monkeypatch) -> None:
    connection = _database()
    _install_read_transaction(monkeypatch, connection)

    projection = {
        "jobs": models.list_native_jobs(OWNER),
        "assets": models.list_native_assets(OWNER),
    }
    encoded = json.dumps(projection, sort_keys=True)

    for private_value in (SECRET, VALID_SHA256, VALID_PACKAGE_KEY, "private-storage-hidden-owner", "C:\\private"):
        assert private_value not in encoded
    for forbidden_key in (
        "account_id",
        "project_id",
        "source_asset_id",
        "storage_key",
        "sha256",
        "request_fingerprint",
        "idempotency_key",
        "failure_code",
        "settings_json",
    ):
        assert f'"{forbidden_key}"' not in encoded
    assert projection["assets"][0]["name"] == "brief.pdf"
    assert projection["jobs"][0]["id"].startswith("wnj:v1:")


def test_native_read_models_preserve_state_and_require_sealed_output_metadata(monkeypatch) -> None:
    connection = _database()
    _install_read_transaction(monkeypatch, connection)

    incomplete = models.get_native_job(OWNER, models.encode_native_job_id("document-operation", "document-incomplete"))
    completed = models.get_native_job(OWNER, models.encode_native_job_id("image-operation", "image-complete"))
    queued = models.get_native_job(OWNER, models.encode_native_job_id("image-operation", "image-queued"))
    video_completed = models.get_native_job(OWNER, models.encode_native_job_id("video-operation", "video-complete"))
    video_queued = models.get_native_job(OWNER, models.encode_native_job_id("video-operation", "video-queued"))

    assert incomplete is not None
    assert incomplete["state"] == incomplete["status"] == "completed"
    assert incomplete["output"] is None
    assert completed is not None
    assert completed["state"] == completed["status"] == "completed"
    assert completed["output"] == {
        "filename": "toan-aas-image-resized.png",
        "content_type": "image/png",
        "byte_size": 256,
    }
    assert queued is not None
    assert queued["state"] == queued["status"] == "queued"
    assert queued["output"] is None
    assert video_completed is not None
    assert video_completed["output"] == {
        "filename": "toan-aas-video-poster.jpg",
        "content_type": "image/jpeg",
        "byte_size": 384,
    }
    assert video_queued is not None
    assert video_queued["output"] is None


def test_native_read_models_match_direct_document_mime_and_page_count_contracts(monkeypatch) -> None:
    connection = _database()
    _install_read_transaction(monkeypatch, connection)
    png_key = "outputs/" + ("e" * 32) + ".png"
    zip_key = "outputs/" + ("f" * 32) + ".zip"
    text_key = "outputs/" + ("1" * 32) + ".txt"
    _insert_document_operation(
        connection,
        "ocr-wrong-mime",
        kind="image_ocr",
        content_type="text/plain",
        storage_key=text_key,
        output_page_count=None,
    )
    _insert_document_operation(
        connection,
        "ocr-exact-mime",
        kind="image_ocr",
        content_type="text/plain; charset=utf-8",
        storage_key=text_key,
        output_page_count=None,
    )
    _insert_document_operation(
        connection,
        "pdf-images-one-page",
        kind="pdf_to_images",
        content_type="image/png",
        storage_key=png_key,
        output_page_count=1,
    )
    _insert_document_operation(
        connection,
        "pdf-images-mismatched-page-count",
        kind="pdf_to_images",
        content_type="application/zip",
        storage_key=zip_key,
        output_page_count=1,
    )
    _insert_document_operation(
        connection,
        "pdf-images-many-pages",
        kind="pdf_to_images",
        content_type="application/zip",
        storage_key=zip_key,
        output_page_count=2,
    )

    wrong_ocr = models.get_native_job(OWNER, models.encode_native_job_id("document-operation", "ocr-wrong-mime"))
    exact_ocr = models.get_native_job(OWNER, models.encode_native_job_id("document-operation", "ocr-exact-mime"))
    one_page = models.get_native_job(OWNER, models.encode_native_job_id("document-operation", "pdf-images-one-page"))
    mismatched = models.get_native_job(
        OWNER,
        models.encode_native_job_id("document-operation", "pdf-images-mismatched-page-count"),
    )
    many_pages = models.get_native_job(OWNER, models.encode_native_job_id("document-operation", "pdf-images-many-pages"))

    assert wrong_ocr and wrong_ocr["output"] is None
    assert exact_ocr and exact_ocr["output"] == {
        "filename": "toan-aas-image-ocr.txt",
        "content_type": "text/plain; charset=utf-8",
        "byte_size": 128,
    }
    assert one_page and one_page["output"] == {
        "filename": "toan-aas-pdf-page-001.png",
        "content_type": "image/png",
        "byte_size": 128,
    }
    assert mismatched and mismatched["output"] is None
    assert many_pages and many_pages["output"] == {
        "filename": "toan-aas-pdf-pages.zip",
        "content_type": "application/zip",
        "byte_size": 128,
    }


def test_native_completed_outputs_are_not_hidden_by_a_page_of_newer_queued_jobs(monkeypatch) -> None:
    connection = _database()
    _install_read_transaction(monkeypatch, connection)
    connection.executemany(
        """INSERT INTO web_image_operations
           (id, account_id, source_asset_id, kind, state, target_width,
            target_height, preset, fit_mode, source_width, source_height,
            storage_key, original_filename, content_type, byte_size, sha256,
            created_at, queued_at, started_at, completed_at, updated_at,
            idempotency_key, request_fingerprint, settings_json, failure_code)
           VALUES (?, ?, ?, 'image_resize', 'queued', 1024, 1024, '1:1',
                   'crop', 1600, 1200, ?, 'queued.png', 'image/png', 256, ?,
                   ?, ?, NULL, NULL, ?, ?, ?, '{}', ?)""",
        [
            (
                f"newer-queued-{index:03d}",
                OWNER,
                "asset-owner",
                VALID_IMAGE_KEY,
                VALID_SHA256,
                "2026-07-18T00:00:00+00:00",
                "2026-07-18T00:00:00+00:00",
                f"2026-07-18T00:00:{index:02d}+00:00",
                SECRET,
                SECRET,
                SECRET,
            )
            for index in range(100)
        ],
    )

    recent_jobs = models.list_native_jobs(OWNER, limit=100)
    completed_outputs = models.list_native_completed_outputs(OWNER, limit=100)
    completed_image_id = models.encode_native_job_id("image-operation", "image-complete")

    assert completed_image_id not in {item["id"] for item in recent_jobs}
    assert completed_image_id in {item["id"] for item in completed_outputs}
    assert all(isinstance(item.get("output"), dict) for item in completed_outputs)


def test_native_read_models_reject_unknown_public_job_ids_without_lookup(monkeypatch) -> None:
    connection = _database()
    _install_read_transaction(monkeypatch, connection)

    assert models.parse_native_job_id("unknown") is None
    assert models.parse_public_job_id("wnj:v1:bot-job:YWJj") is None
    assert models.parse_native_job_id("wnj:v1:image-operation:not*route-safe") is None
    assert models.parse_native_job_id("x" * 161) is None
    assert models.get_native_job(OWNER, "wnj:v1:bot-job:YWJj") is None
    assert models.get_native_job(OWNER, "wnj:v1:document-operation:not*route-safe") is None
    assert len(models.encode_native_job_id("document-operation", "a" * 100)) == 160
    with pytest.raises(ValueError):
        models.encode_native_job_id("document-operation", "a" * 101)


def test_subtitle_asset_projection_keeps_validate_outputless_and_hides_private_fields(monkeypatch) -> None:
    connection = _database()
    _install_read_transaction(monkeypatch, connection)
    connection.executescript(
        """
        CREATE TABLE web_subtitle_asset_operations (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            state TEXT NOT NULL,
            source_format TEXT NOT NULL,
            target_format TEXT,
            cue_count INTEGER,
            timed_duration_ms INTEGER,
            storage_key TEXT,
            original_filename TEXT,
            content_type TEXT,
            byte_size INTEGER,
            sha256 TEXT,
            semantic_sha256 TEXT,
            created_at TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL,
            source_asset_id TEXT,
            request_fingerprint TEXT,
            failure_code TEXT
        );
        """
    )
    connection.executemany(
        """INSERT INTO web_subtitle_asset_operations
           (id, account_id, kind, state, source_format, target_format, cue_count,
            timed_duration_ms, storage_key, original_filename, content_type,
            byte_size, sha256, semantic_sha256, created_at, queued_at, started_at,
            completed_at, updated_at, source_asset_id, request_fingerprint, failure_code)
           VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "subtitle-convert-owner", OWNER, "subtitle_convert", "srt", "vtt", 2,
                3000, VALID_SUBTITLE_KEY, r"D:\private\output.vtt", "text/vtt", 80,
                VALID_SHA256, VALID_SHA256, NOW, NOW, NOW, NOW,
                "2026-07-18T00:00:00+00:00", "asset-owner", SECRET, SECRET,
            ),
            (
                "subtitle-validate-owner", OWNER, "subtitle_validate", "vtt", None, 1,
                1000, None, None, None, None, None, VALID_SHA256, NOW, NOW, NOW, NOW,
                "2026-07-18T00:01:00+00:00", "asset-owner", SECRET, SECRET,
            ),
        ],
    )
    monkeypatch.setattr(models, "subtitle_asset_operations_enabled", lambda: True)
    monkeypatch.setattr(models, "verified_subtitle_asset_output_available", lambda **_kwargs: True)

    jobs = models.list_native_jobs(OWNER)
    convert_id = models.encode_native_job_id("subtitle-asset-operation", "subtitle-convert-owner")
    validate_id = models.encode_native_job_id("subtitle-asset-operation", "subtitle-validate-owner")
    projected = {job["id"]: job for job in jobs}

    assert projected[convert_id]["output"] == {
        "filename": "toan-aas-subtitle.vtt",
        "content_type": "text/vtt",
        "byte_size": 80,
    }
    assert projected[validate_id]["output"] is None
    serialized = json.dumps(projected, sort_keys=True)
    for forbidden in (SECRET, "asset-owner", "storage_key", "semantic_sha256", "D:\\private"):
        assert forbidden not in serialized


def test_audio_asset_projection_keeps_inspect_outputless_and_requires_verified_transform(monkeypatch) -> None:
    connection = _database()
    _install_read_transaction(monkeypatch, connection)
    connection.executescript(
        """
        CREATE TABLE web_audio_asset_operations (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            source_asset_id TEXT,
            project_id TEXT,
            kind TEXT NOT NULL,
            target_format TEXT,
            normalization_profile TEXT,
            state TEXT NOT NULL,
            source_sha256 TEXT,
            source_byte_size INTEGER,
            source_lifecycle_revision INTEGER,
            source_format TEXT,
            source_duration_ms INTEGER,
            source_channels INTEGER,
            source_sample_rate INTEGER,
            source_codec TEXT,
            output_duration_ms INTEGER,
            output_channels INTEGER,
            output_sample_rate INTEGER,
            output_codec TEXT,
            storage_key TEXT,
            original_filename TEXT,
            content_type TEXT,
            byte_size INTEGER,
            sha256 TEXT,
            failure_code TEXT,
            created_at TEXT NOT NULL,
            queued_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    connection.executemany(
        """INSERT INTO web_audio_asset_operations
           (id, account_id, source_asset_id, project_id, kind, target_format,
            normalization_profile, state, source_sha256, source_byte_size,
            source_lifecycle_revision, source_format, source_duration_ms,
            source_channels, source_sample_rate, source_codec,
            output_duration_ms, output_channels, output_sample_rate,
            output_codec, storage_key, original_filename, content_type,
            byte_size, sha256, failure_code, created_at, queued_at, started_at,
            completed_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "audio-normalize-owner", OWNER, "audio-source-owner", "project-owner",
                "audio_normalize", "m4a", "speech_safe_v1", "completed",
                VALID_SHA256, 200, 4, "wav", 3_000, 1, 48_000, SECRET,
                2_980, 1, 48_000, "aac", VALID_AUDIO_KEY, r"D:\\private\\output.m4a",
                "audio/mp4", 80, VALID_SHA256, SECRET, NOW, NOW, NOW, NOW,
                "2026-07-18T01:00:00+00:00",
            ),
            (
                "audio-inspect-owner", OWNER, "audio-source-owner", None,
                "audio_inspect", None, None, "completed",
                VALID_SHA256, 200, 4, "mp3", 1_500, 2, 44_100, SECRET,
                None, None, None, None, None, None, None, None, None, SECRET,
                NOW, NOW, NOW, NOW, "2026-07-18T01:01:00+00:00",
            ),
        ],
    )
    monkeypatch.setattr(models, "subtitle_asset_operations_enabled", lambda: False)
    monkeypatch.setattr(models, "frame_video_operations_enabled", lambda: False)
    monkeypatch.setattr(models, "video_transform_operations_enabled", lambda: False)
    monkeypatch.setattr(models, "audio_asset_operations_enabled", lambda: True)
    monkeypatch.setattr(models, "verified_audio_asset_output_available", lambda **_kwargs: True)

    jobs = models.list_native_jobs(OWNER)
    normalize_id = models.encode_native_job_id("audio-asset-operation", "audio-normalize-owner")
    inspect_id = models.encode_native_job_id("audio-asset-operation", "audio-inspect-owner")
    projected = {job["id"]: job for job in jobs}

    assert projected[normalize_id]["output"] == {
        "filename": "toan-aas-audio.m4a",
        "content_type": "audio/mp4",
        "byte_size": 80,
    }
    assert projected[normalize_id]["summary"]["normalization_profile"] == "speech_safe_v1"
    assert projected[inspect_id]["output"] is None
    completed_outputs = models.list_native_completed_outputs(OWNER)
    assert normalize_id in {item["id"] for item in completed_outputs}
    assert inspect_id not in {item["id"] for item in completed_outputs}

    serialized = json.dumps(projected, sort_keys=True)
    for forbidden in (SECRET, "audio-source-owner", "project-owner", "storage_key", "source_sha256", "D:\\private"):
        assert forbidden not in serialized
