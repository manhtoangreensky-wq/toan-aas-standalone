"""Security and output contracts for Web-native PDF Split and Merge."""

from __future__ import annotations

from io import BytesIO
import importlib
from pathlib import Path
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, TextStringObject


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry",
    "copyfast_api", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
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


def test_pdf_split_rejects_archived_tampered_encrypted_and_oversize_page_inputs_without_fake_success(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "pdf-safety@example.com")
        archived_source = upload_pdf(client, csrf, key="pdf-source-archive-0001")
        archived = client.post(
            f"/api/v1/asset-vault/{archived_source['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "pdf-source-archive-action-0001"},
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


def test_pdf_split_has_no_bot_bridge_public_storage_or_unbounded_parser_contract():
    source = Path("copyfast_document_operations.py").read_text(encoding="utf-8")
    assert "from copyfast_bridge" not in source
    assert "import copyfast_bridge" not in source
    assert "bridge_request(" not in source
    assert "MAX_INPUT_BYTES = 20 * 1024 * 1024" in source
    assert "MAX_PAGES = 30" in source
    assert "PDF_EXCLUDED_PAGE_KEYS" in source
    assert 'app.mount("/document-operations"' not in Path("app.py").read_text(encoding="utf-8")
