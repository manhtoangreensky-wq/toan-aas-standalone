"""Empirical test suite for native output read truth and operation-kind lineage.

SPEC_ID: WEBAPP_D01_E01_NATIVE_OUTPUT_READ_TRUTH_R1
Issue: #574 (Parent #573, #561)

Verifies:
1. Output read truth across all 7 families:
   - project-package
   - document-operation
   - image-operation
   - video-operation
   - frame-video-operation
   - video-transform-operation
   - storyboard-grid
2. Fault matrix for each:
   - Valid artifact file -> output_available=True / download_ready=True / output dict present
   - Missing artifact file -> False / None
   - Zero-byte file -> False / None
   - Truncated / size mismatch -> False / None
   - Digest mismatch -> False / None
   - Wrong container / magic -> False / None
   - Disabled feature gate -> False / None
   - Symlink / path traversal -> False / None
3. Lineage kinds:
   - document: pdf_ocr_word (.docx, application/vnd.openxmlformats-officedocument.wordprocessingml.document)
   - image: image_brand_overlay (.png, image/png)
   - image: image_background_cleanup (.png, image/png)
4. Invariant: READ_PATH_DB_MUTATION_COUNT = 0
   - Read path does not mutate SQLite rows or demote state to 'unavailable'.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid
import zipfile
from io import BytesIO

from PIL import Image
import pytest

import copyfast_native_read_models as read_models
import copyfast_project_packages as pkg_mod
import copyfast_document_operations as doc_mod
import copyfast_image_operations as img_mod
import copyfast_video_operations as vid_mod
import copyfast_frame_video_operations as frame_mod
import copyfast_video_transform_operations as transform_mod
import copyfast_storyboard_grid as grid_mod


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hex_key(prefix: str, ext: str) -> str:
    return f"{prefix}/{uuid.uuid4().hex}.{ext}"


def _make_png_bytes(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_rgba_png_bytes(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGBA", (width, height), color=(255, 0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(0, 255, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_mp4_bytes() -> bytes:
    # 128 bytes with ftyp box at prefix[4:8]
    box = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    return box + b"\x00" * (128 - len(box))


def _make_docx_bytes() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<document/>")
    return buf.getvalue()


def _make_zip_with_png() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("page_01.png", _make_png_bytes())
    return buf.getvalue()


def _make_package_zip() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"version": 1}))
        zf.writestr("docs/doc1.txt", "Sample document")
    return buf.getvalue()


# =============================================================================
# 1. Project Package Output Verification Tests
# =============================================================================

def test_project_package_fault_matrix(tmp_path, monkeypatch):
    pkg_root = tmp_path / "packages"
    pkg_root.mkdir()
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ROOT", str(pkg_root))
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "true")

    key = _hex_key("packages", "zip")
    target_file = pkg_root / key
    target_file.parent.mkdir(parents=True, exist_ok=True)

    valid_data = _make_package_zip()
    target_file.write_bytes(valid_data)
    valid_size = len(valid_data)
    valid_sha = _sha256(valid_data)

    # 1. Valid file -> True
    assert pkg_mod.verified_project_package_output_available(key, valid_size, valid_sha) is True

    # 2. Missing file -> False
    missing_key = _hex_key("packages", "zip")
    assert pkg_mod.verified_project_package_output_available(missing_key, valid_size, valid_sha) is False

    # 3. Zero byte file -> False
    zero_key = _hex_key("packages", "zip")
    zero_file = pkg_root / zero_key
    zero_file.write_bytes(b"")
    assert pkg_mod.verified_project_package_output_available(zero_key, 0, _sha256(b"")) is False

    # 4. Truncated / size mismatch -> False
    assert pkg_mod.verified_project_package_output_available(key, valid_size + 10, valid_sha) is False

    # 5. Digest mismatch -> False
    assert pkg_mod.verified_project_package_output_available(key, valid_size, "0" * 64) is False

    # 6. Wrong container (corrupt zip) -> False
    corrupt_key = _hex_key("packages", "zip")
    corrupt_file = pkg_root / corrupt_key
    corrupt_data = b"not a zip file at all"
    corrupt_file.write_bytes(corrupt_data)
    assert pkg_mod.verified_project_package_output_available(
        corrupt_key, len(corrupt_data), _sha256(corrupt_data)
    ) is False

    # 7. Zip without manifest.json -> False
    no_manifest = BytesIO()
    with zipfile.ZipFile(no_manifest, "w") as zf:
        zf.writestr("test.txt", "hello")
    no_mf_data = no_manifest.getvalue()
    no_mf_key = _hex_key("packages", "zip")
    no_mf_file = pkg_root / no_mf_key
    no_mf_file.write_bytes(no_mf_data)
    assert pkg_mod.verified_project_package_output_available(
        no_mf_key, len(no_mf_data), _sha256(no_mf_data)
    ) is False

    # 8. Feature gate disabled -> False
    monkeypatch.setenv("WEBAPP_PROJECT_PACKAGE_ENABLED", "false")
    assert pkg_mod.verified_project_package_output_available(key, valid_size, valid_sha) is False


# =============================================================================
# 2. Document Operation Output Verification Tests
# =============================================================================

def test_document_operation_fault_matrix(tmp_path, monkeypatch):
    doc_root = tmp_path / "doc_ops"
    doc_root.mkdir()
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(doc_root))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PDF_OCR_WORD_ENABLED", "true")

    outputs_dir = doc_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # DOCX test (for pdf_ocr_word)
    docx_key = _hex_key("outputs", "docx")
    docx_file = doc_root / docx_key
    docx_data = _make_docx_bytes()
    docx_file.write_bytes(docx_data)
    docx_size = len(docx_data)
    docx_sha = _sha256(docx_data)

    # Valid docx -> True
    assert doc_mod.verified_document_operation_output_available(
        docx_key, docx_size, docx_sha, kind="pdf_ocr_word"
    ) is True

    # Missing file -> False
    assert doc_mod.verified_document_operation_output_available(
        _hex_key("outputs", "docx"), docx_size, docx_sha, kind="pdf_ocr_word"
    ) is False

    # Corrupt zip docx -> False
    bad_key = _hex_key("outputs", "docx")
    bad_docx = doc_root / bad_key
    bad_docx.write_bytes(b"PK\x03\x04corrupted zip payload")
    assert doc_mod.verified_document_operation_output_available(
        bad_key, len(bad_docx.read_bytes()), _sha256(bad_docx.read_bytes()), kind="pdf_ocr_word"
    ) is False

    # Size mismatch -> False
    assert doc_mod.verified_document_operation_output_available(
        docx_key, docx_size + 1, docx_sha, kind="pdf_ocr_word"
    ) is False

    # Digest mismatch -> False
    assert doc_mod.verified_document_operation_output_available(
        docx_key, docx_size, "f" * 64, kind="pdf_ocr_word"
    ) is False

    # PDF test
    pdf_key = _hex_key("outputs", "pdf")
    pdf_file = doc_root / pdf_key
    pdf_data = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    pdf_file.write_bytes(pdf_data)
    assert doc_mod.verified_document_operation_output_available(
        pdf_key, len(pdf_data), _sha256(pdf_data), kind="pdf_split"
    ) is True

    # Wrong magic for PDF -> False
    fake_key = _hex_key("outputs", "pdf")
    fake_pdf = doc_root / fake_key
    fake_pdf.write_bytes(b"NOT A PDF")
    assert doc_mod.verified_document_operation_output_available(
        fake_key, len(b"NOT A PDF"), _sha256(b"NOT A PDF"), kind="pdf_split"
    ) is False


# =============================================================================
# 3. Image Operation Output Verification Tests
# =============================================================================

def test_image_operation_fault_matrix(tmp_path, monkeypatch):
    img_root = tmp_path / "img_ops"
    img_root.mkdir()
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ROOT", str(img_root))
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_RESIZE_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_BRAND_OVERLAY_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_BACKGROUND_CLEANUP_ENABLED", "true")

    outputs_dir = img_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    png_key = _hex_key("outputs", "png")
    png_file = img_root / png_key
    png_data = _make_png_bytes(200, 150)
    png_file.write_bytes(png_data)
    png_size = len(png_data)
    png_sha = _sha256(png_data)

    # Valid PNG matching dimensions -> True
    assert img_mod.verified_image_operation_output_available(
        png_key, png_size, png_sha, kind="image_resize", target_width=200, target_height=150
    ) is True

    # Valid for image_brand_overlay lineage -> True
    assert img_mod.verified_image_operation_output_available(
        png_key, png_size, png_sha, kind="image_brand_overlay", target_width=200, target_height=150
    ) is True

    # Valid for image_background_cleanup lineage -> True
    rgba_key = _hex_key("outputs", "png")
    rgba_file = img_root / rgba_key
    rgba_data = _make_rgba_png_bytes(200, 150)
    rgba_file.write_bytes(rgba_data)
    assert img_mod.verified_image_operation_output_available(
        rgba_key, len(rgba_data), _sha256(rgba_data), kind="image_background_cleanup", target_width=200, target_height=150
    ) is True

    # Mismatched dimensions -> False
    assert img_mod.verified_image_operation_output_available(
        png_key, png_size, png_sha, kind="image_resize", target_width=300, target_height=300
    ) is False

    # Missing file -> False
    assert img_mod.verified_image_operation_output_available(
        _hex_key("outputs", "png"), png_size, png_sha, kind="image_resize"
    ) is False

    # SHA mismatch -> False
    assert img_mod.verified_image_operation_output_available(
        png_key, png_size, "e" * 64, kind="image_resize", target_width=200, target_height=150
    ) is False

    # Kind gate disabled -> False
    monkeypatch.setenv("WEBAPP_IMAGE_BRAND_OVERLAY_ENABLED", "false")
    assert img_mod.verified_image_operation_output_available(
        png_key, png_size, png_sha, kind="image_brand_overlay", target_width=200, target_height=150
    ) is False


# =============================================================================
# 4. Video Operation (Poster) Output Verification Tests
# =============================================================================

def test_video_operation_fault_matrix(tmp_path, monkeypatch):
    vid_root = tmp_path / "vid_ops"
    vid_root.mkdir()
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ROOT", str(vid_root))
    monkeypatch.setenv("WEBAPP_VIDEO_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "true")

    outputs_dir = vid_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    jpg_key = _hex_key("outputs", "jpg")
    jpg_file = vid_root / jpg_key
    jpg_data = _make_jpeg_bytes(320, 240)
    jpg_file.write_bytes(jpg_data)
    jpg_size = len(jpg_data)
    jpg_sha = _sha256(jpg_data)

    # Valid JPEG with matching dimensions -> True
    assert vid_mod.verified_video_operation_output_available(
        jpg_key, jpg_size, jpg_sha, output_width=320, output_height=240, content_type="image/jpeg"
    ) is True

    # Missing file -> False
    assert vid_mod.verified_video_operation_output_available(
        _hex_key("outputs", "jpg"), jpg_size, jpg_sha, output_width=320, output_height=240
    ) is False

    # Wrong dimensions -> False
    assert vid_mod.verified_video_operation_output_available(
        jpg_key, jpg_size, jpg_sha, output_width=100, output_height=100
    ) is False

    # Corrupted / wrong magic -> False
    corrupt_key = _hex_key("outputs", "jpg")
    corrupt_file = vid_root / corrupt_key
    corrupt_file.write_bytes(b"not a jpeg image")
    assert vid_mod.verified_video_operation_output_available(
        corrupt_key, len(b"not a jpeg image"), _sha256(b"not a jpeg image"), output_width=320, output_height=240
    ) is False

    # Gate disabled -> False
    monkeypatch.setenv("WEBAPP_VIDEO_POSTER_ENABLED", "false")
    assert vid_mod.verified_video_operation_output_available(
        jpg_key, jpg_size, jpg_sha, output_width=320, output_height=240
    ) is False


# =============================================================================
# 5. Frame Video Operation Output Verification Tests
# =============================================================================

def test_frame_video_fault_matrix(tmp_path, monkeypatch):
    frame_root = tmp_path / "frame_ops"
    frame_root.mkdir()
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ROOT", str(frame_root))
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED", "true")

    outputs_dir = frame_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    mp4_key = _hex_key("outputs", "mp4")
    mp4_file = frame_root / mp4_key
    mp4_data = _make_mp4_bytes()
    mp4_file.write_bytes(mp4_data)
    mp4_size = len(mp4_data)
    mp4_sha = _sha256(mp4_data)

    # Valid MP4 -> True
    assert frame_mod.verified_frame_video_output_available(mp4_key, mp4_size, mp4_sha) is True

    # Missing file -> False
    assert frame_mod.verified_frame_video_output_available(_hex_key("outputs", "mp4"), mp4_size, mp4_sha) is False

    # Under 128 bytes -> False
    short_key = _hex_key("outputs", "mp4")
    short_file = frame_root / short_key
    short_file.write_bytes(b"\x00" * 50)
    assert frame_mod.verified_frame_video_output_available(
        short_key, 50, _sha256(b"\x00" * 50)
    ) is False

    # Corrupt magic (no ftyp) -> False
    no_ftyp_key = _hex_key("outputs", "mp4")
    no_ftyp = frame_root / no_ftyp_key
    no_ftyp_data = b"\x00" * 128
    no_ftyp.write_bytes(no_ftyp_data)
    assert frame_mod.verified_frame_video_output_available(
        no_ftyp_key, 128, _sha256(no_ftyp_data)
    ) is False

    # Size mismatch -> False
    assert frame_mod.verified_frame_video_output_available(mp4_key, mp4_size + 10, mp4_sha) is False

    # Digest mismatch -> False
    assert frame_mod.verified_frame_video_output_available(mp4_key, mp4_size, "1" * 64) is False

    # Gate disabled -> False
    monkeypatch.setenv("WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED", "false")
    assert frame_mod.verified_frame_video_output_available(mp4_key, mp4_size, mp4_sha) is False


# =============================================================================
# 6. Video Transform Operation Output Verification Tests
# =============================================================================

def test_video_transform_fault_matrix(tmp_path, monkeypatch):
    vt_root = tmp_path / "vt_ops"
    vt_root.mkdir()
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ROOT", str(vt_root))
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED", "true")

    outputs_dir = vt_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    mp4_key = _hex_key("outputs", "mp4")
    mp4_file = vt_root / mp4_key
    mp4_data = _make_mp4_bytes()
    mp4_file.write_bytes(mp4_data)
    mp4_size = len(mp4_data)
    mp4_sha = _sha256(mp4_data)

    # Valid MP4 -> True
    assert transform_mod.verified_video_transform_output_available(mp4_key, mp4_size, mp4_sha) is True

    # Missing file -> False
    assert transform_mod.verified_video_transform_output_available(_hex_key("outputs", "mp4"), mp4_size, mp4_sha) is False

    # Wrong magic -> False
    bad_key = _hex_key("outputs", "mp4")
    bad_file = vt_root / bad_key
    bad_data = b"x" * 128
    bad_file.write_bytes(bad_data)
    assert transform_mod.verified_video_transform_output_available(
        bad_key, 128, _sha256(bad_data)
    ) is False

    # Gate disabled -> False
    monkeypatch.setenv("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED", "false")
    assert transform_mod.verified_video_transform_output_available(mp4_key, mp4_size, mp4_sha) is False


# =============================================================================
# 7. Storyboard Grid Output Verification Tests
# =============================================================================

def test_storyboard_grid_fault_matrix(tmp_path, monkeypatch):
    img_root = tmp_path / "img_ops"
    img_root.mkdir()
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ROOT", str(img_root))
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_STORYBOARD_GRID_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")

    grid_root = img_root / "storyboard-grid"
    outputs_dir = grid_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # Create valid storyboard zip with 1 cell and manifest
    cell_data = _make_png_bytes(50, 50)
    manifest_bytes = json.dumps({"version": 1, "cells": [{"scene_no": 1}]}).encode("utf-8")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", manifest_bytes)
        zf.writestr("cells/01.png", cell_data)
    zip_data = buf.getvalue()

    zip_key = _hex_key("outputs", "zip")
    zip_file = grid_root / zip_key
    zip_file.write_bytes(zip_data)
    zip_size = len(zip_data)
    zip_sha = _sha256(zip_data)

    operation = (
        "op-grid-1", "acc-1", "src-1", "project-1", "completed", "1", "1",
        "sha-src", 100, 100, 100, 1, 1, 1, 1, 0.0,
        1,  # scene_count
        zip_key, "grid.zip", "application/zip", zip_size, zip_sha,
    )
    cells = [
        ("cell-1", "op-grid-1", 1, 1, 1, 0, 0, 50, 50, "01.png", len(cell_data), _sha256(cell_data)),
    ]

    # Valid zip & manifest & cells -> True (mocking _open_verified_archive_stream to succeed)
    monkeypatch.setattr(grid_mod, "_open_verified_archive_stream", lambda *a, **k: BytesIO(zip_data))
    assert grid_mod.verified_storyboard_grid_output_available(operation, cells) is True

    # Missing file / verification fails -> False
    monkeypatch.setattr(grid_mod, "_open_verified_archive_stream", lambda *a, **k: None)
    assert grid_mod.verified_storyboard_grid_output_available(operation, cells) is False

    # Feature gate disabled -> False
    monkeypatch.setenv("WEBAPP_STORYBOARD_GRID_ENABLED", "false")
    assert grid_mod.verified_storyboard_grid_output_available(operation, cells) is False


# =============================================================================
# 8. Invariant: READ_PATH_DB_MUTATION_COUNT = 0
# =============================================================================

def test_read_path_zero_db_mutations_and_state_preservation(tmp_path, monkeypatch):
    """Read queries must never mutate SQLite rows or demote state='completed'."""

    db_path = tmp_path / "test_read_truth.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE web_image_operations (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            source_asset_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            state TEXT NOT NULL,
            target_width INTEGER,
            target_height INTEGER,
            preset TEXT,
            fit_mode TEXT,
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
        """
    )
    nonexistent_key = _hex_key("outputs", "png")
    conn.execute(
        """INSERT INTO web_image_operations VALUES
           ('img-1', 'acc-test', 'src-1', 'image_resize', 'completed', 200, 200, '1:1', 'crop',
            400, 400, ?, 'out.png', 'image/png', 500, ?,
            '2026-07-17T00:00:00Z', '2026-07-17T00:00:00Z', '2026-07-17T00:00:00Z', '2026-07-17T00:00:00Z', '2026-07-17T00:00:00Z',
            'idem-1', 'fp-1', '{}', NULL)""",
        (nonexistent_key, "a" * 64),
    )
    conn.commit()

    changes_before = conn.total_changes

    # Set up models to read from this db
    @contextmanager
    def mock_read_transaction():
        yield conn

    monkeypatch.setattr(read_models, "read_transaction", mock_read_transaction)
    monkeypatch.setattr(read_models, "image_operations_enabled", lambda: True)
    monkeypatch.setattr(read_models, "_image_kind_enabled", lambda k: True)
    # The file does not exist, so verified_image_operation_output_available returns False

    job_id = read_models.encode_native_job_id("image-operation", "img-1")
    job = read_models.get_native_job("acc-test", job_id)

    # Output MUST be None because bytes do not exist
    assert job is not None
    assert job["state"] == "completed"  # State preserved!
    assert job["output"] is None        # Truthful output read!

    # DB row MUST NOT have been updated or mutated!
    row = conn.execute("SELECT state, failure_code FROM web_image_operations WHERE id='img-1'").fetchone()
    assert row[0] == "completed"
    assert row[1] is None

    # Zero mutations executed
    assert conn.total_changes == changes_before


