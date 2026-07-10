import importlib
import hashlib
import hmac
import json
from pathlib import Path
import sys
import time
import uuid

import pytest
from fastapi.testclient import TestClient


MODULES = [
    "app", "config", "db", "copyfast_db", "copyfast_auth", "copyfast_bridge",
    "copyfast_registry", "copyfast_api", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch):
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
    return TestClient(application)


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


def confirm_link(client, code, *, role="user", request_id=None):
    body = json.dumps(
        {"code": code, "canonical_user_id": "telegram-123", "role": role},
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
    payload = response.json()
    csrf = payload["data"]["csrf_token"]
    link = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
    assert link.status_code == 200
    code = link.json()["data"]["code"]
    confirmed = confirm_link(client, code, role=role)
    assert confirmed.json()["ok"] is True
    return csrf


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
        csrf = registration.json()["data"]["csrf_token"]
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

        monkeypatch.setenv("BOT_USERNAME", "not/a-valid-telegram-username")
        invalid_name = client.get("/api/v1/payments/options").json()["data"]["manual"]
        assert invalid_name["available"] is False
        assert invalid_name["telegram_url"] == ""
        invalid_deep_link = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
        assert invalid_deep_link.status_code == 200
        assert invalid_deep_link.json()["data"]["deep_link"] == ""


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
        csrf = registration.json()["data"]["csrf_token"]
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
            "caption", "image_remove_background", "music_song", "documents_ocr",
        }.issubset(keys)
        register_and_link(client)
        page = client.get("/video/multiscene")
        assert page.status_code == 200
        assert "TOAN AAS" in page.text
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
        csrf = registration.json()["data"]["csrf_token"]
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


def test_telegram_link_revokes_other_sessions_but_keeps_the_initiating_session(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "two-sessions@example.com", "password": "correct-horse-battery-staple"},
        )
        csrf = registration.json()["data"]["csrf_token"]
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
        first_code = client.post(
            "/api/v1/auth/telegram/link/start",
            headers={"X-CSRF-Token": first.json()["data"]["csrf_token"]},
        ).json()["data"]["code"]
        assert confirm_link(client, first_code).json()["ok"] is True

        with TestClient(client.app) as other_client:
            second = other_client.post(
                "/api/v1/auth/register",
                json={"email": "second-link@example.com", "password": "correct-horse-battery-staple"},
            )
            second_code = other_client.post(
                "/api/v1/auth/telegram/link/start",
                headers={"X-CSRF-Token": second.json()["data"]["csrf_token"]},
            ).json()["data"]["code"]
            collision = confirm_link(other_client, second_code)
            assert collision.status_code == 200
            assert collision.json()["ok"] is False
            assert collision.json()["error_code"] == "TELEGRAM_ALREADY_LINKED"


def test_production_environment_requires_a_real_secret_and_sets_secure_session_cookie(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with make_client(tmp_path, monkeypatch) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "production-cookie@example.com", "password": "correct-horse-battery-staple"},
        )
        assert registration.status_code == 200
        assert "Secure" in registration.headers["set-cookie"]
        assert registration.headers["cache-control"] == "no-store, private"

    import copyfast_auth

    monkeypatch.delenv("WEB_SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="WEB_SESSION_SECRET"):
        copyfast_auth.ensure_auth_configuration()


def test_credentialed_cors_rejects_wildcards_and_non_https_remote_origins(monkeypatch):
    application = importlib.import_module("app")
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
