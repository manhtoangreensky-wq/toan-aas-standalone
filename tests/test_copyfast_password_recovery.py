"""Focused security contracts for Web-native password recovery.

The suite uses an in-process SMTP fake only. It never calls a provider, Bot,
PayOS, wallet, job or live email service.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys
from typing import Any
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth"]
OLD_PASSWORD = "correct-horse-battery-staple"
NEW_PASSWORD = "different-horse-battery-staple"


def make_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, Any, Path]:
    db_path = tmp_path / "password-recovery.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "password-recovery-test-secret")
    monkeypatch.setenv("WEBAPP_PASSWORD_RECOVERY_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_EMAIL_VERIFICATION_PUBLIC_BASE_URL", "http://localhost")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_PORT", "587")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_PASSWORD", "smtp-test-password")
    monkeypatch.setenv("WEBAPP_EMAIL_SMTP_TLS_MODE", "starttls")
    monkeypatch.setenv("WEBAPP_EMAIL_VERIFICATION_FROM", "no-reply@example.test")
    for name in (
        "APP_ENV",
        "ENVIRONMENT",
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PUBLIC_DOMAIN",
        "WEBAPP_EMAIL_VERIFICATION_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    auth = importlib.import_module("copyfast_auth")
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    return TestClient(app), auth, db_path


def register_and_login(client: TestClient, email: str) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": OLD_PASSWORD, "display_name": "Recovery owner"},
    )
    assert registered.status_code == 200 and registered.json()["ok"] is True
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": OLD_PASSWORD},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True


def latest_challenge(db_path: Path) -> tuple[str, str, str]:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """SELECT id, token_hash, state
               FROM web_password_recovery_challenges
               ORDER BY created_at DESC, id DESC LIMIT 1"""
        ).fetchone()
    assert row is not None
    return str(row[0]), str(row[1]), str(row[2])


def test_password_recovery_is_non_enumerating_and_revokes_existing_sessions(tmp_path, monkeypatch):
    client, auth, db_path = make_client(tmp_path, monkeypatch)
    try:
        email = "recovery-owner@example.test"
        register_and_login(client, email)
        # A second valid browser session exists in SQLite before recovery.
        assert client.post("/api/v1/auth/login", json={"email": email, "password": OLD_PASSWORD}).json()["ok"] is True
        delivered: list[dict[str, str]] = []

        async def fake_send(_config: dict, *, recipient: str, challenge_id: str, token: str) -> None:
            delivered.append({"recipient": recipient, "challenge_id": challenge_id, "token": token})

        monkeypatch.setattr(auth, "_send_password_recovery_message", fake_send)
        unknown = client.post("/api/v1/auth/password-recovery/start", json={"email": "not-a-member@example.test"})
        started = client.post("/api/v1/auth/password-recovery/start", json={"email": email})

        assert unknown.status_code == 200 and started.status_code == 200
        assert unknown.json() == started.json()
        assert started.json()["data"] == {"password_recovery": {"accepted": True}}
        assert email not in started.text
        assert len(delivered) == 1 and delivered[0]["recipient"] == email

        challenge_id, token_hash, state = latest_challenge(db_path)
        assert state == "sent"
        assert token_hash != delivered[0]["token"]
        assert delivered[0]["token"] not in token_hash

        preview = client.get(
            "/api/v1/auth/password-recovery/confirm",
            params={"c": challenge_id, "t": delivered[0]["token"]},
        )
        assert preview.status_code == 200
        assert "Chọn mật khẩu mới" in preview.text
        assert preview.headers["cache-control"] == "no-store, private"
        assert latest_challenge(db_path)[2] == "sent"

        mismatch = client.post(
            "/api/v1/auth/password-recovery/confirm",
            data={
                "c": challenge_id,
                "t": delivered[0]["token"],
                "confirm": "password-recovery",
                "password": NEW_PASSWORD,
                "confirm_password": "not-the-same-password",
            },
        )
        assert mismatch.status_code == 200
        assert "chưa khớp" in mismatch.text
        assert latest_challenge(db_path)[2] == "sent"

        completed = client.post(
            "/api/v1/auth/password-recovery/confirm",
            data={
                "c": challenge_id,
                "t": delivered[0]["token"],
                "confirm": "password-recovery",
                "password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
        )
        assert completed.status_code == 200
        assert "Mật khẩu đã được đặt lại" in completed.text
        assert latest_challenge(db_path)[2] == "consumed"
        assert "max-age=0" in completed.headers["set-cookie"].lower()

        with sqlite3.connect(db_path) as conn:
            active_sessions = conn.execute(
                "SELECT COUNT(*) FROM web_sessions WHERE revoked_at IS NULL"
            ).fetchone()[0]
        assert active_sessions == 0

        old_login = client.post("/api/v1/auth/login", json={"email": email, "password": OLD_PASSWORD})
        assert old_login.status_code == 200 and old_login.json()["ok"] is False
        new_login = client.post("/api/v1/auth/login", json={"email": email, "password": NEW_PASSWORD})
        assert new_login.status_code == 200 and new_login.json()["ok"] is True

        replay = client.post(
            "/api/v1/auth/password-recovery/confirm",
            data={
                "c": challenge_id,
                "t": delivered[0]["token"],
                "confirm": "password-recovery",
                "password": OLD_PASSWORD,
                "confirm_password": OLD_PASSWORD,
            },
        )
        assert replay.status_code == 200
        assert "không còn hợp lệ" in replay.text
    finally:
        client.close()


def test_password_recovery_fails_closed_on_delivery_error_and_per_account_rate_limit(tmp_path, monkeypatch):
    client, auth, db_path = make_client(tmp_path, monkeypatch)
    try:
        email = "recovery-delivery@example.test"
        register_and_login(client, email)

        async def broken_send(_config: dict, **_kwargs) -> None:
            raise OSError("smtp private transport details")

        monkeypatch.setattr(auth, "_send_password_recovery_message", broken_send)
        failed_delivery = client.post("/api/v1/auth/password-recovery/start", json={"email": email})
        assert failed_delivery.status_code == 200 and failed_delivery.json()["ok"] is True
        assert "smtp private" not in failed_delivery.text
        assert latest_challenge(db_path)[2] == "failed"

        sent: list[str] = []

        async def fake_send(_config: dict, *, token: str, **_kwargs) -> None:
            sent.append(token)

        monkeypatch.setattr(auth, "_send_password_recovery_message", fake_send)
        for _ in range(2):
            response = client.post("/api/v1/auth/password-recovery/start", json={"email": email})
            assert response.status_code == 200 and response.json()["ok"] is True
        limited = client.post("/api/v1/auth/password-recovery/start", json={"email": email})
        assert limited.status_code == 200 and limited.json()["ok"] is True
        assert len(sent) == 2

        with sqlite3.connect(db_path) as conn:
            states = [
                row[0]
                for row in conn.execute(
                    "SELECT state FROM web_password_recovery_challenges ORDER BY created_at, id"
                ).fetchall()
            ]
        assert states.count("failed") == 1
        assert states.count("sent") == 1
        assert states.count("superseded") == 1
    finally:
        client.close()


def test_confirmation_headers_survive_the_full_app_middleware(tmp_path, monkeypatch):
    """The app middleware must not widen a one-time email-link page's policy."""

    client, _auth, _db_path = make_client(tmp_path, monkeypatch)
    try:
        sys.modules.pop("app", None)
        app_module = importlib.import_module("app")
        challenge_id = str(uuid.uuid4())
        token = "A" * 43
        with TestClient(app_module.app) as full_app:
            for path in (
                "/api/v1/auth/email-verification/confirm",
                "/api/v1/auth/password-recovery/confirm",
            ):
                response = full_app.get(path, params={"c": challenge_id, "t": token})
                assert response.status_code == 200
                assert response.headers["cache-control"] == "no-store, private"
                assert response.headers["referrer-policy"] == "no-referrer"
                assert response.headers["cross-origin-resource-policy"] == "same-origin"
                assert response.headers["content-security-policy"] == (
                    "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; "
                    "form-action 'self'; frame-ancestors 'none'"
                )
    finally:
        client.close()
        sys.modules.pop("app", None)