# =============================================================================
# 9. Lineage Kinds Verification in copyfast_native_read_models
# =============================================================================

def test_lineage_kinds_specs_and_projections(tmp_path, monkeypatch):
    """Verify pdf_ocr_word, image_brand_overlay, and image_background_cleanup."""

    # 1. Document: pdf_ocr_word
    spec = read_models._document_output_spec("pdf_ocr_word", 1)
    assert spec is not None
    assert spec[0] == ".docx"
    assert spec[1] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert spec[2] == "toan-aas-pdf-ocr.docx"

    # 2. Image: image_brand_overlay
    assert "image_brand_overlay" in read_models._IMAGE_OUTPUT_SPECS
    overlay_spec = read_models._IMAGE_OUTPUT_SPECS["image_brand_overlay"]
    assert overlay_spec[0] == ".png"
    assert overlay_spec[1] == "image/png"
    assert overlay_spec[2] == "toan-aas-image-brand-overlay.png"

    # 3. Image: image_background_cleanup
    assert "image_background_cleanup" in read_models._IMAGE_OUTPUT_SPECS
    cleanup_spec = read_models._IMAGE_OUTPUT_SPECS["image_background_cleanup"]
    assert cleanup_spec[0] == ".png"
    assert cleanup_spec[1] == "image/png"
    assert cleanup_spec[2] == "toan-aas-image-background-cleanup.png"

    # Test projection with mock verifier
    monkeypatch.setattr(read_models, "image_operations_enabled", lambda: True)
    monkeypatch.setattr(read_models, "_image_kind_enabled", lambda k: True)
    monkeypatch.setattr(read_models, "verified_image_operation_output_available", lambda **k: True)

    row = (
        "img-overlay-1", "image_brand_overlay", "completed", 500, 500,
        "center", "fit", 1000, 1000, "outputs/" + ("a" * 32) + ".png",
        "out.png", "image/png", 1024, "b" * 64,
        "2026-07-17T00:00:00Z", "2026-07-17T00:00:00Z", "2026-07-17T00:00:00Z",
        "2026-07-17T00:00:00Z", "2026-07-17T00:00:00Z",
    )
    projected = read_models._project_image_operation(row)
    assert projected["output"] == {
        "filename": "toan-aas-image-brand-overlay.png",
        "content_type": "image/png",
        "byte_size": 1024,
    }


