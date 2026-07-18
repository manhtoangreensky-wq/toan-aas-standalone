"""Security and output contracts for Web-native PDF Split, Merge and Optimize."""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import sqlite3
import sys
from zipfile import ZipFile

from docx import Document
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject, TextStringObject


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(
    tmp_path,
    monkeypatch,
    *,
    image_to_pdf_enabled: bool = True,
    pdf_to_images_enabled: bool = True,
    pdf_to_word_enabled: bool = True,
) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-document-operations-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-document-operations-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "private-document-outputs"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OCR_PDF_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_TO_PDF_ENABLED", "true" if image_to_pdf_enabled else "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_IMAGES_ENABLED", "true" if pdf_to_images_enabled else "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_WORD_ENABLED", "true" if pdf_to_word_enabled else "false")
    monkeypatch.delenv("WEBAPP_PROJECT_PACKAGE_ENABLED", raising=False)
    monkeypatch.delenv("WEBAPP_PROJECT_PACKAGE_ROOT", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def register_and_login(client: TestClient, email: str) -> str:
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "PDF Split Owner"},
    ).status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def pdf_bytes(
    page_count: int,
    *,
    encrypted: bool = False,
    with_annotation: bool = False,
    page_size: tuple[int, int] = (144, 144),
    metadata_padding: int = 0,
) -> bytes:
    writer = PdfWriter()
    for page_index in range(page_count):
        page = writer.add_blank_page(width=page_size[0], height=page_size[1])
        if with_annotation and page_index == 0:
            annotation = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Annot"),
                    NameObject("/Subtype"): NameObject("/Text"),
                    NameObject("/Rect"): ArrayObject([NumberObject(8), NumberObject(8), NumberObject(36), NumberObject(36)]),
                    NameObject("/Contents"): TextStringObject("Untrusted interactive source annotation"),
                }
            )
            page[NameObject("/Annots")] = ArrayObject([writer._add_object(annotation)])
    if metadata_padding:
        writer.add_metadata(
            {
                "/Title": "Untrusted source metadata",
                "/Subject": "x" * metadata_padding,
            }
        )
    if encrypted:
        writer.encrypt("test-password")
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def _pdf_literal(value: str) -> bytes:
    """Minimal PDF literal escaping for deterministic selectable ASCII text."""
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1")


def pdf_text_bytes(pages: list[str], *, encrypted: bool = False) -> bytes:
    """Create small text-bearing PDFs without adding a renderer dependency."""
    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=360, height=360)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_ref = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        content = DecodedStreamObject()
        lines = [line for line in text.split("\n") if line]
        instructions = [b"BT", b"/F1 12 Tf", b"32 320 Td"]
        for index, line in enumerate(lines):
            if index:
                instructions.append(b"0 -18 Td")
            instructions.append(b"(" + _pdf_literal(line) + b") Tj")
        instructions.append(b"ET")
        content.set_data(b"\n".join(instructions))
        page[NameObject("/Contents")] = writer._add_object(content)
    if encrypted:
        writer.encrypt("test-password")
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def upload_pdf(client: TestClient, csrf: str, *, key: str, body: bytes | None = None, name: str = "source.pdf") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "PDF nguồn riêng tư"},
        files={"file": (name, body if body is not None else pdf_bytes(3), "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def split(client: TestClient, csrf: str, *, asset_id: str, page_range: str, key: str):
    return client.post(
        "/api/v1/document-operations/pdf-split",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "page_range": page_range, "idempotency_key": key},
    )


def merge(client: TestClient, csrf: str, *, asset_ids: list[str], key: str):
    return client.post(
        "/api/v1/document-operations/pdf-merge",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_ids": asset_ids, "idempotency_key": key},
    )


def optimize(client: TestClient, csrf: str, *, asset_id: str, key: str):
    return client.post(
        "/api/v1/document-operations/pdf-optimize",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "idempotency_key": key},
    )


def pdf_to_word(client: TestClient, csrf: str, *, asset_id: str, key: str):
    return client.post(
        "/api/v1/document-operations/pdf-to-word",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "idempotency_key": key},
    )


def pdf_to_images(client: TestClient, csrf: str, *, asset_id: str, key: str):
    return client.post(
        "/api/v1/document-operations/pdf-to-images",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "idempotency_key": key},
    )


def image_bytes(
    image_format: str,
    *,
    size: tuple[int, int] = (160, 100),
    color: tuple[int, ...] = (32, 144, 240),
) -> bytes:
    mode = "RGBA" if image_format.upper() == "PNG" and len(color) == 4 else "RGB"
    image = Image.new(mode, size, color)
    stream = BytesIO()
    try:
        image.save(stream, format=image_format, quality=95)
        return stream.getvalue()
    finally:
        image.close()


def animated_webp_bytes() -> bytes:
    first = Image.new("RGB", (96, 64), (240, 96, 64))
    second = Image.new("RGB", (96, 64), (64, 160, 240))
    stream = BytesIO()
    try:
        first.save(stream, format="WEBP", save_all=True, append_images=[second], duration=100, loop=0, quality=95)
        return stream.getvalue()
    finally:
        first.close()
        second.close()


def upload_image(
    client: TestClient,
    csrf: str,
    *,
    key: str,
    body: bytes,
    name: str,
    content_type: str,
) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Ảnh nguồn riêng tư"},
        files={"file": (name, body, content_type)},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def images_to_pdf(client: TestClient, csrf: str, *, asset_ids: list[str], key: str):
    return client.post(
        "/api/v1/document-operations/image-to-pdf",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_ids": asset_ids, "idempotency_key": key},
    )


