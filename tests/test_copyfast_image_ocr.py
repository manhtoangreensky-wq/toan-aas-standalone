"""Focused security and delivery contracts for private Image OCR.

The OCR runtime is deliberately mocked at its local adapter boundary.  These
tests exercise the real Asset Vault, ownership, image inspection, private
artifact, and operation-lifecycle paths without requiring Tesseract to be
installed on the test machine.
"""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient
from PIL import Image


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch, *, ocr_enabled: bool = True) -> TestClient:
    """Build an isolated app with every unrelated decoder feature disabled."""

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-image-ocr-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-image-ocr-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "private-document-outputs"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OCR_IMAGE_ENABLED", "true" if ocr_enabled else "false")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OCR_PDF_ENABLED", "false")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "OCR Owner"},
    ).status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def image_bytes(image_format: str, *, size: tuple[int, int] = (160, 100)) -> bytes:
    image = Image.new("RGB", size, (32, 144, 240))
    stream = BytesIO()
    try:
        image.save(stream, format=image_format, quality=95)
        return stream.getvalue()
    finally:
        image.close()


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
        data={"display_name": "Ảnh OCR private"},
        files={"file": (name, body, content_type)},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def upload_non_image(client: TestClient, csrf: str, *, key: str) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Không phải ảnh OCR"},
        files={"file": ("source.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 200
    return response.json()["data"]["asset"]


def ocr(client: TestClient, csrf: str, *, asset_id: str, language: str = "auto"):
    """The browser contract intentionally has exactly two fields."""

    return client.post(
        "/api/v1/document-operations/ocr-image",
        headers={"X-CSRF-Token": csrf},
        json={"source_asset_id": asset_id, "language": language},
    )


class FakeLocalTesseract:
    """Deterministic local adapter; no binary, provider, or network required."""

    calls: list[dict[str, object]] = []

    @classmethod
    def image_to_string(cls, image, *args, **kwargs) -> str:
        cls.calls.append({"size": image.size, "args": args, "kwargs": kwargs})
        return "Văn bản OCR đã xác minh\r\nDòng thứ hai\x00"


def _fake_runtime():
    FakeLocalTesseract.calls.clear()
    return FakeLocalTesseract, frozenset({"eng", "vie"})


@pytest.mark.parametrize(
    ("image_format", "filename", "content_type"),
    [
        ("JPEG", "source.jpg", "image/jpeg"),
        ("PNG", "source.png", "image/png"),
        ("WEBP", "source.webp", "image/webp"),
    ],
)
def test_image_ocr_delivers_only_verified_private_text_for_owner_assets(
    tmp_path,
    monkeypatch,
    image_format: str,
    filename: str,
    content_type: str,
):
    """JPEG/PNG/WebP sources produce an owner-only UTF-8 text attachment."""

    with make_client(tmp_path, monkeypatch) as first:
        csrf = register_and_login(first, f"ocr-owner-{image_format.lower()}@example.com")
        assert first.get("/documents/ocr").status_code == 200
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "_image_ocr_runtime", _fake_runtime)
        source = upload_image(
            first,
            csrf,
            key=f"ocr-{image_format.lower()}-source-0001",
            body=image_bytes(image_format),
            name=filename,
            content_type=content_type,
        )

        # A signed session without the CSRF proof cannot start an operation.
        denied = first.post(
            "/api/v1/document-operations/ocr-image",
            json={"source_asset_id": source["id"], "language": "auto"},
        )
        assert denied.status_code == 403

        created = ocr(first, csrf, asset_id=source["id"])
        assert created.status_code == 200
        payload = created.json()
        assert payload["ok"] is True
        assert payload["status"] == "completed"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "image_ocr"
        assert operation["source_asset_id"] == source["id"]
        assert operation["source_count"] == 1
        assert operation["language"] == "auto"
        assert operation["content_type"] == "text/plain; charset=utf-8"
        assert operation["original_filename"] == "toan-aas-image-ocr.txt"
        assert operation["download_ready"] is True
        assert FakeLocalTesseract.calls == [
            {
                "size": (160, 100),
                "args": (),
                "kwargs": {"lang": "vie+eng", "config": "--oem 1 --psm 6", "timeout": 30},
            }
        ]
        for forbidden in ("storage_key", "sha256", "source_sha", "filesystem", "provider", "payment", "wallet", "telegram"):
            assert forbidden not in created.text.lower()

        # The endpoint has no browser-controlled idempotency field. A second
        # identical owner/source/language request returns the same artifact.
        replay = ocr(first, csrf, asset_id=source["id"])
        assert replay.status_code == 200
        assert replay.json()["data"]["operation"]["id"] == operation["id"]

        download = first.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("text/plain; charset=utf-8")
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["referrer-policy"] == "no-referrer"
        assert download.headers["content-security-policy"] == "sandbox"
        assert "attachment" in download.headers["content-disposition"]
        assert download.content.decode("utf-8") == "Văn bản OCR đã xác minh\nDòng thứ hai\n"

        detail = first.get(f"/api/v1/document-operations/{operation['id']}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == ["queued", "processing", "completed"]
        with sqlite3.connect(tmp_path / "copyfast-image-ocr-test.db") as conn:
            audit = conn.execute(
                "SELECT detail FROM web_audit_events WHERE action='web.document_operation.image_ocr'"
            ).fetchone()
            storage_key = conn.execute(
                "SELECT storage_key FROM web_document_operations WHERE id=?", (operation["id"],)
            ).fetchone()[0]
        assert audit and "characters=" in audit[0] and "pixels=16000" in audit[0]
        assert source["id"] not in audit[0]
        assert Path(storage_key).suffix == ".txt"

        # A different signed Web account cannot see either the source or the
        # derived private artifact.
        with make_client(tmp_path, monkeypatch) as second:
            csrf_second = register_and_login(second, f"ocr-other-{image_format.lower()}@example.com")
            second_operations = importlib.import_module("copyfast_document_operations")
            monkeypatch.setattr(second_operations, "_image_ocr_runtime", _fake_runtime)
            hidden = second.get(f"/api/v1/document-operations/{operation['id']}")
            assert hidden.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            hidden_download = second.get(f"/api/v1/document-operations/{operation['id']}/download")
            assert hidden_download.json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"
            rejected = ocr(second, csrf_second, asset_id=source["id"])
            assert rejected.json()["error_code"] == "WEB_DOCUMENT_OCR_SOURCE_NOT_FOUND"


def test_image_ocr_closes_schema_source_and_decoder_capacity_boundaries(tmp_path, monkeypatch):
    """No URL/path/raw upload, foreign source, oversized decode, or busy slot leaks through."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "ocr-boundaries@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        monkeypatch.setattr(operations, "_image_ocr_runtime", _fake_runtime)
        source = upload_image(
            client,
            csrf,
            key="ocr-boundaries-source-0001",
            body=image_bytes("PNG"),
            name="source.png",
            content_type="image/png",
        )

        for invalid in (
            {"source_asset_id": source["id"], "language": "fr"},
            {"source_asset_id": source["id"], "language": "AUTO"},
            {"source_asset_id": source["id"], "language": "auto", "url": "https://untrusted.invalid/image.png"},
            {"source_asset_id": source["id"], "language": "auto", "path": "C:\\private\\source.png"},
            {"source_asset_id": source["id"], "language": "auto", "file": "browser bytes are forbidden"},
        ):
            response = client.post(
                "/api/v1/document-operations/ocr-image",
                headers={"X-CSRF-Token": csrf},
                json=invalid,
            )
            assert response.status_code == 422

        oversized = client.post(
            "/api/v1/document-operations/ocr-image",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"source_asset_id":"' + (b"x" * (17 * 1024)) + b'","language":"auto"}',
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_DOCUMENT_OPERATION_BODY_TOO_LARGE"

        non_image = upload_non_image(client, csrf, key="ocr-boundaries-non-image-0001")
        invalid_source = ocr(client, csrf, asset_id=non_image["id"])
        assert invalid_source.status_code == 422

        # Serialize OCR against the shared image decoder: no DB lifecycle row
        # may be created when the slot is already held.
        assert operations._IMAGE_OCR_CAPACITY.acquire(blocking=False)
        try:
            busy = ocr(client, csrf, asset_id=source["id"])
            assert busy.status_code == 429
        finally:
            operations._IMAGE_OCR_CAPACITY.release()
        with sqlite3.connect(tmp_path / "copyfast-image-ocr-test.db") as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_document_operations WHERE kind='image_ocr'").fetchone()[0] == 0

        # Keep the actual decoder path in the test, but shrink the constant so
        # a tiny fixture proves the 16 MP circuit fails closed before OCR.
        monkeypatch.setattr(operations, "MAX_IMAGE_PIXELS_PER_SOURCE", 1)
        pixel_limited = ocr(client, csrf, asset_id=source["id"])
        assert pixel_limited.status_code == 413
        assert "16 MP" in pixel_limited.json()["message"]
        with sqlite3.connect(tmp_path / "copyfast-image-ocr-test.db") as conn:
            failed = conn.execute(
                "SELECT state, storage_key FROM web_document_operations WHERE kind='image_ocr'"
            ).fetchone()
        assert failed == ("failed", None)
        assert not list((tmp_path / "private-document-outputs" / "outputs").glob("*.txt"))

    with make_client(tmp_path, monkeypatch, ocr_enabled=False) as disabled:
        csrf = register_and_login(disabled, "ocr-disabled@example.com")
        response = ocr(
            disabled,
            csrf,
            asset_id="11111111-1111-4111-8111-111111111111",
        )
        assert response.status_code == 503
        assert "WEBAPP_DOCUMENT_OCR_IMAGE_ENABLED" in response.json()["message"]


def test_image_ocr_guarded_runtime_language_and_empty_text_never_create_fake_delivery(tmp_path, monkeypatch):
    """Readiness guards create no output; empty OCR records a non-downloadable state."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "ocr-guarded@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        source = upload_image(
            client,
            csrf,
            key="ocr-guarded-source-0001",
            body=image_bytes("JPEG"),
            name="source.jpg",
            content_type="image/jpeg",
        )

        def unavailable_runtime():
            raise operations.DocumentOperationError("runtime missing", code="OCR_RUNTIME_UNAVAILABLE")

        monkeypatch.setattr(operations, "_image_ocr_runtime", unavailable_runtime)
        runtime_guard = ocr(client, csrf, asset_id=source["id"])
        assert runtime_guard.status_code == 200
        assert runtime_guard.json()["status"] == "guarded"
        assert runtime_guard.json()["error_code"] == "WEB_DOCUMENT_OCR_RUNTIME_UNAVAILABLE"
        assert "operation" not in runtime_guard.json()["data"]

        monkeypatch.setattr(operations, "_image_ocr_runtime", lambda: (FakeLocalTesseract, frozenset({"eng"})))
        language_guard = ocr(client, csrf, asset_id=source["id"], language="vi")
        assert language_guard.status_code == 200
        assert language_guard.json()["status"] == "guarded"
        assert language_guard.json()["error_code"] == "WEB_DOCUMENT_OCR_LANGUAGE_UNAVAILABLE"
        assert "operation" not in language_guard.json()["data"]

        class EmptyLocalTesseract:
            @staticmethod
            def image_to_string(*_args, **_kwargs) -> str:
                return "\x00\r\n\t   "

        monkeypatch.setattr(operations, "_image_ocr_runtime", lambda: (EmptyLocalTesseract, frozenset({"eng", "vie"})))
        empty = ocr(client, csrf, asset_id=source["id"])
        assert empty.status_code == 200
        payload = empty.json()
        assert payload["ok"] is False
        assert payload["status"] == "guarded"
        assert payload["error_code"] == "WEB_DOCUMENT_OCR_TEXT_NOT_FOUND"
        operation = payload["data"]["operation"]
        assert operation["kind"] == "image_ocr"
        assert operation["state"] == "guarded"
        assert operation["download_ready"] is False
        assert operation["byte_size"] is None
        assert client.get(f"/api/v1/document-operations/{operation['id']}/download").json()["error_code"] == "WEB_DOCUMENT_OPERATION_NOT_FOUND"

        with sqlite3.connect(tmp_path / "copyfast-image-ocr-test.db") as conn:
            rows = conn.execute(
                "SELECT state, failure_code, storage_key FROM web_document_operations WHERE kind='image_ocr' ORDER BY created_at"
            ).fetchall()
            source_state = conn.execute("SELECT state FROM web_asset_files WHERE id=?", (source["id"],)).fetchone()[0]
        assert rows == [("guarded", "OCR_TEXT_NOT_FOUND", None)]
        assert source_state == "active"
        assert not list((tmp_path / "private-document-outputs" / "outputs").glob("*.txt"))


def test_image_ocr_retries_a_transient_runtime_guard_with_the_same_private_operation(tmp_path, monkeypatch):
    """A recovered local runtime may resume, while empty text remains final."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "ocr-retry-runtime@example.com")
        operations = importlib.import_module("copyfast_document_operations")
        source = upload_image(
            client,
            csrf,
            key="ocr-retry-runtime-source-0001",
            body=image_bytes("PNG"),
            name="source.png",
            content_type="image/png",
        )

        class FlakyLocalTesseract:
            calls = 0

            @classmethod
            def image_to_string(cls, *_args, **_kwargs) -> str:
                cls.calls += 1
                if cls.calls == 1:
                    raise RuntimeError("local runtime temporarily unavailable")
                return "Kết quả OCR phục hồi"

        monkeypatch.setattr(operations, "_image_ocr_runtime", lambda: (FlakyLocalTesseract, frozenset({"eng", "vie"})))
        first = ocr(client, csrf, asset_id=source["id"])
        assert first.status_code == 200
        assert first.json()["status"] == "guarded"
        assert first.json()["error_code"] == "WEB_DOCUMENT_OCR_RUNTIME_UNAVAILABLE"
        operation_id = first.json()["data"]["operation"]["id"]

        resumed = ocr(client, csrf, asset_id=source["id"])
        assert resumed.status_code == 200
        assert resumed.json()["status"] == "completed"
        assert resumed.json()["data"]["operation"]["id"] == operation_id
        detail = client.get(f"/api/v1/document-operations/{operation_id}")
        assert [event["state"] for event in detail.json()["data"]["events"]] == [
            "queued", "processing", "guarded", "processing", "completed"
        ]