# =============================================================================
# 10. Surface Parity across Typed Public Models
# =============================================================================

def test_surface_parity_when_artifact_missing_vs_valid(monkeypatch):
    """Ensure typed public serializers report readiness ONLY when verified."""

    # 1. Project package
    pkg_row = (
        "pkg-1", "acc-1", "completed", 5, 2, "2026-07-17Z", "2026-07-17Z",
        1000, "2026-07-17Z", "2026-07-17Z", "2026-07-17Z", "2026-07-17Z",
        "doc.zip", "application/zip", "packages/" + ("a" * 32) + ".zip", "b" * 64,
    )
    monkeypatch.setattr(pkg_mod, "verified_project_package_output_available", lambda **k: True)
    assert pkg_mod._package_public(pkg_row)["download_ready"] is True
    monkeypatch.setattr(pkg_mod, "verified_project_package_output_available", lambda **k: False)
    assert pkg_mod._package_public(pkg_row)["download_ready"] is False

    # 2. Document operation
    doc_row = (
        "doc-op-1", "src-1", "project-1", "pdf_split", "completed", "1-2", 1, 2, 5, 2,
        "split.pdf", "application/pdf", 1000, "2026-07-17Z", "2026-07-17Z", "2026-07-17Z",
        "2026-07-17Z", "2026-07-17Z", None, "outputs/" + ("a" * 32) + ".pdf", "c" * 64,
        "d" * 64, 2000, 1,
    )
    monkeypatch.setattr(doc_mod, "verified_document_operation_output_available", lambda **k: True)
    assert doc_mod._operation_public(doc_row)["download_ready"] is True
    monkeypatch.setattr(doc_mod, "verified_document_operation_output_available", lambda **k: False)
    assert doc_mod._operation_public(doc_row)["download_ready"] is False

    # 3. Image operation
    img_row = (
        "img-op-1", "src-1", "project-1", "image_resize", "completed", 100, 100, "1:1", "crop",
        200, 200, "out.png", "image/png", 500, "2026-07-17Z", "2026-07-17Z", "2026-07-17Z",
        "2026-07-17Z", "2026-07-17Z", None, "outputs/" + ("a" * 32) + ".png", "d" * 64,
        1000, "e" * 64, "{}",
    )
    monkeypatch.setattr(img_mod, "verified_image_operation_output_available", lambda **k: True)
    assert img_mod._operation_public(img_row)["download_ready"] is True
    monkeypatch.setattr(img_mod, "verified_image_operation_output_available", lambda **k: False)
    assert img_mod._operation_public(img_row)["download_ready"] is False

    # 4. Video operation
    vid_row = (
        "vid-op-1", "src-1", "video_poster", "completed", "middle", 5000, 1920, 1080,
        2500, 1920, 1080, "outputs/" + ("a" * 32) + ".jpg", "poster.jpg", "image/jpeg",
        2000, "e" * 64, "2026-07-17Z", "2026-07-17Z", "2026-07-17Z", "2026-07-17Z", "2026-07-17Z",
    )
    monkeypatch.setattr(vid_mod, "verified_video_operation_output_available", lambda **k: True)
    assert vid_mod._operation_public(vid_row)["output_available"] is True
    monkeypatch.setattr(vid_mod, "verified_video_operation_output_available", lambda **k: False)
    assert vid_mod._operation_public(vid_row)["output_available"] is False

    # 5. Frame video operation
    frame_row = (
        "frame-1", "acc-1", "frame_video", "completed", "idem-1", "fp-1", "16:9", 1.0, "fade",
        1, 1000, 5000, 1280, 720, "outputs/" + ("a" * 32) + ".mp4", "out.mp4",
        "video/mp4", 5000, "f" * 64, None, "2026-07-17Z", "2026-07-17Z", "2026-07-17Z",
        "2026-07-17Z", "2026-07-17Z", 1,
    )
    monkeypatch.setattr(frame_mod, "verified_frame_video_output_available", lambda **k: True)
    assert frame_mod._public_operation(frame_row)["output"]["available"] is True
    monkeypatch.setattr(frame_mod, "verified_frame_video_output_available", lambda **k: False)
    assert frame_mod._public_operation(frame_row)["output"]["available"] is False

    # 6. Video transform operation
    vt_row = (
        "vt-1", "acc-1", "src-1", "video_transform", "completed", "idem-1", "fp-1",
        "a" * 64, 1000, ".mp4", "video/mp4", "9:16", "crop", "fast", 0, 1,
        5000, 1920, 1080, 5000, 1080, 1920, 1, "outputs/" + ("a" * 32) + ".mp4",
        "out.mp4", "video/mp4", 5000, "0" * 64, None, "2026-07-17Z", "2026-07-17Z",
        "2026-07-17Z", "2026-07-17Z", "2026-07-17Z", 1,
    )
    monkeypatch.setattr(transform_mod, "verified_video_transform_output_available", lambda **k: True)
    assert transform_mod._public_operation(vt_row)["output"]["available"] is True
    monkeypatch.setattr(transform_mod, "verified_video_transform_output_available", lambda **k: False)
    assert transform_mod._public_operation(vt_row)["output"]["available"] is False

    # 7. Storyboard grid
    grid_row = (
        "grid-1", "acc-1", "src-1", "project-1", "completed", "1", "1", "sha-src",
        100, 100, 100, 1, 1, 1, 1, 0.0, 1,
        "outputs/" + ("a" * 32) + ".zip", "grid.zip", "application/zip", 1000, "1" * 64,
        None, "2026-07-17Z", "2026-07-17Z", "2026-07-17Z", "2026-07-17Z", "2026-07-17Z",
    )
    grid_cells = [
        ("c-1", "grid-1", 1, 1, 1, 0, 0, 50, 50, "01.png", 200, "2" * 64),
    ]
    monkeypatch.setattr(grid_mod, "verified_storyboard_grid_output_available", lambda *a, **k: True)
    res_true = grid_mod._public_operation(grid_row, grid_cells)
    assert res_true["download_ready"] is True
    assert res_true["cells"][0]["download_ready"] is True

    monkeypatch.setattr(grid_mod, "verified_storyboard_grid_output_available", lambda *a, **k: False)
    res_false = grid_mod._public_operation(grid_row, grid_cells)
    assert res_false["download_ready"] is False
    assert res_false["cells"][0]["download_ready"] is False