def test_image_to_pdf_is_private_ordered_idempotent_and_verifies_the_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "image-to-pdf-owner@example.com")
        assert first.get("/documents/image-to-pdf").status_code == 200
        first_source = upload_image(
            first,
            csrf,
            key="image-to-pdf-source-jpeg-0001",
            body=image_bytes("JPEG", size=(160, 100), color=(32, 144, 240)),
            name="first.jpg",
            content_type="image/jpeg",
        )
        second_source = upload_image(
            first,
            csrf,
            key="image-to-pdf-source-png-0001",
            body=image_bytes("PNG", size=(240, 100), color=(240, 64, 128, 128)),
            name="second.png",
            content_type="image/png",
        )

        denied = first.post(
            "/api/v1/document-operations/image-to-pdf",
            json={"source_asset_ids": [first_source["id"], second_source["id"]], "idempotency_key": "image-to-pdf-denied-0001"},
        )
        assert denied.status_code == 403

        created = images_to_pdf(
            first,
            csrf,
            asset_ids=[first_source["id"], second_source["id"]],
            key="image-to-pdf-create-0001",
        )
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "image_to_pdf"
        assert operation["source_asset_id"] == first_source["id"]
        assert operation["source_count"] == 2
        assert operation["source_page_count"] == 2
        assert operation["output_page_count"] == 2
        assert operation["download_ready"] is True
        image_history = first.get("/api/v1/document-operations?kind=image_to_pdf&limit=100")
        assert image_history.status_code == 200
        assert [item["id"] for item in image_history.json()["data"]["items"]] == [operation["id"]]
        assert first.get("/api/v1/document-operations?kind=untrusted_operation").status_code == 422
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment"):
            assert forbidden not in created.text.lower()

        replay = images_to_pdf(
            first,
            csrf,
            asset_ids=[first_source["id"], second_source["id"]],
            key="image-to-pdf-create-0001",
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        reordered = images_to_pdf(
            first,
            csrf,
            asset_ids=[second_source["id"], first_source["id"]],
            key="image-to-pdf-create-0001",
        )
        assert reordered.status_code == 409

        download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert download.status_code == 200
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["referrer-policy"] == "no-referrer"
        assert download.headers["content-security-policy"] == "sandbox"
        assert "attachment" in download.headers["content-disposition"]
        output = PdfReader(BytesIO(download.content), strict=True)
        assert len(output.pages) == 2
        # 144dpi normalization makes the different source widths observable,
        # so this asserts server-preserved page order without exposing names.
        assert [round(float(page.mediabox.width), 3) for page in output.pages] == [80.0, 120.0]
        assert all("/Annots" not in page and "/AA" not in page for page in output.pages)

        detail = first.get(f"/api/v1/document-operations/{operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            source_rows = conn.execute(
                "SELECT source_asset_id, source_index FROM web_document_operation_sources WHERE operation_id=? ORDER BY source_index",
                (operation["id"],),
            ).fetchall()
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.image_to_pdf'"
            ).fetchone()
            output_key = conn.execute(
                "SELECT storage_key FROM web_document_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0]
        assert source_rows == [(first_source["id"], 1), (second_source["id"], 2)]
        assert audit and audit[0].startswith("sources=2;pixels=40000;bytes=")
        assert first_source["id"] not in audit[0]
        assert second_source["id"] not in audit[0]

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "image-to-pdf-other@example.com")
            hidden = second.get(f"/api/v1/document-operations/{operation['id']}")
            assert hidden.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            hidden_download = second.get(f"/api/v1/document-operations/{operation['id']}/download")
            assert hidden_download.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            rejected = images_to_pdf(
                second,
                csrf_second,
                asset_ids=[first_source["id"]],
                key="image-to-pdf-other-0001",
            )
            assert rejected.json()["error_code"] == "WEB_IMAGE_TO_PDF_SOURCE_NOT_FOUND"

        (tmp_path / "private-document-outputs" / output_key).write_bytes(b"%PDF-tampered")
        unavailable = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_DOCUMENT_OPERATION_UNAVAILABLE"
        assert first.get(f"/api/v1/document-operations/{operation['id']}").json()["data"]["operation"]["state"] == "unavailable"


def test_image_to_pdf_accepts_a_static_private_webp_source(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "image-to-pdf-webp@example.com")
        source = upload_image(
            client,
            csrf,
            key="image-to-pdf-webp-source-0001",
            body=image_bytes("WEBP", size=(128, 96), color=(64, 192, 128)),
            name="source.webp",
            content_type="image/webp",
        )
        created = images_to_pdf(client, csrf, asset_ids=[source["id"]], key="image-to-pdf-webp-run-0001")
        assert created.status_code == 200
        operation = created.json()["data"]["operation"]
        assert operation["kind"] == "image_to_pdf"
        assert operation["source_count"] == 1
        output = client.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert output.status_code == 200
        assert len(PdfReader(BytesIO(output.content), strict=True).pages) == 1


def test_image_to_pdf_fails_closed_for_disabled_decoder_and_unsafe_sources(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch, image_to_pdf_enabled=False) as client:
        csrf = register_and_login(client, "image-to-pdf-disabled@example.com")
        source = upload_image(
            client,
            csrf,
            key="image-to-pdf-disabled-source-0001",
            body=image_bytes("JPEG"),
            name="source.jpg",
            content_type="image/jpeg",
        )
        disabled = images_to_pdf(client, csrf, asset_ids=[source["id"]], key="image-to-pdf-disabled-run-0001")
        assert disabled.status_code == 503
        assert "WEBAPP_IMAGE_TO_PDF_ENABLED" in disabled.json()["message"]

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "image-to-pdf-safety@example.com")
        malformed = upload_image(
            client,
            csrf,
            key="image-to-pdf-malformed-source-0001",
            body=b"\x89PNG\r\n\x1a\nnot-a-real-png",
            name="malformed.png",
            content_type="image/png",
        )
        malformed_result = images_to_pdf(client, csrf, asset_ids=[malformed["id"]], key="image-to-pdf-malformed-run-0001")
        assert malformed_result.status_code == 422
        assert "không hợp lệ" in malformed_result.json()["message"].lower() or "bị hỏng" in malformed_result.json()["message"].lower()

        animated = upload_image(
            client,
            csrf,
            key="image-to-pdf-animated-source-0001",
            body=animated_webp_bytes(),
            name="animated.webp",
            content_type="image/webp",
        )
        animated_result = images_to_pdf(client, csrf, asset_ids=[animated["id"]], key="image-to-pdf-animated-run-0001")
        assert animated_result.status_code == 422
        assert "động" in animated_result.json()["message"].lower()

        pixel_limited = upload_image(
            client,
            csrf,
            key="image-to-pdf-pixel-source-0001",
            body=image_bytes("JPEG", size=(20, 20)),
            name="pixel.jpg",
            content_type="image/jpeg",
        )
        operations = importlib.import_module("copyfast_document_operations")
        with monkeypatch.context() as limits:
            limits.setattr(operations, "MAX_IMAGE_PIXELS_PER_SOURCE", 1)
            pixel_result = images_to_pdf(client, csrf, asset_ids=[pixel_limited["id"]], key="image-to-pdf-pixel-run-0001")
        assert pixel_result.status_code == 413
        assert "16 MP" in pixel_result.json()["message"]

        dimension_limited = upload_image(
            client,
            csrf,
            key="image-to-pdf-dimension-source-0001",
            body=image_bytes("JPEG", size=(20, 20)),
            name="dimension.jpg",
            content_type="image/jpeg",
        )
        with monkeypatch.context() as limits:
            limits.setattr(operations, "MAX_IMAGE_DIMENSION", 10)
            dimension_result = images_to_pdf(client, csrf, asset_ids=[dimension_limited["id"]], key="image-to-pdf-dimension-run-0001")
        assert dimension_result.status_code == 413
        assert "7680 px" in dimension_result.json()["message"]

        aspect_limited = upload_image(
            client,
            csrf,
            key="image-to-pdf-aspect-source-0001",
            body=image_bytes("PNG", size=(120, 10)),
            name="aspect.png",
            content_type="image/png",
        )
        with monkeypatch.context() as limits:
            limits.setattr(operations, "MAX_IMAGE_ASPECT_RATIO", 2)
            aspect_result = images_to_pdf(client, csrf, asset_ids=[aspect_limited["id"]], key="image-to-pdf-aspect-run-0001")
        assert aspect_result.status_code == 413
        assert "Tỷ lệ" in aspect_result.json()["message"]

        bomb_limited = upload_image(
            client,
            csrf,
            key="image-to-pdf-bomb-source-0001",
            body=image_bytes("JPEG", size=(20, 20)),
            name="bomb.jpg",
            content_type="image/jpeg",
        )
        with monkeypatch.context() as limits:
            limits.setattr(Image, "MAX_IMAGE_PIXELS", 1)
            bomb_result = images_to_pdf(client, csrf, asset_ids=[bomb_limited["id"]], key="image-to-pdf-bomb-run-0001")
        assert bomb_result.status_code == 413
        assert "Độ phân giải" in bomb_result.json()["message"]

        tampered = upload_image(
            client,
            csrf,
            key="image-to-pdf-tamper-source-0001",
            body=image_bytes("PNG"),
            name="tampered.png",
            content_type="image/png",
        )
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            storage_key = conn.execute("SELECT storage_key FROM web_asset_files WHERE id=?", (tampered["id"],)).fetchone()[0]
        (tmp_path / "private-web-assets" / storage_key).write_bytes(b"\x89PNG\r\n\x1a\ntampered")
        tampered_result = images_to_pdf(client, csrf, asset_ids=[tampered["id"]], key="image-to-pdf-tamper-run-0001")
        assert tampered_result.status_code == 422

        duplicate = images_to_pdf(
            client,
            csrf,
            asset_ids=[malformed["id"], malformed["id"]],
            key="image-to-pdf-duplicate-run-0001",
        )
        assert duplicate.status_code == 422
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            malformed_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (malformed["id"],)).fetchone()[0]
            animated_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (animated["id"],)).fetchone()[0]
            tampered_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (tampered["id"],)).fetchone()[0]
            failures = conn.execute(
                "SELECT failure_code, storage_key FROM web_document_operations WHERE kind='image_to_pdf' ORDER BY created_at"
            ).fetchall()
        assert malformed_state == "active"
        assert animated_state == "active"
        assert tampered_state == "unavailable"
        assert all(storage_key is None for _, storage_key in failures)
        assert {code for code, _ in failures} >= {
            "IMAGE_PARSE_FAILED",
            "IMAGE_ANIMATED",
            "IMAGE_PIXEL_LIMIT",
            "IMAGE_DIMENSION_LIMIT",
            "IMAGE_ASPECT_RATIO_LIMIT",
            "IMAGE_SOURCE_UNAVAILABLE",
        }
        staging = tmp_path / "private-document-outputs" / ".staging"
        assert not list(staging.iterdir())


