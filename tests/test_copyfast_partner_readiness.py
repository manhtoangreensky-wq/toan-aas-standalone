"""Contract tests for the private Web-native Partner Readiness profile."""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
import pytest


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_partner_readiness"]


def make_client(tmp_path, monkeypatch, *, enabled: bool = True) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "partner-readiness.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "partner-readiness-test-secret")
    monkeypatch.setenv("WEBAPP_PARTNER_READINESS_ENABLED", "true" if enabled else "false")
    for name in MODULES:
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    readiness = importlib.import_module("copyfast_partner_readiness")
    application = FastAPI()
    application.include_router(auth.router, prefix="/api/v1/auth")
    application.include_router(readiness.router)
    return TestClient(application)


def login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple", "display_name": "Readiness Owner"},
    )
    assert registered.status_code == 200
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert signed_in.status_code == 200
    return str(signed_in.json()["data"]["csrf_token"])


def payload(key: str = "partner-readiness-create-0001", **overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "service_focus": "Thiết kế quy trình nội dung số cho đội nhỏ.",
        "capabilities": ["brief_review", "content_system"],
        "availability": "limited",
        "rate_display_preference": "on_request",
        "preferred_briefs": ["product_content", "campaign"],
        "portfolio_summary": "Đã xây bộ khung brief và quy tắc duyệt nội dung có thể bàn giao.",
        "collaboration_note": "Ưu tiên brief rõ mục tiêu, thời hạn và tiêu chí duyệt nội bộ.",
        "visibility_draft": "private",
        "expected_revision": 0,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def revision_payload(revision: int, key: str, **overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {"expected_revision": revision, "idempotency_key": key}
    value.update(overrides)
    return value


def assert_boundary(data: dict[str, Any], *, persisted: bool, interest: bool = False) -> None:
    assert data["execution"] == "web_native_partner_readiness_profile_only"
    assert data["profile_persisted"] is persisted
    assert data["interest_submitted"] is interest
    for key in (
        "bot_called", "telegram_called", "bridge_called", "provider_called", "job_created",
        "wallet_mutated", "xu_mutated", "payment_started", "payos_called", "referral_created",
        "attribution_created", "commission_created", "payout_created", "public_listing_created",
        "matching_started", "contact_released", "crm_record_created", "notification_sent", "delivery_created",
    ):
        assert data[key] is False


def test_partner_readiness_requires_session_csrf_and_creates_a_private_revisioned_profile(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        path = "/api/v1/partner-readiness/profile"
        assert client.get(path).status_code == 401
        assert client.patch(path, json=payload()).status_code == 401
        csrf = login(client, "readiness-owner@example.com")
        assert client.patch(path, json=payload()).status_code == 403
        created = client.patch(path, headers={"X-CSRF-Token": csrf}, json=payload())

    assert created.status_code == 200 and created.json()["ok"] is True
    assert created.headers["cache-control"] == "no-store, private"
    body = created.json()
    assert body["status"] == "draft"
    assert_boundary(body["data"], persisted=True)
    assert body["data"]["profile"] == {"revision": 1, "state": "draft"}


def test_partner_readiness_profile_history_owner_scope_idempotency_and_transitions(tmp_path, monkeypatch):
    db_path = tmp_path / "partner-readiness.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "readiness-owner@example.com")
        created = client.patch("/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf}, json=payload())
        assert created.status_code == 200
        replay = client.patch("/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf}, json=payload())
        assert replay.status_code == 200 and replay.json() == created.json()
        collision = client.patch(
            "/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf},
            json=payload(service_focus="Một trọng tâm khác hoàn toàn."),
        )
        assert collision.status_code == 409
        detail = client.get("/api/v1/partner-readiness/profile")
        assert detail.status_code == 200 and detail.json()["data"]["profile"]["service_focus"] == payload()["service_focus"]
        assert detail.json()["data"]["profile"]["revision"] == 1
        assert_boundary(detail.json()["data"], persisted=False)
        history = client.get("/api/v1/partner-readiness/profile/history")
        assert history.status_code == 200 and [item["revision"] for item in history.json()["data"]["versions"]] == [1]
        stale = client.patch(
            "/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf},
            json=payload("partner-readiness-stale-0001", expected_revision=0),
        )
        assert stale.status_code == 409
        review = client.post(
            "/api/v1/partner-readiness/profile/request-review", headers={"X-CSRF-Token": csrf},
            json=revision_payload(1, "partner-readiness-review-0001"),
        )
        assert review.status_code == 200 and review.json()["data"]["profile"] == {"revision": 2, "state": "review"}
        invalid_review = client.post(
            "/api/v1/partner-readiness/profile/request-review", headers={"X-CSRF-Token": csrf},
            json=revision_payload(2, "partner-readiness-review-invalid-0001"),
        )
        assert invalid_review.status_code == 409
        extra_lifecycle_field = client.post(
            "/api/v1/partner-readiness/profile/request-review", headers={"X-CSRF-Token": csrf},
            json=revision_payload(2, "partner-readiness-review-extra-0001", confirm_interest=True),
        )
        assert extra_lifecycle_field.status_code == 422
        reset = client.patch(
            "/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf},
            json=payload("partner-readiness-review-update-0001", expected_revision=2, visibility_draft="handoff_ready"),
        )
        assert reset.status_code == 200 and reset.json()["data"]["profile"] == {"revision": 3, "state": "draft"}
        review_again = client.post(
            "/api/v1/partner-readiness/profile/request-review", headers={"X-CSRF-Token": csrf},
            json=revision_payload(3, "partner-readiness-review-0002"),
        )
        assert review_again.status_code == 200 and review_again.json()["data"]["profile"]["state"] == "review"
        missing_confirm = client.post(
            "/api/v1/partner-readiness/profile/interest", headers={"X-CSRF-Token": csrf},
            json=revision_payload(4, "partner-readiness-interest-0001"),
        )
        assert missing_confirm.status_code == 422
        submitted = client.post(
            "/api/v1/partner-readiness/profile/interest", headers={"X-CSRF-Token": csrf},
            json=revision_payload(4, "partner-readiness-interest-0001", confirm_interest=True),
        )
        assert submitted.status_code == 200 and submitted.json()["data"]["profile"] == {"revision": 5, "state": "submitted"}
        assert_boundary(submitted.json()["data"], persisted=True, interest=True)
        interest_replay = client.post(
            "/api/v1/partner-readiness/profile/interest", headers={"X-CSRF-Token": csrf},
            json=revision_payload(4, "partner-readiness-interest-0001", confirm_interest=True),
        )
        assert interest_replay.status_code == 200 and interest_replay.json() == submitted.json()
        submitted_update = client.patch(
            "/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf},
            json=payload("partner-readiness-submitted-update-0001", expected_revision=5),
        )
        assert submitted_update.status_code == 409
        archived = client.post(
            "/api/v1/partner-readiness/profile/archive", headers={"X-CSRF-Token": csrf},
            json=revision_payload(5, "partner-readiness-archive-0001"),
        )
        assert archived.status_code == 200 and archived.json()["data"]["profile"] == {"revision": 6, "state": "archived"}
        restored = client.post(
            "/api/v1/partner-readiness/profile/restore", headers={"X-CSRF-Token": csrf},
            json=revision_payload(6, "partner-readiness-restore-0001"),
        )
        assert restored.status_code == 200 and restored.json()["data"]["profile"] == {"revision": 7, "state": "draft"}

        csrf_other = login(client, "readiness-other@example.com")
        hidden = client.get("/api/v1/partner-readiness/profile")
        assert hidden.status_code == 200 and hidden.json()["data"]["profile"] is None
        foreign_write = client.patch(
            "/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf_other},
            json=payload("partner-readiness-other-create-0001", expected_revision=7),
        )
        assert foreign_write.status_code == 409

    with sqlite3.connect(db_path) as conn:
        receipts = conn.execute("SELECT COUNT(*) FROM web_partner_readiness_interest_submissions").fetchone()[0]
        versions = conn.execute("SELECT revision FROM web_partner_readiness_versions ORDER BY revision").fetchall()
        schema = conn.execute("PRAGMA table_info(web_partner_readiness_profiles)").fetchall()
        audit = conn.execute("SELECT detail FROM web_audit_events WHERE action LIKE 'web.partner_readiness.%'").fetchall()
    assert receipts == 1
    assert [row[0] for row in versions] == [1, 2, 3, 4, 5, 6, 7]
    assert not {"telegram_id", "referral_code", "payout", "recipient", "amount"} & {row[1] for row in schema}
    assert audit and payload()["portfolio_summary"] not in " ".join(str(row[0]) for row in audit)


def test_partner_readiness_rejects_unsafe_fields_and_disabled_feature_without_side_effects(tmp_path, monkeypatch):
    db_path = tmp_path / "partner-readiness.db"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "readiness-safety@example.com")
        headers = {"X-CSRF-Token": csrf}
        for invalid in (
            payload("partner-readiness-extra-0001", telegram_id="123"),
            payload("partner-readiness-url-0001", collaboration_note="Xem https://example.com trước."),
            payload("partner-readiness-www-0001", collaboration_note="Xem www.example.com trước."),
            payload("partner-readiness-contact-0001", collaboration_note="Liên hệ @someone để trao đổi."),
            payload("partner-readiness-secret-0001", portfolio_summary="api_key=super-secret-value-123456"),
            payload("partner-readiness-token-0001", portfolio_summary="token=opaque-secret-value-123456"),
            payload("partner-readiness-session-token-0001", portfolio_summary="session_token=opaque-secret-value-123456"),
            payload("partner-readiness-jwt-0001", portfolio_summary="jwt=opaque-secret-value-123456"),
            payload("partner-readiness-ftp-0001", portfolio_summary="ftp://private.example.invalid/resource"),
            payload("partner-readiness-tel-0001", portfolio_summary="tel:+84901234567"),
            payload("partner-readiness-admin-identity-0001", portfolio_summary="admin identity: operator-42"),
            payload("partner-readiness-admin-id-0001", portfolio_summary="admin_id=operator-42"),
            payload("partner-readiness-operator-id-0001", portfolio_summary="operator_id=operator-42"),
            payload("partner-readiness-amount-0001", service_focus="Gói 2.000.000đ mỗi tháng."),
            payload("partner-readiness-markup-0001", service_focus="<script>alert(1)</script>"),
        ):
            assert client.patch("/api/v1/partner-readiness/profile", headers=headers, json=invalid).status_code == 422
        assert client.get("/api/v1/partner-readiness/policy").status_code == 200
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM web_partner_readiness_profiles").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM web_partner_readiness_versions").fetchone()[0] == 0

    with make_client(tmp_path, monkeypatch, enabled=False) as disabled:
        csrf = login(disabled, "readiness-disabled@example.com")
        assert disabled.get("/api/v1/partner-readiness/policy").status_code == 503
        assert disabled.patch("/api/v1/partner-readiness/profile", headers={"X-CSRF-Token": csrf}, json=payload()).status_code == 503


def test_partner_readiness_is_bounded_before_router_parsing(tmp_path, monkeypatch):
    """The production ASGI shell rejects oversized raw bodies with no store."""

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "partner-readiness-app.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "partner-readiness-app-test-secret")
    monkeypatch.setenv("WEBAPP_PARTNER_READINESS_ENABLED", "true")
    for name in (*MODULES, "app"):
        sys.modules.pop(name, None)
    application = importlib.import_module("app")
    with TestClient(application.app) as client:
        too_large = client.patch(
            "/api/v1/partner-readiness/profile",
            content=b"{" + (b'"x":' + b'"a"' * 6_000),
            headers={"Content-Type": "application/json"},
        )
    assert too_large.status_code == 413
    assert too_large.headers["cache-control"] == "no-store, private"
    assert too_large.json()["error_code"] == "WEB_PARTNER_READINESS_BODY_TOO_LARGE"
    assert_boundary(too_large.json()["data"], persisted=False)


def test_production_error_envelopes_keep_partner_readiness_boundary(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "partner-readiness-errors.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "partner-readiness-errors-secret")
    monkeypatch.setenv("WEBAPP_PARTNER_READINESS_ENABLED", "true")
    for name in (*MODULES, "app"):
        sys.modules.pop(name, None)
    application = importlib.import_module("app")
    with TestClient(application.app) as client:
        denied = client.post("/api/v1/partner-readiness/profile/request-review", json={})
        csrf = login(client, "partner-readiness-validation@example.com")
        invalid = client.patch(
            "/api/v1/partner-readiness/profile",
            headers={"X-CSRF-Token": csrf},
            json={"unexpected": True},
        )
    assert denied.status_code == 401
    assert denied.json()["data"]["execution"] == "web_native_partner_readiness_profile_only"
    assert denied.json()["data"]["profile_persisted"] is False
    assert denied.json()["data"]["bot_called"] is False
    assert invalid.status_code == 422
    assert invalid.json()["data"]["execution"] == "web_native_partner_readiness_profile_only"
    assert invalid.json()["data"]["profile_persisted"] is False
    assert invalid.json()["data"]["bot_called"] is False


class _LostUpdateCursor:
    def __init__(self, row=None, *, rowcount: int = 1):
        self._row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self._row


class _LostUpdateConnection:
    def __init__(self, row):
        self.row = row

    def execute(self, sql: str, _parameters=()):
        if sql.lstrip().startswith("SELECT"):
            return _LostUpdateCursor(self.row)
        if sql.lstrip().startswith("UPDATE"):
            return _LostUpdateCursor(rowcount=0)
        return _LostUpdateCursor()


def _lost_update_readiness(monkeypatch):
    for name in MODULES:
        sys.modules.pop(name, None)
    readiness = importlib.import_module("copyfast_partner_readiness")
    row = (
        "profile-1", "Quy trình nội dung số", '["brief_review"]', "open", "on_request",
        '["product_content"]', "", "", "private", "draft", 1,
        "2026-08-01T00:00:00+00:00", "2026-08-01T00:00:00+00:00", None,
    )
    connection = _LostUpdateConnection(row)
    monkeypatch.setattr(readiness, "_require_enabled", lambda: None)
    monkeypatch.setattr(readiness, "_record_version_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(readiness, "_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        readiness,
        "_idempotent",
        lambda _scope, _account_id, _key, _fingerprint, operation: operation(connection),
    )
    return readiness


def test_partner_readiness_rejects_lost_profile_revision_update(monkeypatch):
    readiness = _lost_update_readiness(monkeypatch)
    body = readiness.ProfilePayload(**payload("partner-readiness-lost-update-0001", expected_revision=1))
    with pytest.raises(HTTPException) as raised:
        readiness.patch_profile(body, None, Response(), {"id": "account-1"}, {})
    assert raised.value.status_code == 409


def test_partner_readiness_rejects_lost_state_transition_update(monkeypatch):
    readiness = _lost_update_readiness(monkeypatch)
    body = readiness.RevisionPayload(**revision_payload(1, "partner-readiness-lost-transition-0001"))
    with pytest.raises(HTTPException) as raised:
        readiness.request_review(body, None, Response(), {"id": "account-1"}, {})
    assert raised.value.status_code == 409
