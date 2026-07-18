"""Focused privacy, truthfulness and resource contracts for private PDF OCR.

The local Tesseract adapter is mocked, but the signed Web session, Asset Vault,
PDF parser, PDFium rasterization, operation lifecycle and private download path
are real.  No test needs a Bot, provider, Telegram, payment or Tesseract binary.
"""

from __future__ import annotations

from io import BytesIO
import hashlib
import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch, *, pdf_ocr_enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-pdf-ocr-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-pdf-ocr-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "private-document-outputs"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OCR_PDF_ENABLED", "true" if pdf_ocr_enabled else "false")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OCR_IMAGE_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_OCR_WORD_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_TO_PDF_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_IMAGES_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_WORD_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "PDF OCR Owner"},
    ).status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def pdf_bytes(page_count: int, *, encrypted: bool = False) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=360, height=360)
    if encrypted:
        writer.encrypt("test-password")
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def pdf_text_bytes(pages: list[str]) -> bytes:
    """Generate small parseable PDF pages without adding a drawing runtime."""

    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=360, height=360)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        font_ref = writer._add_object(font)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        content = DecodedStreamObject()
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1")
        content.set_data(b"BT\n/F1 12 Tf\n32 320 Td\n(" + escaped + b") Tj\nET")
        page[NameObject("/Contents")] = writer._add_object(content)
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def upload_pdf(client: TestClient, csrf: str, *, key: str, body: bytes, name: str = "source.pdf") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "PDF OCR private"},
        files={"file": (name, body, "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def upload_text(client: TestClient, csrf: str, *, key: str) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Không phải PDF"},
        files={"file": ("source.txt", b"not a PDF", "text/plain")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def ocr_pdf(client: TestClient, csrf: str, *, asset_id: str, language: str = "auto"):
    return client.post(
        "/api/v1/document-operations/ocr-pdf",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "language": language},
    )


class FakePdfOcrTesseract:
    responses: list[str] = []
    calls: list[dict[str, object]] = []

    @classmethod
    def image_to_string(cls, image, *args, **kwargs) -> str:
        cls.calls.append({"size": image.size, "args": args, "kwargs": kwargs})
        return cls.responses.pop(0) if cls.responses else ""


def fake_runtime(*responses: str):
    FakePdfOcrTesseract.responses = list(responses)
    FakePdfOcrTesseract.calls.clear()
    return lambda: (FakePdfOcrTesseract, frozenset({"eng", "vie"}))


def test_pdf_ocr_delivers_verified_private_text_and_owner_isolation(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "pdf-ocr-owner@example.com")
        assert first.get("/documents/pdf-ocr").status_code == 200
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "_image_ocr_runtime", fake_runtime("Trang một\r\nDòng A\x00", "Trang hai"))
        source = upload_pdf(
            first,
            csrf,
            key="pdf-ocr-owner-source-0001",
            body=pdf_text_bytes(["source one", "source two"]),
        )

        denied = first.post(
            "/api/v1/document-operations/ocr-pdf",
            json={"source_asset_id": source["id"], "language": "auto"},
        )
        assert denied.status_code == 403

        created = ocr_pdf(first, csrf, asset_id=source["id"])
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True and payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "pdf_ocr"
        assert operation["source_asset_id"] == source["id"]
        assert operation["source_page_count"] == 2
        assert operation["source_count"] == 1
        assert operation["language"] == "auto"
        assert operation["content_type"] == "text/plain; charset=utf-8"
        assert operation["original_filename"] == "toan-aas-pdf-ocr.txt"
        assert operation["download_ready"] is True
        assert FakePdfOcrTesseract.calls == [
            {"size": (720, 720), "args": (), "kwargs": {"lang": "vie+eng", "config": "--oem 1 --psm 6", "timeout": 30}},
            {"size": (720, 720), "args": (), "kwargs": {"lang": "vie+eng", "config": "--oem 1 --psm 6", "timeout": 30}},
        ]
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment", "wallet", "telegram", "Trang một"):
            assert forbidden.lower() not in created.text.lower()

        replay = ocr_pdf(first, csrf, asset_id=source["id"])
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]

        download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("text/plain; charset=utf-8")
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["referrer-policy"] == "no-referrer"
        assert download.headers["content-security-policy"] == "sandbox"
        assert download.headers["content-length"] == str(len(download.content))
        assert download.content.decode("utf-8") == "=== Trang 1 ===\nTrang một\nDòng A\n\n=== Trang 2 ===\nTrang hai\n"
        # The sealed temporary file and its bounded download slot are released
        # after the response body is consumed.
        assert operations._DOCUMENT_OPERATION_DOWNLOAD_CAPACITY.acquire(blocking=False)
        operations._DOCUMENT_OPERATION_DOWNLOAD_CAPACITY.release()
        assert operations._DOCUMENT_OPERATION_DOWNLOAD_CAPACITY.acquire(blocking=False)
        assert operations._DOCUMENT_OPERATION_DOWNLOAD_CAPACITY.acquire(blocking=False)
        try:
            busy_download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
            assert busy_download.status_code == 429
        finally:
            operations._DOCUMENT_OPERATION_DOWNLOAD_CAPACITY.release()
            operations._DOCUMENT_OPERATION_DOWNLOAD_CAPACITY.release()

        detail = first.get(f"/api/v1/document-operations/{operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.pdf_ocr' AND target=?",
                (operation["id"],),
            ).fetchone()
            storage_key = conn.execute(
                "SELECT storage_key FROM web_document_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0]
        assert audit and "recognized_pages=2" in audit[0] and "characters=" in audit[0]
        assert source["id"] not in audit[0] and "Trang một" not in audit[0]
        assert Path(storage_key).suffix == ".txt"

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "pdf-ocr-other@example.com")
            second_operations = importlib.import_module("copyfast_document_operations")
            monkeypatch.setattr(second_operations, "_image_ocr_runtime", fake_runtime("never used"))
            assert second.get(f"/api/v1/document-operations/{operation['id']}").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert second.get(f"/api/v1/document-operations/{operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert ocr_pdf(second, csrf_second, asset_id=source["id"]).json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"


def test_pdf_ocr_rejects_browser_controls_bad_sources_and_busy_resources(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-ocr-boundaries@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "_image_ocr_runtime", fake_runtime("recognized"))
        source = upload_pdf(client, csrf, key="pdf-ocr-boundaries-source-0001", body=pdf_bytes(1))

        for invalid in (
            {"source_asset_id": source["id"], "language": "fr"},
            {"source_asset_id": source["id"], "language": "auto", "url": "https://untrusted.invalid/source.pdf"},
            {"source_asset_id": source["id"], "language": "auto", "path": "C:\\private\\source.pdf"},
            {"source_asset_id": source["id"], "language": "auto", "idempotency_key": "browser-must-not-control-this"},
            {"source_asset_id": source["id"], "language": "auto", "render_scale": 99},
        ):
            response = client.post(
                "/api/v1/document-operations/ocr-pdf",
                headers={"X-CSRF-Token": csrf},
                json=invalid,
            )
            assert response.status_code == 422

        non_pdf = upload_text(client, csrf, key="pdf-ocr-boundaries-text-0001")
        assert ocr_pdf(client, csrf, asset_id=non_pdf["id"]).status_code == 422

        encrypted = upload_pdf(client, csrf, key="pdf-ocr-boundaries-encrypted-0001", body=pdf_bytes(1, encrypted=True))
        assert ocr_pdf(client, csrf, asset_id=encrypted["id"]).status_code == 422
        too_many = upload_pdf(client, csrf, key="pdf-ocr-boundaries-pages-0001", body=pdf_bytes(11))
        page_limit = ocr_pdf(client, csrf, asset_id=too_many["id"])
        assert page_limit.status_code == 413
        assert "10" in page_limit.json()["message"]

        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            before_busy = conn.execute("SELECT COUNT(*) FROM web_document_operations WHERE kind='pdf_ocr'").fetchone()[0]
        assert operations._PDF_TO_IMAGES_CAPACITY.acquire(blocking=False)
        try:
            assert ocr_pdf(client, csrf, asset_id=source["id"]).status_code == 429
        finally:
            operations._PDF_TO_IMAGES_CAPACITY.release()
        assert operations._IMAGE_OCR_CAPACITY.acquire(blocking=False)
        try:
            assert ocr_pdf(client, csrf, asset_id=source["id"]).status_code == 429
        finally:
            operations._IMAGE_OCR_CAPACITY.release()
        # The renderer reservation made before the OCR gate must have rolled
        # back: a new explicit acquisition proves it was not leaked.
        assert operations._PDF_TO_IMAGES_CAPACITY.acquire(blocking=False)
        operations._PDF_TO_IMAGES_CAPACITY.release()
        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_document_operations WHERE kind='pdf_ocr'").fetchone()[0] == before_busy

    with make_client(tmp_path, monkeypatch, pdf_ocr_enabled=False) as disabled:
        csrf = register_and_login(disabled, "pdf-ocr-disabled@example.com")
        response = ocr_pdf(disabled, csrf, asset_id="11111111-1111-4111-8111-111111111111")
        assert response.status_code == 503
        assert "WEBAPP_DOCUMENT_OCR_PDF_ENABLED" in response.json()["message"]


def test_pdf_ocr_skips_blank_pages_never_fakes_text_and_marks_tampered_output_unavailable(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-ocr-truth@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        source = upload_pdf(client, csrf, key="pdf-ocr-truth-source-0001", body=pdf_text_bytes(["one", "two"]))

        monkeypatch.setattr(operations, "_image_ocr_runtime", fake_runtime("\x00\r\n\t   ", "Chỉ trang hai"))
        partial = ocr_pdf(client, csrf, asset_id=source["id"])
        assert partial.status_code == 200
        partial_operation = partial.json()["data"]["operation"]
        partial_download = client.get(f"/api/v1/document-operations/{partial_operation['id']}/download")
        assert partial_download.content.decode("utf-8") == "=== Trang 2 ===\nChỉ trang hai\n"

        all_blank_source = upload_pdf(client, csrf, key="pdf-ocr-truth-blank-0001", body=pdf_text_bytes(["one", "two"]))
        monkeypatch.setattr(operations, "_image_ocr_runtime", fake_runtime("\x00\r\n", "\t "))
        blank = ocr_pdf(client, csrf, asset_id=all_blank_source["id"])
        assert blank.status_code == 200
        assert blank.json()["status"] == "guarded"
        assert blank.json()["error_code"] == "WEB_DOCUMENT_OCR_TEXT_NOT_FOUND"
        blank_operation = blank.json()["data"]["operation"]
        assert blank_operation["download_ready"] is False and blank_operation["byte_size"] is None
        assert client.get(f"/api/v1/document-operations/{blank_operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"

        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            output_key = conn.execute(
                "SELECT storage_key FROM web_document_operations WHERE id=?", (partial_operation["id"],)
            ).fetchone()[0]
            blank_row = conn.execute(
                "SELECT state, failure_code, storage_key FROM web_document_operations WHERE id=?", (blank_operation["id"],)
            ).fetchone()
        assert blank_row == ("guarded", "OCR_TEXT_NOT_FOUND", None)
        (tmp_path / "private-document-outputs" / output_key).write_bytes(b"tampered")
        unavailable = client.get(f"/api/v1/document-operations/{partial_operation['id']}/download")
        assert unavailable.json()["error_code"] == "WEB_DOCUMENT_OPERATION_UNAVAILABLE"
        assert client.get(f"/api/v1/document-operations/{partial_operation['id']}").json()["data"]["operation"]["state"] == "unavailable"


def test_pdf_ocr_timeout_is_terminal_and_never_replayed_as_runtime_readiness(tmp_path, monkeypatch):
    class TimeoutTesseract:
        calls = 0

        @classmethod
        def image_to_string(cls, _image, *args, **kwargs):
            cls.calls += 1
            raise RuntimeError("Tesseract process timeout")

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-ocr-timeout@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(
            operations,
            "_image_ocr_runtime",
            lambda: (TimeoutTesseract, frozenset({"eng", "vie"})),
        )
        source = upload_pdf(client, csrf, key="pdf-ocr-timeout-source-0001", body=pdf_bytes(1))

        timed_out = ocr_pdf(client, csrf, asset_id=source["id"])
        assert timed_out.status_code == 422
        assert "timeout" not in timed_out.text.casefold()
        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            state, failure_code = conn.execute(
                "SELECT state, failure_code FROM web_document_operations WHERE kind='pdf_ocr'"
            ).fetchone()
        assert (state, failure_code) == ("failed", "OCR_TIMEOUT")

        replay = ocr_pdf(client, csrf, asset_id=source["id"])
        assert replay.status_code == 200
        assert replay.json()["status"] == "failed"
        assert TimeoutTesseract.calls == 1


def test_document_operation_download_seals_the_verified_descriptor_before_delivery(tmp_path, monkeypatch):
    """A later pathname mutation cannot alter bytes already prepared for HTTP."""

    with make_client(tmp_path, monkeypatch):
        operations = importlib.import_module("copyfast_document_operations")
        root = tmp_path / "sealed-document-operation-output"
        output = root / "outputs" / ("a" * 32 + ".txt")
        output.parent.mkdir(parents=True)
        original = b"verified private document output\n"
        output.write_bytes(original)
        digest = hashlib.sha256(original).hexdigest()
        pinned = operations._open_verified_operation_output(
            output,
            expected_bytes=len(original),
            expected_digest=digest,
        )
        assert pinned is not None
        sealed = operations._seal_verified_operation_output(
            pinned,
            expected_bytes=len(original),
            expected_digest=digest,
        )
        assert sealed is not None
        try:
            output.write_bytes(b"changed after verification")
            assert sealed.read() == original
        finally:
            sealed.close()
