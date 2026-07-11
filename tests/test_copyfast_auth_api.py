import importlib
import base64
import asyncio
import hashlib
import hmac
from io import BytesIO
import json
from pathlib import Path
import sys
import time
import uuid
from zipfile import ZipFile
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient


MODULES = [
    "app", "config", "db", "copyfast_db", "copyfast_auth", "copyfast_bridge",
    "copyfast_registry", "copyfast_api", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch, *, base_url="http://testserver"):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    monkeypatch.delenv("WEBAPP_LINK_CALLBACK_TOKEN", raising=False)
    monkeypatch.delenv("WEBAPP_LINK_CALLBACK_HMAC_SECRET", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    application = importlib.import_module("app").app
    return TestClient(application, base_url=base_url)


def link_callback_headers(body, *, request_id=None, timestamp=None):
    request_id = request_id or f"link-callback-{uuid.uuid4()}"
    timestamp = timestamp or str(int(time.time()))
    digest = hashlib.sha256(body).hexdigest()
    material = f"{timestamp}.{request_id}.POST./api/v1/auth/internal/telegram-link/confirm.{digest}".encode("utf-8")
    signature = hmac.new(b"bridge-test-hmac", material, hashlib.sha256).hexdigest()
    return {
        "X-TOAN-AAS-BRIDGE-TOKEN": "bridge-test-token",
        "X-TOAN-AAS-Timestamp": timestamp,
        "X-TOAN-AAS-Request-ID": request_id,
        "X-TOAN-AAS-Signature": signature,
        "Content-Type": "application/json",
    }


def confirm_link(client, code, *, role="user", canonical_user_id="telegram-123", request_id=None):
    body = json.dumps(
        {"code": code, "canonical_user_id": canonical_user_id, "role": role},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return client.post(
        "/api/v1/auth/internal/telegram-link/confirm",
        headers=link_callback_headers(body, request_id=request_id),
        content=body,
    )


def register_and_link(client, *, role="user"):
    response = client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "correct-horse-battery-staple", "display_name": "User"})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    # Register never creates a session; login is the one indistinguishable
    # password flow that issues the signed cookie and CSRF credential.
    login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "correct-horse-battery-staple"})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    link = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
    assert link.status_code == 200
    code = link.json()["data"]["code"]
    confirmed = confirm_link(client, code, role=role)
    assert confirmed.json()["ok"] is True
    return csrf


def enable_oauth_provider(monkeypatch, provider):
    monkeypatch.setenv(f"WEBAPP_{provider.upper()}_OAUTH_ENABLED", "true")
    monkeypatch.setenv(f"{provider.upper()}_OAUTH_CLIENT_ID", f"{provider}-client-id")
    monkeypatch.setenv(f"{provider.upper()}_OAUTH_CLIENT_SECRET", f"{provider}-client-secret")
    monkeypatch.setenv("WEBAPP_PUBLIC_BASE_URL", "http://localhost")
    monkeypatch.setenv("WEB_OAUTH_IDENTITY_HMAC_SECRET", "oauth-test-hmac-secret")


def enable_apple_oauth(monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    monkeypatch.setenv("WEBAPP_APPLE_OAUTH_ENABLED", "true")
    monkeypatch.setenv("APPLE_OAUTH_CLIENT_ID", "com.toanaas.web")
    monkeypatch.setenv("APPLE_OAUTH_TEAM_ID", "APPLETEAM1")
    monkeypatch.setenv("APPLE_OAUTH_KEY_ID", "APPLEKEY01")
    monkeypatch.setenv("APPLE_OAUTH_PRIVATE_KEY_BASE64", base64.b64encode(pem).decode("ascii"))
    monkeypatch.setenv("WEBAPP_PUBLIC_BASE_URL", "https://app.toanaas.vn")
    monkeypatch.setenv("WEB_OAUTH_IDENTITY_HMAC_SECRET", "oauth-test-hmac-secret")
    monkeypatch.setenv("WEB_COOKIE_SECURE", "true")


def oauth_state_from_redirect(response):
    assert response.status_code == 303
    query = parse_qs(urlparse(response.headers["location"]).query)
    state = query.get("state", [""])[0]
    assert state
    return state, query


def test_signed_session_csrf_and_telegram_link(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        browser_account = me.json()["data"]["account"]
        assert browser_account["telegram_linked"] is True
        assert "canonical_user_id" not in browser_account
        assert "telegram-123" not in me.text
        link_status = client.get("/api/v1/auth/telegram/link/status")
        assert link_status.json()["data"] == {"linked": True}
        assert "telegram-123" not in link_status.text
        core_me = client.get("/api/v1/core/me")
        assert core_me.status_code == 200
        assert core_me.json()["error_code"] == "BROWSER_IDENTITY_NOT_EXPOSED"
        assert "telegram-123" not in core_me.text
        invalid = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": "wrong"})
        assert invalid.status_code == 403
        guarded = client.get("/api/v1/wallet")
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        confirmed = client.post(
            "/api/v1/features/video_single/confirm",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "feature-confirm-0001"},
            json={"input": {"prompt": "test"}, "idempotency_key": "feature-confirm-0001"},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["error_code"] == "WEBAPP_PROVIDER_CALLS_DISABLED"

        monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
        still_guarded = client.post(
            "/api/v1/features/video_single/confirm",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "feature-confirm-adapter-0001"},
            json={"input": {"prompt": "test"}, "idempotency_key": "feature-confirm-adapter-0001"},
        )
        assert still_guarded.status_code == 200
        assert still_guarded.json()["error_code"] == "WEBAPP_FEATURE_JOB_ADAPTER_REQUIRED"


def test_web_owned_profile_defaults_are_csrf_protected_and_cannot_change_canonical_authority(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        initial = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert initial["profile"] == {"locale": "vi", "timezone": "Asia/Ho_Chi_Minh", "avatar_style": "gradient"}

        updated = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": csrf},
            json={
                "display_name": "Hồ sơ Web",
                "locale": "en",
                "timezone": "UTC",
                "role": "admin",
                "canonical_user_id": "browser-forged",
            },
        )
        assert updated.status_code == 200
        payload = updated.json()
        assert payload["ok"] is True
        assert payload["data"]["account"]["display_name"] == "Hồ sơ Web"
        assert payload["data"]["account"]["profile"] == {"locale": "en", "timezone": "UTC", "avatar_style": "gradient"}
        assert payload["data"]["account"]["role"] == "user"
        assert "canonical_user_id" not in updated.text

        persisted = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert persisted["display_name"] == "Hồ sơ Web"
        assert persisted["profile"]["timezone"] == "UTC"
        invalid_timezone = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": csrf},
            json={"display_name": "Hồ sơ Web", "locale": "vi", "timezone": "Browser/forged"},
        )
        assert invalid_timezone.json()["error_code"] == "PROFILE_TIMEZONE_INVALID"
        forbidden = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": "invalid"},
            json={"display_name": "Không được lưu"},
        )
        assert forbidden.status_code == 403


