"""Focused high-risk contracts for the Web-native Data Control Center.

The feature deliberately exposes a small, current Web-authoring projection.
These tests lock the boundaries that matter most: the default-off flag, signed
owner/CSRF checks, a direct private attachment, staged request lifecycle and
the guarantee that a request never deletes source data by itself.
"""

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
import uuid

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_image_studio",
    "copyfast_document_workspace", "copyfast_chat_workspace", "copyfast_analytics_workspace", "copyfast_workboard",
    "copyfast_memory", "copyfast_prompt_library", "copyfast_music_media", "copyfast_content_studio",
    "copyfast_voice_studio", "copyfast_video_studio", "copyfast_subtitle_workspace", "copyfast_support",
    "copyfast_data_controls",
]

POLICY_VERSION = "web_data_controls_v1"
SCOPE_KEY = "web_authoring_only"
ERASURE_ACKNOWLEDGEMENT = "REQUEST WEB AUTHORING ERASURE"
CANCEL_ACKNOWLEDGEMENT = "CANCEL WEB ERASURE REQUEST"


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "data-controls-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "data-controls-test-session-secret")
    monkeypatch.setenv("WEBAPP_DATA_CONTROLS_ENABLED", "true" if enabled else "false")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Data Control Owner"},
    )
    assert registered.status_code == 200 and registered.json()["ok"] is True
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True
    return signed_in.json()["data"]["csrf_token"]


def sign_in(client: TestClient, email: str) -> str:
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True
    return signed_in.json()["data"]["csrf_token"]


def export_payload(**overrides) -> dict:
    value = {"policy_version": POLICY_VERSION, "confirm": True}
    value.update(overrides)
    return value


