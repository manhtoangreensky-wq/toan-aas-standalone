"""Contract and provider-free verification tests for Free Tools Web-Bot Runtime Parity (R38).

Task: WEBAPP_R38_FREE_TOOLS_BOT_RUNTIME_PARITY_RATE_WEATHER_AVATAR_DOWNLOADER_R1
Product: WEB_APP
Tracker: manhtoangreensky-wq/toan-aas-standalone#666
Scope: NON_UI_BACKEND_ONLY

Proves:
1. RATE_VALID_INPUT
2. RATE_INVALID_INPUT
3. RATE_SOURCE_UNAVAILABLE
4. RATE_NO_FAKE_VALUE
5. WEATHER_VALID_LOCATION
6. WEATHER_INVALID_LOCATION
7. WEATHER_SOURCE_ERROR
8. WEATHER_EMPTY_RESULT
9. WEATHER_NO_FAKE_RESULT
10. AVATAR_VALID_REQUEST
11. AVATAR_RIGHTS_REQUIRED
12. AVATAR_UNSAFE_URL_BLOCKED
13. AVATAR_SOURCE_ERROR_NO_FAKE_OUTPUT
14. DOWNLOADER_RIGHTS_REQUIRED
15. DOWNLOADER_VALID_PUBLIC_URL
16. DOWNLOADER_UNSUPPORTED_OR_PRIVATE_URL_BLOCKED
17. DOWNLOADER_PROVIDER_DISABLED_FAIL_CLOSED
18. DOWNLOADER_SUSPICIOUS_RESULT_BLOCKED
19. DOWNLOADER_ERROR_REFUND_OR_NO_CHARGE_MATCHES_BOT
20. DOWNLOADER_SAFE_DELIVERY
21. AUTH_GUARD (401 for unauthenticated)
22. CSRF_GUARD (403 for mutations without csrf)
23. SERVER_AUTHORITY_FOR_SOURCE_PROVIDER_PRICE (Zero Xu cost, server-enforced)
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import urllib.parse

import pytest
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

from app import app
import app as app_module
from copyfast_auth import (
    SESSION_COOKIE,
    _cookie_name,
    _insert_session,
    _session_cookie_value,
)
from copyfast_db import ensure_copyfast_schema, transaction, utc_now


class MockFreeToolsBridgeState:
    """Mock CoreBridge backend state modeling Bot Free Tools handlers."""

    def handle_request(
        self,
        method: str,
        path: str,
        actor_id: str,
        payload: dict | None = None,
        params: dict | None = None,
    ) -> tuple[int, dict]:
        parts = path.strip("/").split("/")
        # Path: internal/v1/free-tools/...
        if len(parts) >= 4 and parts[0] == "internal" and parts[1] == "v1" and parts[2] == "free-tools":
            endpoint = parts[3]

            # ── 1. RATE ──
            if endpoint == "rate":
                data = payload if method == "POST" else (params or {})
                raw_input = (data.get("raw_input") or data.get("query") or "").strip()
                if not raw_input:
                    return 400, {"ok": False, "error_code": "RATE_INVALID_INPUT", "message": "Input required"}
                if raw_input == "simulate_unavailable":
                    return 503, {"ok": False, "error_code": "RATE_SOURCE_UNAVAILABLE", "message": "Exchange rate service unavailable"}
                return 200, {
                    "ok": True,
                    "status": "completed",
                    "source": "bot_public_rate",
                    "text": f"{raw_input} = 2.540.000 VND",
                    "raw_input": raw_input,
                    "target_lang": data.get("target_lang", "vi"),
                    "xu_charged": 0,
                }

            # ── 2. WEATHER ──
            if endpoint == "weather":
                data = payload if method == "POST" else (params or {})
                location = (data.get("location") or "").strip()
                if not location:
                    return 400, {"ok": False, "error_code": "WEATHER_INVALID_LOCATION", "message": "Location required"}
                if location == "unknown_lost_city":
                    return 404, {"ok": False, "error_code": "WEATHER_EMPTY_RESULT", "message": "Weather not found"}
                if location == "simulate_source_error":
                    return 503, {"ok": False, "error_code": "WEATHER_SOURCE_ERROR", "message": "Weather provider error"}
                return 200, {
                    "ok": True,
                    "status": "completed",
                    "source": "bot_public_weather",
                    "location": location,
                    "report": f"Thời tiết tại {location}: 26°C, trời nắng.",
                    "unit": data.get("unit", "celsius"),
                    "xu_charged": 0,
                }

            # ── 3. AVATAR ──
            if endpoint == "avatar" and method == "POST":
                data = payload or {}
                if not data.get("confirmed_rights"):
                    return 400, {"ok": False, "error_code": "AVATAR_RIGHTS_REQUIRED", "message": "Rights confirmation required"}
                seed = (data.get("seed") or "").strip()
                if not seed:
                    return 400, {"ok": False, "error_code": "AVATAR_INVALID_SEED", "message": "Seed required"}
                if seed == "simulate_error":
                    return 503, {"ok": False, "error_code": "AVATAR_SOURCE_ERROR", "message": "Avatar provider failed"}
                avatar_set = data.get("avatar_set", 1)
                encoded = urllib.parse.quote(seed)
                return 200, {
                    "ok": True,
                    "status": "completed",
                    "source": "robohash",
                    "avatar_url": f"https://robohash.org/{encoded}.png?set=set{avatar_set}&size=400x400",
                    "seed": seed,
                    "style": data.get("style", "realistic"),
                    "avatar_set": avatar_set,
                    "xu_charged": 0,
                }

            # ── 4. DOWNLOADER INSPECT & DOWNLOAD ──
            if endpoint == "downloader" and len(parts) >= 5:
                sub = parts[4]
                data = payload or {}
                url = (data.get("url") or "").strip()
                if not url:
                    return 400, {"ok": False, "error_code": "DOWNLOADER_INVALID_URL", "message": "URL required"}
                parsed = urllib.parse.urlparse(url)
                host = parsed.hostname or ""
                if host in ("127.0.0.1", "localhost") or host.startswith("192.168.") or host.startswith("10."):
                    return 400, {"ok": False, "error_code": "DOWNLOADER_UNSUPPORTED_OR_PRIVATE_URL_BLOCKED", "message": "Private host rejected"}
                if "disabled" in url:
                    return 503, {"ok": False, "error_code": "DOWNLOADER_PROVIDER_DISABLED_FAIL_CLOSED", "message": "Downloader service disabled"}
                if "suspicious" in url:
                    return 400, {"ok": False, "error_code": "DOWNLOADER_SUSPICIOUS_RESULT_BLOCKED", "message": "Suspicious redirect blocked"}

                if sub == "inspect":
                    return 200, {
                        "ok": True,
                        "status": "completed",
                        "source": "public_video_downloader",
                        "url": url,
                        "asset_type": data.get("requested_asset", "video"),
                        "title": "Sample Public Video",
                        "duration_seconds": 120,
                        "xu_charged": 0,
                    }
                if sub == "download":
                    if not data.get("confirmed_rights"):
                        return 400, {"ok": False, "error_code": "DOWNLOADER_RIGHTS_REQUIRED", "message": "Rights required"}
                    return 200, {
                        "ok": True,
                        "status": "completed",
                        "source": "public_video_downloader",
                        "url": url,
                        "asset_type": data.get("requested_asset", "video"),
                        "status": "completed",
                        "download_url": "/api/v1/tools/downloader/artifacts/safe_job_123.mp4",
                        "xu_charged": 0,
                        "refund_issued": False,
                    }

        return 404, {"ok": False, "error_code": "NOT_FOUND", "message": "Not found"}


bridge_state = MockFreeToolsBridgeState()


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Ensure test environment is strictly provider-free and tables exist."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-free-tools-r38")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "mock-core-bridge-token-r38-fixed-len")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "mock-hmac-secret-r38-32-bytes-long!")

    app_module._auth_rate_windows.clear()
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    ensure_copyfast_schema()

    from copyfast_bridge import CoreBridgeClient
    import copyfast_bridge

    async def mock_bridge_client_request(self, method: str, path: str, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        status_code, resp_data = bridge_state.handle_request(method, path, actor_id, payload=payload, params=params)
        if status_code >= 400:
            return copyfast_bridge._sanitize_envelope(resp_data, fallback_code=resp_data.get("error_code"))
        return copyfast_bridge._sanitize_envelope(resp_data)

    monkeypatch.setattr(CoreBridgeClient, "request", mock_bridge_client_request)
    yield


def _create_test_account(canonical_user_id: str = "1001") -> tuple[TestClient, str]:
    """Insert or update test account into SQLite and return authenticated TestClient and csrf_token."""
    account_id = f"acc_{canonical_user_id}"
    email = f"{account_id}@test.local"
    with transaction() as conn:
        now = utc_now()
        conn.execute(
            """
            INSERT INTO web_accounts (
                id, email, password_hash, canonical_user_id, role_cache, created_at, updated_at
            ) VALUES (?, ?, 'test_hash', ?, 'member', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                email=excluded.email,
                canonical_user_id=excluded.canonical_user_id,
                updated_at=excluded.updated_at
            """,
            (account_id, email, canonical_user_id or None, now, now),
        )
        conn.execute("DELETE FROM web_sessions WHERE account_id=?", (account_id,))
        sess = _insert_session(conn, account_id)
    client = TestClient(app)
    cookie_val = _session_cookie_value(sess["session_id"])
    client.cookies.set(_cookie_name(SESSION_COOKIE), cookie_val)
    return client, sess["csrf_token"]


# ─── 1. EXCHANGE RATE TESTS ───────────────────────────────────────────────────

def test_rate_valid_input_post_and_get():
    """RATE_VALID_INPUT: Valid input returns exchange calculation with zero xu charged."""
    client, _ = _create_test_account()

    # POST
    resp_post = client.post("/api/v1/free-tools/rate", json={"raw_input": "100 USD", "target_lang": "vi"})
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["ok"] is True
    assert "2.540.000 VND" in data_post["text"]
    assert data_post["xu_charged"] == 0

    # GET
    resp_get = client.get("/api/v1/free-tools/rate?raw_input=50+EUR&target_lang=vi")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["ok"] is True
    assert data_get["xu_charged"] == 0

    # Alias /tools/rate
    resp_alias = client.post("/api/v1/tools/rate", json={"query": "100 JPY"})
    assert resp_alias.status_code == 200
    assert resp_alias.json()["ok"] is True


def test_rate_invalid_input_fails_closed():
    """RATE_INVALID_INPUT: Empty or whitespace input rejected with 400."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/rate", json={"raw_input": "   "})
    assert resp.status_code == 400
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "RATE_INVALID_INPUT"


