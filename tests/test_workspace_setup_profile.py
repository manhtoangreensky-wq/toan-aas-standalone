"""Focused contracts for the private Web-native Workspace Setup profile."""

from __future__ import annotations

import importlib
import sqlite3
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_bridge", "copyfast_registry", "copyfast_api",
    "copyfast_pages", "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime", "copyfast_image_operations", "copyfast_memory",
    "copyfast_workspace_setup",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "workspace-setup-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "workspace-setup-test-session-secret")
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
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Workspace Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return signed_in.json()["data"]["csrf_token"]


def complete_payload(key: str, revision: int = 0, **overrides) -> dict:
    payload = {
        "intent": "complete",
        "role": "solo_creator",
        "goal": "create_content",
        "experience": "growing",
        "focus_areas": ["projects", "content"],
        "expected_revision": revision,
        "idempotency_key": key,
    }
    payload.update(overrides)
    return payload


def assert_web_only_boundary(data: dict) -> None:
    boundary = data["boundary"] if isinstance(data.get("boundary"), dict) else data
    assert boundary["execution"] == "web_native_workspace_setup_profile"
    for key in (
        "bot_called", "bridge_called", "provider_called", "job_created", "wallet_mutated",
        "payment_started", "publish_action_created", "notification_sent",
    ):
        assert boundary[key] is False


def test_workspace_setup_requires_signed_session_csrf_and_bounded_body(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        unsigned = client.get("/api/v1/workspace/setup")
        assert unsigned.status_code == 401
        assert_web_only_boundary(unsigned.json()["data"])
        csrf = login(client, "setup-auth@example.com")
        initial = client.get("/api/v1/workspace/setup")
        assert initial.status_code == 200
        assert initial.json()["status"] == "read_only"
        assert initial.json()["data"]["profile"]["setup_state"] == "not_started"
        assert initial.json()["data"]["profile"]["revision"] == 0
        assert initial.json()["data"]["preferences"] == {"locale": "vi", "timezone": "Asia/Ho_Chi_Minh"}
        assert_web_only_boundary(initial.json()["data"])

        denied = client.post("/api/v1/workspace/setup", json=complete_payload("setup-auth-csrf-0001"))
        assert denied.status_code == 403
        assert_web_only_boundary(denied.json()["data"])
        too_large = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"intent":"complete","padding":"' + (b"x" * (9 * 1024)) + b'"}',
        )
        assert too_large.status_code == 413
        assert too_large.json()["error_code"] == "WEB_WORKSPACE_SETUP_BODY_TOO_LARGE"
        assert too_large.headers["Cache-Control"] == "no-store, private"
        assert_web_only_boundary(too_large.json()["data"])
        # The redirect-form route receives the same pre-parse cap before
        # Starlette can turn it into the canonical private endpoint.
        slash_too_large = client.post(
            "/api/v1/workspace/setup/",
            headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"},
            content=b'{"intent":"complete","padding":"' + (b"x" * (9 * 1024)) + b'"}',
            follow_redirects=False,
        )
        assert slash_too_large.status_code == 413
        assert slash_too_large.json()["error_code"] == "WEB_WORKSPACE_SETUP_BODY_TOO_LARGE"
        assert_web_only_boundary(slash_too_large.json()["data"])


