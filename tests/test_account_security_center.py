"""Focused contracts for the Web-native Account Security Center.

These tests deliberately exercise only session/password/factor boundaries.
They never contact Telegram, OAuth providers, PayOS or a Bot bridge.
"""

from __future__ import annotations

import sqlite3
import uuid
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from test_copyfast_auth_api import confirm_link, enable_oauth_provider, make_client


PASSWORD = "correct-horse-battery-staple"
NEW_PASSWORD = "new-correct-horse-battery-staple"


def _register_and_login(client: TestClient, email: str, password: str = PASSWORD) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Security owner"},
    )
    assert registered.status_code == 200
    assert registered.json()["ok"] is True
    logged_in = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert logged_in.status_code == 200
    assert logged_in.json()["ok"] is True
    return logged_in.json()["data"]["csrf_token"]


def _csrf(client: TestClient) -> str:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    return response.json()["data"]["csrf_token"]


def _oauth_state_from_redirect(response) -> str:
    assert response.status_code == 303
    state = parse_qs(urlparse(response.headers["location"]).query).get("state", [""])[0]
    assert state
    return state


def test_login_method_contact_assurance_requires_same_verified_oauth_contact(tmp_path, monkeypatch):
    """A private OAuth contact becomes evidence only for the same login email."""

    email = "contact-assurance@example.com"
    mismatched_contact = "different-mailbox@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        _register_and_login(client, email)
        first = client.get("/api/v1/auth/security/login-methods")
        assert first.status_code == 200
        assert first.json()["data"]["login_methods"]["contact"] == {
            "state": "unverified", "provider": "", "verified": False,
        }

        db_path = tmp_path / "copyfast-test.db"
        with sqlite3.connect(db_path) as conn:
            account_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                (email,),
            ).fetchone()[0]
            now = "2026-07-16T12:00:00+00:00"
            conn.execute(
                "INSERT INTO web_external_identities (provider, subject_hash, account_id, created_at, last_login_at) VALUES (?, ?, ?, ?, ?)",
                ("google", "contact-assurance-subject", account_id, now, now),
            )
            conn.execute(
                "INSERT INTO web_account_oauth_contacts (account_id, provider, email, verified_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (account_id, "google", mismatched_contact, now, now, now),
            )
            conn.commit()

        mismatched = client.get("/api/v1/auth/security/login-methods")
        assert mismatched.status_code == 200
        assert mismatched.json()["data"]["login_methods"]["contact"] == {
            "state": "unverified", "provider": "", "verified": False,
        }
        assert mismatched_contact not in mismatched.text

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_account_oauth_contacts SET email=? WHERE account_id=?",
                (email, account_id),
            )
            conn.commit()

        verified = client.get("/api/v1/auth/security/login-methods")
        assert verified.status_code == 200
        assert verified.json()["data"]["login_methods"]["contact"] == {
            "state": "verified_oauth", "provider": "google", "verified": True,
        }
        assert email not in verified.text

        # A contact row without the immutable identity binding is never enough
        # to represent mailbox ownership, even for the same signed account.
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "DELETE FROM web_external_identities WHERE account_id=? AND provider='google'",
                (account_id,),
            )
            conn.commit()
        orphaned = client.get("/api/v1/auth/security/login-methods")
        assert orphaned.status_code == 200
        assert orphaned.json()["data"]["login_methods"]["contact"] == {
            "state": "unverified", "provider": "", "verified": False,
        }
        assert email not in orphaned.text


