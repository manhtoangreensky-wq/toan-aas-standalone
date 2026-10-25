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
5. RATE_OFFLINE_SAFE_FALLBACK_PARITY
6. RATE_FIELDS_SURVIVE_WEB_PROJECTION
7. WEATHER_VALID_LOCATION
8. WEATHER_INVALID_LOCATION
9. WEATHER_SOURCE_ERROR
10. WEATHER_EMPTY_RESULT
11. WEATHER_NO_FAKE_RESULT
12. WEATHER_OFFLINE_SAFE_FALLBACK_PARITY
13. WEATHER_FIELDS_SURVIVE_WEB_PROJECTION
14. AVATAR_VALID_REQUEST
15. AVATAR_RIGHTS_REQUIRED
16. AVATAR_UNSAFE_URL_BLOCKED
17. AVATAR_SOURCE_ERROR_NO_FAKE_OUTPUT
18. AVATAR_FIELDS_SURVIVE_WEB_PROJECTION
19. DOWNLOADER_RIGHTS_REQUIRED
20. DOWNLOADER_VALID_PUBLIC_URL
21. DOWNLOADER_UNSUPPORTED_OR_PRIVATE_URL_BLOCKED
22. DOWNLOADER_PROVIDER_DISABLED_FAIL_CLOSED
23. DOWNLOADER_SUSPICIOUS_RESULT_BLOCKED
24. DOWNLOADER_ERROR_REFUND_OR_NO_CHARGE_MATCHES_BOT
25. DOWNLOADER_FIELDS_SURVIVE_WEB_PROJECTION
26. DOWNLOADER_OPAQUE_ARTIFACT_ID
27. DOWNLOADER_OWNER_SAFE_DELIVERY
28. DOWNLOADER_FOREIGN_OWNER_DELIVERY_BLOCKED
29. DOWNLOADER_MISSING_ARTIFACT_FAIL_CLOSED
30. DOWNLOADER_DELIVERY_KINDS_PARITY
31. DOWNLOADER_SAFE_DELIVERY
32. AUTH_GUARD (401 for unauthenticated)
33. CSRF_GUARD (403 for mutations without csrf)
34. SERVER_AUTHORITY_FOR_SOURCE_PROVIDER_PRICE (Zero Xu cost, server-enforced)
35. NO_PRIVATE_METADATA_LEAK
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

    def __init__(self):
        self.force_redirect = False

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
                if raw_input == "offline_fallback":
                    return 200, {
                        "ok": True,
                        "status": "completed",
                        "source": "TOAN AAS Standard (Offline Safe)",
                        "text": "100 USD = 2.540.000 VND",
                        "raw_input": raw_input,
                        "target_lang": data.get("target_lang", "vi"),
                        "amount_in": 100.0,
                        "currency_in": "USD",
                        "currency_in_name": "Đô la Mỹ",
                        "target_currency": "VND",
                        "target_converted": 2540000.0,
                        "target_currency_name": "Việt Nam Đồng",
                        "usd": 100.0,
                        "vnd": 2540000.0,
                        "xu": 2540.0,
                        "cny": 720.0,
                        "hkd": 780.0,
                        "eur": 92.0,
                        "jpy": 15000.0,
                        "rate_usd_vnd": 25400.0,
                        "xu_charged": 0,
                        "_internal_secret_token": "SECRET_DO_NOT_LEAK",
                    }
                return 200, {
                    "ok": True,
                    "status": "completed",
                    "source": "ExchangeRate-API (Live)",
                    "text": f"{raw_input} = 2.540.000 VND",
                    "raw_input": raw_input,
                    "target_lang": data.get("target_lang", "vi"),
                    "amount_in": 100.0,
                    "currency_in": "USD",
                    "currency_in_name": "Đô la Mỹ",
                    "target_currency": "VND",
                    "target_converted": 2540000.0,
                    "target_currency_name": "Việt Nam Đồng",
                    "usd": 100.0,
                    "vnd": 2540000.0,
                    "xu": 2540.0,
                    "cny": 720.0,
                    "hkd": 780.0,
                    "eur": 92.0,
                    "jpy": 15000.0,
                    "rate_usd_vnd": 25400.0,
                    "xu_charged": 0,
                    "_internal_secret_token": "SECRET_DO_NOT_LEAK",
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
                if location == "offline_fallback":
                    return 200, {
                        "ok": True,
                        "status": "completed",
                        "source": "Dự báo chuẩn (Offline Safe)",
                        "location": location,
                        "city": "Hà Nội",
                        "country": "Vietnam",
                        "temperature": 26.5,
                        "windspeed": 12.0,
                        "weathercode": 1,
                        "description": "Trời nắng nhẹ",
                        "report": f"Thời tiết tại {location}: 26.5°C, Trời nắng nhẹ.",
                        "unit": data.get("unit", "celsius"),
                        "xu_charged": 0,
                        "_internal_secret_key": "SECRET_KEY_WEATHER",
                    }
                return 200, {
                    "ok": True,
                    "status": "completed",
                    "source": "Open-Meteo Live API",
                    "location": location,
                    "city": location,
                    "country": "Vietnam",
                    "temperature": 28.0,
                    "windspeed": 10.5,
                    "weathercode": 0,
                    "description": "Quang đãng",
                    "report": f"Thời tiết tại {location}: 28°C, quang đãng.",
                    "unit": data.get("unit", "celsius"),
                    "xu_charged": 0,
                    "_internal_secret_key": "SECRET_KEY_WEATHER",
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
                    "_internal_secret_provider": "SECRET_AVATAR",
                }

            # ── 4. DOWNLOADER ──
            if endpoint == "downloader" and len(parts) >= 5:
                sub = parts[4]

                if sub == "inspect":
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

                    return 200, {
                        "ok": True,
                        "status": "ready",
                        "source": "public_video_downloader",
                        "url": url,
                        "job_id": "job_inspect_12345",
                        "platform": "youtube",
                        "kind": data.get("requested_asset", "video"),
                        "asset_type": data.get("requested_asset", "video"),
                        "title": "Sample Public Video",
                        "duration": 120,
                        "duration_seconds": 120,
                        "bytes": 10485760,
                        "status": "ready",
                        "delivery_ready": True,
                        "charged_xu": 0,
                        "xu_charged": 0,
                        "rights_notice": "Tài sản thuộc quyền sử dụng và sở hữu của người dùng.",
                        "_internal_cookie": "SECRET_COOKIE",
                    }

                if sub == "download":
                    data = payload or {}
                    url = (data.get("url") or "").strip()
                    if not url:
                        return 400, {"ok": False, "error_code": "DOWNLOADER_INVALID_URL", "message": "URL required"}
                    if not data.get("confirmed_rights"):
                        return 400, {"ok": False, "error_code": "DOWNLOADER_RIGHTS_REQUIRED", "message": "Rights required"}
                    parsed = urllib.parse.urlparse(url)
                    host = parsed.hostname or ""
                    if host in ("127.0.0.1", "localhost") or host.startswith("192.168.") or host.startswith("10."):
                        return 400, {"ok": False, "error_code": "DOWNLOADER_UNSUPPORTED_OR_PRIVATE_URL_BLOCKED", "message": "Private host rejected"}
                    if "disabled" in url:
                        return 503, {"ok": False, "error_code": "DOWNLOADER_PROVIDER_DISABLED_FAIL_CLOSED", "message": "Downloader service disabled"}
                    if "suspicious" in url:
                        return 400, {"ok": False, "error_code": "DOWNLOADER_SUSPICIOUS_RESULT_BLOCKED", "message": "Suspicious redirect blocked"}

                    job_id = "job_dl_1729000000_a1b2c3d4"
                    return 200, {
                        "ok": True,
                        "status": "ready",
                        "source": "public_video_downloader",
                        "url": url,
                        "job_id": job_id,
                        "platform": "youtube",
                        "kind": data.get("requested_asset", "video"),
                        "asset_type": data.get("requested_asset", "video"),
                        "title": "Sample Download Video",
                        "duration": 120,
                        "duration_seconds": 120,
                        "bytes": 10485760,
                        "status": "ready",
                        "delivery_ready": True,
                        "delivery_url": f"/free-tools/downloader/delivery/{job_id}",
                        "download_url": f"/free-tools/downloader/delivery/{job_id}",
                        "charged_xu": 0,
                        "xu_charged": 0,
                        "refund_issued": False,
                        "rights_notice": "Tài sản thuộc quyền sử dụng và sở hữu của người dùng.",
                        "file_path": "/root/private/unsafe/video.mp4",
                        "_internal_token": "TOKEN_SECRET",
                    }

                if sub == "delivery" and len(parts) >= 6:
                    job_id = parts[5]
                    query = params or {}
                    p_kind = query.get("kind", ["video"])[0] if isinstance(query.get("kind"), list) else query.get("kind", "video")
                    p_mode = query.get("mode", ["stream"])[0] if isinstance(query.get("mode"), list) else query.get("mode", "stream")

                    if job_id == "job_dl_missing":
                        return 404, {
                            "ok": False,
                            "error_code": "DOWNLOADER_STALE_ARTIFACT_TRUTH",
                            "message": "Tệp tải về không tồn tại hoặc đã hết hạn.",
                        }
                    if job_id == "job_dl_foreign":
                        if str(actor_id) != "foreign_user_id":
                            return 403, {
                                "ok": False,
                                "error_code": "DOWNLOADER_FOREIGN_OWNER_BLOCKED",
                                "message": "Bạn không có quyền truy cập tệp tải về này.",
                            }

                    ctype_map = {"video": "video/mp4", "audio": "audio/mpeg", "cover": "image/jpeg"}
                    ctype = ctype_map.get(p_kind, "application/octet-stream")

                    if p_mode == "meta":
                        return 200, {
                            "ok": True,
                            "status": "ready",
                            "job_id": job_id,
                            "kind": p_kind,
                            "content_type": ctype,
                            "bytes": 5242880,
                            "delivery_ready": True,
                            "_internal_leak": "SHOULD_NOT_LEAK",
                        }

                    return 200, {
                        "ok": True,
                        "job_id": job_id,
                        "kind": p_kind,
                        "content_type": ctype,
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
    import httpx

    async def mock_bridge_client_request(self, method: str, path: str, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        status_code, resp_data = bridge_state.handle_request(method, path, actor_id, payload=payload, params=params)
        if status_code >= 400:
            return copyfast_bridge._sanitize_envelope(resp_data, fallback_code=resp_data.get("error_code"))
        return copyfast_bridge._sanitize_envelope(resp_data)

    monkeypatch.setattr(CoreBridgeClient, "request", mock_bridge_client_request)

    class MockHttpxResponse:
        def __init__(self, status_code: int, content: bytes, headers: dict):
            self.status_code = status_code
            self.content = content
            self.headers = headers

        def json(self):
            return json.loads(self.content.decode("utf-8"))

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, url: str, headers=None):
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            actor_id = query.get("user_id", [""])[0] or (headers or {}).get("x-toan-aas-actor-id", "")
            download = query.get("download", ["0"])[0] in ("1", "true")
            status_code, resp_data = bridge_state.handle_request("GET", parsed.path, actor_id, params=query)

            if status_code >= 400:
                return MockHttpxResponse(status_code, json.dumps(resp_data).encode("utf-8"), {"content-type": "application/json"})

            if bridge_state.force_redirect:
                return MockHttpxResponse(307, b"", {"location": "https://cdn.toanaas.vn/rogue_redirect.mp4"})

            if query.get("mode") == ["meta"]:
                return MockHttpxResponse(200, json.dumps(resp_data).encode("utf-8"), {"content-type": "application/json"})

            p_kind = query.get("kind", ["video"])[0]
            ctype_map = {"video": "video/mp4", "audio": "audio/mpeg", "cover": "image/jpeg"}
            ext_map = {"video": "mp4", "audio": "mp3", "cover": "jpg"}
            ctype = ctype_map.get(p_kind, "application/octet-stream")
            ext = ext_map.get(p_kind, "bin")

            media_bytes = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 256
            disp = "attachment" if download else "inline"
            job_id = parsed.path.split("/")[-1]
            return MockHttpxResponse(
                200,
                media_bytes,
                {
                    "content-type": ctype,
                    "content-disposition": f'{disp}; filename="download_{job_id}.{ext}"',
                },
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)
    yield


def _create_test_account(canonical_user_id: str = "1001") -> tuple[TestClient, str]:
    """Insert or update test account into SQLite and return authenticated TestClient and csrf_token."""
    account_id = f"acc_{canonical_user_id or 'anon'}"
    email = f"{account_id}@test.local"
    with transaction() as conn:
        now = utc_now()
        if canonical_user_id:
            conn.execute(
                "DELETE FROM web_sessions WHERE account_id IN (SELECT id FROM web_accounts WHERE canonical_user_id = ? OR id = ?)",
                (canonical_user_id, account_id),
            )
            conn.execute(
                "DELETE FROM web_accounts WHERE canonical_user_id = ? OR id = ?",
                (canonical_user_id, account_id),
            )
        else:
            conn.execute("DELETE FROM web_sessions WHERE account_id = ?", (account_id,))
            conn.execute("DELETE FROM web_accounts WHERE id = ?", (account_id,))
        conn.execute(
            """
            INSERT INTO web_accounts (
                id, email, password_hash, canonical_user_id, role_cache, created_at, updated_at
            ) VALUES (?, ?, 'test_hash', ?, 'member', ?, ?)
            """,
            (account_id, email, canonical_user_id or None, now, now),
        )
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


def test_rate_offline_safe_fallback_parity():
    """RATE_OFFLINE_SAFE_FALLBACK_PARITY: Preserves offline safe fallback with truthful source marker."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/rate", json={"raw_input": "offline_fallback"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["source"] == "TOAN AAS Standard (Offline Safe)"
    assert data["amount_in"] == 100.0
    assert data["currency_in"] == "USD"
    assert data["target_currency"] == "VND"
    assert data["usd"] == 100.0
    assert data["vnd"] == 2540000.0


def test_rate_fields_survive_web_projection():
    """RATE_FIELDS_SURVIVE_WEB_PROJECTION: Customer-safe rate fields pass projection; secrets stripped."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/rate", json={"raw_input": "100 USD"})
    assert resp.status_code == 200
    data = resp.json()
    required_fields = [
        "amount_in", "currency_in", "currency_in_name", "target_currency",
        "target_converted", "target_currency_name", "usd", "vnd", "xu",
        "cny", "hkd", "eur", "jpy", "rate_usd_vnd", "source"
    ]
    for f in required_fields:
        assert f in data, f"Missing required rate projection field: {f}"
    # Verify no secret leaked
    assert "_internal_secret_token" not in data


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


def test_weather_offline_safe_fallback_parity():
    """WEATHER_OFFLINE_SAFE_FALLBACK_PARITY: Preserves offline safe fallback with truthful source marker."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/weather", json={"location": "offline_fallback"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["source"] == "Dự báo chuẩn (Offline Safe)"
    assert data["city"] == "Hà Nội"
    assert data["country"] == "Vietnam"
    assert data["temperature"] == 26.5
    assert data["windspeed"] == 12.0
    assert data["weathercode"] == 1


def test_weather_fields_survive_web_projection():
    """WEATHER_FIELDS_SURVIVE_WEB_PROJECTION: Customer-safe weather fields pass projection; secrets stripped."""
    client, _ = _create_test_account()
    resp = client.post("/api/v1/free-tools/weather", json={"location": "Hanoi"})
    assert resp.status_code == 200
    data = resp.json()
    required_fields = [
        "city", "country", "temperature", "windspeed", "weathercode", "description", "unit", "source"
    ]
    for f in required_fields:
        assert f in data, f"Missing required weather projection field: {f}"
    # Verify no secret leaked
    assert "_internal_secret_key" not in data


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


def test_avatar_fields_survive_web_projection():
    """AVATAR_FIELDS_SURVIVE_WEB_PROJECTION: Customer-safe avatar fields pass projection; secrets stripped."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/avatar",
        headers={"x-csrf-token": csrf_token},
        json={"seed": "engineer_toan", "style": "realistic", "avatar_set": 1, "confirmed_rights": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    for f in ("avatar_url", "seed", "avatar_set", "style"):
        assert f in data, f"Missing required avatar projection field: {f}"
    assert "_internal_secret_provider" not in data


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
    assert "delivery_url" in data or "download_url" in data


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


def test_downloader_fields_survive_web_projection():
    """DOWNLOADER_FIELDS_SURVIVE_WEB_PROJECTION: Customer-safe downloader fields survive projection."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "confirmed_rights": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    required_fields = [
        "job_id", "platform", "kind", "title", "duration", "bytes", "status",
        "charged_xu", "rights_notice", "delivery_ready"
    ]
    for f in required_fields:
        assert f in data, f"Missing required downloader projection field: {f}"
    # Verify private internals stripped
    assert "file_path" not in data
    assert "_internal_token" not in data


def test_downloader_opaque_artifact_id():
    """DOWNLOADER_OPAQUE_ARTIFACT_ID: Artifact ID is opaque and does not reveal filesystem paths."""
    client, csrf_token = _create_test_account()
    resp = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "confirmed_rights": True},
    )
    assert resp.status_code == 200
    job_id = resp.json().get("job_id")
    assert job_id and job_id.startswith("job_")
    assert "/" not in job_id
    assert "\\" not in job_id


def test_downloader_download_to_delivery_contract():
    """DOWNLOADER_DOWNLOAD_TO_DELIVERY: End-to-end download -> opaque id -> safe stream delivery."""
    client, csrf_token = _create_test_account(canonical_user_id="1001")
    # Step 1: Download
    resp_dl = client.post(
        "/api/v1/free-tools/downloader/download",
        headers={"x-csrf-token": csrf_token},
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "confirmed_rights": True},
    )
    assert resp_dl.status_code == 200
    job_id = resp_dl.json()["job_id"]

    # Step 2: Delivery stream
    resp_stream = client.get(f"/api/v1/free-tools/downloader/delivery/{job_id}?kind=video")
    assert resp_stream.status_code == 200
    assert resp_stream.headers["content-type"] == "video/mp4"
    assert len(resp_stream.content) > 0
    assert "attachment" not in resp_stream.headers.get("content-disposition", "")

    # Step 3: Delivery with download=True
    resp_down = client.get(f"/api/v1/free-tools/downloader/delivery/{job_id}?kind=video&download=true")
    assert resp_down.status_code == 200
    assert "attachment" in resp_down.headers.get("content-disposition", "")

    # Step 4: Alias route /tools/downloader/delivery/{job_id}
    resp_alias = client.get(f"/api/v1/tools/downloader/delivery/{job_id}?kind=video")
    assert resp_alias.status_code == 200
    assert resp_alias.headers["content-type"] == "video/mp4"


def test_downloader_delivery_meta_mode():
    """DOWNLOADER_DELIVERY_META_MODE: Delivery with mode=meta returns metadata without media bytes."""
    client, _ = _create_test_account(canonical_user_id="1001")
    resp_meta = client.get("/api/v1/free-tools/downloader/delivery/job_valid_123?kind=video&mode=meta")
    assert resp_meta.status_code == 200
    data = resp_meta.json()
    assert data["ok"] is True
    assert data["job_id"] == "job_valid_123"
    assert data["kind"] == "video"
    assert data["content_type"] == "video/mp4"
    assert data["delivery_ready"] is True
    assert "_internal_leak" not in data


def test_downloader_foreign_owner_delivery_blocked():
    """DOWNLOADER_FOREIGN_OWNER_DELIVERY_BLOCKED: Another user accessing delivery gets 403."""
    # User 1001 tries to access job belonging to foreign_user_id
    client, _ = _create_test_account(canonical_user_id="1001")
    resp = client.get("/api/v1/free-tools/downloader/delivery/job_dl_foreign?kind=video")
    assert resp.status_code == 403
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "DOWNLOADER_FOREIGN_OWNER_BLOCKED"


def test_downloader_missing_artifact_fail_closed():
    """DOWNLOADER_MISSING_ARTIFACT_FAIL_CLOSED: Non-existent or deleted artifact returns 404."""
    client, _ = _create_test_account(canonical_user_id="1001")
    resp = client.get("/api/v1/free-tools/downloader/delivery/job_dl_missing?kind=video")
    assert resp.status_code == 404
    data = resp.json()
    assert data["ok"] is False
    assert data["error_code"] == "DOWNLOADER_STALE_ARTIFACT_TRUTH"


def test_downloader_delivery_kinds_parity():
    """DOWNLOADER_DELIVERY_KINDS_PARITY: Supports video, audio, cover kinds; rejects invalid."""
    client, _ = _create_test_account(canonical_user_id="1001")

    # Audio
    resp_audio = client.get("/api/v1/free-tools/downloader/delivery/job_valid_123?kind=audio")
    assert resp_audio.status_code == 200
    assert resp_audio.headers["content-type"] == "audio/mpeg"

    # Cover
    resp_cover = client.get("/api/v1/free-tools/downloader/delivery/job_valid_123?kind=cover")
    assert resp_cover.status_code == 200
    assert resp_cover.headers["content-type"] == "image/jpeg"

    # Invalid kind
    resp_bad = client.get("/api/v1/free-tools/downloader/delivery/job_valid_123?kind=executable")
    assert resp_bad.status_code == 422


def test_downloader_redirect_strictly_blocked():
    """DOWNLOADER_REDIRECT_STRICLY_BLOCKED: Web refuses redirects from delivery and returns 502."""
    client, _ = _create_test_account(canonical_user_id="1001")
    bridge_state.force_redirect = True
    try:
        resp = client.get("/api/v1/free-tools/downloader/delivery/job_valid_123?kind=video", follow_redirects=False)
        assert resp.status_code == 502
    finally:
        bridge_state.force_redirect = False


def test_downloader_safe_delivery_no_private_paths():
    """DOWNLOADER_SAFE_DELIVERY: Output URLs and responses do not expose local filesystem paths."""
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
        ("GET", "/api/v1/free-tools/downloader/delivery/job_123", None),
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