def erasure_payload(key: str, **overrides) -> dict:
    value = {
        "policy_version": POLICY_VERSION,
        "scope_key": SCOPE_KEY,
        "acknowledgement": ERASURE_ACKNOWLEDGEMENT,
        "confirm": True,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def cancel_payload(revision: int, key: str, **overrides) -> dict:
    value = {
        "expected_revision": revision,
        "acknowledgement": CANCEL_ACKNOWLEDGEMENT,
        "confirm": True,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def account_id(db_path, email: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()
    assert row
    return str(row[0])


def authoring_counts(db_path, owner_id: str) -> dict[str, int]:
    statements = {
        "notes": "SELECT COUNT(*) FROM web_memory_notes WHERE account_id=?",
        "reminders": "SELECT COUNT(*) FROM web_memory_reminders WHERE account_id=?",
        "prompts": "SELECT COUNT(*) FROM web_prompt_templates WHERE account_id=?",
        "workboard": "SELECT COUNT(*) FROM web_workboard_items WHERE account_id=?",
        "checklists": "SELECT COUNT(*) FROM web_workboard_checklist_items WHERE account_id=?",
    }
    with sqlite3.connect(db_path) as conn:
        return {key: int(conn.execute(statement, (owner_id,)).fetchone()[0]) for key, statement in statements.items()}


def assert_web_only_boundary(data: dict) -> None:
    assert data["execution"] == "web_data_control_request_only"
    assert data["data_origin"] == "explicit_web_owned_authoring_projection"
    for key in (
        "bot_called", "telegram_data_included", "bridge_called", "wallet_mutated", "payment_processed",
        "provider_called", "job_created", "job_or_asset_data_included", "account_deleted", "files_deleted",
        "support_evidence_deleted", "external_notification_sent",
    ):
        assert data[key] is False


def test_data_controls_default_off_preserves_signed_session_boundary(tmp_path, monkeypatch):
    """The new surface is unavailable unless its narrow feature flag is enabled."""

    with make_client(tmp_path, monkeypatch, enabled=False) as client:
        assert client.get("/api/v1/account/data-controls/summary").status_code == 401
        csrf = login(client, "data-controls-disabled@example.com")

        summary = client.get("/api/v1/account/data-controls/summary")
        assert summary.status_code == 503
        assert "WEBAPP_DATA_CONTROLS_ENABLED" in summary.text

        export = client.post(
            "/api/v1/account/data-controls/export.json",
            headers={"X-CSRF-Token": csrf},
            json=export_payload(),
        )
        assert export.status_code == 503
        assert "Content-Disposition" not in export.headers


def test_data_controls_require_signed_owner_and_csrf_for_private_writes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        assert client.get("/api/v1/account/data-controls/summary").status_code == 401
        assert client.get("/api/v1/account/data-controls/requests").status_code == 401
        assert client.post("/api/v1/account/data-controls/export.json", json=export_payload()).status_code == 401
        assert client.post(
            "/api/v1/account/data-controls/erasure-requests",
            json=erasure_payload("data-control-csrf-create-0001"),
        ).status_code == 401

        csrf = login(client, "data-controls-csrf@example.com")
        assert client.get("/api/v1/account/data-controls/summary").status_code == 200
        assert client.post("/api/v1/account/data-controls/export.json", json=export_payload()).status_code == 403
        assert client.post(
            "/api/v1/account/data-controls/erasure-requests",
            json=erasure_payload("data-control-csrf-create-0001"),
        ).status_code == 403

        unconfirmed = client.post(
            "/api/v1/account/data-controls/export.json",
            headers={"X-CSRF-Token": csrf},
            json=export_payload(confirm=False),
        )
        assert unconfirmed.status_code == 200
        assert unconfirmed.json()["error_code"] == "WEB_DATA_CONTROL_EXPORT_CONFIRMATION_REQUIRED"
        assert_web_only_boundary(unconfirmed.json()["data"])


def test_data_controls_export_is_direct_private_and_explicitly_web_authoring_only(tmp_path, monkeypatch):
    email = "data-controls-export@example.com"
    db_path = tmp_path / "data-controls-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, email)
        owner_id = account_id(db_path, email)
        allowed_title = "Ghi chú authoring được export"
        excluded_audit_marker = "DO-NOT-EXPORT-audit-detail-or-canonical-identity"
        now = "2026-07-17T08:00:00+00:00"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO web_memory_notes
                   (id, account_id, title, content, tags_json, category, priority, state, revision, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (str(uuid.uuid4()), owner_id, allowed_title, "Nội dung Web-owned hiện tại.", "[\"privacy\"]", "ops", "normal", "active", now, now),
            )
            conn.execute(
                """INSERT INTO web_audit_events
                   (id, account_id, canonical_user_id, action, request_id, target, outcome, detail, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), owner_id, "telegram-must-not-export", "private.audit", "private-request-id", "private-target", "ok", excluded_audit_marker, now),
            )
            conn.commit()

        exported = client.post(
            "/api/v1/account/data-controls/export.json",
            headers={"X-CSRF-Token": csrf},
            json=export_payload(),
        )
        assert exported.status_code == 200
        assert exported.headers["Content-Type"].startswith("application/json")
        assert exported.headers["Content-Disposition"] == 'attachment; filename="toan-aas-web-authoring-data.json"'
        assert exported.headers["Cache-Control"] == "no-store, private"
        assert exported.headers["X-Content-Type-Options"] == "nosniff"
        assert exported.headers["Referrer-Policy"] == "no-referrer"
        assert exported.headers["Content-Security-Policy"] == "sandbox"
        assert exported.headers["Cross-Origin-Resource-Policy"] == "same-origin"

        document = json.loads(exported.content)
        assert document["schema"] == "toan-aas-web-authoring-data-export-v1"
        assert document["policy_version"] == POLICY_VERSION
        assert document["scope"] == {
            "key": SCOPE_KEY,
            "description": "Current Web-authored profile, Memory, Prompt Library and Workboard records only.",
            "includes_history": False,
            "includes_assets_or_outputs": False,
        }
        assert document["memory"]["notes"][0]["title"] == allowed_title
        assert any("Telegram/Bot" in item for item in document["excluded_systems"])
        assert any("PayOS" in item for item in document["excluded_systems"])
        assert excluded_audit_marker not in exported.text
        assert "telegram-must-not-export" not in exported.text
        assert "private-request-id" not in exported.text
        assert owner_id not in exported.text

        with sqlite3.connect(db_path) as conn:
            audit = conn.execute(
                "SELECT action, target FROM web_audit_events WHERE action='web.data_control.export' ORDER BY created_at DESC, id DESC LIMIT 1"
            ).fetchone()
        assert audit == ("web.data_control.export", SCOPE_KEY)


def test_data_controls_erasure_is_idempotent_owner_scoped_revision_safe_and_non_destructive(tmp_path, monkeypatch):
    owner_email = "data-controls-owner@example.com"
    other_email = "data-controls-other@example.com"
    db_path = tmp_path / "data-controls-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        owner_csrf = login(client, owner_email)
        owner_id = account_id(db_path, owner_email)
        now = "2026-07-17T08:00:00+00:00"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO web_memory_notes
                   (id, account_id, title, content, tags_json, category, priority, state, revision, created_at, updated_at)
                   VALUES (?, ?, ?, ?, '[]', '', 'normal', 'active', 1, ?, ?)""",
                (str(uuid.uuid4()), owner_id, "Không được xóa tự động", "Bản ghi source phải còn nguyên", now, now),
            )
            conn.commit()
        before = authoring_counts(db_path, owner_id)

        create_body = erasure_payload("data-control-erasure-create-0001")
        created = client.post(
            "/api/v1/account/data-controls/erasure-requests",
            headers={"X-CSRF-Token": owner_csrf},
            json=create_body,
        )
        assert created.status_code == 200 and created.json()["ok"] is True
        assert created.json()["status"] == "awaiting_review"
        assert_web_only_boundary(created.json()["data"])
        request_item = created.json()["data"]["request"]
        assert request_item["scope_key"] == SCOPE_KEY
        assert request_item["revision"] == 1
        assert request_item["automatic_deletion"] is False
        assert request_item["human_review_required"] is True
        request_id = request_item["id"]
        assert authoring_counts(db_path, owner_id) == before

        malformed_cancel = client.post(
            "/api/v1/account/data-controls/erasure-requests/not-a-uuid/cancel",
            headers={"X-CSRF-Token": owner_csrf},
            json=cancel_payload(1, "data-control-malformed-cancel-0001"),
        )
        assert malformed_cancel.status_code == 422
        assert "không hợp lệ" in malformed_cancel.text

        replay = client.post(
            "/api/v1/account/data-controls/erasure-requests",
            headers={"X-CSRF-Token": owner_csrf},
            json=create_body,
        )
        assert replay.status_code == 200 and replay.json()["ok"] is True
        assert replay.json()["data"]["request"]["id"] == request_id
        assert replay.json()["data"]["request"]["revision"] == 1
        duplicate_active = client.post(
            "/api/v1/account/data-controls/erasure-requests",
            headers={"X-CSRF-Token": owner_csrf},
            json=erasure_payload("data-control-erasure-second-0001"),
        )
        assert duplicate_active.status_code == 200
        assert duplicate_active.json()["ok"] is False
        assert duplicate_active.json()["error_code"] == "WEB_DATA_CONTROL_ERASURE_ALREADY_PENDING"
        assert_web_only_boundary(duplicate_active.json()["data"])
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_data_control_requests WHERE account_id=?", (owner_id,)).fetchone()[0] == 1
            assert conn.execute("SELECT COUNT(*) FROM web_data_control_request_events WHERE account_id=?", (owner_id,)).fetchone()[0] == 1

        other_csrf = login(client, other_email)
        hidden = client.get("/api/v1/account/data-controls/requests")
        assert hidden.status_code == 200
        assert hidden.json()["data"]["items"] == []
        assert request_id not in hidden.text
        foreign_cancel = client.post(
            f"/api/v1/account/data-controls/erasure-requests/{request_id}/cancel",
            headers={"X-CSRF-Token": other_csrf},
            json=cancel_payload(1, "data-control-foreign-cancel-0001"),
        )
        assert foreign_cancel.status_code == 200
        assert foreign_cancel.json()["error_code"] == "WEB_DATA_CONTROL_REQUEST_NOT_FOUND"
        assert request_id not in foreign_cancel.text
        assert authoring_counts(db_path, owner_id) == before

        owner_csrf = sign_in(client, owner_email)
        stale = client.post(
            f"/api/v1/account/data-controls/erasure-requests/{request_id}/cancel",
            headers={"X-CSRF-Token": owner_csrf},
            json=cancel_payload(2, "data-control-stale-cancel-0001"),
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_DATA_CONTROL_REQUEST_CONFLICT"

        cancel_body = cancel_payload(1, "data-control-owner-cancel-0001")
        cancelled = client.post(
            f"/api/v1/account/data-controls/erasure-requests/{request_id}/cancel",
            headers={"X-CSRF-Token": owner_csrf},
            json=cancel_body,
        )
        assert cancelled.status_code == 200 and cancelled.json()["ok"] is True
        assert cancelled.json()["status"] == "cancelled"
        assert_web_only_boundary(cancelled.json()["data"])
        assert cancelled.json()["data"]["request"]["state"] == "cancelled"
        assert cancelled.json()["data"]["request"]["revision"] == 2
        assert authoring_counts(db_path, owner_id) == before

        cancel_replay = client.post(
            f"/api/v1/account/data-controls/erasure-requests/{request_id}/cancel",
            headers={"X-CSRF-Token": owner_csrf},
            json=cancel_body,
        )
        assert cancel_replay.status_code == 200 and cancel_replay.json()["ok"] is True
        assert cancel_replay.json()["data"]["request"]["state"] == "cancelled"
        assert cancel_replay.json()["data"]["request"]["revision"] == 2

        listed = client.get("/api/v1/account/data-controls/requests")
        assert listed.status_code == 200
        assert listed.json()["data"]["items"] == [
            {
                "id": request_id,
                "scope_key": SCOPE_KEY,
                "state": "cancelled",
                "revision": 2,
                "requested_at": request_item["requested_at"],
                "updated_at": cancelled.json()["data"]["request"]["updated_at"],
                "cancelled_at": cancelled.json()["data"]["request"]["cancelled_at"],
                "automatic_deletion": False,
                "human_review_required": True,
            }
        ]
        assert authoring_counts(db_path, owner_id) == before


def test_data_controls_export_stops_at_preflight_or_incremental_size_limit(tmp_path, monkeypatch):
    """Export limits must fail closed without producing a partial attachment."""

    email = "data-controls-limits@example.com"
    db_path = tmp_path / "data-controls-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, email)
        owner_id = account_id(db_path, email)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO web_memory_notes
                   (id, account_id, title, content, tags_json, category, priority, state, revision, created_at, updated_at)
                   VALUES (?, ?, ?, ?, '[]', '', 'normal', 'active', 1, ?, ?)""",
                (str(uuid.uuid4()), owner_id, "Preflight limit", "Bản ghi không được tải một phần", "2026-07-17T08:00:00+00:00", "2026-07-17T08:00:00+00:00"),
            )
            conn.commit()
        module = importlib.import_module("copyfast_data_controls")

        # A zero-record bound proves the count check executes before result
        # rows are materialized into an attachment.
        monkeypatch.setattr(module, "MAX_EXPORT_RECORDS", 0)
        record_limited = client.post(
            "/api/v1/account/data-controls/export.json",
            headers={"X-CSRF-Token": csrf},
            json=export_payload(),
        )
        assert record_limited.status_code == 200
        assert record_limited.json()["error_code"] == "WEB_DATA_CONTROL_EXPORT_RECORD_LIMIT"
        assert "Content-Disposition" not in record_limited.headers

        # Restore the row cap and force the exact incremental encoder cap. A
        # response must remain a guarded envelope, never a partial download.
        monkeypatch.setattr(module, "MAX_EXPORT_RECORDS", 8_000)
        monkeypatch.setattr(module, "MAX_EXPORT_BYTES", 1)
        byte_limited = client.post(
            "/api/v1/account/data-controls/export.json",
            headers={"X-CSRF-Token": csrf},
            json=export_payload(),
        )
        assert byte_limited.status_code == 200
        assert byte_limited.json()["error_code"] == "WEB_DATA_CONTROL_EXPORT_SIZE_LIMIT"
        assert "Content-Disposition" not in byte_limited.headers
