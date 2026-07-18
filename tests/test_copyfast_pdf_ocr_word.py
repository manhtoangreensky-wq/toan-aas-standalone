"""Focused contracts for private scan-PDF OCR-to-DOCX delivery.

The local OCR adapter is mocked. Sessions, Asset Vault ownership, PDF parsing,
PDFium rasterization, DOCX verification, lifecycle storage and attachment
delivery are exercised without a Bot, provider, wallet, PayOS or live
Tesseract binary.
"""

from __future__ import annotations

from io import BytesIO
import importlib
import sqlite3
import sys

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(
    tmp_path,
    monkeypatch,
    *,
    ocr_word_enabled: bool = True,
    pdf_ocr_enabled: bool = True,
    pdf_to_word_enabled: bool = True,
) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-pdf-ocr-word-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-pdf-ocr-word-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "private-document-outputs"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OCR_PDF_ENABLED", "true" if pdf_ocr_enabled else "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_WORD_ENABLED", "true" if pdf_to_word_enabled else "false")
    monkeypatch.setenv("WEBAPP_PDF_OCR_WORD_ENABLED", "true" if ocr_word_enabled else "false")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OCR_IMAGE_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_TO_PDF_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_IMAGES_ENABLED", "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "PDF OCR Word Owner"},
    ).status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def pdf_text_bytes(pages: list[str]) -> bytes:
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
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def upload_pdf(client: TestClient, csrf: str, *, key: str, body: bytes) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Private scan PDF"},
        files={"file": ("scan.pdf", body, "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def ocr_word(client: TestClient, csrf: str, *, asset_id: str, language: str = "auto"):
    return client.post(
        "/api/v1/document-operations/pdf-ocr-to-word",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "language": language},
    )


class FakeTesseract:
    responses: list[str] = []
    calls = 0

    @classmethod
    def image_to_string(cls, _image, *args, **kwargs) -> str:
        cls.calls += 1
        return cls.responses.pop(0) if cls.responses else ""


def fake_runtime(*responses: str):
    FakeTesseract.responses = list(responses)
    FakeTesseract.calls = 0
    return lambda: (FakeTesseract, frozenset({"eng", "vie"}))


def test_scan_pdf_ocr_to_word_is_private_verified_and_owner_scoped(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, "pdf-ocr-word-owner@example.com")
        assert first.get("/documents/pdf-ocr-to-word").status_code == 200
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "_image_ocr_runtime", fake_runtime("Trang quét một\r\nDòng A", "Trang quét hai"))
        source = upload_pdf(first, csrf, key="pdf-ocr-word-source-0001", body=pdf_text_bytes(["source one", "source two"]))

        denied = first.post(
            "/api/v1/document-operations/pdf-ocr-to-word",
            json={"source_asset_id": source["id"], "language": "auto"},
        )
        assert denied.status_code == 403
        assert first.post(
            "/api/v1/document-operations/pdf-ocr-to-word",
            headers={"X-CSRF-Token": csrf},
            json={"source_asset_id": source["id"], "language": "auto", "output_format": "pdf"},
        ).status_code == 422

        created = ocr_word(first, csrf, asset_id=source["id"])
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True and payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "pdf_ocr_word"
        assert operation["language"] == "auto"
        assert operation["source_page_count"] == 2
        assert operation["content_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert operation["original_filename"] == "toan-aas-pdf-ocr.docx"
        assert operation["download_ready"] is True
        for forbidden in ("storage_key", "sha256", "source_sha", "provider", "payment", "wallet", "telegram", "Trang quét một"):
            assert forbidden.casefold() not in created.text.casefold()

        replay = ocr_word(first, csrf, asset_id=source["id"])
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        assert FakeTesseract.calls == 2

        download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["content-security-policy"] == "sandbox"
        assert len(download.content) == operation["byte_size"]
        document = Document(BytesIO(download.content))
        assert [paragraph.text for paragraph in document.paragraphs if paragraph.text] == [
            "=== Trang 1 ===", "Trang quét một", "Dòng A", "=== Trang 2 ===", "Trang quét hai"
        ]

        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-word-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.pdf_ocr_word' AND target=?",
                (operation["id"],),
            ).fetchone()
        assert audit and "recognized_pages=2" in audit[0]
        assert source["id"] not in audit[0] and "Trang quét một" not in audit[0]

        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, "pdf-ocr-word-other@example.com")
            second_operations = importlib.import_module("copyfast_document_operations")
            monkeypatch.setattr(second_operations, "_image_ocr_runtime", fake_runtime("never used"))
            assert second.get(f"/api/v1/document-operations/{operation['id']}").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert second.get(f"/api/v1/document-operations/{operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert ocr_word(second, csrf_second, asset_id=source["id"]).json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"


def test_scan_pdf_ocr_to_word_guards_blank_times_out_terminally_and_fails_closed(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-ocr-word-safety@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        source = upload_pdf(client, csrf, key="pdf-ocr-word-blank-0001", body=pdf_text_bytes(["scan"]))
        monkeypatch.setattr(operations, "_image_ocr_runtime", fake_runtime("\x00\r\n\t "))
        blank = ocr_word(client, csrf, asset_id=source["id"])
        assert blank.status_code == 200
        assert blank.json()["status"] == "guarded"
        blank_operation = blank.json()["data"]["operation"]
        assert blank_operation["download_ready"] is False
        assert client.get(f"/api/v1/document-operations/{blank_operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"

        busy_source = upload_pdf(client, csrf, key="pdf-ocr-word-busy-0001", body=pdf_text_bytes(["scan"]))
        assert operations._PDF_TO_WORD_CAPACITY.acquire(blocking=False)
        try:
            assert ocr_word(client, csrf, asset_id=busy_source["id"]).status_code == 429
        finally:
            operations._PDF_TO_WORD_CAPACITY.release()

        class TimeoutTesseract:
            calls = 0

            @classmethod
            def image_to_string(cls, _image, *args, **kwargs):
                cls.calls += 1
                raise RuntimeError("Tesseract process timeout")

        timeout_source = upload_pdf(client, csrf, key="pdf-ocr-word-timeout-0001", body=pdf_text_bytes(["scan"]))
        monkeypatch.setattr(operations, "_image_ocr_runtime", lambda: (TimeoutTesseract, frozenset({"eng", "vie"})))
        timed_out = ocr_word(client, csrf, asset_id=timeout_source["id"])
        assert timed_out.status_code == 422
        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-word-test.db") as conn:
            state, failure_code = conn.execute(
                "SELECT state, failure_code FROM web_document_operations WHERE kind='pdf_ocr_word' ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
        assert (state, failure_code) == ("failed", "OCR_TIMEOUT")
        replay = ocr_word(client, csrf, asset_id=timeout_source["id"])
        assert replay.status_code == 200 and replay.json()["status"] == "failed"
        assert TimeoutTesseract.calls == 1

    with make_client(tmp_path, monkeypatch, ocr_word_enabled=False) as disabled:
        csrf = register_and_login(disabled, "pdf-ocr-word-disabled@example.com")
        response = ocr_word(disabled, csrf, asset_id="11111111-1111-4111-8111-111111111111")
        assert response.status_code == 503
        assert "WEBAPP_PDF_OCR_WORD_ENABLED" in response.json()["message"]


def test_ocr_word_misconfiguration_does_not_probe_an_inactive_prerequisite_at_startup(tmp_path, monkeypatch):
    def unavailable_runtime(*_args, **_kwargs):
        raise RuntimeError("inactive runtime must not be probed")

    # The DOCX prerequisite remains active, but PDF OCR does not.  A raw OCR→Word
    # flag must not cause PDFium to be probed at startup in that configuration.
    inactive_pdf_ocr = make_client(
        tmp_path,
        monkeypatch,
        pdf_ocr_enabled=False,
        pdf_to_word_enabled=True,
    )
    operations = importlib.import_module("copyfast_document_operations")
    monkeypatch.setattr(operations, "_pdf_to_images_classes", unavailable_runtime)
    with inactive_pdf_ocr as client:
        status = client.get("/api/v1/core/status")
        assert status.status_code == 200
        assert status.json()["data"]["flags"]["pdf_ocr_word_enabled"] is False

    # Conversely, when PDF OCR is active but DOCX is not, startup must not probe
    # the DOCX writer merely because the composite flag is present.
    inactive_docx = make_client(
        tmp_path,
        monkeypatch,
        pdf_ocr_enabled=True,
        pdf_to_word_enabled=False,
    )
    operations = importlib.import_module("copyfast_document_operations")
    monkeypatch.setattr(operations, "_word_classes", unavailable_runtime)
    with inactive_docx as client:
        status = client.get("/api/v1/core/status")
        assert status.status_code == 200
        assert status.json()["data"]["flags"]["pdf_ocr_word_enabled"] is False