def test_workspace_setup_complete_skip_idempotency_and_revision(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "setup-owner@example.com")
        payload = complete_payload("workspace-setup-complete-0001")
        completed = client.post("/api/v1/workspace/setup", headers={"X-CSRF-Token": csrf}, json=payload)
        assert completed.status_code == 200
        data = completed.json()["data"]
        assert completed.json()["status"] == "completed"
        assert data["profile"]["revision"] == 1
        assert data["profile"]["focus_areas"] == ["projects", "content"]
        assert_web_only_boundary(data)

        replay = client.post("/api/v1/workspace/setup", headers={"X-CSRF-Token": csrf}, json=payload)
        assert replay.status_code == 200
        assert replay.json() == completed.json()
        collision = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf},
            json=complete_payload("workspace-setup-complete-0001", goal="build_brand"),
        )
        assert collision.status_code == 409
        assert_web_only_boundary(collision.json()["data"])
        stale = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf},
            json=complete_payload("workspace-setup-stale-0001", revision=0),
        )
        assert stale.status_code == 409
        assert_web_only_boundary(stale.json()["data"])

        invalid_skip = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf},
            json={
                "intent": "skip", "role": "solo_creator", "goal": "", "experience": "", "focus_areas": [],
                "expected_revision": 1, "idempotency_key": "workspace-setup-bad-skip-0001",
            },
        )
        assert invalid_skip.status_code == 422
        assert_web_only_boundary(invalid_skip.json()["data"])
        skipped = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf},
            json={
                "intent": "skip", "role": "", "goal": "", "experience": "", "focus_areas": [],
                "expected_revision": 1, "idempotency_key": "workspace-setup-skip-0001",
            },
        )
        assert skipped.status_code == 200
        assert skipped.json()["status"] == "skipped"
        assert skipped.json()["data"]["profile"] == {
            "setup_state": "skipped", "role": "", "goal": "", "experience": "", "focus_areas": [],
            "revision": 2, "completed_at": "", "updated_at": skipped.json()["data"]["profile"]["updated_at"],
        }


def test_workspace_setup_can_be_skipped_then_completed_and_edited(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "setup-update@example.com")
        skipped = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf},
            json={
                "intent": "skip", "role": "", "goal": "", "experience": "", "focus_areas": [],
                "expected_revision": 0, "idempotency_key": "workspace-setup-skip-first-0001",
            },
        )
        assert skipped.status_code == 200
        assert skipped.json()["data"]["profile"]["setup_state"] == "skipped"
        completed = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf},
            json=complete_payload(
                "workspace-setup-complete-after-skip-0001",
                revision=1,
                role="team_lead",
                goal="run_operations",
                experience="advanced",
                focus_areas=["projects", "documents", "automation"],
            ),
        )
        assert completed.status_code == 200
        assert completed.json()["data"]["profile"]["revision"] == 2
        edited = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf},
            json=complete_payload(
                "workspace-setup-edit-complete-0001",
                revision=2,
                role="solo_creator",
                goal="build_brand",
                experience="growing",
                focus_areas=["content", "image"],
            ),
        )
        assert edited.status_code == 200
        profile = edited.json()["data"]["profile"]
        assert profile["setup_state"] == "completed"
        assert profile["revision"] == 3
        assert profile["role"] == "solo_creator"
        assert profile["focus_areas"] == ["content", "image"]
        assert profile["completed_at"] and profile["updated_at"]


def test_workspace_setup_idempotency_receipts_expire_and_are_capped(tmp_path, monkeypatch):
    db_path = tmp_path / "workspace-setup-test.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "setup-receipt@example.com")
        first = client.post(
            "/api/v1/workspace/setup", headers={"X-CSRF-Token": csrf},
            json=complete_payload("workspace-setup-expire-old-0001"),
        )
        assert first.status_code == 200
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_idempotency SET created_at=? WHERE scope LIKE ?",
                ("2000-01-01T00:00:00+00:00", "web-workspace-setup:%"),
            )
            conn.commit()
        after_expiry = client.post(
            "/api/v1/workspace/setup", headers={"X-CSRF-Token": csrf},
            json=complete_payload("workspace-setup-expire-next-0001", revision=1, goal="build_brand"),
        )
        assert after_expiry.status_code == 200
        with sqlite3.connect(db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
                ("web-workspace-setup:%",),
            ).fetchone()[0]
        assert count == 1

        workspace_module = sys.modules["copyfast_workspace_setup"]
        monkeypatch.setattr(workspace_module, "MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT", 1)
        limited = client.post(
            "/api/v1/workspace/setup", headers={"X-CSRF-Token": csrf},
            json=complete_payload("workspace-setup-limit-new-0001", revision=2, goal="learn_workflows"),
        )
        assert limited.status_code == 200
        assert limited.json()["ok"] is False
        assert limited.json()["status"] == "guarded"
        assert limited.json()["error_code"] == "WEB_WORKSPACE_SETUP_IDEMPOTENCY_LIMIT"
        assert_web_only_boundary(limited.json()["data"])
        assert client.get("/api/v1/workspace/setup").json()["data"]["profile"]["revision"] == 2