def test_security_sessions_are_owner_scoped_redacted_and_csrf_protected(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as owner:
        owner_csrf = _register_and_login(owner, "security-owner@example.com")
        # A separate browser signs into the same account, creating a session
        # that the first browser may revoke through an opaque reference.
        with TestClient(owner.app) as second_browser:
            _register_and_login(second_browser, "security-owner@example.com")
            listed = owner.get("/api/v1/auth/security/sessions")
            assert listed.status_code == 200
            body = listed.json()
            assert body["ok"] is True
            sessions = body["data"]["sessions"]
            assert len(sessions) >= 2
            assert all(set(item) == {"session_ref", "current", "created_at", "last_seen_at", "expires_at"} for item in sessions)
            assert all(len(item["session_ref"]) == 64 for item in sessions)
            assert sum(1 for item in sessions if item["current"]) == 1

            db_path = tmp_path / "copyfast-test.db"
            with sqlite3.connect(db_path) as conn:
                raw_ids = [row[0] for row in conn.execute("SELECT id FROM web_sessions").fetchall()]
            assert all(raw_id not in listed.text for raw_id in raw_ids)
            assert "csrf_token" not in listed.text
            assert "toan_aas_session" not in listed.text

            current_ref = next(item["session_ref"] for item in sessions if item["current"])
            other_ref = next(item["session_ref"] for item in sessions if not item["current"])
            assert owner.post(
                "/api/v1/auth/security/sessions/revoke",
                json={"session_ref": other_ref},
            ).status_code == 403

            # A foreign signed account gets the same no-op as a stale reference.
            with TestClient(owner.app) as foreign:
                foreign_csrf = _register_and_login(foreign, "security-foreign@example.com")
                foreign_attempt = foreign.post(
                    "/api/v1/auth/security/sessions/revoke",
                    headers={"X-CSRF-Token": foreign_csrf},
                    json={"session_ref": other_ref},
                )
                assert foreign_attempt.status_code == 200
                assert foreign_attempt.json()["data"] == {"revoked": False}

            current_attempt = owner.post(
                "/api/v1/auth/security/sessions/revoke",
                headers={"X-CSRF-Token": owner_csrf},
                json={"session_ref": current_ref},
            )
            assert current_attempt.status_code == 200
            assert current_attempt.json()["data"] == {"revoked": False}

            revoked = owner.post(
                "/api/v1/auth/security/sessions/revoke",
                headers={"X-CSRF-Token": owner_csrf},
                json={"session_ref": other_ref},
            )
            assert revoked.status_code == 200
            assert revoked.json()["data"] == {"revoked": True}
            assert owner.get("/api/v1/auth/me").status_code == 200
            assert second_browser.get("/api/v1/auth/me").status_code == 401


def test_session_revocation_rechecks_a_revoked_actor_before_touching_other_sessions(tmp_path, monkeypatch):
    """A once-valid CSRF request cannot revoke another browser after its own session is stale."""

    with make_client(tmp_path, monkeypatch) as first:
        import copyfast_auth

        email = "stale-session-revoke@example.com"
        csrf = _register_and_login(first, email)
        with TestClient(first.app) as second:
            _register_and_login(second, email)
            sessions = first.get("/api/v1/auth/security/sessions").json()["data"]["sessions"]
            other_ref = next(item["session_ref"] for item in sessions if not item["current"])
            db_path = tmp_path / "copyfast-test.db"
            with sqlite3.connect(db_path) as conn:
                account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0]
                active_before = conn.execute(
                    "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL",
                    (account_id,),
                ).fetchone()[0]

            original_current_session = copyfast_auth.current_session
            calls = 0

            def revoke_after_initial_proof(request):
                nonlocal calls
                session = original_current_session(request)
                calls += 1
                if calls == 2:
                    with sqlite3.connect(db_path) as conn:
                        conn.execute(
                            "UPDATE web_sessions SET revoked_at=? WHERE id=?",
                            ("2026-07-16T12:00:01+00:00", session["session_id"]),
                        )
                        conn.commit()
                return session

            monkeypatch.setattr(copyfast_auth, "current_session", revoke_after_initial_proof)
            stale = first.post(
                "/api/v1/auth/security/sessions/revoke",
                headers={"X-CSRF-Token": csrf},
                json={"session_ref": other_ref},
            )
            assert stale.status_code == 401
            assert stale.json()["error_code"] == "SECURITY_SESSION_STALE"

            with sqlite3.connect(db_path) as conn:
                active_after = conn.execute(
                    "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL",
                    (account_id,),
                ).fetchone()[0]
                audit = conn.execute(
                    "SELECT outcome, detail FROM web_audit_events WHERE action='auth.security_session_revoke' ORDER BY created_at DESC, id DESC LIMIT 1"
                ).fetchone()
            assert active_after == active_before - 1
            assert audit == ("denied", "initiating signed session is no longer active")
            assert second.get("/api/v1/auth/me").status_code == 200