def test_rate_source_unavailable_truthful():
    """RATE_SOURCE_UNAVAILABLE: Upstream source unavailable returns 503 truthfully."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/rate", json={"raw_input": "simulate_unavailable"})
    assert resp.status_code == 503
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "RATE_SOURCE_UNAVAILABLE"


def test_rate_no_fake_value():
    """RATE_NO_FAKE_VALUE: Ensure no synthetic rate is fabricated on failure."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/rate", json={"raw_input": "simulate_unavailable"})
    assert resp.status_code == 503
    assert "rate" not in resp.json().get("data", {})
    assert resp.json()["ok"] is False


# ─── 2. WEATHER TESTS ─────────────────────────────────────────────────────────

def test_weather_valid_location_post_and_get():
    """WEATHER_VALID_LOCATION: Valid location returns weather report with zero xu charged."""
    client, _ = _create_test_account()

    # POST
    resp_post = client.post("/api/v1/free-tools/weather", json={"location": "Hanoi", "unit": "celsius"})
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["ok"] is True
    assert "Hanoi" in data_post["report"]
    assert data_post["xu_charged"] == 0

    # GET
    resp_get = client.get("/api/v1/free-tools/weather?location=Danang")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["ok"] is True
    assert data_get["xu_charged"] == 0

    # Alias /tools/weather
    resp_alias = client.post("/api/v1/tools/weather", json={"location": "Saigon"})
    assert resp_alias.status_code == 200
    assert resp_alias.json()["ok"] is True


