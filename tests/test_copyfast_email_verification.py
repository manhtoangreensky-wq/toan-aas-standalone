"""Focused contract tests for the Web-owned mailbox verification adapter.

The tests use an in-process SMTP handoff fake. They never open a network
connection, call an OAuth provider, access the Bot bridge, mutate a wallet or
invoke a provider/job/payment flow.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth"]
PASSWORD = "correct-horse-battery-staple"


def make_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, Any, Path]:
    db_path = tmp_path / "email-verification.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "email-verification-test-secret")
    monkeypatch.setenv("WEBAPP_EMAIL_VERIFICATION_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL", "http://localhost")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_PORT", "587")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_PASSWORD", "smtp-test-password")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_TLS_MODE", "starttls")
    monkeypatch.setenv("WEBAPP_EMAIL_VERIFICATION_FROM", "no-reply@example.test")
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_PUBLIC_DOMAIN"):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    return TestClient(app), auth, db_path


def register_and_login(client: TestClient, email: str = "mailbox-owner@example.test") -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Mailbox owner"},
    )
    assert registered.status_code == 200 and registered.json()["ok"] is True
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True
    return str(signed_in.json()["data"]["csrf_token"])


def latest_challenge(db_path: Path) -> tuple[str, str, str]:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """SELECT id, token_hash, state
               FROM web_email_verification_challenges
               ORDER BY created_at DESC, id DESC LIMIT 1"""
        ).fetchone()
    assert row is not None
    return str(row[0]), str(row[1]), str(row[2])


def test_email_link_requires_csrf_delivery_and_manual_confirmation(tmp_path, monkeypatch):
    client, auth, db_path = make_client(tmp_path, monkeypatch)
    try:
        csrf = register_and_login(client)
        delivered: list[dict[str, str]] = []

        async def fake_send(config: dict, *, recipient: str, challenge_id: str, token: str) -> None:
            assert config["host"] == "smtp.example.test"
            assert config["password"] == "smtp-test-password"
            delivered.append(
                {
                    "recipient": recipient,
                    "challenge_id": challenge_id,
                    "token": token,
                }
            )

        monkeypatch.setattr(auth, "_send_email_verification_message", fake_send)

        assert client.post(
            "/api/v1/auth/security/email-verification/start",
            json={"confirm": True},
        ).status_code == 403

        missing_confirmation = client.post(
            "/api/v1/auth/security/email-verification/start",
            headers={"X-CSRF-Token": csrf},
            json={"confirm": False},
        )
        assert missing_confirmation.status_code == 200
        assert missing_confirmation.json()["error_code"] == "EMAIL_VERIFICATION_CONFIRM_REQUIRED"

        started = client.post(
            "/api/v1/auth/security/email-verification/start",
            headers={"X-CSRF-Token": csrf},
            json={"confirm": True},
        )
        body = started.json()
        assert started.status_code == 200 and body["ok"] is True
        assert body["status"] == "awaiting_confirm"
        assert body["data"]["email_verification"] == {
            "started": True,
            "pending": True,
            "expires_in_minutes": 20,
        }
        assert len(delivered) == 1
        assert delivered[0]["recipient"] == "mailbox-owner@example.test"
        assert delivered[0]["token"] not in started.text
        assert delivered[0]["recipient"] not in started.text

        challenge_id, token_hash, state = latest_challenge(db_path)
        assert state == "sent"
        assert token_hash != delivered[0]["token"]
        assert delivered[0]["token"] not in token_hash

        preview = client.get(
            "/api/v1/auth/email-verification/confirm",
            params={"c": challenge_id, "t": delivered[0]["token"]},
        )
        assert preview.status_code == 200
        assert "Xác nhận quyền sở hữu email" in preview.text
        assert preview.headers["cache-control"] == "no-store, private"
        assert preview.headers["referrer-policy"] == "no-referrer"
        assert latest_challenge(db_path)[2] == "sent"

        completed = client.post(
            "/api/v1/auth/email-verification/confirm",
            data={"c": challenge_id, "t": delivered[0]["token"], "confirm": "email-link"},
        )
        assert completed.status_code == 200
        assert "Email đã được xác minh" in completed.text
        assert latest_challenge(db_path)[2] == "consumed"

        with sqlite3.connect(db_path) as conn:
            contact = conn.execute(
                """SELECT email, verification_method
                   FROM web_account_email_contacts"""
            ).fetchone()
        assert contact == ("mailbox-owner@example.test", "email_link")

        methods = client.get("/api/v1/auth/security/login-methods")
        assert methods.status_code == 200
        login_methods = methods.json()["data"]["login_methods"]
        assert login_methods["contact"] == {
            "state": "verified_email_link",
            "provider": "email_link",
            "verified": True,
        }
        assert login_methods["email_verification"] == {
            "available": True,
            "can_start": False,
            "pending": False,
        }
        assert "mailbox-owner@example.test" not in methods.text

        replay = client.post(
            "/api/v1/auth/email-verification/confirm",
            data={"c": challenge_id, "t": delivered[0]["token"], "confirm": "email-link"},
        )
        assert replay.status_code == 200
        assert "không còn hợp lệ" in replay.text
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_account_email_contacts").fetchone()[0] == 1
    finally:
        client.close()


def test_email_link_fails_closed_on_delivery_error_and_rate_limits_starts(tmp_path, monkeypatch):
    client, auth, db_path = make_client(tmp_path, monkeypatch)
    try:
        csrf = register_and_login(client, "delivery-owner@example.test")

        async def broken_send(_config: dict, **_kwargs) -> None:
            raise OSError("smtp unavailable: private details must not escape")

        monkeypatch.setattr(auth, "_send_email_verification_message", broken_send)
        failed = client.post(
            "/api/v1/auth/security/email-verification/start",
            headers={"X-CSRF-Token": csrf},
            json={"confirm": True},
        )
        assert failed.status_code == 503
        assert failed.json()["error_code"] == "EMAIL_VERIFICATION_DELIVERY_FAILED"
        assert "smtp unavailable" not in failed.text
        assert latest_challenge(db_path)[2] == "failed"
        assert client.get("/api/v1/auth/security/login-methods").json()["data"]["login_methods"]["contact"]["state"] == "unverified"

        sent_tokens: list[str] = []

        async def delivered_send(_config: dict, *, token: str, **_kwargs) -> None:
            sent_tokens.append(token)

        monkeypatch.setattr(auth, "_send_email_verification_message", delivered_send)
        for _ in range(2):
            accepted = client.post(
                "/api/v1/auth/security/email-verification/start",
                headers={"X-CSRF-Token": csrf},
                json={"confirm": True},
            )
            assert accepted.status_code == 200 and accepted.json()["ok"] is True
        limited = client.post(
            "/api/v1/auth/security/email-verification/start",
            headers={"X-CSRF-Token": csrf},
            json={"confirm": True},
        )
        assert limited.status_code == 429
        assert limited.json()["error_code"] == "EMAIL_VERIFICATION_RATE_LIMITED"
        assert len(sent_tokens) == 2
        with sqlite3.connect(db_path) as conn:
            states = [
                row[0]
                for row in conn.execute(
                    "SELECT state FROM web_email_verification_challenges ORDER BY created_at, id"
                ).fetchall()
            ]
        assert states.count("failed") == 1
        assert states.count("sent") == 1
        assert states.count("superseded") == 1
    finally:
        client.close()


def test_email_verification_is_guarded_without_a_real_delivery_configuration(tmp_path, monkeypatch):
    client, _auth, db_path = make_client(tmp_path, monkeypatch)
    try:
        csrf = register_and_login(client, "no-delivery@example.test")
        monkeypatch.delenv("WEBAPP_EMAIL_SMTP_PASSWORD", raising=False)
        guarded = client.post(
            "/api/v1/auth/security/email-verification/start",
            headers={"X-CSRF-Token": csrf},
            json={"confirm": True},
        )
        assert guarded.status_code == 503
        assert guarded.json()["error_code"] == "EMAIL_VERIFICATION_UNAVAILABLE"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_email_verification_challenges").fetchone()[0] == 0
    finally:
        client.close()