def test_revoke_other_sessions_rechecks_a_revoked_actor_before_bulk_revocation(tmp_path, monkeypatch):
    """The bulk session action has the same in-transaction actor fence."""

    with make_client(tmp_path, monkeypatch) as first:
        import copyfast_auth

        email = "stale-session-revoke-others@example.com"
        csrf = _register_and_login(first, email)
        with TestClient(first.app) as second:
            _register_and_login(second, email)
            db_path = tmp_path / "copyfast-test.db"
            with sqlite3.connect(db_path) as conn:
                account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0]
                active_before = conn.execute(
                    "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL",
                    (account_id,),
                ).fetchone()[0]

            original_current_session = copyfast_auth.current_session
            calls = 0

            def revoke_after_initial_proof(request):
                nonlocal calls
                session = original_current_session(request)
                calls += 1
                if calls == 2:
                    with sqlite3.connect(db_path) as conn:
                        conn.execute(
                            "UPDATE web_sessions SET revoked_at=? WHERE id=?",
                            ("2026-07-16T12:00:01+00:00", session["session_id"]),
                        )
                        conn.commit()
                return session

            monkeypatch.setattr(copyfast_auth, "current_session", revoke_after_initial_proof)
            stale = first.post(
                "/api/v1/auth/security/sessions/revoke-others",
                headers={"X-CSRF-Token": csrf},
            )
            assert stale.status_code == 401
            assert stale.json()["error_code"] == "SECURITY_SESSION_STALE"

            with sqlite3.connect(db_path) as conn:
                active_after = conn.execute(
                    "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL",
                    (account_id,),
                ).fetchone()[0]
                audit = conn.execute(
                    "SELECT outcome, detail FROM web_audit_events WHERE action='auth.security_sessions_revoke_others' ORDER BY created_at DESC, id DESC LIMIT 1"
                ).fetchone()
            assert active_after == active_before - 1
            assert audit == ("denied", "initiating signed session is no longer active")
            assert second.get("/api/v1/auth/me").status_code == 200