def test_image_to_pdf_replays_completed_idempotency_while_rejecting_a_new_busy_batch(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "image-to-pdf-capacity@example.com")
        source = upload_image(
            client,
            csrf,
            key="image-to-pdf-capacity-source-0001",
            body=image_bytes("JPEG", size=(32, 32)),
            name="source.jpg",
            content_type="image/jpeg",
        )
        created = images_to_pdf(client, csrf, asset_ids=[source["id"]], key="image-to-pdf-capacity-completed-0001")
        assert created.status_code == 200
        completed_id = created.json()["data"]["operation"]["id"]
        operations = importlib.import_module("copyfast_document_operations")
        assert operations._IMAGE_TO_PDF_CAPACITY.acquire(blocking=False)
        try:
            replay = images_to_pdf(client, csrf, asset_ids=[source["id"]], key="image-to-pdf-capacity-completed-0001")
            busy = images_to_pdf(client, csrf, asset_ids=[source["id"]], key="image-to-pdf-capacity-new-run-0001")
        finally:
            operations._IMAGE_TO_PDF_CAPACITY.release()
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == completed_id
        assert busy.status_code == 429
        assert "đang bận" in busy.json()["message"].lower()
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_document_operations WHERE kind='image_to_pdf'").fetchone()[0] == 1


def test_pdf_split_is_private_idempotent_and_matches_the_bounded_bot_range_behavior(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "pdf-owner@example.com")
        assert first.get("/documents/split").status_code == 200
        source = upload_pdf(first, csrf, key="pdf-source-upload-0001")

        denied = first.post(
            "/api/v1/document-operations/pdf-split",
            json={"source_asset_id": source["id"], "page_range": "1-2", "idempotency_key": "pdf-split-denied-0001"},
        )
        assert denied.status_code == 403

        # The Bot's current parser normalizes reversed contiguous ranges. The
        # Web implementation keeps that useful behavior while bounding pages.
        created = split(first, csrf, asset_id=source["id"], page_range="3-2", key="pdf-split-create-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "pdf_split"
        assert operation["source_asset_id"] == source["id"]
        assert operation["selected_start_page"] == 2
        assert operation["selected_end_page"] == 3
        assert operation["source_page_count"] == 3
        assert operation["output_page_count"] == 2
        assert operation["download_ready"] is True
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment"):
            assert forbidden not in created.text.lower()

        # Equivalent reversed/canonical page ranges are one normalized intent,
        # so an interrupted browser retry cannot create a duplicate artifact.
        replay = split(first, csrf, asset_id=source["id"], page_range="2-3", key="pdf-split-create-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        conflicting = split(first, csrf, asset_id=source["id"], page_range="1-2", key="pdf-split-create-0001")
        assert conflicting.status_code == 409

        download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert download.status_code == 200
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["referrer-policy"] == "no-referrer"
        assert download.headers["content-security-policy"] == "sandbox"
        assert "attachment" in download.headers["content-disposition"]
        assert len(PdfReader(BytesIO(download.content), strict=True).pages) == 2

        detail = first.get(f"/api/v1/document-operations/{operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        listing = first.get("/api/v1/document-operations")
        assert listing.json()["data"]["items"][0]["id"] == operation["id"]

        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.pdf_split'"
            ).fetchone()
        assert audit
        assert source["original_filename"] not in audit[0]
        assert "storage" not in audit[0]

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "pdf-other@example.com")
            hidden = second.get(f"/api/v1/document-operations/{operation['id']}")
            assert hidden.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert source["id"] not in hidden.text
            hidden_download = second.get(f"/api/v1/document-operations/{operation['id']}/download")
            assert hidden_download.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            rejected = split(second, csrf_second, asset_id=source["id"], page_range="1", key="pdf-split-other-0001")
            assert rejected.json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"


def test_pdf_merge_is_private_ordered_idempotent_and_sanitizes_the_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "pdf-merge-owner@example.com")
        assert first.get("/documents/merge").status_code == 200
        first_source = upload_pdf(
            first,
            csrf,
            key="pdf-merge-source-first-0001",
            body=pdf_bytes(2, page_size=(144, 144)),
            name="first.pdf",
        )
        second_source = upload_pdf(
            first,
            csrf,
            key="pdf-merge-source-second-0001",
            body=pdf_bytes(1, page_size=(222, 144), with_annotation=True),
            name="second.pdf",
        )

        denied = first.post(
            "/api/v1/document-operations/pdf-merge",
            json={"source_asset_ids": [first_source["id"], second_source["id"]], "idempotency_key": "pdf-merge-denied-0001"},
        )
        assert denied.status_code == 403

        created = merge(
            first,
            csrf,
            asset_ids=[first_source["id"], second_source["id"]],
            key="pdf-merge-create-0001",
        )
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "pdf_merge"
        assert operation["source_asset_id"] == first_source["id"]
        assert operation["source_count"] == 2
        assert operation["requested_page_range"] == ""
        assert operation["selected_start_page"] is None
        assert operation["selected_end_page"] is None
        assert operation["source_page_count"] == 3
        assert operation["output_page_count"] == 3
        assert operation["download_ready"] is True
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment"):
            assert forbidden not in created.text.lower()

        replay = merge(
            first,
            csrf,
            asset_ids=[first_source["id"], second_source["id"]],
            key="pdf-merge-create-0001",
        )
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        reordered = merge(
            first,
            csrf,
            asset_ids=[second_source["id"], first_source["id"]],
            key="pdf-merge-create-0001",
        )
        assert reordered.status_code == 409

        download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert download.status_code == 200
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        output = PdfReader(BytesIO(download.content), strict=True)
        assert len(output.pages) == 3
        # Different source page widths make the server-preserved source order
        # observable without exposing source names or storage metadata.
        assert [float(page.mediabox.width) for page in output.pages] == [144.0, 144.0, 222.0]
        assert all("/Annots" not in page and "/AA" not in page for page in output.pages)

        detail = first.get(f"/api/v1/document-operations/{operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        listing = first.get("/api/v1/document-operations")
        assert listing.json()["data"]["items"][0]["id"] == operation["id"]

        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            source_rows = conn.execute(
                "SELECT source_asset_id, source_index FROM web_document_operation_sources WHERE operation_id=? ORDER BY source_index",
                (operation["id"],),
            ).fetchall()
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.pdf_merge'"
            ).fetchone()
        assert source_rows == [(first_source["id"], 1), (second_source["id"], 2)]
        assert audit
        assert audit[0].startswith("sources=2;pages=3;bytes=")
        assert audit[0].removeprefix("sources=2;pages=3;bytes=").isdigit()
        assert first_source["id"] not in audit[0]
        assert second_source["id"] not in audit[0]

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "pdf-merge-other@example.com")
            hidden = second.get(f"/api/v1/document-operations/{operation['id']}")
            assert hidden.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            rejected = merge(
                second,
                csrf_second,
                asset_ids=[first_source["id"], second_source["id"]],
                key="pdf-merge-other-0001",
            )
            assert rejected.json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"