def test_workspace_setup_uses_fixed_read_and_write_rate_limit_scopes(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "setup-rate@example.com")
        app_module = sys.modules["app"]
        client_ip = "testclient"
        now = time.monotonic()
        app_module._auth_rate_windows[f"workspace-setup-read:{client_ip}"] = [now] * 120
        read_limited = client.get("/api/v1/workspace/setup")
        assert read_limited.status_code == 429
        assert read_limited.json()["error_code"] == "AUTH_RATE_LIMITED"
        assert_web_only_boundary(read_limited.json()["data"])

        app_module._auth_rate_windows.clear()
        app_module._auth_rate_windows[f"workspace-setup-write:{client_ip}"] = [time.monotonic()] * 30
        write_limited = client.post(
            "/api/v1/workspace/setup",
            headers={"X-CSRF-Token": csrf},
            json=complete_payload("workspace-setup-rate-write-0001"),
        )
        assert write_limited.status_code == 429
        assert write_limited.json()["error_code"] == "AUTH_RATE_LIMITED"
        assert_web_only_boundary(write_limited.json()["data"])

        app_module._auth_rate_windows.clear()
        app_module._auth_rate_windows[f"workspace-setup-read:{client_ip}"] = [time.monotonic()] * 120
        slash_read_limited = client.get("/api/v1/workspace/setup/", follow_redirects=False)
        assert slash_read_limited.status_code == 429
        assert slash_read_limited.json()["error_code"] == "AUTH_RATE_LIMITED"
        assert_web_only_boundary(slash_read_limited.json()["data"])


def test_workspace_setup_is_owner_scoped_strict_and_audited(tmp_path, monkeypatch):
    db_path = tmp_path / "workspace-setup-test.db"
    with make_client(tmp_path, monkeypatch) as first:
        first_csrf = login(first, "setup-first@example.com")
        saved = first.post(
            "/api/v1/workspace/setup", headers={"X-CSRF-Token": first_csrf},
            json=complete_payload("workspace-setup-owner-0001"),
        )
        assert saved.status_code == 200
        assert saved.json()["data"]["profile"]["setup_state"] == "completed"

        invalid_values = [
            complete_payload("workspace-setup-invalid-role-0001", role="admin"),
            complete_payload("workspace-setup-duplicate-focus-0001", focus_areas=["projects", "projects"]),
            complete_payload("workspace-setup-too-many-focus-0001", focus_areas=["projects", "content", "image", "voice"]),
            complete_payload("workspace-setup-empty-focus-0001", focus_areas=[]),
            {**complete_payload("workspace-setup-extra-0001"), "unexpected": "nope"},
            {**complete_payload("workspace-setup-strict-revision-0001"), "expected_revision": "1"},
        ]
        for invalid in invalid_values:
            invalid_response = first.post("/api/v1/workspace/setup", headers={"X-CSRF-Token": first_csrf}, json=invalid)
            assert invalid_response.status_code == 422
            assert_web_only_boundary(invalid_response.json()["data"])

        with make_client(tmp_path, monkeypatch) as second:
            second_csrf = login(second, "setup-second@example.com")
            private = second.get("/api/v1/workspace/setup")
            assert private.status_code == 200
            assert private.json()["data"]["profile"]["setup_state"] == "not_started"
            # The key is only unique within the signed account's scope.
            separate = second.post(
                "/api/v1/workspace/setup", headers={"X-CSRF-Token": second_csrf},
                json=complete_payload("workspace-setup-owner-0001"),
            )
            assert separate.status_code == 200
            assert separate.json()["data"]["profile"]["revision"] == 1

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT action, detail FROM web_audit_events WHERE action LIKE 'web.workspace_setup.%'").fetchall()
    assert rows
    assert all(action in {"web.workspace_setup.complete", "web.workspace_setup.skip"} for action, _ in rows)
    assert all("setup-first@example.com" not in detail and "setup-second@example.com" not in detail for _, detail in rows)
    module_source = (Path(__file__).resolve().parents[1] / "copyfast_workspace_setup.py").read_text(encoding="utf-8").lower()
    for forbidden in ("copyfast_bridge", "payos", "import requests", "import httpx", "telegram_send"):
        assert forbidden not in module_source
