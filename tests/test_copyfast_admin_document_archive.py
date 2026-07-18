"""Focused contracts for the opt-in Web Admin Internal Document Archive.

The suite intentionally mounts only local signed-Web auth plus this router.
It never imports Bot runtime or makes provider, bridge, wallet/Xu, PayOS, job
or notification calls.
"""

from __future__ import annotations

import ast
import importlib
from io import BytesIO
from pathlib import Path
import sqlite3
import sys
from typing import Any
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_admin_document_archive"]


def make_app(tmp_path, monkeypatch, *, archive_enabled: bool = True, erp_enabled: bool = True) -> tuple[FastAPI, Any, Path, Path]:
    db_path = tmp_path / "archive-test.db"
    root = tmp_path / "private-admin-archive"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "admin-archive-test-session-secret")
    monkeypatch.setenv("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED", "true" if archive_enabled else "false")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true" if erp_enabled else "false")
    monkeypatch.setenv("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ROOT", str(root))
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    archive = importlib.import_module("copyfast_admin_document_archive")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(archive.router)
    return app, archive, db_path, root


def register_admin(client: TestClient, db_path: Path, email: str) -> tuple[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Archive Admin"},
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
        assert row
        account_id = str(row[0])
        conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE id=?", (account_id,))
        conn.commit()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery-staple"})
    assert response.status_code == 200 and response.json()["ok"] is True
    return response.json()["data"]["csrf_token"], account_id


def upload(
    client: TestClient,
    csrf: str,
    key: str,
    *,
    content: bytes = b"Tai lieu noi bo Web-native an toan.",
    filename: str = "architecture.txt",
    content_type: str = "text/plain",
):
    return client.post(
        "/api/v1/admin/internal-documents/documents/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={
            "department": "tech_codex",
            "document_type": "architecture_doc",
            "title": "Quy uoc kien truc Web noi bo",
            "tags_json": '["architecture", "web-native"]',
            "description": "Metadata van hanh khong tao external side effect.",
            "retention_label": "5_years",
            "confidentiality_level": "confidential",
        },
        files={"file": (filename, content, content_type)},
    )


def archive_payload(revision: int, key: str, action: str) -> dict[str, Any]:
    return {
        "expected_revision": revision,
        "acknowledgement": "ARCHIVE INTERNAL DOCUMENT" if action == "archive" else "RESTORE INTERNAL DOCUMENT",
        "confirm": True,
        "idempotency_key": key,
    }


def boundary(data: dict[str, Any]) -> None:
    assert data["execution"] == "web_native_admin_internal_document_archive_only"
    assert data["data_origin"] == "web_admin_archive_tables_and_private_volume_only"
    assert data["external_effects"] == "none"
    assert data["legacy_bot_scope"] == "TELEGRAM_ONLY"
    assert any("PayOS" in item for item in data["excluded_domains"])