def test_pdf_merge_rejects_duplicate_encrypted_oversize_page_and_tampered_inputs_without_fake_success(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-merge-safety@example.com")
        first_source = upload_pdf(client, csrf, key="pdf-merge-safety-first-0001", body=pdf_bytes(1))
        duplicate = merge(
            client,
            csrf,
            asset_ids=[first_source["id"], first_source["id"]],
            key="pdf-merge-duplicate-0001",
        )
        assert duplicate.status_code == 422

        encrypted_source = upload_pdf(
            client,
            csrf,
            key="pdf-merge-encrypted-source-0001",
            body=pdf_bytes(1, encrypted=True),
            name="encrypted.pdf",
        )
        encrypted = merge(
            client,
            csrf,
            asset_ids=[first_source["id"], encrypted_source["id"]],
            key="pdf-merge-encrypted-0001",
        )
        assert encrypted.status_code == 422
        assert "mã hóa" in encrypted.json()["message"].lower()

        many_pages = upload_pdf(
            client,
            csrf,
            key="pdf-merge-pages-source-0001",
            body=pdf_bytes(30),
            name="many-pages.pdf",
        )
        page_limit = merge(
            client,
            csrf,
            asset_ids=[first_source["id"], many_pages["id"]],
            key="pdf-merge-page-limit-0001",
        )
        assert page_limit.status_code == 422
        assert "30" in page_limit.json()["message"]
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            failed = conn.execute(
                "SELECT state, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-merge-page-limit-0001",),
            ).fetchone()
        assert failed == ("failed", None)

        good_source = upload_pdf(client, csrf, key="pdf-merge-tamper-good-0001", body=pdf_bytes(1))
        tampered_source = upload_pdf(client, csrf, key="pdf-merge-tamper-bad-0001", body=pdf_bytes(1))
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            storage_key = conn.execute(
                "SELECT storage_key FROM web_asset_files WHERE id=?", (tampered_source["id"],)
            ).fetchone()[0]
        (tmp_path / "private-web-assets" / storage_key).write_bytes(b"%PDF-tampered")
        tampered = merge(
            client,
            csrf,
            asset_ids=[good_source["id"], tampered_source["id"]],
            key="pdf-merge-tampered-0001",
        )
        assert tampered.status_code == 422
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            states = dict(
                conn.execute(
                    "SELECT id, state FROM web_asset_files WHERE id IN (?, ?)",
                    (good_source["id"], tampered_source["id"]),
                ).fetchall()
            )
            failed = conn.execute(
                "SELECT state, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-merge-tampered-0001",),
            ).fetchone()
        assert states == {good_source["id"]: "active", tampered_source["id"]: "unavailable"}
        assert failed == ("failed", None)
        staging = tmp_path / "private-document-outputs" / ".staging"
        assert not list(staging.iterdir())