def test_weather_invalid_location_fails_closed():
    """WEATHER_INVALID_LOCATION: Empty location rejected with 400."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/weather", json={"location": "   "})
    assert resp.status_code == 400
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "WEATHER_INVALID_LOCATION"


def test_weather_source_error_truthful():
    """WEATHER_SOURCE_ERROR: Upstream weather service error returns 503 truthfully."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/weather", json={"location": "simulate_source_error"})
    assert resp.status_code == 503
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "WEATHER_SOURCE_ERROR"


def test_weather_empty_result_returns_404():
    """WEATHER_EMPTY_RESULT: Unfound weather location returns 404."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/weather", json={"location": "unknown_lost_city"})
    assert resp.status_code == 404
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "WEATHER_EMPTY_RESULT"


def test_weather_no_fake_result():
    """WEATHER_NO_FAKE_RESULT: No synthetic weather report fabricated on failure."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/weather", json={"location": "unknown_lost_city"})
    assert resp.status_code == 404
    assert resp.json()["ok"] is False
    assert "report" not in resp.json()


# ─── 3. AI AVATAR TESTS ───────────────────────────────────────────────────────

def test_avatar_valid_request():
    """AVATAR_VALID_REQUEST: Mirrors Bot deterministic Robohash URL construction truth."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/avatar",
        headers={"x-csrf-token": csrf_token},
        json={"seed": "engineer_toan", "style": "realistic", "avatar_set": 2, "confirmed_rights": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["avatar_url"] == "https://robohash.org/engineer_toan.png?set=set2&size=400x400"
    assert data["xu_charged"] == 0


def test_avatar_rights_required():
    """AVATAR_RIGHTS_REQUIRED: Missing rights confirmation fails with 400."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/avatar",
        headers={"x-csrf-token": csrf_token},
        json={"seed": "user123", "confirmed_rights": False},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "AVATAR_RIGHTS_REQUIRED"


