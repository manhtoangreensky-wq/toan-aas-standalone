"""Focused contracts for the redacted, read-only Security & Access Posture."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import copyfast_admin_security_posture as posture


def _database() -> tuple[sqlite3.Connection, datetime, str]:
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    marker = "POSTURE-PRIVATE-SECRET-0123456789"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    connection.executescript(
        """
        CREATE TABLE web_accounts (
            id TEXT, email TEXT, password_hash TEXT, canonical_user_id TEXT,
            role_cache TEXT NOT NULL, is_active INTEGER NOT NULL
        );
        CREATE TABLE web_sessions (
            id TEXT, account_id TEXT, csrf_token TEXT, revoked_at TEXT, expires_at TEXT NOT NULL
        );
        CREATE TABLE web_totp_factors (
            id TEXT, account_id TEXT, secret_ciphertext TEXT, enrollment_token_hash TEXT, state TEXT NOT NULL
        );
        CREATE TABLE web_totp_recovery_codes (
            id TEXT, factor_id TEXT, account_id TEXT, code_hash TEXT, used_at TEXT, invalidated_at TEXT
        );
        CREATE TABLE web_totp_login_challenges (
            id TEXT, account_id TEXT, token_hash TEXT, state TEXT NOT NULL, expires_at TEXT NOT NULL
        );
        CREATE TABLE web_auth_throttle_buckets (
            action TEXT NOT NULL, email_hmac TEXT, client_scope_hmac TEXT, expires_at_epoch INTEGER NOT NULL
        );
        CREATE TABLE web_audit_events (
            id TEXT, account_id TEXT, canonical_user_id TEXT, action TEXT NOT NULL, request_id TEXT,
            target TEXT, outcome TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL
        );
        """
    )
    connection.executemany(
        """INSERT INTO web_accounts (id, email, password_hash, canonical_user_id, role_cache, is_active)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            ("account-admin", f"{marker}@example.com", marker, marker, "admin", 1),
            ("account-manager", "manager@example.com", marker, marker, "support_manager", 1),
            ("account-operator", "operator@example.com", marker, marker, "support_operator", 0),
            ("account-user", "user@example.com", marker, marker, "user", 1),
        ],
    )
    connection.executemany(
        """INSERT INTO web_sessions (id, account_id, csrf_token, revoked_at, expires_at)
           VALUES (?, ?, ?, ?, ?)""",
        [
            ("session-active", "account-admin", marker, None, (now + timedelta(days=1)).isoformat()),
            ("session-revoked", "account-manager", marker, (now - timedelta(hours=1)).isoformat(), (now + timedelta(days=1)).isoformat()),
            ("session-expired", "account-operator", marker, None, (now - timedelta(days=1)).isoformat()),
        ],
    )
    connection.executemany(
        """INSERT INTO web_totp_factors (id, account_id, secret_ciphertext, enrollment_token_hash, state)
           VALUES (?, ?, ?, ?, ?)""",
        [
            ("factor-active", "account-admin", marker, marker, "active"),
            ("factor-prepared", "account-manager", marker, marker, "prepared"),
            ("factor-disabled", "account-user", marker, marker, "disabled"),
        ],
    )
    connection.executemany(
        """INSERT INTO web_totp_recovery_codes (id, factor_id, account_id, code_hash, used_at, invalidated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            ("recovery-active", "factor-active", "account-admin", marker, None, None),
            ("recovery-used", "factor-active", "account-admin", marker, now.isoformat(), None),
            ("recovery-invalid", "factor-active", "account-admin", marker, None, now.isoformat()),
        ],
    )
    connection.executemany(
        """INSERT INTO web_totp_login_challenges (id, account_id, token_hash, state, expires_at)
           VALUES (?, ?, ?, ?, ?)""",
        [
            ("challenge-pending", "account-admin", marker, "pending", (now + timedelta(minutes=5)).isoformat()),
            ("challenge-locked", "account-admin", marker, "locked", (now + timedelta(minutes=5)).isoformat()),
            ("challenge-consumed", "account-admin", marker, "consumed", (now + timedelta(minutes=5)).isoformat()),
        ],
    )
    current_epoch = int(now.timestamp())
    connection.executemany(
        """INSERT INTO web_auth_throttle_buckets (action, email_hmac, client_scope_hmac, expires_at_epoch)
           VALUES (?, ?, ?, ?)""",
        [
            ("login", marker, marker, current_epoch + 600),
            ("register", marker, marker, current_epoch + 600),
            ("password_change", marker, marker, current_epoch + 600),
            ("login", marker, marker, current_epoch - 600),
        ],
    )
    connection.executemany(
        """INSERT INTO web_audit_events
           (id, account_id, canonical_user_id, action, request_id, target, outcome, detail, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ("audit-sign-in-ok", marker, marker, "auth.login", marker, marker, "ok", marker, now.isoformat()),
            ("audit-sign-in-denied", marker, marker, "auth.login", marker, marker, "denied", marker, now.isoformat()),
            ("audit-mfa-ok", marker, marker, "auth.mfa_enrollment_start", marker, marker, "ok", marker, now.isoformat()),
            ("audit-mfa-guarded", marker, marker, "auth.mfa_login", marker, marker, "guarded", marker, now.isoformat()),
            ("audit-credential-ok", marker, marker, "auth.security_password_change", marker, marker, "ok", marker, now.isoformat()),
            ("audit-credential-failed", marker, marker, "auth.password_recovery_confirm", marker, marker, "failed", marker, now.isoformat()),
            ("audit-session-ok", marker, marker, "auth.logout", marker, marker, "ok", marker, now.isoformat()),
            ("audit-session-denied", marker, marker, "auth.security_session_revoke", marker, marker, "denied", marker, now.isoformat()),
            # A global audit event unrelated to this narrow security projection
            # must not make its raw action or detail browser-visible.
            ("audit-unrelated", marker, marker, "content.private_action", marker, marker, "ok", marker, now.isoformat()),
        ],
    )
    connection.commit()
    return connection, now, marker


