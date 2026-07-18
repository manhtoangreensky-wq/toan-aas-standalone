"""Focused safety/delivery tests for bounded private PDF OCR.

The test uses a real private Asset Vault and PDFium renderer, while replacing
only the service-installed Tesseract adapter. No provider, Bot, payment or
network is involved.
"""

from __future__ import annotations

import importlib
from io import BytesIO
import sqlite3
import sys

from fastapi.testclient import TestClient
from pypdf import PdfWriter
import pytest


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
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return response.json()["data"]["csrf_token"]


def pdf_bytes(pages: int = 1, *, page_size: tuple[int, int] = (144, 144)) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=page_size[0], height=page_size[1])
    payload = BytesIO()
    writer.write(payload)
    return payload.getvalue()


def upload_pdf(client: TestClient, csrf: str, *, key: str, body: bytes) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "PDF OCR private"},
        files={"file": ("source.pdf", body, "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def ocr(client: TestClient, csrf: str, *, asset_id: str, language: str = "auto"):
    return client.post(
        "/api/v1/document-operations/ocr-pdf",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "language": language},
    )


class FakeLocalTesseract:
    calls: list[dict[str, object]] = []

    @classmethod
    def image_to_string(cls, image, *args, **kwargs) -> str:
        cls.calls.append({"size": image.size, "args": args, "kwargs": kwargs})
        return f"Văn bản trang {len(cls.calls)}\r\nĐã xác minh\x00"


def _fake_runtime():
    return FakeLocalTesseract, frozenset({"eng", "vie"})


def test_pdf_ocr_owner_scoped_replays_and_delivers_only_verified_text(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        FakeLocalTesseract.calls.clear()
        csrf = register_and_login(client, "pdf-ocr-owner@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "_image_ocr_runtime", _fake_runtime)
        source = upload_pdf(client, csrf, key="pdf-ocr-source-0001", body=pdf_bytes(2))

        denied = client.post(
            "/api/v1/document-operations/ocr-pdf",
            json={"source_asset_id": source["id"], "language": "auto"},
        )
        assert denied.status_code == 403

        created = ocr(client, csrf, asset_id=source["id"])
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "pdf_ocr"
        assert operation["source_asset_id"] == source["id"]
        assert operation["source_page_count"] == 2
        assert operation["language"] == "auto"
        assert operation["content_type"] == "text/plain; charset=utf-8"
        assert operation["original_filename"] == "toan-aas-pdf-ocr.txt"
        assert operation["download_ready"] is True
        assert [call["size"] for call in FakeLocalTesseract.calls] == [(288, 288), (288, 288)]
        assert all(call["kwargs"] == {"lang": "vie+eng", "config": "--oem 1 --psm 6", "timeout": 15} for call in FakeLocalTesseract.calls)
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment", "wallet", "telegram"):
            assert forbidden not in created.text.lower()

        replay = ocr(client, csrf, asset_id=source["id"])
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]
        assert len(FakeLocalTesseract.calls) == 2

        def runtime_removed():
            raise operations.DocumentOperationError("runtime removed", code="OCR_RUNTIME_UNAVAILABLE")

        # A verified completed receipt is still a private Web artifact even
        # if a later deploy temporarily lacks the optional OCR executable.
        monkeypatch.setattr(operations, "_image_ocr_runtime", runtime_removed)
        offline_replay = ocr(client, csrf, asset_id=source["id"])
        assert offline_replay.status_code == 200
        assert offline_replay.json()["status"] == "completed"
        assert offline_replay.json()["data"]["operation"]["id"] == operation["id"]
        assert len(FakeLocalTesseract.calls) == 2

        downloaded = client.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"].startswith("text/plain; charset=utf-8")
        assert downloaded.headers["cache-control"] == "no-store, private"
        assert downloaded.headers["x-content-type-options"] == "nosniff"
        assert downloaded.headers["referrer-policy"] == "no-referrer"
        assert downloaded.headers["content-security-policy"] == "sandbox"
        assert downloaded.content.decode("utf-8") == (
            "--- Trang 1 ---\nVăn bản trang 1\nĐã xác minh\n\n"
            "--- Trang 2 ---\nVăn bản trang 2\nĐã xác minh\n"
        )
        assert [event["state"] for event in client.get(f"/api/v1/document-operations/{operation['id']}").json()["data"]["events"]] == [
            "queued", "processing", "completed"
        ]

        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.pdf_ocr'"
            ).fetchone()
        assert audit and "pages=2" in audit[0] and source["id"] not in audit[0]

        with make_client(tmp_path, monkeypatch) as other:
            csrf_other = register_and_login(other, "pdf-ocr-other@example.com")
            second_operations = importlib.import_module("copyfast_document_operations")
            monkeypatch.setattr(second_operations, "_image_ocr_runtime", _fake_runtime)
            assert other.get(f"/api/v1/document-operations/{operation['id']}").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert other.get(f"/api/v1/document-operations/{operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            assert ocr(other, csrf_other, asset_id=source["id"]).json()["error_code"] == "WEB_DOCUMENT_SOURCE_NOT_FOUND"


def test_pdf_ocr_fails_closed_for_busy_bounds_empty_text_and_disabled_feature(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        FakeLocalTesseract.calls.clear()
        csrf = register_and_login(client, "pdf-ocr-boundaries@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "_image_ocr_runtime", _fake_runtime)
        source = upload_pdf(client, csrf, key="pdf-ocr-boundary-source-0001", body=pdf_bytes(1))

        for invalid in (
            {"source_asset_id": source["id"], "language": "fr"},
            {"source_asset_id": source["id"], "language": "AUTO"},
            {"source_asset_id": source["id"], "language": "auto", "url": "https://untrusted.invalid/source.pdf"},
            {"source_asset_id": source["id"], "language": "auto", "page_range": "1-2"},
        ):
            response = client.post("/api/v1/document-operations/ocr-pdf", headers={"X-CSRF-Token": csrf}, json=invalid)
            assert response.status_code == 422

        assert operations._PDF_TO_IMAGES_CAPACITY.acquire(blocking=False)
        try:
            busy = ocr(client, csrf, asset_id=source["id"])
            assert busy.status_code == 429
        finally:
            operations._PDF_TO_IMAGES_CAPACITY.release()
        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_document_operations WHERE kind='pdf_ocr'").fetchone()[0] == 0

        too_many = upload_pdf(client, csrf, key="pdf-ocr-many-pages-0001", body=pdf_bytes(6))
        limited = ocr(client, csrf, asset_id=too_many["id"])
        assert limited.status_code == 413
        assert "1 đến 5" in limited.json()["message"]

        class EmptyLocalTesseract:
            @staticmethod
            def image_to_string(*_args, **_kwargs) -> str:
                return "\x00\r\n\t   "

        empty_source = upload_pdf(client, csrf, key="pdf-ocr-empty-source-0001", body=pdf_bytes(1))
        monkeypatch.setattr(operations, "_image_ocr_runtime", lambda: (EmptyLocalTesseract, frozenset({"eng", "vie"})))
        empty = ocr(client, csrf, asset_id=empty_source["id"])
        assert empty.status_code == 200
        assert empty.json()["status"] == "guarded"
        assert empty.json()["error_code"] == "WEB_DOCUMENT_OCR_TEXT_NOT_FOUND"
        empty_operation = empty.json()["data"]["operation"]
        assert empty_operation["kind"] == "pdf_ocr"
        assert empty_operation["download_ready"] is False
        assert client.get(f"/api/v1/document-operations/{empty_operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"

    with make_client(tmp_path, monkeypatch, pdf_ocr_enabled=False) as disabled:
        csrf = register_and_login(disabled, "pdf-ocr-disabled@example.com")
        response = ocr(disabled, csrf, asset_id="11111111-1111-4111-8111-111111111111")
        assert response.status_code == 503
        assert "WEBAPP_DOCUMENT_OCR_PDF_ENABLED" in response.json()["message"]


def test_pdf_ocr_runtime_guard_never_creates_a_lifecycle_or_txt(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-ocr-runtime@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        source = upload_pdf(client, csrf, key="pdf-ocr-runtime-source-0001", body=pdf_bytes(1))

        def missing_runtime():
            raise operations.DocumentOperationError("runtime missing", code="OCR_RUNTIME_UNAVAILABLE")

        monkeypatch.setattr(operations, "_image_ocr_runtime", missing_runtime)
        guarded = ocr(client, csrf, asset_id=source["id"])
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_DOCUMENT_OCR_RUNTIME_UNAVAILABLE"
        assert "operation" not in guarded.json()["data"]
        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_document_operations WHERE kind='pdf_ocr'").fetchone()[0] == 0
        assert not list((tmp_path / "private-document-outputs" / "outputs").glob("*.txt"))

    # PDFium/Pillow/pypdf are also optional local prerequisites. Their absence
    # must be detected before an operation row is created, exactly like a
    # missing Tesseract binary.
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-ocr-pdfium-runtime@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        source = upload_pdf(client, csrf, key="pdf-ocr-pdfium-source-0001", body=pdf_bytes(1))

        def missing_pdfium():
            raise operations.DocumentOperationError("pdfium missing", code="PDF_TO_IMAGES_RUNTIME_UNAVAILABLE")

        monkeypatch.setattr(operations, "_image_ocr_runtime", _fake_runtime)
        monkeypatch.setattr(operations, "_pdf_to_images_classes", missing_pdfium)
        guarded = ocr(client, csrf, asset_id=source["id"])
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_DOCUMENT_OCR_RUNTIME_UNAVAILABLE"
        with sqlite3.connect(tmp_path / "copyfast-pdf-ocr-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_document_operations WHERE kind='pdf_ocr'").fetchone()[0] == 0

    # A runtime can disappear after preflight (for example while a container
    # is being replaced). It still must leave a guarded, no-output receipt
    # rather than a false failed/completed job.
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-ocr-runtime-race@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        source = upload_pdf(client, csrf, key="pdf-ocr-race-source-0001", body=pdf_bytes(1))
        real_pdfium = operations._pdf_to_images_classes
        calls = 0

        def pdfium_disappears_after_preflight():
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_pdfium()
            raise operations.DocumentOperationError("pdfium stopped", code="PDF_TO_IMAGES_RUNTIME_UNAVAILABLE")

        monkeypatch.setattr(operations, "_image_ocr_runtime", _fake_runtime)
        monkeypatch.setattr(operations, "_pdf_to_images_classes", pdfium_disappears_after_preflight)
        guarded = ocr(client, csrf, asset_id=source["id"])
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "WEB_DOCUMENT_OCR_RUNTIME_UNAVAILABLE"
        operation = guarded.json()["data"]["operation"]
        assert operation["state"] == "guarded"
        assert operation["download_ready"] is False
        assert client.get(f"/api/v1/document-operations/{operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