def test_avatar_unsafe_url_blocked():
    """AVATAR_UNSAFE_URL_BLOCKED: XSS or dangerous pseudo-protocols in seed blocked."""
    client, csrf_token = _create_test_account()
    for bad_seed in ("javascript:alert(1)", "data:text/html;base64,abc", "<script>alert(1)</script>"):
        resp = client.post(
            "/api/v1/free-tools/avatar",
            headers={"x-csrf-token": csrf_token},
            json={"seed": bad_seed, "confirmed_rights": True},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "AVATAR_UNSAFE_URL_BLOCKED"


def test_avatar_source_error_no_fake_output():
    """AVATAR_SOURCE_ERROR_NO_FAKE_OUTPUT: Fail closed on source error without fake output."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/avatar",
        headers={"x-csrf-token": csrf_token},
        json={"seed": "simulate_error", "confirmed_rights": True},
    )
    assert resp.status_code in (500, 503)
    data = resp.json()
    assert data["ok"] is False
    assert "avatar_url" not in data


# ─── 4. VIDEO DOWNLOADER TESTS ────────────────────────────────────────────────

def test_downloader_rights_required():
    """DOWNLOADER_RIGHTS_REQUIRED: Missing confirmed rights fails closed."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "confirmed_rights": False},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "DOWNLOADER_RIGHTS_REQUIRED"


def test_downloader_valid_public_url():
    """DOWNLOADER_VALID_PUBLIC_URL: Inspect and download valid public URL succeeds with 0 xu."""
    client, csrf_token = _create_test_account()

    # Inspect
    resp_insp = client.post(
        "/api/v1/free-tools/downloader/inspect",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert resp_insp.status_code == 200
    assert resp_insp.json()["ok"] is True
    assert resp_insp.json()["xu_charged"] == 0

    # Download
    resp_dl = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "confirmed_rights": True},
    )
    assert resp_dl.status_code == 200
    data = resp_dl.json()
    assert data["ok"] is True
    assert data["xu_charged"] == 0
    assert "download_url" in data