def test_pdf_optimize_is_private_idempotent_and_only_publishes_a_verified_smaller_artifact(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "pdf-optimize-owner@example.com")
        assert first.get("/documents/compress").status_code == 200
        source = upload_pdf(
            first,
            csrf,
            key="pdf-optimize-source-0001",
            body=pdf_bytes(2, with_annotation=True, metadata_padding=16_384),
            name="metadata-heavy.pdf",
        )

        denied = first.post(
            "/api/v1/document-operations/pdf-optimize",
            json={"source_asset_id": source["id"], "idempotency_key": "pdf-optimize-denied-0001"},
        )
        assert denied.status_code == 403

        created = optimize(first, csrf, asset_id=source["id"], key="pdf-optimize-create-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "pdf_optimize"
        assert operation["source_asset_id"] == source["id"]
        assert operation["source_count"] == 1
        assert operation["source_page_count"] == 2
        assert operation["output_page_count"] == 2
        assert operation["input_byte_size"] == source["byte_size"]
        assert operation["byte_size"] < source["byte_size"]
        assert operation["saved_bytes"] == source["byte_size"] - operation["byte_size"]
        assert operation["saved_bytes"] >= 1024
        assert operation["saved_percent"] > 0
        assert operation["download_ready"] is True
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment"):
            assert forbidden not in created.text.lower()

        replay = optimize(first, csrf, asset_id=source["id"], key="pdf-optimize-create-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        other_source = upload_pdf(first, csrf, key="pdf-optimize-source-other-0001", body=pdf_bytes(1, metadata_padding=8_192))
        conflicting = optimize(first, csrf, asset_id=other_source["id"], key="pdf-optimize-create-0001")
        assert conflicting.status_code == 409

        download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert download.status_code == 200
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["content-security-policy"] == "sandbox"
        output = PdfReader(BytesIO(download.content), strict=True)
        assert len(output.pages) == 2
        assert all("/Annots" not in page and "/AA" not in page for page in output.pages)
        assert len(download.content) == operation["byte_size"]

        detail = first.get(f"/api/v1/document-operations/{operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.pdf_optimize'"
            ).fetchone()
            source_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (source["id"],)).fetchone()[0]
        assert audit and audit[0].startswith("source_pages=2;saved_bytes=")
        assert source["id"] not in audit[0]
        assert source_state == "active"

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "pdf-optimize-other@example.com")
            hidden = second.get(f"/api/v1/document-operations/{operation['id']}")
            assert hidden.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            rejected = optimize(second, csrf_second, asset_id=source["id"], key="pdf-optimize-other-0001")
            assert rejected.json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"

        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            output_key = conn.execute(
                "SELECT storage_key FROM web_document_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0]
        (tmp_path / "private-document-outputs" / output_key).write_bytes(b"%PDF-tampered")
        unavailable = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_DOCUMENT_OPERATION_UNAVAILABLE"
        assert first.get(f"/api/v1/document-operations/{operation['id']}").json()["data"]["operation"]["state"] == "unavailable"


def test_pdf_to_word_exports_only_real_private_pdf_text_and_keeps_docx_download_private(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "pdf-to-word-owner@example.com")
        assert first.get("/documents/pdf-to-word").status_code == 200
        source = upload_pdf(
            first,
            csrf,
            key="pdf-to-word-text-source-0001",
            body=pdf_text_bytes(["First source paragraph\nSecond source paragraph", "Third page text"]),
            name="selectable-text.pdf",
        )
        denied = first.post(
            "/api/v1/document-operations/pdf-to-word",
            json={"source_asset_id": source["id"], "idempotency_key": "pdf-to-word-denied-0001"},
        )
        assert denied.status_code == 403

        created = pdf_to_word(first, csrf, asset_id=source["id"], key="pdf-to-word-create-0001")
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "pdf_to_word_text"
        assert operation["source_asset_id"] == source["id"]
        assert operation["source_count"] == 1
        assert operation["source_page_count"] == 2
        assert operation["output_page_count"] is None
        assert operation["content_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert operation["original_filename"] == "toan-aas-pdf-text.docx"
        assert operation["download_ready"] is True
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment", "bot"):
            assert forbidden not in created.text.lower()

        replay = pdf_to_word(first, csrf, asset_id=source["id"], key="pdf-to-word-create-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        other_source = upload_pdf(
            first,
            csrf,
            key="pdf-to-word-other-source-0001",
            body=pdf_text_bytes(["Other selectable text"]),
        )
        assert pdf_to_word(first, csrf, asset_id=other_source["id"], key="pdf-to-word-create-0001").status_code == 409

        history = first.get("/api/v1/document-operations?kind=pdf_to_word_text&limit=100")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["data"]["items"]] == [operation["id"]]
        download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert "toan-aas-pdf-text.docx" in download.headers["content-disposition"]
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["content-security-policy"] == "sandbox"
        exported = Document(BytesIO(download.content))
        assert [paragraph.text for paragraph in exported.paragraphs if paragraph.text] == [
            "First source paragraph",
            "Second source paragraph",
            "Third page text",
        ]
        assert len(download.content) == operation["byte_size"]

        detail = first.get(f"/api/v1/document-operations/{operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.pdf_to_word_text'"
            ).fetchone()
            source_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (source["id"],)).fetchone()[0]
        assert audit and audit[0].startswith("source_pages=2;characters=")
        assert source["id"] not in audit[0]
        assert source_state == "active"

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "pdf-to-word-other@example.com")
            hidden = second.get(f"/api/v1/document-operations/{operation['id']}")
            assert hidden.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert pdf_to_word(second, csrf_second, asset_id=source["id"], key="pdf-to-word-other-0001").json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"


def test_pdf_to_word_guards_scans_and_rejects_unsafe_or_disabled_inputs_without_fake_docx(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-to-word-safety@example.com")
        scan = upload_pdf(client, csrf, key="pdf-to-word-scan-source-0001", body=pdf_bytes(1))
        guarded = pdf_to_word(client, csrf, asset_id=scan["id"], key="pdf-to-word-scan-0001")
        assert guarded.status_code == 422
        assert "không phát docx giả" in guarded.json()["message"].lower()
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            row = conn.execute(
                "SELECT id, state, failure_code, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-to-word-scan-0001",),
            ).fetchone()
            source_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (scan["id"],)).fetchone()[0]
        assert row[1:] == ("guarded", "PDF_TEXT_NOT_FOUND", None)
        assert source_state == "active"
        replay = pdf_to_word(client, csrf, asset_id=scan["id"], key="pdf-to-word-scan-0001")
        assert replay.status_code == 200
        assert replay.json()["status"] == "guarded"
        assert replay.json()["data"]["operation"]["download_ready"] is False
        assert client.get(f"/api/v1/document-operations/{row[0]}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"

        encrypted = upload_pdf(
            client,
            csrf,
            key="pdf-to-word-encrypted-source-0001",
            body=pdf_text_bytes(["locked text"], encrypted=True),
        )
        encrypted_result = pdf_to_word(client, csrf, asset_id=encrypted["id"], key="pdf-to-word-encrypted-0001")
        assert encrypted_result.status_code == 422
        assert "mã hóa" in encrypted_result.json()["message"].lower()

        too_many = upload_pdf(
            client,
            csrf,
            key="pdf-to-word-pages-source-0001",
            body=pdf_text_bytes(["page"] * 31),
        )
        page_limit = pdf_to_word(client, csrf, asset_id=too_many["id"], key="pdf-to-word-pages-0001")
        assert page_limit.status_code == 413
        assert "30" in page_limit.json()["message"]

        limited = upload_pdf(
            client,
            csrf,
            key="pdf-to-word-text-limit-source-0001",
            body=pdf_text_bytes(["six chars"]),
        )
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "MAX_PDF_TO_WORD_PAGE_CHARACTERS", 5)
        text_limit = pdf_to_word(client, csrf, asset_id=limited["id"], key="pdf-to-word-text-limit-0001")
        assert text_limit.status_code == 413
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            failed = conn.execute(
                "SELECT state, failure_code, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-to-word-text-limit-0001",),
            ).fetchone()
        assert failed == ("failed", "PDF_TEXT_LIMIT", None)

        tampered = upload_pdf(client, csrf, key="pdf-to-word-tamper-source-0001", body=pdf_text_bytes(["integrity text"]))
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            source_key = conn.execute("SELECT storage_key FROM web_asset_files WHERE id=?", (tampered["id"],)).fetchone()[0]
        (tmp_path / "private-web-assets" / source_key).write_bytes(b"%PDF-tampered")
        tampered_result = pdf_to_word(client, csrf, asset_id=tampered["id"], key="pdf-to-word-tamper-0001")
        assert tampered_result.status_code == 422
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            failed = conn.execute(
                "SELECT state, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-to-word-tamper-0001",),
            ).fetchone()
            source_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (tampered["id"],)).fetchone()[0]
        assert failed == ("failed", None)
        assert source_state == "unavailable"
        staging = tmp_path / "private-document-outputs" / ".staging"
        assert not list(staging.iterdir())

    with make_client(tmp_path, monkeypatch, pdf_to_word_enabled=False) as disabled:
        csrf = register_and_login(disabled, "pdf-to-word-disabled@example.com")
        response = pdf_to_word(
            disabled,
            csrf,
            asset_id="11111111-1111-4111-8111-111111111111",
            key="pdf-to-word-disabled-0001",
        )
        assert response.status_code == 503
        assert "WEBAPP_PDF_TO_WORD_ENABLED" in response.json()["message"]


