import importlib
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "config", "db", "copyfast_db", "copyfast_auth", "copyfast_bridge",
    "copyfast_registry", "copyfast_api", "copyfast_pages",
]


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "copyfast-test.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    for name in MODULES:
        sys.modules.pop(name, None)
    application = importlib.import_module("app").app
    return TestClient(application)


def register_and_link(client, *, role="user"):
    response = client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "correct-horse-battery-staple", "display_name": "User"})
    assert response.status_code == 200
    payload = response.json()
    csrf = payload["data"]["csrf_token"]
    link = client.post("/api/v1/auth/telegram/link/start", headers={"X-CSRF-Token": csrf})
    assert link.status_code == 200
    code = link.json()["data"]["code"]
    confirmed = client.post(
        "/api/v1/auth/internal/telegram-link/confirm",
        headers={"X-TOAN-AAS-BRIDGE-TOKEN": "bridge-test-token"},
        json={"code": code, "canonical_user_id": "telegram-123", "role": role},
    )
    assert confirmed.json()["ok"] is True
    return csrf


def test_signed_session_csrf_and_telegram_link(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_link(client)
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["data"]["account"]["canonical_user_id"] == "telegram-123"
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


def test_catalog_and_portal_routes_are_available(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        catalog = client.get("/api/v1/catalog")
        assert catalog.status_code == 200
        keys = {item["key"] for item in catalog.json()["data"]["features"]}
        assert {
            "video_multiscene", "voice_tts", "subtitle_asr", "admin_jobs",
            "caption", "image_remove_background", "music_song", "documents_ocr",
        }.issubset(keys)
        page = client.get("/video/multiscene")
        assert page.status_code == 200
        assert "TOAN AAS" in page.text
        compatibility = client.get("/features/image")
        assert compatibility.status_code == 200
        legacy = client.get("/campaign-app", follow_redirects=False)
        assert legacy.status_code == 307
        assert legacy.headers["location"] == "/admin/campaigns"


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


def test_portal_template_uses_inert_bootstrap_for_strict_csp(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        page = client.get("/dashboard")
        assert page.status_code == 200
        assert 'id="portal-bootstrap" type="application/json"' in page.text
        assert "window.__TOAN_AAS_PORTAL__=" not in page.text


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
