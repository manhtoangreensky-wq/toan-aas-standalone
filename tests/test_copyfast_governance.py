"""Focused security contracts for the Web-native Governance Documents Center.

The suite mounts only signed Web auth plus the Governance router.  It is
deliberately narrow: no Bot, Core Bridge, provider, wallet/Xu, PayOS, job,
notification or publishing runtime is loaded or exercised here.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
import sqlite3
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_governance"]

ACKNOWLEDGEMENTS = {
    "submit": "SUBMIT GOVERNANCE DOCUMENT FOR REVIEW",
    "approve": "APPROVE GOVERNANCE DOCUMENT",
    "reject": "REJECT GOVERNANCE DOCUMENT",
    "archive": "ARCHIVE GOVERNANCE DOCUMENT",
    "restore": "RESTORE GOVERNANCE DOCUMENT",
}


def make_app(tmp_path, monkeypatch, *, dedicated_enabled: bool, erp_enabled: bool) -> tuple[FastAPI, Any, Path]:
    db_path = tmp_path / "governance-test.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "governance-test-session-secret")
    monkeypatch.setenv("WEBAPP_GOVERNANCE_DOCUMENTS_ENABLED", "true" if dedicated_enabled else "false")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true" if erp_enabled else "false")
    for name in (
        "APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH",
        "CORE_BRIDGE_BASE_URL", "CORE_BRIDGE_TOKEN", "CORE_BRIDGE_HMAC_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    governance = importlib.import_module("copyfast_governance")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(governance.router)
    return app, governance, db_path


def register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Governance test account",
        },
    )
    assert response.status_code == 200 and response.json()["ok"] is True
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True
    return signed_in.json()["data"]["csrf_token"]


def register_admin(client: TestClient, db_path: Path, email: str) -> tuple[str, str]:
    register(client, email)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
        assert row is not None
        account_id = str(row[0])
        conn.execute("UPDATE web_accounts SET role_cache='admin' WHERE id=?", (account_id,))
        conn.commit()
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True
    return signed_in.json()["data"]["csrf_token"], account_id


def document_payload(key: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "department": "tech_codex",
        "document_type": "architecture_doc",
        "title": "Quy ước review kiến trúc Web nội bộ",
        "summary": "Bản nháp nội bộ để hai quản trị viên review trước khi áp dụng thủ công.",
        "body": "Tài liệu chỉ mô tả quy ước Web-native, không tạo deploy, publish hoặc gọi hệ thống bên ngoài.",
        "tags": ["architecture", "internal-review"],
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def transition_payload(action: str, revision: int, key: str, *, review_note: str = "") -> dict[str, Any]:
    return {
        "expected_revision": revision,
        "acknowledgement": ACKNOWLEDGEMENTS[action],
        "confirm": True,
        "review_note": review_note,
        "idempotency_key": key,
    }


def boundary(data: dict[str, Any]) -> None:
    assert data["execution"] == "web_native_admin_governance_documents_only"
    assert data["data_origin"] == "web_governance_document_tables_only"
    assert data["external_effects"] == "none"
    assert data["publication"] == "not_available"
    assert data["legacy_bot_scope"] == "TELEGRAM_ONLY"
    assert any("Core bridge" in item for item in data["excluded_domains"])
    assert any("PayOS" in item for item in data["excluded_domains"])


def governance_counts(db_path: Path) -> dict[str, int]:
    tables = (
        "web_governance_documents",
        "web_governance_document_versions",
        "web_governance_document_events",
        "web_idempotency",
        "web_audit_events",
    )
    with sqlite3.connect(db_path) as conn:
        return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}


def receipt_document(response) -> dict[str, Any]:
    body = response.json()
    assert response.status_code == 200 and body["ok"] is True
    boundary(body["data"])
    return body["data"]["document"]


def test_governance_is_opt_in_and_uses_signed_local_admin_csrf_only(tmp_path, monkeypatch):
    app, governance, db_path = make_app(tmp_path, monkeypatch, dedicated_enabled=False, erp_enabled=True)
    client = TestClient(app)
    try:
        # The contract must be explicit in the router itself; role/CSRF are
        # server dependencies, never fields supplied by a browser request.
        route_calls = {
            (route.path, method): {dependency.call for dependency in route.dependant.dependencies}
            for route in governance.router.routes
            for method in (route.methods or set())
        }
        read_paths = (
            "/api/v1/admin/governance/policy",
            "/api/v1/admin/governance/summary",
            "/api/v1/admin/governance/documents",
            "/api/v1/admin/governance/documents/{document_id}",
            "/api/v1/admin/governance/documents/{document_id}/versions",
            "/api/v1/admin/governance/documents/{document_id}/events",
        )
        write_paths = (
            "/api/v1/admin/governance/documents",
            "/api/v1/admin/governance/documents/{document_id}",
            "/api/v1/admin/governance/documents/{document_id}/submit-review",
            "/api/v1/admin/governance/documents/{document_id}/approve",
            "/api/v1/admin/governance/documents/{document_id}/reject",
            "/api/v1/admin/governance/documents/{document_id}/archive",
            "/api/v1/admin/governance/documents/{document_id}/restore",
        )
        for path in read_paths:
            assert governance.require_admin in route_calls[(path, "GET")]
        for path in write_paths:
            method = "PATCH" if path == "/api/v1/admin/governance/documents/{document_id}" else "POST"
            assert governance.require_admin_csrf in route_calls[(path, method)]

        # No unauthenticated or ordinary account receives a policy projection.
        assert client.get("/api/v1/admin/governance/policy").status_code == 401
        regular_csrf = register(client, "governance-regular@example.com")
        assert regular_csrf
        assert client.get("/api/v1/admin/governance/policy").status_code == 403

        admin_csrf, _admin_id = register_admin(client, db_path, "governance-admin@example.com")
        default_off = client.get("/api/v1/admin/governance/policy")
        assert default_off.status_code == 503
        assert "departments" not in default_off.text

        # The dedicated opt-in alone is insufficient when the ERP umbrella is
        # disabled.  Both flags are checked before a privileged projection.
        monkeypatch.setenv("WEBAPP_GOVERNANCE_DOCUMENTS_ENABLED", "true")
        monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
        assert client.get("/api/v1/admin/governance/policy").status_code == 503

        monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
        policy = client.get("/api/v1/admin/governance/policy")
        assert policy.status_code == 200 and policy.json()["status"] == "read_only"
        boundary(policy.json()["data"])
        assert policy.json()["data"]["policy_version"] == "web_governance_documents_v1"

        # A valid signed admin still needs CSRF for every mutation.
        denied = client.post("/api/v1/admin/governance/documents", json=document_payload("governance-no-csrf-0001"))
        assert denied.status_code == 403
        created = client.post(
            "/api/v1/admin/governance/documents",
            headers={"X-CSRF-Token": admin_csrf},
            json=document_payload("governance-csrf-create-0001"),
        )
        assert receipt_document(created)["state"] == "draft"

        # The feature must not import an outbound Bot/Core Bridge/payment or
        # provider client merely to manage this Web-owned record system.
        tree = ast.parse(Path(governance.__file__).read_text(encoding="utf-8"))
        imported = {
            module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for module in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if module
        }
        assert not {"copyfast_bridge", "requests", "httpx", "payos"}.intersection(imported)
    finally:
        client.close()


def test_governance_dlp_rejects_sensitive_values_without_persisting_and_invalid_ids_are_422(tmp_path, monkeypatch):
    app, _governance, db_path = make_app(tmp_path, monkeypatch, dedicated_enabled=True, erp_enabled=True)
    client = TestClient(app)
    try:
        csrf, _account_id = register_admin(client, db_path, "governance-dlp-admin@example.com")
        before = governance_counts(db_path)
        sensitive_inputs = (
            {"title": "-----BEGIN PRIVATE KEY-----"},
            {"summary": "Bearer abcdefghijklmnop"},
            {"body": "api_token=abcdef123456"},
            {"body": "telegram_file_id=AgACAgIAAxkBAABC123456789"},
            {"body": "Không được ghi đường dẫn /var/lib/toanaas/private-output.json vào tài liệu."},
            {"tags": ["sk_abcdefghijklmnop"]},
        )
        for index, override in enumerate(sensitive_inputs, start=1):
            blocked = client.post(
                "/api/v1/admin/governance/documents",
                headers={"X-CSRF-Token": csrf},
                json=document_payload(f"governance-dlp-{index:04d}-request", **override),
            )
            assert blocked.status_code == 422
            assert blocked.status_code != 500
            assert governance_counts(db_path) == before

        malformed = client.get("/api/v1/admin/governance/documents/not-a-governance-uuid")
        assert malformed.status_code == 422
        assert malformed.status_code != 500
        assert governance_counts(db_path) == before
    finally:
        client.close()


def test_governance_retention_policy_accepts_numeric_year_labels(tmp_path, monkeypatch):
    app, _governance, db_path = make_app(tmp_path, monkeypatch, dedicated_enabled=True, erp_enabled=True)
    client = TestClient(app)
    try:
        csrf, _account_id = register_admin(client, db_path, "governance-retention-admin@example.com")
        for index, retention_label in enumerate(("manual_review", "3_years", "5_years", "permanent"), start=1):
            created = client.post(
                "/api/v1/admin/governance/documents",
                headers={"X-CSRF-Token": csrf},
                json=document_payload(
                    f"governance-retention-{index:04d}",
                    title=f"Nhãn lưu trữ nội bộ {index}",
                    retention_label=retention_label,
                    confidentiality_level="restricted",
                ),
            )
            receipt = receipt_document(created)
            detail = client.get(f"/api/v1/admin/governance/documents/{receipt['id']}")
            assert detail.status_code == 200 and detail.json()["ok"] is True
            document = detail.json()["data"]["document"]
            assert document["retention_label"] == retention_label
            assert document["confidentiality_level"] == "restricted"
    finally:
        client.close()


def test_governance_lifecycle_is_revisioned_idempotent_and_requires_a_second_admin(tmp_path, monkeypatch):
    app, _governance, db_path = make_app(tmp_path, monkeypatch, dedicated_enabled=True, erp_enabled=True)
    owner = TestClient(app)
    reviewer = TestClient(app)
    outsider = TestClient(app)
    try:
        owner_csrf, owner_id = register_admin(owner, db_path, "governance-owner@example.com")
        reviewer_csrf, reviewer_id = register_admin(reviewer, db_path, "governance-reviewer@example.com")
        outsider_csrf, outsider_id = register_admin(outsider, db_path, "governance-outsider@example.com")
        assert len({owner_id, reviewer_id, outsider_id}) == 3

        raw = document_payload("governance-owner-create-0001")
        created_response = owner.post(
            "/api/v1/admin/governance/documents", headers={"X-CSRF-Token": owner_csrf}, json=raw
        )
        created = receipt_document(created_response)
        document_id = created["id"]
        assert created["revision"] == 1 and created["state"] == "draft"
        assert {"body", "owner_account_id", "reviewer_account_id"}.isdisjoint(created)

        replay = owner.post(
            "/api/v1/admin/governance/documents", headers={"X-CSRF-Token": owner_csrf}, json=raw
        )
        assert replay.status_code == 200 and replay.json() == created_response.json()
        collision = owner.post(
            "/api/v1/admin/governance/documents",
            headers={"X-CSRF-Token": owner_csrf},
            json=document_payload(raw["idempotency_key"], title="Một tài liệu Governance hoàn toàn khác"),
        )
        assert collision.status_code == 409

        stale = owner.patch(
            f"/api/v1/admin/governance/documents/{document_id}",
            headers={"X-CSRF-Token": owner_csrf},
            json={"body": "Bản cập nhật stale không được ghi.", "expected_revision": 99, "idempotency_key": "governance-owner-stale-0001"},
        )
        assert stale.status_code == 200 and stale.json()["error_code"] == "WEB_GOVERNANCE_DOCUMENT_CONFLICT"
        updated = owner.patch(
            f"/api/v1/admin/governance/documents/{document_id}",
            headers={"X-CSRF-Token": owner_csrf},
            json={"body": "Bản cập nhật revision hai chỉ là chính sách Web nội bộ đã được rà soát.", "expected_revision": 1, "idempotency_key": "governance-owner-update-0001"},
        )
        assert receipt_document(updated) == {
            "id": document_id,
            "state": "draft",
            "state_label": "Bản nháp",
            "revision": 2,
            "updated_at": receipt_document(updated)["updated_at"],
        }

        submitted = owner.post(
            f"/api/v1/admin/governance/documents/{document_id}/submit-review",
            headers={"X-CSRF-Token": owner_csrf},
            json=transition_payload("submit", 2, "governance-owner-submit-0001"),
        )
        submitted_document = receipt_document(submitted)
        assert submitted_document["state"] == "in_review" and submitted_document["revision"] == 3

        # The creator cannot approve/reject their own record even with a
        # signed admin session, valid CSRF and the current revision.
        self_approval = owner.post(
            f"/api/v1/admin/governance/documents/{document_id}/approve",
            headers={"X-CSRF-Token": owner_csrf},
            json=transition_payload("approve", 3, "governance-owner-self-approve-0001"),
        )
        assert self_approval.status_code == 200
        assert self_approval.json()["error_code"] == "WEB_GOVERNANCE_REVIEW_SEPARATION_REQUIRED"

        review_queue = reviewer.get("/api/v1/admin/governance/documents?scope=review")
        assert review_queue.status_code == 200
        listed = next(item for item in review_queue.json()["data"]["documents"] if item["id"] == document_id)
        assert listed["ownership"] == "other"
        assert listed["permissions"]["can_review"] is True
        assert "body" not in listed and "owner_account_id" not in listed

        approved = reviewer.post(
            f"/api/v1/admin/governance/documents/{document_id}/approve",
            headers={"X-CSRF-Token": reviewer_csrf},
            json=transition_payload("approve", 3, "governance-reviewer-approve-0001", review_note="Đã review nội bộ, không có action bên ngoài."),
        )
        approved_document = receipt_document(approved)
        assert approved_document["state"] == "approved" and approved_document["revision"] == 4

        # A third admin can see the internal record but cannot mutate a
        # non-owned draft/approved lifecycle record by guessing its UUID.
        foreign_update = outsider.patch(
            f"/api/v1/admin/governance/documents/{document_id}",
            headers={"X-CSRF-Token": outsider_csrf},
            json={"title": "Không có quyền đổi tài liệu", "expected_revision": 4, "idempotency_key": "governance-outsider-update-0001"},
        )
        assert foreign_update.status_code == 200
        assert foreign_update.json()["error_code"] == "WEB_GOVERNANCE_DOCUMENT_NOT_FOUND"

        archived = owner.post(
            f"/api/v1/admin/governance/documents/{document_id}/archive",
            headers={"X-CSRF-Token": owner_csrf},
            json=transition_payload("archive", 4, "governance-owner-archive-0001"),
        )
        assert receipt_document(archived)["state"] == "archived"
        restored = owner.post(
            f"/api/v1/admin/governance/documents/{document_id}/restore",
            headers={"X-CSRF-Token": owner_csrf},
            json=transition_payload("restore", 5, "governance-owner-restore-0001"),
        )
        assert receipt_document(restored)["state"] == "draft"
        assert receipt_document(restored)["revision"] == 6

        detail = owner.get(f"/api/v1/admin/governance/documents/{document_id}")
        assert detail.status_code == 200
        document = detail.json()["data"]["document"]
        assert document["ownership"] == "own"
        assert document["permissions"]["can_update"] is True
        for private in (owner_id, reviewer_id, outsider_id):
            assert private not in str(document)

        versions = owner.get(f"/api/v1/admin/governance/documents/{document_id}/versions")
        events = owner.get(f"/api/v1/admin/governance/documents/{document_id}/events")
        assert versions.status_code == 200 and events.status_code == 200
        assert {entry["revision"] for entry in versions.json()["data"]["versions"]} == {1, 2, 3, 4, 5, 6}
        assert {entry["action"] for entry in events.json()["data"]["events"]} == {
            "created", "updated", "submitted", "approved", "archived", "restored"
        }
        for rendered in (str(versions.json()["data"]), str(events.json()["data"])):
            for private in (owner_id, reviewer_id, outsider_id):
                assert private not in rendered

        with sqlite3.connect(db_path) as conn:
            receipts = conn.execute("SELECT response_json FROM web_idempotency WHERE scope LIKE 'web-governance:%'").fetchall()
            audit_details = conn.execute("SELECT detail FROM web_audit_events WHERE action LIKE 'web.governance.%'").fetchall()
        assert receipts and audit_details
        for stored in [*receipts, *audit_details]:
            rendered = str(stored)
            assert raw["title"] not in rendered
            assert raw["summary"] not in rendered
            assert raw["body"] not in rendered
    finally:
        owner.close()
        reviewer.close()
        outsider.close()


def test_governance_rejection_requires_another_admin_a_safe_note_and_returns_to_draft(tmp_path, monkeypatch):
    app, _governance, db_path = make_app(tmp_path, monkeypatch, dedicated_enabled=True, erp_enabled=True)
    owner = TestClient(app)
    reviewer = TestClient(app)
    try:
        owner_csrf, _ = register_admin(owner, db_path, "governance-reject-owner@example.com")
        reviewer_csrf, _ = register_admin(reviewer, db_path, "governance-reject-reviewer@example.com")
        created = receipt_document(owner.post(
            "/api/v1/admin/governance/documents",
            headers={"X-CSRF-Token": owner_csrf},
            json=document_payload("governance-reject-create-0001"),
        ))
        document_id = created["id"]
        submitted = receipt_document(owner.post(
            f"/api/v1/admin/governance/documents/{document_id}/submit-review",
            headers={"X-CSRF-Token": owner_csrf},
            json=transition_payload("submit", 1, "governance-reject-submit-0001"),
        ))
        assert submitted["revision"] == 2

        missing_note = reviewer.post(
            f"/api/v1/admin/governance/documents/{document_id}/reject",
            headers={"X-CSRF-Token": reviewer_csrf},
            json=transition_payload("reject", 2, "governance-reject-no-note-0001"),
        )
        assert missing_note.status_code == 200
        assert missing_note.json()["error_code"] == "WEB_GOVERNANCE_REJECTION_NOTE_REQUIRED"

        secret_note = reviewer.post(
            f"/api/v1/admin/governance/documents/{document_id}/reject",
            headers={"X-CSRF-Token": reviewer_csrf},
            json=transition_payload(
                "reject", 2, "governance-reject-secret-note-0001", review_note="Authorization: Bearer abcdefghijklmnop"
            ),
        )
        assert secret_note.status_code == 422

        rejected = reviewer.post(
            f"/api/v1/admin/governance/documents/{document_id}/reject",
            headers={"X-CSRF-Token": reviewer_csrf},
            json=transition_payload(
                "reject", 2, "governance-reject-valid-note-0001", review_note="Cần bổ sung tiêu chí kiểm tra nội bộ trước khi gửi review lại."
            ),
        )
        document = receipt_document(rejected)
        assert document["state"] == "draft" and document["revision"] == 3
    finally:
        owner.close()
        reviewer.close()