def test_pdf_to_word_capacity_and_private_docx_integrity_fail_closed(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-to-word-capacity@example.com")
        source = upload_pdf(client, csrf, key="pdf-to-word-capacity-source-0001", body=pdf_text_bytes(["capacity text"]))
        operations = importlib.import_module("copyfast_document_operations")
        assert operations._PDF_TO_WORD_CAPACITY.acquire(blocking=False)
        try:
            busy = pdf_to_word(client, csrf, asset_id=source["id"], key="pdf-to-word-capacity-busy-0001")
            assert busy.status_code == 429
        finally:
            operations._PDF_TO_WORD_CAPACITY.release()
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-to-word-capacity-busy-0001",),
            ).fetchone()[0]
        assert count == 0

        created = pdf_to_word(client, csrf, asset_id=source["id"], key="pdf-to-word-capacity-create-0001")
        assert created.status_code == 200
        operation = created.json()["data"]["operation"]
        assert operations._PDF_TO_WORD_CAPACITY.acquire(blocking=False)
        try:
            replay = pdf_to_word(client, csrf, asset_id=source["id"], key="pdf-to-word-capacity-create-0001")
            assert replay.status_code == 200
            assert replay.json()["data"]["operation"]["id"] == operation["id"]
            second = upload_pdf(client, csrf, key="pdf-to-word-capacity-source-0002", body=pdf_text_bytes(["other text"]))
            assert pdf_to_word(client, csrf, asset_id=second["id"], key="pdf-to-word-capacity-new-0001").status_code == 429
        finally:
            operations._PDF_TO_WORD_CAPACITY.release()

        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            output_key = conn.execute(
                "SELECT storage_key FROM web_document_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0]
        (tmp_path / "private-document-outputs" / output_key).write_bytes(b"not-a-docx")
        unavailable = client.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_DOCUMENT_OPERATION_UNAVAILABLE"
        assert client.get(f"/api/v1/document-operations/{operation['id']}").json()["data"]["operation"]["state"] == "unavailable"

        canonical_source = upload_pdf(
            client,
            csrf,
            key="pdf-to-word-mime-source-0001",
            body=pdf_text_bytes(["canonical MIME text"]),
        )
        canonical = pdf_to_word(client, csrf, asset_id=canonical_source["id"], key="pdf-to-word-mime-create-0001")
        assert canonical.status_code == 200
        canonical_id = canonical.json()["data"]["operation"]["id"]
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            conn.execute(
                "UPDATE web_document_operations SET content_type='application/pdf' WHERE id=?",
                (canonical_id,),
            )
            conn.commit()
        noncanonical = client.get(f"/api/v1/document-operations/{canonical_id}/download")
        assert noncanonical.json()["error_code"] == "WEB_DOCUMENT_OPERATION_UNAVAILABLE"


def test_pdf_to_images_renders_private_png_and_deterministic_multi_page_zip(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "pdf-to-images-owner@example.com")
        assert first.get("/documents/pdf-to-images").status_code == 200
        single_source = upload_pdf(
            first,
            csrf,
            key="pdf-to-images-single-source-0001",
            body=pdf_bytes(1, page_size=(144, 144)),
            name="one-page.pdf",
        )
        denied = first.post(
            "/api/v1/document-operations/pdf-to-images",
            json={"source_asset_id": single_source["id"], "idempotency_key": "pdf-to-images-denied-0001"},
        )
        assert denied.status_code == 403

        single = pdf_to_images(first, csrf, asset_id=single_source["id"], key="pdf-to-images-single-create-0001")
        assert single.status_code == 200
        payload = single.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "pdf_to_images"
        assert operation["source_asset_id"] == single_source["id"]
        assert operation["source_count"] == 1
        assert operation["source_page_count"] == 1
        assert operation["output_page_count"] == 1
        assert operation["content_type"] == "image/png"
        assert operation["original_filename"] == "toan-aas-pdf-page-001.png"
        assert operation["download_ready"] is True
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment", "bot", "fitz"):
            assert forbidden not in single.text.lower()

        replay = pdf_to_images(first, csrf, asset_id=single_source["id"], key="pdf-to-images-single-create-0001")
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        collision_source = upload_pdf(first, csrf, key="pdf-to-images-collision-source-0001", body=pdf_bytes(1))
        assert pdf_to_images(first, csrf, asset_id=collision_source["id"], key="pdf-to-images-single-create-0001").status_code == 409

        png_download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert png_download.status_code == 200
        assert png_download.headers["content-type"].startswith("image/png")
        assert "toan-aas-pdf-page-001.png" in png_download.headers["content-disposition"]
        assert png_download.headers["cache-control"] == "no-store, private"
        assert png_download.headers["x-content-type-options"] == "nosniff"
        assert png_download.headers["referrer-policy"] == "no-referrer"
        assert png_download.headers["content-security-policy"] == "sandbox"
        with Image.open(BytesIO(png_download.content)) as image:
            assert image.format == "PNG"
            assert image.mode == "RGB"
            assert image.size == (288, 288)
            image.verify()
        assert len(png_download.content) == operation["byte_size"]

        multi_source = upload_pdf(
            first,
            csrf,
            key="pdf-to-images-multi-source-0001",
            body=pdf_bytes(2, page_size=(144, 216)),
            name="two-pages.pdf",
        )
        multi = pdf_to_images(first, csrf, asset_id=multi_source["id"], key="pdf-to-images-multi-create-0001")
        assert multi.status_code == 200
        multi_operation = multi.json()["data"]["operation"]
        assert multi_operation["kind"] == "pdf_to_images"
        assert multi_operation["source_page_count"] == 2
        assert multi_operation["output_page_count"] == 2
        assert multi_operation["content_type"] == "application/zip"
        assert multi_operation["original_filename"] == "toan-aas-pdf-pages.zip"
        history = first.get("/api/v1/document-operations?kind=pdf_to_images&limit=100")
        assert history.status_code == 200
        assert [item["id"] for item in history.json()["data"]["items"]] == [multi_operation["id"], operation["id"]]
        zip_download = first.get(f"/api/v1/document-operations/{multi_operation['id']}/download")
        assert zip_download.status_code == 200
        assert zip_download.headers["content-type"].startswith("application/zip")
        assert "toan-aas-pdf-pages.zip" in zip_download.headers["content-disposition"]
        with ZipFile(BytesIO(zip_download.content), "r") as archive:
            assert archive.namelist() == ["page_001.png", "page_002.png"]
            assert [member.date_time for member in archive.infolist()] == [(1980, 1, 1, 0, 0, 0)] * 2
            assert all(not member.extra and not member.comment for member in archive.infolist())
            for name in archive.namelist():
                with Image.open(BytesIO(archive.read(name))) as image:
                    assert image.format == "PNG"
                    assert image.mode == "RGB"
                    assert image.size == (288, 432)
                    image.verify()
        assert len(zip_download.content) == multi_operation["byte_size"]

        detail = first.get(f"/api/v1/document-operations/{multi_operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.pdf_to_images' AND target=?",
                (multi_operation["id"],),
            ).fetchone()
            output_key = conn.execute(
                "SELECT storage_key FROM web_document_operations WHERE id=?", (multi_operation["id"],)
            ).fetchone()[0]
        assert audit and audit[0].startswith("source_pages=2;output_pages=2;artifact=zip;bytes=")
        assert multi_source["id"] not in audit[0]

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "pdf-to-images-other@example.com")
            assert second.get(f"/api/v1/document-operations/{multi_operation['id']}").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert second.get(f"/api/v1/document-operations/{multi_operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert pdf_to_images(second, csrf_second, asset_id=multi_source["id"], key="pdf-to-images-other-0001").json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"

        (tmp_path / "private-document-outputs" / output_key).write_bytes(b"not-a-zip")
        unavailable = first.get(f"/api/v1/document-operations/{multi_operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_DOCUMENT_OPERATION_UNAVAILABLE"
        assert first.get(f"/api/v1/document-operations/{multi_operation['id']}").json()["data"]["operation"]["state"] == "unavailable"


def test_pdf_to_images_fails_closed_for_disabled_busy_encrypted_oversize_page_and_tampered_sources(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-to-images-safety@example.com")
        source = upload_pdf(client, csrf, key="pdf-to-images-busy-source-0001", body=pdf_bytes(1))
        operations = importlib.import_module("copyfast_document_operations")
        assert operations._PDF_TO_IMAGES_CAPACITY.acquire(blocking=False)
        try:
            busy = pdf_to_images(client, csrf, asset_id=source["id"], key="pdf-to-images-busy-0001")
            assert busy.status_code == 429
        finally:
            operations._PDF_TO_IMAGES_CAPACITY.release()
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-to-images-busy-0001",),
            ).fetchone()[0] == 0

        encrypted = upload_pdf(client, csrf, key="pdf-to-images-encrypted-source-0001", body=pdf_bytes(1, encrypted=True))
        encrypted_result = pdf_to_images(client, csrf, asset_id=encrypted["id"], key="pdf-to-images-encrypted-0001")
        assert encrypted_result.status_code == 422
        assert "mã hóa" in encrypted_result.json()["message"].lower()

        too_many = upload_pdf(client, csrf, key="pdf-to-images-pages-source-0001", body=pdf_bytes(31))
        page_limit = pdf_to_images(client, csrf, asset_id=too_many["id"], key="pdf-to-images-pages-0001")
        assert page_limit.status_code == 413
        assert "30" in page_limit.json()["message"]

        tampered = upload_pdf(client, csrf, key="pdf-to-images-tamper-source-0001", body=pdf_bytes(1))
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            source_key = conn.execute("SELECT storage_key FROM web_asset_files WHERE id=?", (tampered["id"],)).fetchone()[0]
        (tmp_path / "private-web-assets" / source_key).write_bytes(b"%PDF-tampered")
        tampered_result = pdf_to_images(client, csrf, asset_id=tampered["id"], key="pdf-to-images-tamper-0001")
        assert tampered_result.status_code == 422
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            failed = conn.execute(
                "SELECT state, failure_code, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-to-images-tamper-0001",),
            ).fetchone()
            source_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (tampered["id"],)).fetchone()[0]
        assert failed == ("failed", "PDF_SOURCE_UNAVAILABLE", None)
        assert source_state == "unavailable"
        staging = tmp_path / "private-document-outputs" / ".staging"
        assert not list(staging.iterdir())

    with make_client(tmp_path, monkeypatch, pdf_to_images_enabled=False) as disabled:
        csrf = register_and_login(disabled, "pdf-to-images-disabled@example.com")
        response = pdf_to_images(
            disabled,
            csrf,
            asset_id="11111111-1111-4111-8111-111111111111",
            key="pdf-to-images-disabled-0001",
        )
        assert response.status_code == 503
        assert "WEBAPP_PDF_TO_IMAGES_ENABLED" in response.json()["message"]