def test_login_runs_password_verification_for_missing_and_existing_accounts(tmp_path, monkeypatch):
    """Avoid an account-enumeration timing oracle on the login endpoint."""
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "timing@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True

        import copyfast_auth

        original_verify = copyfast_auth._verify_password
        hashes_checked = []

        def observing_verify(password, encoded):
            hashes_checked.append(encoded)
            return original_verify(password, encoded)

        monkeypatch.setattr(copyfast_auth, "_verify_password", observing_verify)
        missing = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
        )
        wrong = client.post(
            "/api/v1/auth/login",
            json={"email": "timing@example.com", "password": "wrong-password"},
        )
        assert missing.json()["error_code"] == wrong.json()["error_code"] == "LOGIN_DENIED"
        assert len(hashes_checked) == 2
        assert hashes_checked[0] == copyfast_auth._DUMMY_PASSWORD_HASH
        assert hashes_checked[1] != copyfast_auth._DUMMY_PASSWORD_HASH


def test_oauth_disabled_by_default_exposes_no_live_provider_path(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        providers = client.get("/api/v1/auth/providers")
        assert providers.status_code == 200
        assert providers.json()["data"]["providers"] == {"apple": {"enabled": False}, "github": {"enabled": False}, "google": {"enabled": False}}
        start = client.get("/api/v1/auth/oauth/google/start", follow_redirects=False)
        assert start.status_code == 303
        assert start.headers["location"] == "/login?oauth=unavailable"


def test_google_oauth_uses_signed_state_pkce_and_creates_an_oauth_only_account(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "google")
    with make_client(tmp_path, monkeypatch) as client:
        import copyfast_auth

        seen = []

        async def fake_identity(provider, code, state_value):
            seen.append((provider, code, state_value))
            return {
                "provider": "google",
                "subject": "google-immutable-subject-001",
                "email": "new-google@example.com",
                "display_name": "Google User",
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", fake_identity)
        started = client.get("/api/v1/auth/oauth/google/start", follow_redirects=False)
        state_value, query = oauth_state_from_redirect(started)
        assert started.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        assert query["response_type"] == ["code"]
        assert query["code_challenge_method"] == ["S256"]
        assert query["nonce"]
        assert "google-client-secret" not in started.headers["location"]
        assert "toan_aas_oauth_state" in started.headers["set-cookie"]

        callback = client.get(f"/api/v1/auth/oauth/google/callback?code=opaque-code&state={state_value}", follow_redirects=False)
        assert callback.status_code == 303
        assert callback.headers["location"] == "/onboarding"
        assert seen == [("google", "opaque-code", state_value)]
        me = client.get("/api/v1/auth/me")
        account = me.json()["data"]["account"]
        assert account["email"] == "new-google@example.com"
        assert account["login_methods"] == {"email": False, "telegram": False, "google": True, "github": False, "apple": False}
        assert "google-immutable-subject-001" not in me.text

        from copyfast_db import transaction

        with transaction() as conn:
            stored_subject = conn.execute("SELECT subject_hash FROM web_external_identities WHERE provider='google'").fetchone()[0]
            assert stored_subject != "google-immutable-subject-001"
            assert len(stored_subject) == 64
        replay = client.get(f"/api/v1/auth/oauth/google/callback?code=opaque-code&state={state_value}", follow_redirects=False)
        assert replay.status_code == 303
        assert replay.headers["location"] == "/login?oauth=state"


def test_oauth_never_auto_links_a_matching_email_and_explicit_github_link_needs_csrf(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "github")
    with make_client(tmp_path, monkeypatch) as client:
        import copyfast_auth

        async def matching_email_identity(provider, code, state_value):
            return {
                "provider": provider,
                "subject": "github-immutable-subject-001",
                "email": "existing@example.com",
                "display_name": "GitHub User",
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_oauth_identity", matching_email_identity)
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "existing@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200

        started = client.get("/api/v1/auth/oauth/github/start", follow_redirects=False)
        state_value, query = oauth_state_from_redirect(started)
        assert query["scope"] == ["read:user user:email"]
        collision = client.get(f"/api/v1/auth/oauth/github/callback?code=opaque-code&state={state_value}", follow_redirects=False)
        assert collision.headers["location"] == "/login?oauth=link-required"
        assert client.get("/api/v1/auth/me").status_code == 401

        relogin = client.post("/api/v1/auth/login", json={"email": "existing@example.com", "password": "correct-horse-battery-staple"})
        csrf = relogin.json()["data"]["csrf_token"]
        rejected = client.post("/api/v1/auth/oauth/github/link/start", headers={"X-CSRF-Token": "wrong"}, json={})
        assert rejected.status_code == 403
        link_start = client.post("/api/v1/auth/oauth/github/link/start", headers={"X-CSRF-Token": csrf}, json={})
        assert link_start.status_code == 200
        assert link_start.json()["data"]["start_path"] == "/api/v1/auth/oauth/github/start?link=1"
        provider_redirect = client.get(link_start.json()["data"]["start_path"], follow_redirects=False)
        link_state, _query = oauth_state_from_redirect(provider_redirect)
        completed_link = client.get(f"/api/v1/auth/oauth/github/callback?code=opaque-link-code&state={link_state}", follow_redirects=False)
        assert completed_link.status_code == 303
        assert completed_link.headers["location"] == "/account?oauth=linked"
        account = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert account["login_methods"] == {"email": True, "telegram": False, "google": False, "github": True, "apple": False}


def test_apple_oauth_uses_form_post_and_can_link_without_relaxing_session_cookie(tmp_path, monkeypatch):
    enable_apple_oauth(monkeypatch)
    with make_client(tmp_path, monkeypatch, base_url="https://testserver") as client:
        import copyfast_auth
        import jwt

        seen = []

        async def fake_apple_identity(code, state_value, *, display_name=""):
            seen.append((code, state_value, display_name))
            return {
                "provider": "apple",
                "subject": "apple-immutable-subject-001",
                "email": "apple-user@example.com",
                "display_name": display_name,
            }

        monkeypatch.setattr(copyfast_auth, "_fetch_apple_identity", fake_apple_identity)
        config = copyfast_auth._oauth_client_configuration("apple")
        client_secret = copyfast_auth._apple_client_secret(config)
        claims = jwt.decode(client_secret, options={"verify_signature": False})
        assert claims["iss"] == "APPLETEAM1"
        assert claims["aud"] == "https://appleid.apple.com"
        assert claims["sub"] == "com.toanaas.web"

        started = client.get("/api/v1/auth/oauth/apple/start", follow_redirects=False)
        state_value, query = oauth_state_from_redirect(started)
        assert started.headers["location"].startswith("https://appleid.apple.com/auth/authorize?")
        assert query["response_mode"] == ["form_post"]
        assert query["response_type"] == ["code id_token"]
        assert query["scope"] == ["name email"]
        assert "code_challenge" not in query
        assert "SameSite=none" in started.headers["set-cookie"]
        signed_in = client.post(
            "/api/v1/auth/oauth/apple/callback",
            data={"code": "apple-code", "state": state_value, "user": json.dumps({"name": {"firstName": "Apple", "lastName": "User"}, "email": "untrusted@example.com"})},
            follow_redirects=False,
        )
        assert signed_in.status_code == 303
        assert signed_in.headers["location"] == "/onboarding"
        assert seen == [("apple-code", state_value, "Apple User")]
        account = client.get("/api/v1/auth/me").json()["data"]["account"]
        assert account["login_methods"] == {"email": False, "telegram": False, "google": False, "github": False, "apple": True}
        assert "apple-immutable-subject-001" not in client.get("/api/v1/auth/me").text

    # Apple link callback is cross-site form POST: transfer only its temporary
    # state cookie to a separate HTTPS client, deliberately omitting the Lax
    # signed-session cookie. The active session binding in the DB still
    # protects and completes the explicit link.
    with make_client(tmp_path, monkeypatch, base_url="https://testserver") as client:
        import copyfast_auth

        async def fake_link_identity(code, state_value, *, display_name=""):
            return {"provider": "apple", "subject": "apple-immutable-subject-002", "email": "", "display_name": display_name}

        monkeypatch.setattr(copyfast_auth, "_fetch_apple_identity", fake_link_identity)
        registration = client.post("/api/v1/auth/register", json={"email": "apple-link@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "apple-link@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        link_start = client.post("/api/v1/auth/oauth/apple/link/start", headers={"X-CSRF-Token": csrf}, json={})
        provider_redirect = client.get(link_start.json()["data"]["start_path"], follow_redirects=False)
        link_state, _ = oauth_state_from_redirect(provider_redirect)
        state_cookie_name = copyfast_auth._cookie_name(copyfast_auth.OAUTH_STATE_COOKIE)
        state_cookie = client.cookies.get(state_cookie_name)
        assert state_cookie
        with TestClient(client.app, base_url="https://testserver") as form_post_client:
            form_post_client.cookies.set(state_cookie_name, state_cookie)
            linked = form_post_client.post(
                "/api/v1/auth/oauth/apple/callback",
                data={"code": "apple-link-code", "state": link_state},
                follow_redirects=False,
            )
        assert linked.status_code == 303
        assert linked.headers["location"] == "/account?oauth=linked"
        linked_methods = client.get("/api/v1/auth/me").json()["data"]["account"]["login_methods"]
        assert linked_methods["email"] is True
        assert linked_methods["apple"] is True


def test_secure_deployments_use_host_prefixed_cookie_names_and_reject_legacy_session_cookie(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEB_COOKIE_SECURE", "true")
    with make_client(tmp_path, monkeypatch, base_url="https://testserver") as client:
        import copyfast_auth

        registration = client.post("/api/v1/auth/register", json={"email": "host-cookie@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "host-cookie@example.com", "password": "correct-horse-battery-staple"})
        host_cookie_name = copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE)
        assert host_cookie_name == "__Host-toan_aas_session"
        assert f"{host_cookie_name}=" in login.headers["set-cookie"]
        assert client.get("/api/v1/auth/me").status_code == 200

        # A copied signed value under the legacy parent-domain-capable name
        # must not authenticate a production request.
        host_cookie_value = client.cookies.get(host_cookie_name)
        with TestClient(client.app, base_url="https://testserver") as legacy_client:
            legacy_client.cookies.set("toan_aas_session", host_cookie_value)
            assert legacy_client.get("/api/v1/auth/me").status_code == 401


def test_apple_new_identity_without_a_verified_email_fails_closed(tmp_path, monkeypatch):
    enable_apple_oauth(monkeypatch)
    with make_client(tmp_path, monkeypatch, base_url="https://testserver") as client:
        import copyfast_auth

        calls = []

        async def no_email_identity(code, state_value, *, display_name=""):
            calls.append((code, state_value))
            return {"provider": "apple", "subject": "apple-no-email-subject", "email": "", "display_name": display_name}

        monkeypatch.setattr(copyfast_auth, "_fetch_apple_identity", no_email_identity)
        started = client.get("/api/v1/auth/oauth/apple/start", follow_redirects=False)
        state_value, _ = oauth_state_from_redirect(started)
        failed = client.post("/api/v1/auth/oauth/apple/callback", data={"code": "apple-no-email-code", "state": state_value}, follow_redirects=False)
        assert failed.headers["location"] == "/login?oauth=failed"
        assert calls == [("apple-no-email-code", state_value)]
        from copyfast_db import transaction

        with transaction() as conn:
            assert conn.execute("SELECT COUNT(*) FROM web_external_identities WHERE provider='apple'").fetchone()[0] == 0


def test_apple_id_token_verification_uses_apple_rsa_jwks_not_the_es256_client_secret(tmp_path, monkeypatch):
    enable_apple_oauth(monkeypatch)
    with make_client(tmp_path, monkeypatch, base_url="https://testserver"):
        import copyfast_auth
        import jwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec, rsa

        config = copyfast_auth._oauth_client_configuration("apple")
        state_value = "apple-rsa-verification-state"
        nonce = copyfast_auth._oauth_derived_token("nonce", state_value)
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = rsa_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public_numbers = rsa_key.public_key().public_numbers()

        def jwk_number(value):
            return base64.urlsafe_b64encode(value.to_bytes((value.bit_length() + 7) // 8, "big")).rstrip(b"=").decode("ascii")

        jwks = {"keys": [{"kty": "RSA", "kid": "apple-rsa-kid", "use": "sig", "alg": "RS256", "n": jwk_number(public_numbers.n), "e": jwk_number(public_numbers.e)}]}

        async def fake_jwks(method, url, **_kwargs):
            assert method == "GET"
            assert url == copyfast_auth.APPLE_JWKS_URL
            return jwks

        monkeypatch.setattr(copyfast_auth, "_oauth_json_request", fake_jwks)
        payload = {
            "iss": "https://appleid.apple.com",
            "aud": config["client_id"],
            "sub": "apple-rsa-subject",
            "nonce": nonce,
            "iat": int(time.time()) - 1,
            "exp": int(time.time()) + 60,
            "email": "apple-rsa@example.com",
            "email_verified": True,
        }
        token = jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": "apple-rsa-kid"})
        identity = asyncio.run(copyfast_auth._verify_apple_id_token(token, client_id=config["client_id"], expected_nonce=nonce))
        assert identity == {"provider": "apple", "subject": "apple-rsa-subject", "email": "apple-rsa@example.com"}

        ec_key = ec.generate_private_key(ec.SECP256R1())
        es256_token = jwt.encode(payload, ec_key, algorithm="ES256", headers={"kid": "apple-es256-kid"})
        with pytest.raises(copyfast_auth.OAuthIdentityError):
            asyncio.run(copyfast_auth._verify_apple_id_token(es256_token, client_id=config["client_id"], expected_nonce=nonce))


def test_https_oauth_configuration_requires_secure_cookies(tmp_path, monkeypatch):
    enable_oauth_provider(monkeypatch, "google")
    monkeypatch.setenv("WEBAPP_PUBLIC_BASE_URL", "https://app.toanaas.vn")
    monkeypatch.delenv("WEB_COOKIE_SECURE", raising=False)
    with pytest.raises(RuntimeError, match="WEB_COOKIE_SECURE"):
        with make_client(tmp_path, monkeypatch):
            pass


def test_support_ticket_refuses_sensitive_data_before_it_can_reach_the_bridge(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        rejected = client.post(
            "/api/v1/support/tickets",
            headers={"X-CSRF-Token": csrf},
            json={
                "subject": "Không thể gọi provider",
                "detail": "api_key=sk_1234567890abcdefghi",
                "idempotency_key": "ticket-secret-guard-0001",
            },
        )
        assert rejected.status_code == 422
        assert rejected.json()["error_code"] == "REQUEST_INVALID"
        assert "dữ liệu nhạy cảm" in rejected.json()["message"]


def test_login_response_uses_link_boolean_not_raw_telegram_identity(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "correct-horse-battery-staple"},
        )
        assert login.status_code == 200
        account = login.json()["data"]["account"]
        assert account["telegram_linked"] is True
        assert "canonical_user_id" not in account
        assert "telegram-123" not in login.text


def test_payment_entry_options_are_linked_session_only_and_do_not_expose_manual_bank_data(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("MANUAL_BANK_ACCOUNT", "private-bank-account-must-not-leak")
    monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "false")
    with make_client(tmp_path, monkeypatch) as client:
        denied = client.get("/api/v1/payments/options")
        assert denied.status_code == 401

        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "payment-options@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "payment-options@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        unlinked = client.get("/api/v1/payments/options")
        assert unlinked.status_code == 409

        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        assert confirm_link(client, code).json()["ok"] is True
        options = client.get("/api/v1/payments/options")
        assert options.status_code == 200
        payload = options.json()
        assert payload["status"] == "read_only"
        assert payload["data"]["payos"]["request_enabled"] is False
        assert payload["data"]["payos"]["topup_catalog_available"] is False
        assert payload["data"]["payos"]["topup_packages"] == []
        assert payload["data"]["payos"]["telegram_url"] == "https://t.me/ToanAasSupportBot"
        assert payload["data"]["payos"]["command"] == "/naptien"
        assert payload["data"]["manual"] == {
            "available": True,
            "telegram_url": "https://t.me/ToanAasSupportBot",
            "command": "/thucong",
            "receipt_channel": "telegram_bot",
            "payment_lookup_available": False,
            "wallet_history_signal_available": True,
            "history_in_web": False,
            "history_channel": "telegram_bot",
            "history_command": "/thucong",
            "history_menu_label": "Lịch sử nạp thủ công",
        }
        assert "private-bank-account-must-not-leak" not in options.text

        # An enabled Web-payment flag and configured bridge are not enough:
        # until the dedicated top-up SKU catalog exists, the browser must keep
        # the request path guarded and hand the customer back to the Bot.
        monkeypatch.setenv("WEBAPP_PAYMENT_ENABLED", "true")
        monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://bridge.test")
        monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-token")
        monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-hmac")
        blocked_catalog = client.get("/api/v1/payments/options").json()["data"]["payos"]
        assert blocked_catalog["request_enabled"] is False
        assert blocked_catalog["status"] == "guarded"

        monkeypatch.setenv("BOT_USERNAME", "not/a-valid-telegram-username")
        invalid_name = client.get("/api/v1/payments/options").json()["data"]["manual"]
        assert invalid_name["available"] is False
        assert invalid_name["telegram_url"] == ""
        invalid_deep_link = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
        assert invalid_deep_link.status_code == 200
        # A linked account cannot mint another code just to probe a deep link:
        # canonical Telegram identity is intentionally non-replaceable here.
        assert invalid_deep_link.json()["error_code"] == "TELEGRAM_RELINK_NOT_ALLOWED"


def test_legacy_billing_router_is_not_mounted_as_a_second_payos_or_wallet_writer(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        paths = {getattr(route, "path", "") for route in client.app.routes}
        assert "/api/v1/billing/create-payment-link" not in paths
        assert "/api/v1/billing/webhook/payos" not in paths
        assert "/api/v1/webhook/payos" not in paths
        assert "/payos/create-link" not in paths
        assert "/manual-topup" not in paths
        assert "/admin/manual-orders" not in paths
        assert "/admin/approve-topup" not in paths
        for path in (
            "/api/v1/billing/create-payment-link",
            "/api/v1/billing/webhook/payos",
            "/payos/create-link",
            "/manual-topup",
            "/admin/approve-topup",
        ):
            response = client.post(path, json={})
            assert response.status_code in {404, 405}, path


def test_telegram_link_callback_requires_hmac_timestamp_and_one_time_nonce(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post("/api/v1/auth/register", json={"email": "link@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "link@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        unsigned = client.post(
            "/api/v1/auth/internal/telegram-link/confirm",
            headers={"X-TOAN-AAS-BRIDGE-TOKEN": "bridge-test-token"},
            json={"code": code, "canonical_user_id": "telegram-123"},
        )
        assert unsigned.status_code == 401
        request_id = "link-callback-replay-0001"
        confirmed = confirm_link(client, code, request_id=request_id)
        assert confirmed.status_code == 200
        replay = confirm_link(client, code, request_id=request_id)
        assert replay.status_code == 401
        assert replay.json()["error_code"] == "REQUEST_DENIED"


def test_telegram_callback_rejects_invalid_codes_and_unlinked_login_with_non_success_http(tmp_path, monkeypatch):
    """The Bot treats 2xx as completion, so rejected callbacks must not use it."""
    with make_client(tmp_path, monkeypatch) as client:
        missing = confirm_link(client, "missing-telegram-link-code")
        assert missing.status_code == 410
        assert missing.json()["error_code"] == "LINK_CODE_INVALID"

        started = client.post("/api/v1/auth/telegram/login/start")
        login_code = started.json()["data"]["code"]
        no_account = confirm_link(client, login_code, canonical_user_id="telegram-without-web-account")
        assert no_account.status_code == 409
        assert no_account.json()["error_code"] == "TELEGRAM_LOGIN_ACCOUNT_REQUIRED"
        status = client.get("/api/v1/auth/telegram/login/status")
        assert status.json()["status"] == "guarded"
        assert status.json()["error_code"] == "TELEGRAM_LOGIN_ACCOUNT_REQUIRED"
        assert status.json()["data"] == {"ready": False, "restart_required": True}
        completed = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert completed.json()["error_code"] == "TELEGRAM_LOGIN_ACCOUNT_REQUIRED"


def test_telegram_passwordless_login_is_browser_bound_and_never_accepts_a_raw_id(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        profile_update = client.post(
            "/api/v1/auth/profile",
            headers={"X-CSRF-Token": csrf},
            json={"display_name": "Telegram profile", "locale": "en", "timezone": "UTC"},
        )
        assert profile_update.json()["ok"] is True
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401

        started = client.post("/api/v1/auth/telegram/login/start", json={"telegram_id": "browser-forged"})
        assert started.status_code == 200
        payload = started.json()
        assert payload["status"] == "awaiting_confirm"
        assert payload["data"]["raw_telegram_id_accepted"] is False
        assert payload["data"]["deep_link"].startswith("https://t.me/ToanAasSupportBot?start=web_")
        assert "browser-forged" not in started.text
        code = payload["data"]["code"]

        with TestClient(client.app) as other_client:
            other_status = other_client.get("/api/v1/auth/telegram/login/status")
            assert other_status.json()["error_code"] == "TELEGRAM_LOGIN_CHALLENGE_REQUIRED"
            assert confirm_link(client, code).json()["data"] == {"mode": "login"}
            assert other_client.post("/api/v1/auth/telegram/login/complete", json={}).json()["error_code"] == "TELEGRAM_LOGIN_CHALLENGE_REQUIRED"

        status = client.get("/api/v1/auth/telegram/login/status")
        assert status.json()["data"] == {"ready": True}
        completed = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert completed.status_code == 200
        account = completed.json()["data"]["account"]
        assert account["telegram_linked"] is True
        assert "canonical_user_id" not in completed.text
        assert account["profile"] == {"locale": "en", "timezone": "UTC", "avatar_style": "gradient"}
        assert account["login_methods"] == {"email": True, "telegram": True, "google": False, "github": False, "apple": False}
        assert client.get("/api/v1/auth/me").status_code == 200
        replay = client.post("/api/v1/auth/telegram/login/complete", json={})
        assert replay.json()["error_code"] == "TELEGRAM_LOGIN_CHALLENGE_REQUIRED"


def test_upload_rejects_path_traversal_and_never_falls_back_to_web_storage(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        headers = {"X-CSRF-Token": csrf, "Idempotency-Key": "upload-traversal-0001"}
        traversal = client.post(
            "/api/v1/uploads",
            headers=headers,
            files={"file": ("../unsafe.pdf", b"%PDF-1.4\nunsafe", "application/pdf")},
        )
        assert traversal.status_code == 422
        assert traversal.json()["error_code"] == "REQUEST_INVALID"

        guarded = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "upload-guarded-0001"},
            files={"file": ("safe.pdf", b"%PDF-1.4\nsafe", "application/pdf")},
        )
        assert guarded.status_code == 200
        assert guarded.json()["status"] == "guarded"
        assert guarded.json()["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"


def test_upload_rejects_mime_spoofed_media_and_non_docx_zip_before_bridge(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        headers = {"X-CSRF-Token": csrf, "Idempotency-Key": "upload-media-spoof-0001"}
        fake_video = client.post(
            "/api/v1/uploads",
            headers=headers,
            files={"file": ("clip.mp4", b"not-a-video-container", "video/mp4")},
        )
        assert fake_video.status_code == 422
        assert fake_video.json()["error_code"] == "REQUEST_INVALID"

        mime_mismatch = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "upload-mime-mismatch-0001"},
            files={"file": ("image.png", b"\x89PNG\r\n\x1a\nvalid", "application/pdf")},
        )
        assert mime_mismatch.status_code == 415
        assert mime_mismatch.json()["error_code"] == "REQUEST_INVALID"

        raw_zip = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "upload-docx-zip-guard-0001"},
            files={"file": ("report.docx", b"PK\x03\x04not-a-docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert raw_zip.status_code == 422
        assert raw_zip.json()["error_code"] == "REQUEST_INVALID"

        docx_buffer = BytesIO()
        with ZipFile(docx_buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<w:document/>")
        valid_docx = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "upload-docx-valid-0001"},
            files={"file": ("report.docx", docx_buffer.getvalue(), "application/octet-stream")},
        )
        assert valid_docx.status_code == 200
        assert valid_docx.json()["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"


def test_copyfast_flag_blocks_feature_and_upload_requests_before_bridge_work(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "false")
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        feature = client.post(
            "/api/v1/features/image_create/draft",
            headers={"X-CSRF-Token": csrf},
            json={"input": {"prompt": "an image"}},
        )
        assert feature.status_code == 200
        assert feature.json()["status"] == "guarded"
        assert feature.json()["error_code"] == "WEBAPP_COPYFAST_DISABLED"

        upload = client.post(
            "/api/v1/uploads",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "flag-upload-0001"},
            files={"file": ("ignored.invalid", b"not-read", "application/octet-stream")},
        )
        assert upload.status_code == 200
        assert upload.json()["status"] == "guarded"
        assert upload.json()["error_code"] == "WEBAPP_COPYFAST_DISABLED"


def test_catalog_and_portal_routes_are_available(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        catalog = client.get("/api/v1/catalog")
        assert catalog.status_code == 200
        keys = {item["key"] for item in catalog.json()["data"]["features"]}
        assert {
            "video_multiscene", "voice_tts", "subtitle_asr", "admin_jobs",
            "caption", "image_remove_background", "music_song", "documents_ocr", "feature_catalog",
        }.issubset(keys)
        register_and_link(client)
        page = client.get("/video/multiscene")
        assert page.status_code == 200
        assert "TOAN AAS" in page.text
        feature_catalog = client.get("/features")
        assert feature_catalog.status_code == 200
        assert "Tất cả công cụ" in feature_catalog.text
        legacy_sfx_library = client.get("/music/library?type=sfx", follow_redirects=False)
        assert legacy_sfx_library.status_code == 307
        assert legacy_sfx_library.headers["location"] == "/music/sfx-library"
        sfx_library = client.get("/music/sfx-library")
        assert sfx_library.status_code == 200
        assert "Thư viện SFX" in sfx_library.text
        compatibility = client.get("/features/image")
        assert compatibility.status_code == 200
        legacy = client.get("/campaign-app", follow_redirects=False)
        assert legacy.status_code == 307
        assert legacy.headers["location"] == "/admin/campaigns"


def test_customer_portal_redirects_follow_signed_session_and_telegram_link_state(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        unauthenticated = client.get("/dashboard", follow_redirects=False)
        assert unauthenticated.status_code == 307
        assert unauthenticated.headers["location"] == "/login?next=/dashboard"
        assert client.get("/legal").status_code == 200

        registration = client.post("/api/v1/auth/register", json={"email": "redirect@example.com", "password": "correct-horse-battery-staple"})
        assert registration.json()["ok"] is True
        login = client.post("/api/v1/auth/login", json={"email": "redirect@example.com", "password": "correct-horse-battery-staple"})
        csrf = login.json()["data"]["csrf_token"]
        unlinked_dashboard = client.get("/dashboard", follow_redirects=False)
        assert unlinked_dashboard.status_code == 307
        assert unlinked_dashboard.headers["location"] == "/onboarding"
        assert client.get("/account").status_code == 200
        signed_login = client.get("/login", follow_redirects=False)
        assert signed_login.headers["location"] == "/onboarding"

        code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
        assert confirm_link(client, code).json()["ok"] is True
        linked_onboarding = client.get("/onboarding", follow_redirects=False)
        assert linked_onboarding.status_code == 307
        assert linked_onboarding.headers["location"] == "/dashboard"


def test_admin_portal_requires_signed_session_and_current_canonical_role(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        unauthenticated = client.get("/admin", follow_redirects=False)
        assert unauthenticated.status_code == 401
        assert unauthenticated.json()["error_code"] == "REQUEST_DENIED"

        # A callback may populate the display cache, but the HTML page itself
        # refuses access when the bot core cannot currently prove admin role.
        register_and_link(client, role="admin")
        stale_cached_role = client.get("/admin/users", follow_redirects=False)
        assert stale_cached_role.status_code == 403
        assert stale_cached_role.json()["error_code"] == "REQUEST_DENIED"


def test_every_admin_api_rechecks_canonical_role_for_reads_and_writes(tmp_path, monkeypatch):
    """A stale role cache must never unlock JSON Admin ERP endpoints.

    The test bridge is intentionally unconfigured, so a callback that only
    claims ``role=admin`` proves neither the read endpoints nor CSRF-protected
    writes can reach the bridge without live canonical confirmation.
    """
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client, role="admin")
        for path in (
            "/api/v1/admin/summary",
            "/api/v1/admin/users",
            "/api/v1/admin/jobs",
            "/api/v1/admin/payments",
            "/api/v1/admin/providers",
            "/api/v1/admin/tickets",
        ):
            response = client.get(path)
            assert response.status_code == 403, path
            assert response.json()["error_code"] == "REQUEST_DENIED"

        writes = (
            ("/api/v1/admin/jobs/job-1/retry", {"input": {}, "idempotency_key": "admin-retry-0001"}),
            ("/api/v1/admin/jobs/job-1/refund", {"input": {}, "idempotency_key": "admin-refund-0001"}),
            ("/api/v1/admin/features/video_single/freeze", {"frozen": True, "note": "test", "idempotency_key": "admin-freeze-0001"}),
        )
        for path, payload in writes:
            response = client.post(path, headers={"X-CSRF-Token": csrf}, json=payload)
            # The Web ERP deliberately ships read-only. A local cached admin role
            # still cannot wake the bot bridge unless a separate write flag and
            # canonical adapter are explicitly enabled.
            assert response.status_code == 200, path
            assert response.json()["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"


def test_portal_template_uses_inert_bootstrap_for_strict_csp(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        register_and_link(client)
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert 'id="portal-bootstrap" type="application/json"' in page.text
        assert "window.__TOAN_AAS_PORTAL__=" not in page.text
        assert "__PORTAL_ASSET_VERSION__" not in page.text
        assert "/static/portal/portal.js?v=" in page.text


def test_api_validation_errors_keep_the_standard_envelope(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        response = client.post("/api/v1/auth/register", json={"email": "not-an-email"})
        assert response.status_code == 422
        assert response.json() == {
            "ok": False,
            "status": "failed",
            "message": "Dữ liệu yêu cầu không hợp lệ",
            "data": {},
            "error_code": "REQUEST_INVALID",
        }


def test_auth_rate_limit_is_server_side_and_separates_login_from_registration(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        for _ in range(8):
            denied = client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": "not-the-right-password"})
            assert denied.status_code == 200
        login_limited = client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": "not-the-right-password"})
        assert login_limited.status_code == 429
        assert login_limited.json()["error_code"] == "AUTH_RATE_LIMITED"

        for index in range(4):
            registered = client.post(
                "/api/v1/auth/register",
                json={"email": f"rate-{index}@example.com", "password": "correct-horse-battery-staple"},
            )
            assert registered.status_code == 200
        registration_limited = client.post(
            "/api/v1/auth/register",
            json={"email": "rate-final@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration_limited.status_code == 429
        assert registration_limited.json()["error_code"] == "AUTH_RATE_LIMITED"


def test_registration_does_not_disclose_that_an_email_already_exists(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first = client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "correct-horse-battery-staple"},
        )
        assert first.status_code == 200
        duplicate = client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "different-correct-horse-battery"},
        )
        assert duplicate.status_code == 200
        assert first.json() == duplicate.json() == {
            "ok": True,
            "status": "awaiting_confirm",
            "message": "Nếu email chưa có tài khoản, yêu cầu đăng ký đã được tiếp nhận. Hãy đăng nhập để tiếp tục hoặc dùng chức năng khôi phục mật khẩu khi được phát hành.",
            "data": {},
            "error_code": None,
        }
        assert "set-cookie" not in first.headers
        assert "set-cookie" not in duplicate.headers


def test_telegram_link_revokes_other_sessions_but_keeps_the_initiating_session(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "two-sessions@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.json()["ok"] is True
        first_login = client.post("/api/v1/auth/login", json={"email": "two-sessions@example.com", "password": "correct-horse-battery-staple"})
        csrf = first_login.json()["data"]["csrf_token"]
        with TestClient(client.app) as other_client:
            second_login = other_client.post(
                "/api/v1/auth/login",
                json={"email": "two-sessions@example.com", "password": "correct-horse-battery-staple"},
            )
            assert second_login.status_code == 200
            assert other_client.get("/api/v1/auth/me").status_code == 200

            code = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf}).json()["data"]["code"]
            assert confirm_link(client, code).json()["ok"] is True
            assert client.get("/api/v1/auth/me").status_code == 200
            revoked = other_client.get("/api/v1/auth/me")
            assert revoked.status_code == 401
            assert revoked.json()["error_code"] == "REQUEST_DENIED"


def test_a_canonical_telegram_identity_cannot_link_two_web_accounts(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        first = client.post(
            "/api/v1/auth/register",
            json={"email": "first-link@example.com", "password": "correct-horse-battery-staple"},
        )
        assert first.json()["ok"] is True
        first_login = client.post("/api/v1/auth/login", json={"email": "first-link@example.com", "password": "correct-horse-battery-staple"})
        first_code = client.post(
            "/api/v1/auth/telegram/link/start",
            headers={"X-CSRF-Token": first_login.json()["data"]["csrf_token"]},
        ).json()["data"]["code"]
        assert confirm_link(client, first_code).json()["ok"] is True

        with TestClient(client.app) as other_client:
            second = other_client.post(
                "/api/v1/auth/register",
                json={"email": "second-link@example.com", "password": "correct-horse-battery-staple"},
            )
            assert second.json()["ok"] is True
            second_login = other_client.post("/api/v1/auth/login", json={"email": "second-link@example.com", "password": "correct-horse-battery-staple"})
            second_code = other_client.post(
                "/api/v1/auth/telegram/link/start",
                headers={"X-CSRF-Token": second_login.json()["data"]["csrf_token"]},
            ).json()["data"]["code"]
            collision = confirm_link(other_client, second_code)
            assert collision.status_code == 409
            assert collision.json()["ok"] is False
            assert collision.json()["error_code"] == "TELEGRAM_ALREADY_LINKED"


def test_linked_account_cannot_issue_or_use_a_code_to_replace_telegram_identity(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        blocked_start = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
        assert blocked_start.status_code == 200
        assert blocked_start.json()["error_code"] == "TELEGRAM_RELINK_NOT_ALLOWED"

        import copyfast_auth
        from copyfast_db import transaction

        forged_code = "defensive-relink-code-0001"
        with transaction() as conn:
            account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", ("user@example.com",)).fetchone()[0]
            conn.execute(
                """INSERT INTO telegram_link_codes (code_hash, account_id, expires_at, initiating_session_id, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    hashlib.sha256(forged_code.encode("utf-8")).hexdigest(),
                    account_id,
                    copyfast_auth._link_expiry(),
                    "test-defensive-relink-session",
                    copyfast_auth.utc_now(),
                ),
            )
        blocked_callback = confirm_link(client, forged_code, canonical_user_id="telegram-456")
        assert blocked_callback.status_code == 409
        assert blocked_callback.json()["error_code"] == "TELEGRAM_RELINK_NOT_ALLOWED"
        me = client.get("/api/v1/auth/me")
        assert "telegram-456" not in me.text


def test_production_environment_requires_a_real_secret_and_sets_secure_session_cookie(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "production-cookie@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.status_code == 200
        assert "set-cookie" not in registration.headers
        login = client.post("/api/v1/auth/login", json={"email": "production-cookie@example.com", "password": "correct-horse-battery-staple"})
        assert "Secure" in login.headers["set-cookie"]
        assert login.headers["cache-control"] == "no-store, private"

    import copyfast_auth

    monkeypatch.delenv("WEB_SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="WEB_SESSION_SECRET"):
        copyfast_auth.ensure_auth_configuration()


def test_credentialed_cors_rejects_wildcards_and_non_https_remote_origins(monkeypatch):
    application = importlib.import_module("app")
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    assert application._origins() == ["https://app.toanaas.vn"]
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="tường minh"):
        application._origins()
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://example.invalid")
    with pytest.raises(RuntimeError, match="HTTPS"):
        application._origins()
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:8877,https://app.toanaas.vn")
    assert application._origins() == ["http://localhost:8877", "https://app.toanaas.vn"]


def test_portal_uses_a_single_delegated_listener_after_hydration():
    source = (Path(__file__).parents[1] / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    assert "let interactionsBound = false;" in source
    assert "if (interactionsBound) return;" in source
    assert "dispatchAction(action, getBootstrap())" in source
    assert "bindInteractions(context)" not in source
