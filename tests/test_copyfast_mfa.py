"""Focused contracts for optional Web-native TOTP MFA.

All tests use a temporary SQLite database and local deterministic TOTP math.
They never call Telegram, Bot, OAuth, PayOS, wallet, provider, job, SMTP or
any live service.
"""

from __future__ import annotations

import base64
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


MODULES = ["copyfast_db", "copyfast_auth", "copyfast_mfa"]
PASSWORD = "correct-horse-battery-staple"


def _mfa_key() -> str:
    return base64.urlsafe_b64encode(b"M" * 32).decode("ascii").rstrip("=")


def make_app(tmp_path: Path, monkeypatch) -> tuple[FastAPI, Any, Path]:
    db_path = tmp_path / "totp-mfa.db"
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(db_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "totp-mfa-test-session-secret")
    monkeypatch.setenv("WEBAPP_TOTP_MFA_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_TOTP_MFA_ENCRYPTION_KEY", _mfa_key())
    for name in (
        "APP_ENV",
        "ENVIRONMENT",
        "RAILWAY_ENVIRONMENT",
        "WEBAPP_EMAIL_VERIFICATION_ENABLED",
        "WEBAPP_PASSWORD_RECOVERY_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    import copyfast_auth
    import copyfast_mfa

    app = FastAPI()
    app.include_router(copyfast_auth.router, prefix="/api/v1/auth")
    app.include_router(copyfast_mfa.router)
    return app, copyfast_mfa, db_path


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "MFA owner"},
    )
    assert registered.status_code == 200 and registered.json()["ok"] is True
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert signed_in.status_code == 200 and signed_in.json()["ok"] is True
    return str(signed_in.json()["data"]["csrf_token"])


def _secret_from_manual_key(value: str) -> bytes:
    return base64.b32decode(value + "=" * (-len(value) % 8))


def _counter_now() -> int:
    return int(time.time()) // 30


def test_totp_enrollment_login_recovery_and_disable_are_web_native(tmp_path, monkeypatch):
    app, mfa, db_path = make_app(tmp_path, monkeypatch)
    email = "mfa-owner@example.test"
    with TestClient(app) as owner:
        csrf = register_and_login(owner, email)
        assert owner.post(
            "/api/v1/auth/mfa/enrollment/start",
            json={"current_password": PASSWORD},
        ).status_code == 403

        started = owner.post(
            "/api/v1/auth/mfa/enrollment/start",
            headers={"X-CSRF-Token": csrf},
            json={"current_password": PASSWORD},
        )
        assert started.status_code == 200 and started.json()["ok"] is True
        enrollment = started.json()["data"]["mfa_enrollment"]
        assert enrollment["issuer"] == "TOAN AAS"
        # The signed owner may receive their own account label for manual
        # authenticator setup, but the browser never receives a database
        # account id, factor ciphertext or recovery-code digest.
        assert enrollment["account_label"] == email
        assert "account_id" not in enrollment
        assert started.headers["cache-control"] == "no-store, private"
        secret = _secret_from_manual_key(str(enrollment["manual_key"]))
        assert len(secret) == mfa.TOTP_SECRET_BYTES

        enrollment_counter = _counter_now()
        confirm = owner.post(
            "/api/v1/auth/mfa/enrollment/confirm",
            headers={"X-CSRF-Token": csrf},
            json={
                "factor_id": enrollment["factor_id"],
                "enrollment_token": enrollment["enrollment_token"],
                "code": mfa._totp_code(secret, enrollment_counter),
            },
        )
        assert confirm.status_code == 200 and confirm.json()["ok"] is True
        recovery_codes = confirm.json()["data"]["recovery_codes"]
        assert len(recovery_codes) == mfa.TOTP_RECOVERY_CODE_COUNT
        assert all(mfa.TOTP_RECOVERY_CODE_PATTERN.fullmatch(code) for code in recovery_codes)
        assert confirm.headers["cache-control"] == "no-store, private"

        with sqlite3.connect(db_path) as conn:
            ciphertext, token_hash = conn.execute(
                "SELECT secret_ciphertext, enrollment_token_hash FROM web_totp_factors"
            ).fetchone()
            stored_codes = [
                row[0] for row in conn.execute("SELECT code_hash FROM web_totp_recovery_codes").fetchall()
            ]
        assert enrollment["manual_key"] not in ciphertext
        assert enrollment["enrollment_token"] not in ciphertext
        assert enrollment["enrollment_token"] not in token_hash
        assert all(code not in "\n".join(stored_codes) for code in recovery_codes)

    with TestClient(app) as second_browser:
        password_first = second_browser.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
        )
        assert password_first.status_code == 200 and password_first.json()["ok"] is True
        challenge = password_first.json()["data"]
        assert challenge["mfa_required"] is True
        assert "account_id" not in challenge

        replayed_enrollment_code = second_browser.post(
            "/api/v1/auth/login/mfa",
            json={
                "challenge_id": challenge["challenge_id"],
                "challenge_token": challenge["challenge_token"],
                "code": mfa._totp_code(secret, enrollment_counter),
            },
        )
        assert replayed_enrollment_code.status_code == 200
        assert replayed_enrollment_code.json()["ok"] is False
        assert replayed_enrollment_code.json()["error_code"] == "WEB_TOTP_MFA_LOGIN_DENIED"

        next_counter = max(_counter_now() + 1, enrollment_counter + 1)
        completed = second_browser.post(
            "/api/v1/auth/login/mfa",
            json={
                "challenge_id": challenge["challenge_id"],
                "challenge_token": challenge["challenge_token"],
                "code": mfa._totp_code(secret, next_counter),
            },
        )
        assert completed.status_code == 200 and completed.json()["ok"] is True
        second_csrf = str(completed.json()["data"]["csrf_token"])

        status = second_browser.get("/api/v1/auth/mfa/status")
        assert status.status_code == 200 and status.json()["ok"] is True
        assert status.json()["data"]["mfa"] == {
            "enabled": True,
            "pending_enrollment": False,
            "runtime_available": True,
            "password_factor_available": True,
            "recovery_codes_remaining": mfa.TOTP_RECOVERY_CODE_COUNT,
        }

        disabled = second_browser.post(
            "/api/v1/auth/mfa/disable",
            headers={"X-CSRF-Token": second_csrf},
            json={
                "current_password": PASSWORD,
                # The successful login consumed the adjacent TOTP counter;
                # use a different one-time recovery code instead of waiting
                # for the next 30-second authenticator period.
                "verification_code": recovery_codes[1],
                "confirm": True,
            },
        )
        assert disabled.status_code == 200 and disabled.json()["ok"] is True
        assert disabled.json()["data"]["mfa"]["enabled"] is False
        assert disabled.json()["data"]["csrf_token"] != second_csrf

        with sqlite3.connect(db_path) as conn:
            factor_state = conn.execute("SELECT state FROM web_totp_factors").fetchone()[0]
            remaining = conn.execute(
                "SELECT COUNT(*) FROM web_totp_recovery_codes WHERE used_at IS NULL AND invalidated_at IS NULL"
            ).fetchone()[0]
        assert factor_state == "disabled"
        assert remaining == 0

        normal_login = second_browser.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
        )
        assert normal_login.status_code == 200 and normal_login.json()["ok"] is True
        assert normal_login.json()["data"].get("mfa_required") is None