def _client(monkeypatch, connection: sqlite3.Connection, *, role: str = "admin") -> TestClient:
    app = FastAPI()
    app.include_router(posture.router)

    @contextmanager
    def read_transaction():
        yield connection

    def signed_local_admin():
        if role != "admin":
            raise HTTPException(status_code=403, detail="local admin required")
        return {"id": "admin-private", "role": "admin"}

    app.dependency_overrides[posture.require_admin] = signed_local_admin
    monkeypatch.setattr(posture, "read_transaction", read_transaction)
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_TOTP_MFA_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_EMAIL_VERIFICATION_ENABLED", "false")
    for provider in ("GOOGLE", "GITHUB", "APPLE", "TELEGRAM"):
        monkeypatch.delenv(f"WEBAPP_{provider}_OAUTH_ENABLED", raising=False)
    return TestClient(app)


def test_posture_requires_local_admin_and_never_exposes_private_columns(monkeypatch) -> None:
    connection, _, marker = _database()
    with _client(monkeypatch, connection, role="user") as client:
        assert client.get("/api/v1/admin/security-posture/summary").status_code == 403

    with _client(monkeypatch, connection) as client:
        response = client.get("/api/v1/admin/security-posture/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True and body["status"] == "read_only" and body["error_code"] is None
    data = body["data"]
    assert set(data) == {
        "source", "policy_version", "read_only", "integrity_guarded", "enforcement", "access",
        "sessions", "mfa", "throttle", "security_activity", "boundaries",
    }
    assert data["source"] == data["policy_version"] == "web_security_access_posture_v1"
    assert data["read_only"] is True and data["integrity_guarded"] is False
    assert data["access"] == {
        "active_accounts": 3,
        "inactive_accounts": 1,
        "privileged_accounts": 3,
        "admin_accounts": 1,
        "support_manager_accounts": 1,
        "support_operator_accounts": 1,
        "unknown_role_accounts": 0,
    }
    assert data["sessions"] == {"active": 1, "revoked_recent": 1, "expired_unrevoked": 1}
    assert data["mfa"] == {
        "active_factors": 1,
        "pending_enrollments": 1,
        "locked_login_challenges": 1,
        "pending_login_challenges": 1,
        "active_recovery_codes": 1,
    }
    assert data["throttle"] == {
        "login_active_buckets": 1,
        "register_active_buckets": 1,
        "password_change_active_buckets": 1,
    }
    assert data["security_activity"] == {
        "window_hours": 24,
        "sign_in_completed": 1,
        "sign_in_guarded": 1,
        "mfa_completed": 1,
        "mfa_guarded": 1,
        "credential_change_completed": 1,
        "credential_change_guarded": 1,
        "session_control_completed": 1,
        "session_control_guarded": 1,
    }
    assert data["enforcement"] == {
        "mfa_runtime": "disabled",
        "email_verification_delivery": "disabled_or_unavailable",
        "oauth_feature_flags": {"google": False, "github": False, "apple": False},
    }
    assert data["boundaries"] == [
        "Chỉ hiển thị aggregate Web-native; không có account, email, session, token, secret, IP hoặc audit detail.",
        "Trang chỉ đọc; không cấp role, thu hồi session, reset MFA hoặc thay đổi credential.",
        "Không gọi Bot/Core Bridge, provider, PayOS, ví Xu, job, webhook hoặc deploy.",
    ]
    rendered = json.dumps(body)
    assert marker not in rendered
    for forbidden in (
        "password_hash", "canonical_user_id", "csrf_token", "secret_ciphertext", "enrollment_token_hash",
        "code_hash", "token_hash", "email_hmac", "client_scope_hmac", "request_id", "target",
        "account-admin", "session-active", "audit-unrelated", "content.private_action",
    ):
        assert forbidden not in rendered


def test_posture_hides_every_database_metric_when_role_state_or_outcome_is_malformed(monkeypatch) -> None:
    connection, _, marker = _database()
    connection.executemany(
        """INSERT INTO web_accounts (id, email, password_hash, canonical_user_id, role_cache, is_active)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [("bad-role", marker, marker, marker, "RAW-PRIVATE-UNKNOWN-ROLE", 1)],
    )
    connection.executemany(
        """INSERT INTO web_totp_factors (id, account_id, secret_ciphertext, enrollment_token_hash, state)
           VALUES (?, ?, ?, ?, ?)""",
        [("bad-factor", "account-admin", marker, marker, "RAW-PRIVATE-FACTOR-STATE")],
    )
    connection.executemany(
        """INSERT INTO web_audit_events
           (id, account_id, canonical_user_id, action, request_id, target, outcome, detail, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [("bad-outcome", marker, marker, "auth.login", marker, marker, "RAW-PRIVATE-AUDIT-OUTCOME", marker, datetime.now(timezone.utc).isoformat())],
    )
    connection.commit()

    with _client(monkeypatch, connection) as client:
        response = client.get("/api/v1/admin/security-posture/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "guarded"
    assert body["error_code"] == "ADMIN_SECURITY_ACCESS_POSTURE_DATA_GUARDED"
    data = body["data"]
    assert data["integrity_guarded"] is True
    assert all(value is None for value in data["access"].values())
    assert all(value is None for value in data["sessions"].values())
    assert all(value is None for value in data["mfa"].values())
    assert all(value is None for value in data["throttle"].values())
    assert data["security_activity"]["window_hours"] == 24
    assert all(value is None for key, value in data["security_activity"].items() if key != "window_hours")
    rendered = json.dumps(body)
    for forbidden in (marker, "RAW-PRIVATE-UNKNOWN-ROLE", "RAW-PRIVATE-FACTOR-STATE", "RAW-PRIVATE-AUDIT-OUTCOME"):
        assert forbidden not in rendered


def test_erp_kill_switch_guards_before_any_database_read(monkeypatch) -> None:
    connection, _, _ = _database()
    with _client(monkeypatch, connection) as client:
        monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
        called = {"read": False}

        def forbidden_read():
            called["read"] = True
            raise AssertionError("disabled posture must not open a database read")

        monkeypatch.setattr(posture, "read_transaction", forbidden_read)
        response = client.get("/api/v1/admin/security-posture/summary")

    assert response.status_code == 200
    assert response.json()["status"] == "guarded"
    assert response.json()["error_code"] == "WEBAPP_ADMIN_ERP_DISABLED"
    assert response.json()["data"]["integrity_guarded"] is True
    assert called["read"] is False


def test_posture_source_remains_read_only_web_native_and_redacted() -> None:
    source = (Path(__file__).parents[1] / "copyfast_admin_security_posture.py").read_text(encoding="utf-8")
    assert 'router = APIRouter(prefix="/api/v1/admin/security-posture"' in source
    assert '@router.get("/summary")' in source
    assert "Depends(require_admin)" in source
    for forbidden in (
        "copyfast_bridge", "@router.post", "@router.put", "@router.patch", "@router.delete", "SELECT *",
        "telegram_link_codes", "telegram_login_codes", "web_oauth_states", "web_external_identities",
        "web_email_verification_challenges", "web_password_recovery_challenges", "web_bridge_callback_nonces",
        "web_idempotency", "web_feature_quote_receipts",
    ):
        assert forbidden not in source
    assert "from copyfast_db import read_transaction" in source
    assert "from copyfast_db import transaction" not in source