def test_pdf_optimize_marks_no_reduction_guarded_and_rejects_unsafe_inputs_without_fake_output(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-optimize-safety@example.com")
        source = upload_pdf(client, csrf, key="pdf-optimize-guarded-source-0001", body=pdf_bytes(1, metadata_padding=8_192))
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "_has_meaningful_optimization", lambda **_: False)
        not_reduced = optimize(client, csrf, asset_id=source["id"], key="pdf-optimize-guarded-0001")
        assert not_reduced.status_code == 422
        assert "file gốc không thay đổi" in not_reduced.json()["message"].lower()
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            guarded = conn.execute(
                "SELECT id, state, failure_code, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-optimize-guarded-0001",),
            ).fetchone()
            source_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (source["id"],)).fetchone()[0]
        assert guarded[1:] == ("guarded", "PDF_NOT_REDUCED", None)
        assert source_state == "active"
        detail = client.get(f"/api/v1/document-operations/{guarded[0]}")
        assert detail.json()["data"]["operation"]["state"] == "guarded"
        assert detail.json()["data"]["operation"]["download_ready"] is False
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "guarded"]
        assert client.get(f"/api/v1/document-operations/{guarded[0]}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
        staging = tmp_path / "private-document-outputs" / ".staging"
        assert not list(staging.iterdir())

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-optimize-inputs@example.com")
        encrypted = upload_pdf(client, csrf, key="pdf-optimize-encrypted-source-0001", body=pdf_bytes(1, encrypted=True))
        encrypted_result = optimize(client, csrf, asset_id=encrypted["id"], key="pdf-optimize-encrypted-0001")
        assert encrypted_result.status_code == 422
        assert "mã hóa" in encrypted_result.json()["message"].lower()
        too_many_pages = upload_pdf(client, csrf, key="pdf-optimize-pages-source-0001", body=pdf_bytes(31))
        page_limit = optimize(client, csrf, asset_id=too_many_pages["id"], key="pdf-optimize-pages-0001")
        assert page_limit.status_code == 422
        assert "30" in page_limit.json()["message"]
        tampered = upload_pdf(client, csrf, key="pdf-optimize-tamper-source-0001", body=pdf_bytes(1))
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            storage_key = conn.execute("SELECT storage_key FROM web_asset_files WHERE id=?", (tampered["id"],)).fetchone()[0]
        (tmp_path / "private-web-assets" / storage_key).write_bytes(b"%PDF-tampered")
        tampered_result = optimize(client, csrf, asset_id=tampered["id"], key="pdf-optimize-tamper-0001")
        assert tampered_result.status_code == 422
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            failed = conn.execute(
                "SELECT state, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-optimize-tamper-0001",),
            ).fetchone()
            tampered_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (tampered["id"],)).fetchone()[0]
        assert failed == ("failed", None)
        assert tampered_state == "unavailable"


