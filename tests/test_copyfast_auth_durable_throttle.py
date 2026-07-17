"""Focused evidence for durable email/password credential throttling."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib
import sqlite3
import sys

from fastapi.testclient import TestClient
from starlette.requests import Request


def _prepare(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "web.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "unit-test-session-secret")
    monkeypatch.delenv("WEBAPP_AUTH_THROTTLE_HMAC_SECRET", raising=False)
    monkeypatch.delenv("WEBAPP_AUTH_TRUSTED_PROXY_CIDRS", raising=False)
    import copyfast_auth_throttle
    import copyfast_db

    copyfast_db.ensure_copyfast_schema()
    return copyfast_auth_throttle, copyfast_db


def _request(*, client_host="10.4.0.8", headers=None):
    encoded_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/auth/login",
            "raw_path": b"/api/v1/auth/login",
            "query_string": b"",
            "headers": encoded_headers,
            "client": (client_host, 443),
            "server": ("app.toanaas.vn", 443),
        }
    )


def test_throttle_normalizes_and_persists_only_hmac_fingerprints(tmp_path, monkeypatch):
    throttle, database = _prepare(tmp_path, monkeypatch)

    first = throttle.email_fingerprint("  Person.Example@Example.COM ")
    second = throttle.email_fingerprint("person.example@example.com")
    assert first == second
    assert first and "person.example@example.com" not in first
    scope = throttle.client_scope_fingerprint(_request())
    assert scope and "10.4.0.8" not in scope
    global_scope = throttle.email_global_scope_fingerprint("login", first)
    assert global_scope and global_scope != scope

    decision = throttle.consume_fingerprints(action="login", email_hmac=first, client_scope_hmac=scope, now_epoch=1_000)
    assert decision.allowed is True
    with sqlite3.connect(database.session_database_path()) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(web_auth_throttle_buckets)")}
        rows = conn.execute(
            """SELECT action, email_hmac, client_scope_hmac, attempts
               FROM web_auth_throttle_buckets ORDER BY client_scope_hmac"""
        ).fetchall()
    assert columns == {
        "action", "email_hmac", "client_scope_hmac", "attempts", "window_started_at", "expires_at_epoch", "updated_at"
    }
    assert set(rows) == {
        ("login", first, scope, 1),
        ("login", first, global_scope, 1),
    }
    assert "person.example@example.com" not in repr(rows)
    assert "10.4.0.8" not in repr(rows)


def test_throttle_is_atomic_and_survives_module_restart(tmp_path, monkeypatch):
    throttle, database = _prepare(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_THROTTLE_LIMIT", "2")
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_THROTTLE_WINDOW_SECONDS", "300")
    monkeypatch.setenv("WEBAPP_AUTH_THROTTLE_DB_TIMEOUT_SECONDS", "0.5")
    email_hmac = throttle.email_fingerprint("atomic@example.com")
    scope_hmac = throttle.client_scope_fingerprint(_request())
    assert email_hmac and scope_hmac

    def consume_one():
        return throttle.consume_fingerprints(
            action="login", email_hmac=email_hmac, client_scope_hmac=scope_hmac, now_epoch=2_000
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        decisions = list(executor.map(lambda _: consume_one(), range(4)))
    assert sum(decision.allowed for decision in decisions) == 2
    assert all(decision.reason in {"allowed", "limited"} for decision in decisions)
    with sqlite3.connect(database.session_database_path()) as conn:
        attempts = conn.execute(
            "SELECT attempts FROM web_auth_throttle_buckets WHERE action='login' AND email_hmac=? AND client_scope_hmac=?",
            (email_hmac, scope_hmac),
        ).fetchone()[0]
    assert attempts == 2

    # Reload deliberately discards module globals.  The persisted bucket must
    # still reject a further attempt rather than being reset by a worker restart.
    restarted = importlib.reload(throttle)
    after_restart = restarted.consume_fingerprints(
        action="login", email_hmac=email_hmac, client_scope_hmac=scope_hmac, now_epoch=2_001
    )
    assert after_restart.allowed is False
    assert after_restart.reason == "limited"


def test_email_global_bucket_resists_rotating_client_fingerprints(tmp_path, monkeypatch):
    throttle, database = _prepare(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_THROTTLE_LIMIT", "10")
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_THROTTLE_WINDOW_SECONDS", "300")
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_GLOBAL_THROTTLE_LIMIT", "2")
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_GLOBAL_THROTTLE_WINDOW_SECONDS", "300")
    email_hmac = throttle.email_fingerprint("rotating@example.com")
    first_scope = throttle.client_scope_fingerprint(_request(client_host="10.4.0.8"))
    second_scope = throttle.client_scope_fingerprint(_request(client_host="10.4.0.9"))
    global_scope = throttle.email_global_scope_fingerprint("login", email_hmac or "")
    assert email_hmac and first_scope and second_scope and global_scope
    assert first_scope != second_scope

    first = throttle.consume_fingerprints(
        action="login", email_hmac=email_hmac, client_scope_hmac=first_scope, now_epoch=3_000,
    )
    second = throttle.consume_fingerprints(
        action="login", email_hmac=email_hmac, client_scope_hmac=second_scope, now_epoch=3_000,
    )
    blocked = throttle.consume_fingerprints(
        action="login", email_hmac=email_hmac, client_scope_hmac=first_scope, now_epoch=3_001,
    )
    assert first.allowed is True
    assert second.allowed is True
    assert blocked.allowed is False
    assert blocked.reason == "limited"
    assert blocked.retry_after_seconds == 299

    with sqlite3.connect(database.session_database_path()) as conn:
        client_attempts = conn.execute(
            """SELECT client_scope_hmac, attempts FROM web_auth_throttle_buckets
               WHERE action='login' AND email_hmac=? ORDER BY client_scope_hmac""",
            (email_hmac,),
        ).fetchall()
    assert set(client_attempts) == {(first_scope, 1), (second_scope, 1), (global_scope, 2)}
    assert "rotating@example.com" not in repr(client_attempts)
    assert "10.4.0.8" not in repr(client_attempts)
    assert "10.4.0.9" not in repr(client_attempts)


def test_forwarded_client_is_ignored_until_direct_peer_is_explicitly_trusted(tmp_path, monkeypatch):
    throttle, _database = _prepare(tmp_path, monkeypatch)
    spoofed = throttle.client_scope_fingerprint(
        _request(headers={"X-Forwarded-For": "198.51.100.9"})
    )
    direct = throttle.client_scope_fingerprint(_request())
    assert spoofed == direct

    monkeypatch.setenv("WEBAPP_AUTH_TRUSTED_PROXY_CIDRS", "10.0.0.0/8")
    trusted_forwarded = throttle.client_scope_fingerprint(
        _request(headers={"X-Forwarded-For": "198.51.100.9"})
    )
    public_direct = throttle.client_scope_fingerprint(_request(client_host="198.51.100.9"))
    assert trusted_forwarded == public_direct
    assert trusted_forwarded != direct

    # Invalid allowlists fail closed: no proxy header becomes trusted.
    monkeypatch.setenv("WEBAPP_AUTH_TRUSTED_PROXY_CIDRS", "10.0.0.0/8,not-a-network")
    assert throttle.client_scope_fingerprint(_request(headers={"X-Forwarded-For": "198.51.100.9"})) == direct
    monkeypatch.setenv("WEBAPP_AUTH_TRUSTED_PROXY_CIDRS", "0.0.0.0/0")
    assert throttle.client_scope_fingerprint(_request(headers={"X-Forwarded-For": "198.51.100.9"})) == direct


def test_database_failure_is_a_sanitized_fail_closed_decision(tmp_path, monkeypatch):
    throttle, _database = _prepare(tmp_path, monkeypatch)
    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("not a database directory", encoding="utf-8")
    monkeypatch.setattr(throttle, "session_database_path", lambda: str(blocked_parent / "db.sqlite"))
    email_hmac = throttle.email_fingerprint("unavailable@example.com")
    scope_hmac = throttle.client_scope_fingerprint(_request())
    assert email_hmac and scope_hmac

    decision = throttle.consume_fingerprints(action="login", email_hmac=email_hmac, client_scope_hmac=scope_hmac)
    assert decision.allowed is False
    assert decision.reason == "unavailable"
    assert "unavailable@example.com" not in repr(decision)
    assert "sqlite" not in repr(decision).lower()


def test_password_routes_return_bounded_guard_for_persistence_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "route.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "route-test-session-secret")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "route-test-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "route-test-hmac")
    # The route response must preserve the same bounded Retry-After header
    # when the cross-client email bucket—not the local client bucket—wins.
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_THROTTLE_LIMIT", "10")
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_GLOBAL_THROTTLE_LIMIT", "2")
    monkeypatch.setenv("WEBAPP_AUTH_LOGIN_GLOBAL_THROTTLE_WINDOW_SECONDS", "60")
    for name in ("app", "copyfast_auth", "copyfast_auth_throttle", "copyfast_db"):
        sys.modules.pop(name, None)
    application = importlib.import_module("app").app

    with TestClient(application) as client:
        # The route-level counter only sees a compact replayed body; a chunk
        # this large is rejected by the raw ASGI cap before JSON parsing.
        oversized = client.post(
            "/api/v1/auth/login",
            content=b'{"email":"' + (b"a" * 9_000) + b'@example.com"}',
            headers={"Content-Type": "application/json"},
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_AUTH_CREDENTIAL_BODY_TOO_LARGE"
        first = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "not-the-right-password"},
        )
        assert first.status_code == 200
        second = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "not-the-right-password"},
        )
        assert second.status_code == 200
        limited = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "not-the-right-password"},
        )
        assert limited.status_code == 429
        assert limited.json()["error_code"] == "AUTH_RATE_LIMITED"
        assert 1 <= int(limited.headers["retry-after"]) <= 60
        assert "no-store" in limited.headers["cache-control"]
        assert "missing@example.com" not in limited.text

        throttle = sys.modules["copyfast_auth_throttle"]
        broken_parent = tmp_path / "broken-parent"
        broken_parent.write_text("not a database directory", encoding="utf-8")
        monkeypatch.setattr(throttle, "session_database_path", lambda: str(broken_parent / "db.sqlite"))
        unavailable = client.post(
            "/api/v1/auth/login",
            json={"email": "other-missing@example.com", "password": "not-the-right-password"},
        )
        assert unavailable.status_code == 503
        assert unavailable.json()["error_code"] == "AUTH_THROTTLE_UNAVAILABLE"
        assert unavailable.headers["retry-after"] == "60"
        assert "other-missing@example.com" not in unavailable.text