def test_archive_is_opt_in_owner_scoped_and_has_no_external_runtime(tmp_path, monkeypatch):
    app, archive, db_path, _root = make_app(tmp_path, monkeypatch, archive_enabled=False)
    client = TestClient(app)
    try:
        route_calls = {
            (route.path, method): {dependency.call for dependency in route.dependant.dependencies}
            for route in archive.router.routes
            for method in (route.methods or set())
        }
        for path in (
            "/api/v1/admin/internal-documents/policy",
            "/api/v1/admin/internal-documents/summary",
            "/api/v1/admin/internal-documents/documents",
            "/api/v1/admin/internal-documents/documents/{document_id}",
            "/api/v1/admin/internal-documents/documents/{document_id}/versions",
            "/api/v1/admin/internal-documents/documents/{document_id}/events",
            "/api/v1/admin/internal-documents/documents/{document_id}/download",
            "/api/v1/admin/internal-documents/versions/{version_id}/download",
        ):
            assert archive.require_admin in route_calls[(path, "GET")]
        for path in (
            "/api/v1/admin/internal-documents/documents/upload",
            "/api/v1/admin/internal-documents/documents/{document_id}",
            "/api/v1/admin/internal-documents/documents/{document_id}/versions/upload",
            "/api/v1/admin/internal-documents/documents/{document_id}/archive",
            "/api/v1/admin/internal-documents/documents/{document_id}/restore",
        ):
            method = "PATCH" if path.endswith("{document_id}") else "POST"
            assert archive.require_admin_csrf in route_calls[(path, method)]

        assert client.get("/api/v1/admin/internal-documents/policy").status_code == 401
        csrf, _ = register_admin(client, db_path, "archive-admin@example.com")
        assert csrf
        assert client.get("/api/v1/admin/internal-documents/policy").status_code == 503
        monkeypatch.setenv("WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED", "true")
        policy = client.get("/api/v1/admin/internal-documents/policy")
        assert policy.status_code == 200 and policy.json()["ok"] is True
        boundary(policy.json()["data"])
        assert policy.json()["data"]["limits"]["file_bytes"] == 25 * 1024 * 1024

        tree = ast.parse(Path(archive.__file__).read_text(encoding="utf-8"))
        imported = {
            module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for module in ([alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""])
            if module
        }
        assert not {"copyfast_bridge", "requests", "httpx", "payos", "bot"}.intersection(imported)
        worker = (Path(archive.__file__).parent / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
        assert '"/" + "api/v1/admin/internal-documents"' in worker
        assert '"/admin/internal-documents"' in worker
    finally:
        client.close()


def test_archive_upload_version_download_lifecycle_and_integrity_fail_closed(tmp_path, monkeypatch):
    app, _archive, db_path, root = make_app(tmp_path, monkeypatch)
    client = TestClient(app)
    try:
        csrf, account_id = register_admin(client, db_path, "archive-owner@example.com")
        denied = upload(client, "", "archive-no-csrf-0001")
        assert denied.status_code == 403

        created = upload(client, csrf, "archive-create-0001")
        assert created.status_code == 200 and created.json()["ok"] is True
        boundary(created.json()["data"])
        document = created.json()["data"]["document"]
        document_id = document["id"]
        assert document["state"] == "active" and document["version_number"] == 1
        replay = upload(client, csrf, "archive-create-0001")
        assert replay.status_code == 200 and replay.json() == created.json()
        conflict = upload(client, csrf, "archive-create-0001", content=b"Noi dung khac")
        assert conflict.status_code == 409

        detail = client.get(f"/api/v1/admin/internal-documents/documents/{document_id}")
        assert detail.status_code == 200 and detail.json()["data"]["document"]["owner_relation"] == "self"
        version_id = detail.json()["data"]["document"]["current_version"]["id"]
        assert "storage_key" not in detail.text and "sha256" not in detail.text and account_id not in detail.text

        downloaded = client.get(f"/api/v1/admin/internal-documents/documents/{document_id}/download")
        assert downloaded.status_code == 200 and downloaded.content == b"Tai lieu noi bo Web-native an toan."
        assert downloaded.headers["cache-control"] == "no-store, private"
        assert downloaded.headers["content-security-policy"] == "sandbox"

        uploaded_version = client.post(
            f"/api/v1/admin/internal-documents/documents/{document_id}/versions/upload",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "archive-version-0001"},
            data={"expected_revision": "1", "display_name": "Architecture v2"},
            files={"file": ("architecture-v2.txt", b"Noi dung version 2 an toan.", "text/plain")},
        )
        assert uploaded_version.status_code == 200 and uploaded_version.json()["data"]["document"]["version_number"] == 2
        stale = client.patch(
            f"/api/v1/admin/internal-documents/documents/{document_id}",
            headers={"X-CSRF-Token": csrf},
            json={"title": "Khong duoc ghi stale", "expected_revision": 1, "idempotency_key": "archive-stale-0001"},
        )
        assert stale.status_code == 200 and stale.json()["error_code"] == "WEB_ADMIN_ARCHIVE_DOCUMENT_CONFLICT"

        archived = client.post(
            f"/api/v1/admin/internal-documents/documents/{document_id}/archive",
            headers={"X-CSRF-Token": csrf}, json=archive_payload(2, "archive-transition-0001", "archive"),
        )
        assert archived.status_code == 200 and archived.json()["data"]["document"]["state"] == "archived"
        assert client.get(f"/api/v1/admin/internal-documents/documents/{document_id}/download").json()["error_code"] == "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND"
        restored = client.post(
            f"/api/v1/admin/internal-documents/documents/{document_id}/restore",
            headers={"X-CSRF-Token": csrf}, json=archive_payload(3, "archive-transition-0002", "restore"),
        )
        assert restored.status_code == 200 and restored.json()["data"]["document"]["state"] == "active"

        with sqlite3.connect(db_path) as conn:
            key = conn.execute("SELECT storage_key FROM web_admin_archive_versions WHERE id=?", (version_id,)).fetchone()[0]
        (root / key).write_bytes(b"tampered private blob")
        failed = client.get(f"/api/v1/admin/internal-documents/versions/{version_id}/download")
        assert failed.status_code == 200 and failed.json()["error_code"] == "WEB_ADMIN_ARCHIVE_FILE_UNAVAILABLE"
        with sqlite3.connect(db_path) as conn:
            state = conn.execute("SELECT state FROM web_admin_archive_documents WHERE id=?", (document_id,)).fetchone()[0]
            availability = conn.execute("SELECT availability FROM web_admin_archive_versions WHERE id=?", (version_id,)).fetchone()[0]
        assert state == "unavailable" and availability == "unavailable"
    finally:
        client.close()