def test_pdf_split_rejects_archived_tampered_encrypted_and_oversize_page_inputs_without_fake_success(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-safety@example.com")
        archived_source = upload_pdf(client, csrf, key="pdf-source-archive-0001")
        archived = client.post(
            f"/api/v1/asset-vault/{archived_source['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "pdf-source-archive-action-0001"},
            json={"expected_revision": 1},
        )
        assert archived.status_code == 200
        assert split(client, csrf, asset_id=archived_source["id"], page_range="1", key="pdf-split-archived-0001").json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"

        encrypted_source = upload_pdf(client, csrf, key="pdf-source-encrypted-0001", body=pdf_bytes(2, encrypted=True), name="encrypted.pdf")
        encrypted = split(client, csrf, asset_id=encrypted_source["id"], page_range="1", key="pdf-split-encrypted-0001")
        assert encrypted.status_code == 422
        assert "mã hóa" in encrypted.json()["message"].lower()

        too_many_pages = upload_pdf(client, csrf, key="pdf-source-pages-0001", body=pdf_bytes(31), name="many-pages.pdf")
        too_many = split(client, csrf, asset_id=too_many_pages["id"], page_range="1-2", key="pdf-split-pages-0001")
        assert too_many.status_code == 422
        assert "30" in too_many.json()["message"]

        tampered_source = upload_pdf(client, csrf, key="pdf-source-tamper-0001")
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            source_key = conn.execute("SELECT storage_key FROM web_asset_files WHERE id=?", (tampered_source["id"],)).fetchone()[0]
        (tmp_path / "private-web-assets" / source_key).write_bytes(b"%PDF-tampered")
        tampered = split(client, csrf, asset_id=tampered_source["id"], page_range="1", key="pdf-split-tamper-0001")
        assert tampered.status_code == 422
        # A corrupt source can fail either before (size/availability) or
        # during digest verification. Both paths must fail closed without an
        # output or internal integrity details.
        assert tampered.json()["message"] in {
            "PDF nguồn không vượt qua kiểm tra integrity",
            "PDF nguồn không còn sẵn sàng",
        }
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            failed = conn.execute(
                "SELECT state, storage_key FROM web_document_operations WHERE idempotency_key=?",
                ("pdf-split-tamper-0001",),
            ).fetchone()
            source_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (tampered_source["id"],)).fetchone()[0]
        assert failed == ("failed", None)
        assert source_state == "unavailable"


def test_pdf_split_marks_tampered_output_unavailable_and_enforces_private_roots(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-output-integrity@example.com")
        source = upload_pdf(client, csrf, key="pdf-output-source-0001")
        operation = split(client, csrf, asset_id=source["id"], page_range="1-2", key="pdf-output-operation-0001").json()["data"]["operation"]
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            output_key = conn.execute("SELECT storage_key FROM web_document_operations WHERE id=?", (operation["id"],)).fetchone()[0]
        (tmp_path / "private-document-outputs" / output_key).write_bytes(b"%PDF-tampered")
        unavailable = client.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_DOCUMENT_OPERATION_UNAVAILABLE"
        detail = client.get(f"/api/v1/document-operations/{operation['id']}")
        assert detail.json()["data"]["operation"]["state"] == "unavailable"
        assert detail.json()["data"]["operation"]["download_ready"] is False

    database = importlib.import_module("copyfast_db")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "not-a-volume"))
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    with pytest.raises(RuntimeError):
        database.document_operations_directory()
    volume = tmp_path / "railway-volume"
    volume.mkdir()
    root = volume / "document-operations"
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(root))
    monkeypatch.delenv("WEBAPP_ASSET_VAULT_ENABLED", raising=False)
    monkeypatch.delenv("WEBAPP_PROJECT_PACKAGE_ENABLED", raising=False)
    assert database.document_operations_directory() == root.resolve()
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(root))
    with pytest.raises(RuntimeError):
        database.document_operations_directory()
    monkeypatch.delenv("WEBAPP_ASSET_VAULT_ENABLED", raising=False)
    monkeypatch.delenv("WEBAPP_ASSET_VAULT_ROOT", raising=False)
    with pytest.raises(RuntimeError):
        database.ensure_document_operations_persistence()


def test_pdf_split_strips_interactive_page_annotations_from_the_generated_attachment(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-annotation@example.com")
        source = upload_pdf(
            client,
            csrf,
            key="pdf-annotation-source-0001",
            body=pdf_bytes(2, with_annotation=True),
            name="interactive-source.pdf",
        )
        operation = split(client, csrf, asset_id=source["id"], page_range="1", key="pdf-annotation-operation-0001")
        assert operation.status_code == 200
        output = client.get(f"/api/v1/document-operations/{operation.json()['data']['operation']['id']}/download")
        assert output.status_code == 200
        page = PdfReader(BytesIO(output.content), strict=True).pages[0]
        assert "/Annots" not in page
        assert "/AA" not in page


def test_document_operation_reconciliation_fails_only_stale_interrupted_records(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-reconcile@example.com")
        source = upload_pdf(client, csrf, key="pdf-reconcile-source-0001")
        operation_id = "ea647030-4944-4ce3-85f4-4fef06a8ee8c"
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            account_id = conn.execute("SELECT account_id FROM web_asset_files WHERE id=?", (source["id"],)).fetchone()[0]
            conn.execute(
                """INSERT INTO web_document_operations
                   (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                    request_fingerprint, source_sha256, source_byte_size, requested_page_range,
                    created_at, queued_at, started_at, updated_at)
                   VALUES (?, ?, ?, NULL, 'pdf_split', 'processing', ?, ?, ?, ?, '1', ?, ?, ?, ?)""",
                (
                    operation_id, account_id, source["id"], "pdf-reconcile-operation-0001",
                    "a" * 64, "b" * 64, source["byte_size"],
                    "2000-01-01T00:00:00+00:00", "2000-01-01T00:00:00+00:00",
                    "2000-01-01T00:00:00+00:00", "2000-01-01T00:00:00+00:00",
                ),
            )
            conn.commit()
        operations = importlib.import_module("copyfast_document_operations")
        operations.reconcile_document_operation_storage()
        with sqlite3.connect(tmp_path / "copyfast-document-operations-test.db") as conn:
            state, failure_code = conn.execute(
                "SELECT state, failure_code FROM web_document_operations WHERE id=?", (operation_id,)
            ).fetchone()
            events = conn.execute(
                "SELECT state FROM web_document_operation_events WHERE operation_id=?", (operation_id,)
            ).fetchall()
        assert (state, failure_code) == ("failed", "INTERRUPTED")
        assert events == [("failed",)]


def test_document_operations_have_no_bot_bridge_public_storage_or_unbounded_parser_contract():
    source = Path("copyfast_document_operations.py").read_text(encoding="utf-8")
    assert "from copyfast_bridge" not in source
    assert "import copyfast_bridge" not in source
    assert "bridge_request(" not in source
    assert "MAX_INPUT_BYTES = 20 * 1024 * 1024" in source
    assert "MAX_PAGES = 30" in source
    assert "PDF_EXCLUDED_PAGE_KEYS" in source
    assert "PDF_OPTIMIZE_KIND" in source
    assert "_has_meaningful_optimization" in source
    assert "compress_content_streams(level=9)" in source
    assert "subprocess" not in source
    assert "import fitz" not in source
    assert 'app.mount("/document-operations"' not in Path("app.py").read_text(encoding="utf-8")
    assert '"/api/v1/document-operations/pdf-optimize"' in Path("app.py").read_text(encoding="utf-8")