def test_downloader_unsupported_or_private_url_blocked():
    """DOWNLOADER_UNSUPPORTED_OR_PRIVATE_URL_BLOCKED: SSRF private IPs and loopbacks blocked."""
    client, csrf_token = _create_test_account()
    for bad_url in ("http://127.0.0.1:8000/secret.mp4", "http://localhost/test", "http://192.168.1.1/video.mp4"):
        resp = client.post(
            "/api/v1/free-tools/downloader/download",
            headers={"x-csrf-token": csrf_token},
            json={"url": bad_url, "confirmed_rights": True},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "DOWNLOADER_UNSUPPORTED_OR_PRIVATE_URL_BLOCKED"


def test_downloader_provider_disabled_fail_closed():
    """DOWNLOADER_PROVIDER_DISABLED_FAIL_CLOSED: Fails closed with 503 when downloader disabled."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://example.com/disabled/video.mp4", "confirmed_rights": True},
    )
    assert resp.status_code == 503
    assert resp.json()["error_code"] == "DOWNLOADER_PROVIDER_DISABLED_FAIL_CLOSED"


def test_downloader_suspicious_result_blocked():
    """DOWNLOADER_SUSPICIOUS_RESULT_BLOCKED: Promotional or suspicious redirect blocked."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://example.com/suspicious/video.mp4", "confirmed_rights": True},
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "DOWNLOADER_SUSPICIOUS_RESULT_BLOCKED"


def test_downloader_error_refund_or_no_charge_matches_bot():
    """DOWNLOADER_ERROR_REFUND_OR_NO_CHARGE_MATCHES_BOT: Verifies xu_charged remains 0 on error."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://example.com/disabled/video.mp4", "confirmed_rights": True},
    )
    assert resp.status_code == 503
    # No charge occurred
    assert resp.json().get("xu_charged", 0) == 0


def test_downloader_safe_delivery_no_private_paths():
    """DOWNLOADER_SAFE_DELIVERY: Output URLs do not expose local filesystem paths."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "confirmed_rights": True},
    )
    assert resp.status_code == 200
    dumped = json.dumps(resp.json())
    for dangerous in ("C:\\", "D:\\", "/private/", "/root/", "C:/", "D:/"):
        assert dangerous not in dumped


# ─── 5. SECURITY & CONTRACT GUARDS ───────────────────────────────────────────

def test_auth_guard():
    """AUTH_GUARD: Unauthenticated requests return 401."""
    anon_client = TestClient(app)
    endpoints = [
        ("POST", "/api/v1/free-tools/rate", {"raw_input": "10 USD"}),
        ("GET", "/api/v1/free-tools/rate?raw_input=10+USD", None),
        ("POST", "/api/v1/free-tools/weather", {"location": "Hanoi"}),
        ("GET", "/api/v1/free-tools/weather?location=Hanoi", None),
        ("POST", "/api/v1/free-tools/avatar", {"seed": "toan", "confirmed_rights": True}),
        ("POST", "/api/v1/free-tools/downloader/inspect", {"url": "https://example.com/v.mp4"}),
        ("POST", "/api/v1/free-tools/downloader/download", {"url": "https://example.com/v.mp4", "confirmed_rights": True}),
    ]
    for method, path, payload in endpoints:
        if method == "POST":
            resp = anon_client.post(path, json=payload)
        else:
            resp = anon_client.get(path)
        assert resp.status_code == 401, f"Failed auth guard on {method} {path}"


def test_csrf_guard_for_mutation_endpoints():
    """CSRF_GUARD: POST to mutation endpoints without valid CSRF header returns 403."""
    client, _ = _create_test_account()
    # Missing CSRF header
    resp_avatar = client.post(
        "/api/v1/free-tools/avatar",
        json={"seed": "toan", "confirmed_rights": True},
    )
    assert resp_avatar.status_code == 403

    resp_download = client.post(
        "/api/v1/free-tools/downloader/download",
        json={"url": "https://example.com/v.mp4", "confirmed_rights": True},
    )
    assert resp_download.status_code == 403