def test_recovery_code_is_one_time_and_mfa_never_fails_open_when_paused(tmp_path, monkeypatch):
    app, mfa, _db_path = make_app(tmp_path, monkeypatch)
    email = "mfa-recovery@example.test"
    with TestClient(app) as owner:
        csrf = register_and_login(owner, email)
        started = owner.post(
            "/api/v1/auth/mfa/enrollment/start",
            headers={"X-CSRF-Token": csrf},
            json={"current_password": PASSWORD},
        ).json()["data"]["mfa_enrollment"]
        secret = _secret_from_manual_key(str(started["manual_key"]))
        counter = _counter_now()
        confirmed = owner.post(
            "/api/v1/auth/mfa/enrollment/confirm",
            headers={"X-CSRF-Token": csrf},
            json={
                "factor_id": started["factor_id"],
                "enrollment_token": started["enrollment_token"],
                "code": mfa._totp_code(secret, counter),
            },
        )
        recovery_code = confirmed.json()["data"]["recovery_codes"][0]

    with TestClient(app) as first_recovery:
        challenge = first_recovery.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
        ).json()["data"]
        recovered = first_recovery.post(
            "/api/v1/auth/login/mfa",
            json={
                "challenge_id": challenge["challenge_id"],
                "challenge_token": challenge["challenge_token"],
                "code": recovery_code,
            },
        )
        assert recovered.status_code == 200 and recovered.json()["ok"] is True

    with TestClient(app) as replay_browser:
        challenge = replay_browser.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
        ).json()["data"]
        replay = replay_browser.post(
            "/api/v1/auth/login/mfa",
            json={
                "challenge_id": challenge["challenge_id"],
                "challenge_token": challenge["challenge_token"],
                "code": recovery_code,
            },
        )
        assert replay.status_code == 200 and replay.json()["ok"] is False
        assert replay.json()["error_code"] == "WEB_TOTP_MFA_LOGIN_DENIED"

    monkeypatch.setenv("WEBAPP_TOTP_MFA_ENABLED", "false")
    with TestClient(app) as paused_browser:
        paused = paused_browser.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD},
        )
        assert paused.status_code == 200 and paused.json()["ok"] is False
        assert paused.json()["error_code"] == "WEB_TOTP_MFA_UNAVAILABLE"