def test_password_change_requires_csrf_rotates_all_sessions_and_never_returns_raw_id(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as first:
        csrf = _register_and_login(first, "password-owner@example.com")
        with TestClient(first.app) as second:
            _register_and_login(second, "password-owner@example.com")
            db_path = tmp_path / "copyfast-test.db"
            with sqlite3.connect(db_path) as conn:
                old_ids = [row[0] for row in conn.execute("SELECT id FROM web_sessions").fetchall()]

            missing_csrf = first.post(
                "/api/v1/auth/security/password",
                json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            )
            assert missing_csrf.status_code == 403
            denied = first.post(
                "/api/v1/auth/security/password",
                headers={"X-CSRF-Token": csrf},
                json={"current_password": "wrong-password", "new_password": NEW_PASSWORD},
            )
            assert denied.status_code == 200
            assert denied.json()["error_code"] == "PASSWORD_CHANGE_DENIED"

            changed = first.post(
                "/api/v1/auth/security/password",
                headers={"X-CSRF-Token": csrf},
                json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            )
            assert changed.status_code == 200
            changed_body = changed.json()
            assert changed_body["ok"] is True
            assert set(changed_body["data"]) == {"csrf_token", "expires_at"}
            assert all(raw_id not in changed.text for raw_id in old_ids)
            assert second.get("/api/v1/auth/me").status_code == 401
            refreshed = first.get("/api/v1/auth/me")
            assert refreshed.status_code == 200
            assert refreshed.json()["data"]["csrf_token"] == changed_body["data"]["csrf_token"]

            with TestClient(first.app) as verifier:
                old_login = verifier.post(
                    "/api/v1/auth/login",
                    json={"email": "password-owner@example.com", "password": PASSWORD},
                )
                assert old_login.json()["ok"] is False
                new_login = verifier.post(
                    "/api/v1/auth/login",
                    json={"email": "password-owner@example.com", "password": NEW_PASSWORD},
                )
                assert new_login.json()["ok"] is True


def test_password_change_accepts_unicode_without_compare_digest_error(tmp_path, monkeypatch):
    current_password = "Mật-khẩu-cũ-2026"
    new_password = "Mật-khẩu-mới-2026"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = _register_and_login(client, "unicode-password@example.com", current_password)

        same = client.post(
            "/api/v1/auth/security/password",
            headers={"X-CSRF-Token": csrf},
            json={"current_password": current_password, "new_password": current_password},
        )
        assert same.status_code == 200
        assert same.json()["error_code"] == "PASSWORD_POLICY_INVALID"

        changed = client.post(
            "/api/v1/auth/security/password",
            headers={"X-CSRF-Token": csrf},
            json={"current_password": current_password, "new_password": new_password},
        )
        assert changed.status_code == 200
        assert changed.json()["ok"] is True
        assert current_password not in changed.text
        assert new_password not in changed.text
        fresh_csrf = changed.json()["data"]["csrf_token"]
        assert _csrf(client) == fresh_csrf

        with TestClient(client.app) as verifier:
            assert verifier.post(
                "/api/v1/auth/login",
                json={"email": "unicode-password@example.com", "password": current_password},
            ).json()["ok"] is False
            assert verifier.post(
                "/api/v1/auth/login",
                json={"email": "unicode-password@example.com", "password": new_password},
            ).json()["ok"] is True


def test_successful_oauth_link_rotates_other_browser_sessions(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "github")
    with make_client(tmp_path, monkeypatch) as first:
        import copyfast_auth

        async def fake_identity(provider, code, state_value):
            assert provider == "github"
            return {
                "provider": provider,
                "subject": "github-security-rotation-subject",
                "email": "oauth-rotation@example.com",
                "email_verified": True,
                "display_name": "OAuth Security Owner",
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", fake_identity)
        csrf = _register_and_login(first, "oauth-rotation@example.com")
        with TestClient(first.app) as second:
            _register_and_login(second, "oauth-rotation@example.com")
            start = first.post(
                "/api/v1/auth/oauth/github/link/start",
                headers={"X-CSRF-Token": csrf},
                json={},
            )
            assert start.status_code == 200
            provider_start = first.get(start.json()["data"]["start_path"], follow_redirects=False)
            state = _oauth_state_from_redirect(provider_start)
            callback = first.get(
                f"/api/v1/auth/oauth/github/callback?code=oauth-security-code&state={state}",
                follow_redirects=False,
            )
            assert callback.status_code == 303
            assert callback.headers["location"] == "/account?oauth=linked"
            # The redirect carries only the replacement HttpOnly cookie. The
            # fresh CSRF value is available through the normal signed `/me`
            # bootstrap rather than a URL/query/body transport.
            fresh = first.get("/api/v1/auth/me")
            assert fresh.status_code == 200
            assert fresh.json()["data"]["csrf_token"] != csrf
            assert second.get("/api/v1/auth/me").status_code == 401


def test_oauth_unlink_rechecks_a_revoked_actor_before_mutating(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "google")
    with make_client(tmp_path, monkeypatch) as client:
        import copyfast_auth

        csrf = _register_and_login(client, "stale-unlink@example.com")
        db_path = tmp_path / "copyfast-test.db"
        with sqlite3.connect(db_path) as conn:
            account_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                ("stale-unlink@example.com",),
            ).fetchone()[0]
            now = "2026-07-16T12:00:00+00:00"
            conn.execute(
                "INSERT INTO web_external_identities (provider, subject_hash, account_id, created_at, last_login_at) VALUES (?, ?, ?, ?, ?)",
                ("google", "stale-unlink-subject", account_id, now, now),
            )
            conn.commit()

        original_current_session = copyfast_auth.current_session
        calls = 0

        def revoke_after_initial_proof(request):
            nonlocal calls
            session = original_current_session(request)
            calls += 1
            if calls == 2:
                with sqlite3.connect(db_path) as conn:
                    conn.execute("UPDATE web_sessions SET revoked_at=? WHERE id=?", ("2026-07-16T12:00:01+00:00", session["session_id"]))
                    conn.commit()
            return session

        monkeypatch.setattr(copyfast_auth, "current_session", revoke_after_initial_proof)
        stale = client.post(
            "/api/v1/auth/security/oauth/google/unlink",
            headers={"X-CSRF-Token": csrf},
        )
        assert stale.status_code == 401
        assert stale.json()["error_code"] == "SECURITY_SESSION_STALE"
        assert "stale-unlink-subject" not in stale.text
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM web_external_identities WHERE account_id=? AND provider='google'",
                (account_id,),
            ).fetchone()[0] == 1