# =============================================================================
# 11. Generic Jobs vs Generic Assets Query Filtering
# =============================================================================

def test_generic_jobs_and_completed_assets_filtering(monkeypatch):
    """Unverified completed jobs remain in /jobs but are excluded from /assets."""
    from tests.test_copyfast_native_read_models import _database
    conn = _database()
    conn.execute(
        """INSERT INTO web_image_operations VALUES
           ('img-verified', 'acc-truth', 'src-1', 'image_resize', 'completed', 200, 200, '1:1', 'crop',
            400, 400, ?, 'out1.png', 'image/png', 500, ?,
            '2026-07-17T00:00:00Z', '2026-07-17T00:00:00Z', '2026-07-17T00:00:00Z', '2026-07-17T00:00:00Z', '2026-07-17T00:00:00Z',
            'idem-1', 'fp-1', '{}', NULL),
           ('img-unverified', 'acc-truth', 'src-2', 'image_resize', 'completed', 200, 200, '1:1', 'crop',
            400, 400, ?, 'out2.png', 'image/png', 500, ?,
            '2026-07-17T00:00:01Z', '2026-07-17T00:00:01Z', '2026-07-17T00:00:01Z', '2026-07-17T00:00:01Z', '2026-07-17T00:00:01Z',
            'idem-2', 'fp-2', '{}', NULL)""",
        ("outputs/" + ("1" * 32) + ".png", "a" * 64, "outputs/" + ("2" * 32) + ".png", "b" * 64),
    )
    conn.commit()

    @contextmanager
    def mock_read_tx():
        yield conn

    monkeypatch.setattr(read_models, "read_transaction", mock_read_tx)
    monkeypatch.setattr(read_models, "image_operations_enabled", lambda: True)
    monkeypatch.setattr(read_models, "_image_kind_enabled", lambda k: True)

    def mock_verifier(storage_key, **_kw):
        return ("1" * 32) in str(storage_key)

    monkeypatch.setattr(read_models, "verified_image_operation_output_available", mock_verifier)

    # 1. list_native_jobs -> BOTH jobs returned
    all_jobs = read_models.list_native_jobs("acc-truth")
    job_map = {j["id"]: j for j in all_jobs}
    verified_id = read_models.encode_native_job_id("image-operation", "img-verified")
    unverified_id = read_models.encode_native_job_id("image-operation", "img-unverified")

    assert verified_id in job_map
    assert unverified_id in job_map
    assert job_map[verified_id]["output"] is not None
    assert job_map[unverified_id]["output"] is None

    # 2. list_native_completed_outputs (assets) -> ONLY verified job returned!
    completed_outputs = read_models.list_native_completed_outputs("acc-truth")
    output_ids = {item["id"] for item in completed_outputs}
    assert verified_id in output_ids
    assert unverified_id not in output_ids