def test_archive_rejects_text_secrets_and_cross_admin_access(tmp_path, monkeypatch):
    app, _archive, db_path, _root = make_app(tmp_path, monkeypatch)
    owner = TestClient(app)
    other = TestClient(app)
    try:
        csrf, _ = register_admin(owner, db_path, "archive-owner-isolation@example.com")
        forbidden = upload(owner, csrf, "archive-secret-0001", content=b"api_token=abcdefghijklmno")
        assert forbidden.status_code == 422
        created = upload(owner, csrf, "archive-isolation-0001")
        document_id = created.json()["data"]["document"]["id"]
        other_csrf, _ = register_admin(other, db_path, "archive-other-admin@example.com")
        assert other_csrf
        hidden = other.get(f"/api/v1/admin/internal-documents/documents/{document_id}")
        assert hidden.status_code == 200 and hidden.json()["error_code"] == "WEB_ADMIN_ARCHIVE_DOCUMENT_NOT_FOUND"
        assert other.get("/api/v1/admin/internal-documents/documents").json()["data"]["documents"] == []
    finally:
        owner.close()
        other.close()


def test_archive_accepts_only_verified_pdf_docx_or_utf8_text(tmp_path, monkeypatch):
    app, _archive, db_path, _root = make_app(tmp_path, monkeypatch)
    client = TestClient(app)
    try:
        csrf, _ = register_admin(client, db_path, "archive-file-validation@example.com")
        from pypdf import PdfWriter

        pdf_output = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.write(pdf_output)
        accepted_pdf = upload(
            client, csrf, "archive-pdf-0001", content=pdf_output.getvalue(), filename="record.pdf", content_type="application/pdf"
        )
        assert accepted_pdf.status_code == 200

        docx_output = BytesIO()
        with ZipFile(docx_output, "w") as package:
            package.writestr("[Content_Types].xml", "<Types/>")
            package.writestr("word/document.xml", "<w:document xmlns:w='urn:test'/>")
        accepted_docx = upload(
            client, csrf, "archive-docx-0001", content=docx_output.getvalue(), filename="record.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        assert accepted_docx.status_code == 200

        bad_mime = upload(client, csrf, "archive-mime-0001", filename="record.pdf", content_type="text/plain")
        assert bad_mime.status_code == 422
        wrong_extension = upload(client, csrf, "archive-extension-0001", filename="record.exe")
        assert wrong_extension.status_code == 422
    finally:
        client.close()