def test_password_change_rechecks_a_revoked_actor_before_password_or_session_rotation(tmp_path, monkeypatch):
    """A CSRF-valid request cannot win after another security action revoked it."""

    with make_client(tmp_path, monkeypatch) as client:
        import copyfast_auth

        email = "stale-password-change@example.com"
        csrf = _register_and_login(client, email)
        db_path = tmp_path / "copyfast-test.db"
        with sqlite3.connect(db_path) as conn:
            account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0]
            active_before = conn.execute(
                "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL", (account_id,)
            ).fetchone()[0]

        original_current_session = copyfast_auth.current_session
        calls = 0
        revoked_session_id = ""

        def revoke_after_initial_proof(request):
            nonlocal calls, revoked_session_id
            session = original_current_session(request)
            calls += 1
            if calls == 2:
                revoked_session_id = str(session["session_id"])
                with sqlite3.connect(db_path) as conn:
                    conn.execute(
                        "UPDATE web_sessions SET revoked_at=? WHERE id=?",
                        ("2026-07-16T12:00:01+00:00", revoked_session_id),
                    )
                    conn.commit()
            return session

        monkeypatch.setattr(copyfast_auth, "current_session", revoke_after_initial_proof)
        stale = client.post(
            "/api/v1/auth/security/password",
            headers={"X-CSRF-Token": csrf},
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert stale.status_code == 401
        assert stale.json()["error_code"] == "SECURITY_SESSION_STALE"
        assert revoked_session_id
        assert "set-cookie" not in {key.lower() for key in stale.headers}
        for secret in (PASSWORD, NEW_PASSWORD, revoked_session_id):
            assert secret not in stale.text

        with sqlite3.connect(db_path) as conn:
            active_after = conn.execute(
                "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL", (account_id,)
            ).fetchone()[0]
            audit = conn.execute(
                "SELECT outcome, detail FROM web_audit_events WHERE action='auth.security_password_change' ORDER BY created_at DESC, id DESC LIMIT 1"
            ).fetchone()
        assert active_after == active_before - 1
        assert audit == ("denied", "initiating signed session is no longer active")
        assert all(secret not in str(audit) for secret in (PASSWORD, NEW_PASSWORD, revoked_session_id))

        # The revoked browser cannot get a replacement cookie. A clean browser
        # confirms the stored password stayed unchanged by the stale request.
        assert client.get("/api/v1/auth/me").status_code == 401
        with TestClient(client.app) as verifier:
            old_login = verifier.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
            new_login = verifier.post("/api/v1/auth/login", json={"email": email, "password": NEW_PASSWORD})
        assert old_login.status_code == 200 and old_login.json()["ok"] is True
        assert new_login.status_code == 200 and new_login.json()["ok"] is False


def test_telegram_account_upgrade_rechecks_a_revoked_actor_before_adding_password(tmp_path, monkeypatch):
    """A stale Telegram-first browser cannot attach a new email/password factor."""

    with make_client(tmp_path, monkeypatch) as client:
        import copyfast_auth

        started = client.post("/api/v1/auth/telegram/login/start", json={})
        code = started.json()["data"]["code"]
        assert confirm_link(client, code, canonical_user_id="stale-telegram-upgrade-user").status_code == 200
        completed = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert completed.status_code == 200
        csrf = completed.json()["data"]["csrf_token"]
        db_path = tmp_path / "copyfast-test.db"
        with sqlite3.connect(db_path) as conn:
            account_id, original_email, password_enabled = conn.execute(
                "SELECT id, email, password_login_enabled FROM web_accounts WHERE canonical_user_id=?",
                ("stale-telegram-upgrade-user",),
            ).fetchone()
            active_before = conn.execute(
                "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL",
                (account_id,),
            ).fetchone()[0]
        assert original_email.endswith("@telegram.toanaas.invalid")
        assert password_enabled == 0

        original_current_session = copyfast_auth.current_session
        calls = 0
        revoked_session_id = ""

        def revoke_after_initial_proof(request):
            nonlocal calls, revoked_session_id
            session = original_current_session(request)
            calls += 1
            if calls == 2:
                revoked_session_id = str(session["session_id"])
                with sqlite3.connect(db_path) as conn:
                    conn.execute(
                        "UPDATE web_sessions SET revoked_at=? WHERE id=?",
                        ("2026-07-16T12:00:01+00:00", revoked_session_id),
                    )
                    conn.commit()
            return session

        monkeypatch.setattr(copyfast_auth, "current_session", revoke_after_initial_proof)
        stale = client.post(
            "/api/v1/auth/telegram-account/upgrade",
            headers={"X-CSRF-Token": csrf},
            json={"email": "stale-telegram-upgrade@example.com", "password": NEW_PASSWORD},
        )
        assert stale.status_code == 401
        assert stale.json()["error_code"] == "SECURITY_SESSION_STALE"
        assert revoked_session_id
        assert "set-cookie" not in {key.lower() for key in stale.headers}
        assert NEW_PASSWORD not in stale.text

        with sqlite3.connect(db_path) as conn:
            persisted = conn.execute(
                "SELECT email, password_login_enabled FROM web_accounts WHERE id=?",
                (account_id,),
            ).fetchone()
            active_after = conn.execute(
                "SELECT COUNT(*) FROM web_sessions WHERE account_id=? AND revoked_at IS NULL",
                (account_id,),
            ).fetchone()[0]
            audit = conn.execute(
                "SELECT outcome, detail FROM web_audit_events WHERE action='auth.telegram_account_upgrade' ORDER BY created_at DESC, id DESC LIMIT 1"
            ).fetchone()
        assert persisted == (original_email, 0)
        assert active_after == active_before - 1
        assert audit == ("denied", "initiating signed session is no longer active")
        assert client.get("/api/v1/auth/me").status_code == 401


def test_password_change_has_raw_body_cap_and_durable_hmac_throttle(tmp_path, monkeypatch):
    # Keep this tiny policy only in the test process; production defaults stay
    # intentionally less aggressive for legitimate signed users.
    monkeypatch.setenv("WEBAPP_AUTH_PASSWORD_CHANGE_THROTTLE_LIMIT", "2")
    monkeypatch.setenv("WEBAPP_AUTH_PASSWORD_CHANGE_GLOBAL_THROTTLE_LIMIT", "2")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = _register_and_login(client, "password-throttle@example.com")
        oversized = client.post(
            "/api/v1/auth/security/password",
            headers={"Content-Type": "application/json"},
            content=(b'{"current_password":"' + (b"x" * 9000) + b'","new_password":"valid-new-password-123"}'),
        )
        assert oversized.status_code == 413
        assert oversized.json()["error_code"] == "WEB_AUTH_CREDENTIAL_BODY_TOO_LARGE"
        for _ in range(2):
            denied = client.post(
                "/api/v1/auth/security/password",
                headers={"X-CSRF-Token": csrf},
                json={"current_password": "wrong-password", "new_password": NEW_PASSWORD},
            )
            assert denied.json()["error_code"] == "PASSWORD_CHANGE_DENIED"
        limited = client.post(
            "/api/v1/auth/security/password",
            headers={"X-CSRF-Token": csrf},
            json={"current_password": "wrong-password", "new_password": NEW_PASSWORD},
        )
        assert limited.status_code == 429
        assert limited.json()["error_code"] == "AUTH_RATE_LIMITED"


def test_oauth_unlink_is_config_aware_prevents_lockout_and_cleans_own_contact(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        # Keep provider startup disabled: this contract never performs an
        # OAuth exchange and therefore must not need the optional PyJWT
        # runtime dependency. The unlink endpoint reads the flag at request
        # time and remains server-authoritative.
        enable_oauth_provider(monkeypatch, "google")
        csrf = _register_and_login(client, "oauth-security@example.com")
        db_path = tmp_path / "copyfast-test.db"
        with sqlite3.connect(db_path) as conn:
            account_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                ("oauth-security@example.com",),
            ).fetchone()[0]
            now = "2026-07-16T12:00:00+00:00"
            conn.execute(
                "INSERT INTO web_external_identities (provider, subject_hash, account_id, created_at, last_login_at) VALUES (?, ?, ?, ?, ?)",
                ("google", "subject-hash-for-security-test", account_id, now, now),
            )
            conn.execute(
                "INSERT INTO web_account_oauth_contacts (account_id, provider, email, verified_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (account_id, "google", "private-contact@example.com", now, now, now),
            )
            conn.commit()

        monkeypatch.setenv("WEBAPP_GOOGLE_OAUTH_ENABLED", "false")
        disabled = client.post(
            "/api/v1/auth/security/oauth/google/unlink",
            headers={"X-CSRF-Token": csrf},
        )
        assert disabled.status_code == 200
        assert disabled.json()["error_code"] == "OAUTH_PROVIDER_DISABLED"

        monkeypatch.setenv("WEBAPP_GOOGLE_OAUTH_ENABLED", "true")
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET password_login_enabled=0 WHERE id=?", (account_id,))
            conn.commit()
        locked = client.post(
            "/api/v1/auth/security/oauth/google/unlink",
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert locked.status_code == 200
        assert locked.json()["error_code"] == "SECURITY_LAST_LOGIN_FACTOR"

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_accounts SET password_login_enabled=1 WHERE id=?", (account_id,))
            conn.commit()
        allowed = client.post(
            "/api/v1/auth/security/oauth/google/unlink",
            headers={"X-CSRF-Token": _csrf(client)},
        )
        assert allowed.status_code == 200
        assert allowed.json()["data"]["unlinked"] is True
        assert "subject-hash-for-security-test" not in allowed.text
        assert "private-contact@example.com" not in allowed.text
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_external_identities WHERE account_id=? AND provider='google'", (account_id,)).fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM web_account_oauth_contacts WHERE account_id=?", (account_id,)).fetchone()[0] == 0
            audit_rows = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action='auth.security_oauth_unlink'"
            ).fetchall()
        assert audit_rows
        assert all(not target and not detail for target, detail in audit_rows)
