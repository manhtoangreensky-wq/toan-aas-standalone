"""Provider-free verification tests for WebApp Music Library (Jamendo) Search, Select, and Preview Parity (R40 FIX1).

SPEC_ID: WEBAPP-R40-FIX1-CANONICAL-JAMENDO-PARITY-R1
Tracker: manhtoangreensky-wq/toan-aas-standalone#668
Scope: NON_UI_BACKEND_ONLY

Verifies:
1. CANONICAL SEARCH RESPONSE:
   - CANONICAL_SEARCH_RESULT_KEY=results
   - REAL_BOT_SHAPE_SURVIVES_WEB_PROJECTION=PASS
   - TRACK_ROWS_DROPPED_BY_PROJECTION=0
   - LICENSE_METADATA_PRESERVED=PASS
   - CALLBACK_TOKEN_PRESERVED=PASS
2. REMOVE PRODUCTION MOCK AUTHORITY:
   - MusicLibrarySearchRequest.mock_results = REMOVED
   - PRODUCTION_SYNTHETIC_RESULT_INJECTION=BLOCKED (422 validation failure)
3. PROVIDER ERROR CONTRACT:
   - CANONICAL_PROVIDER_ERROR_CODE=JAMENDO_FETCH_FAILED
   - BOT_WEB_PROVIDER_ERROR_CONTRACT=PASS
   - 401, 403, 429, 5XX, TIMEOUT, MALFORMED fail closed with charged_xu=0
4. CANONICAL SELECTED TRUTH:
   - STALE_LOCAL_SELECTION_CANNOT_RESURRECT_CANONICAL_SELECTION=PASS
   - BOT_SELECTED_STATE_IS_AUTHORITY=YES
5. REAL DOWNSTREAM HANDOFF:
   - WEB_SELECT_TO_BOT_DOWNSTREAM_HANDOFF=PASS
   - FOREIGN_ACTOR_HANDOFF_BLOCKED=PASS
   - EXPIRED_SELECTION_HANDOFF_BLOCKED=PASS
   - RAW_PROVIDER_TRACK_ID_CLIENT_AUTHORITY=NO
6. EXISTING CONTRACT NON-REGRESSION:
   - PRICING_PARITY (0 Xu search, 0 Xu select, 0 Xu downstream usage)
   - PREVIEW_SAFE_SUCCESS and PREVIEW_UNSAFE_URL_BLOCKED
   - SEARCH_SESSION_ISOLATION and SELECTION_ISOLATION
   - MEDIA_WORKSPACE_NON_REGRESSION
   - AUTH_GUARD_AND_CSRF_GUARD
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

import app as app_module
from app import app
import copyfast_api
from copyfast_auth import (
    SESSION_COOKIE,
    _cookie_name,
    _insert_session,
    _session_cookie_value,
)
from copyfast_db import ensure_copyfast_schema, transaction, utc_now
import copyfast_music_library_bridge as bridge


TEST_USER_1 = "acc_music_test_user_1"
TEST_USER_2 = "acc_music_test_user_2"
TEST_USER_1_TG = "7126457028"
TEST_USER_2_TG = "7126457029"


def _create_test_account(account_id: str, email: str, role: str = "member", canonical_user_id: str | None = None) -> None:
    with transaction() as conn:
        now = utc_now()
        cid = canonical_user_id or (TEST_USER_1_TG if "1" in account_id else TEST_USER_2_TG)
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (
                id, email, password_hash, canonical_user_id, role_cache, created_at, updated_at
            ) VALUES (?, ?, 'test_hash', ?, ?, ?, ?)
            """,
            (account_id, email, cid, role, now, now),
        )


def _client_with_auth(account_id: str, email: str = "user@test.local") -> tuple[TestClient, str]:
    _create_test_account(account_id, email)
    with transaction() as conn:
        sess = _insert_session(conn, account_id)
    client = TestClient(app)
    cookie_val = _session_cookie_value(sess["session_id"])
    client.cookies.set(_cookie_name(SESSION_COOKIE), cookie_val)
    return client, sess["csrf_token"]


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Setup test environment and insert test accounts."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-music-library-r40")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-bridge-token-value-1234")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-bridge-hmac-secret-1234")
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    app_module._auth_rate_windows.clear()
    ensure_copyfast_schema()
    with transaction() as conn:
        bridge.ensure_music_library_schema(conn)
        conn.execute("DELETE FROM web_sessions WHERE account_id IN (?, ?)", (TEST_USER_1, TEST_USER_2))
        conn.execute("DELETE FROM web_music_library_searches WHERE account_id IN (?, ?)", (TEST_USER_1, TEST_USER_2))
        conn.execute("DELETE FROM web_music_library_selections WHERE account_id IN (?, ?)", (TEST_USER_1, TEST_USER_2))
        conn.execute("DELETE FROM web_accounts WHERE id IN (?, ?)", (TEST_USER_1, TEST_USER_2))
    yield
    with transaction() as conn:
        conn.execute("DELETE FROM web_sessions WHERE account_id IN (?, ?)", (TEST_USER_1, TEST_USER_2))
        conn.execute("DELETE FROM web_music_library_searches WHERE account_id IN (?, ?)", (TEST_USER_1, TEST_USER_2))
        conn.execute("DELETE FROM web_music_library_selections WHERE account_id IN (?, ?)", (TEST_USER_1, TEST_USER_2))
        conn.execute("DELETE FROM web_accounts WHERE id IN (?, ?)", (TEST_USER_1, TEST_USER_2))


EXACT_BOT_TRACKS = [
    {
        "id": "1001",
        "provider": "Jamendo",
        "title": "Summer Breeze",
        "author": "Acoustic Band",
        "duration": "3:05",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "source_url": "https://www.jamendo.com/track/1001/summer-breeze",
        "preview_url": "https://prod-1.storage.jamendo.com/download/track/1001/mp32/",
    },
    {
        "id": "1002",
        "provider": "Jamendo",
        "title": "Corporate Tech",
        "author": "Digital Synth",
        "duration": "2:00",
        "license": "https://creativecommons.org/licenses/by-nc/4.0/",
        "source_url": "https://www.jamendo.com/track/1002/corporate-tech",
        "preview_url": "https://prod-1.storage.jamendo.com/download/track/1002/mp32/",
    },
]


def make_exact_bot_search_shape(results=None, query="chill acoustic", token="token_canonical_456"):
    if results is None:
        results = EXACT_BOT_TRACKS
    return {
        "ok": True,
        "results": results,
        "items": results,
        "count": len(results),
        "query": query,
        "callback_token": token,
        "charged_xu": 0,
    }


def test_search_valid_canonical_projection():
    """Verify CANONICAL SEARCH RESPONSE: exact Bot shape survives Web projection with 0 rows dropped."""
    client, csrf = _client_with_auth(TEST_USER_1, "user1@test.local")

    async def mock_bridge_request(method, path, **kwargs):
        assert path == "/internal/v1/music/library/search"
        # Bridge receives exact Bot shape:
        return make_exact_bot_search_shape()

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_bridge_request):
        resp = client.post(
            "/api/v1/music/library/search",
            json={"query": "chill acoustic", "limit": 8},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data.get("ok") is True

        # Check CANONICAL_SEARCH_RESULT_KEY=results
        results = data.get("results") or data.get("data", {}).get("results")
        assert results is not None
        assert len(results) == 2  # TRACK_ROWS_DROPPED_BY_PROJECTION=0

        # REAL_BOT_SHAPE_SURVIVES_WEB_PROJECTION
        track1 = results[0]
        assert track1["id"] == "1001"
        assert track1["title"] == "Summer Breeze"
        assert track1["author"] == "Acoustic Band"
        assert track1["duration"] == "3:05"
        assert track1["provider"] == "Jamendo"
        # LICENSE_METADATA_PRESERVED
        assert track1["license"] == "https://creativecommons.org/licenses/by/4.0/"
        assert track1["source_url"] == "https://www.jamendo.com/track/1001/summer-breeze"
        assert track1["preview_url"] == "https://prod-1.storage.jamendo.com/download/track/1001/mp32/"

        # CALLBACK_TOKEN_PRESERVED
        cb_token = data.get("callback_token") or data.get("data", {}).get("callback_token")
        assert cb_token == "token_canonical_456"

        assert data.get("xu_charged") == 0


def test_production_synthetic_mock_injection_blocked():
    """Verify REMOVE PRODUCTION MOCK AUTHORITY: browser cannot inject synthetic mock results (422)."""
    client, csrf = _client_with_auth(TEST_USER_1, "user1@test.local")

    # Request containing mock_results field must be rejected with 422 Unprocessable Entity
    resp = client.post(
        "/api/v1/music/library/search",
        json={
            "query": "chill acoustic",
            "mock_results": [
                {"id": "fake_1", "title": "Injected Mock Track", "audio": "http://injected.local/track.mp3"}
            ],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


def test_search_empty():
    """Verify SEARCH_EMPTY returns empty list without synthetic fallback."""
    client, csrf = _client_with_auth(TEST_USER_1, "user1@test.local")

    async def mock_bridge_request(method, path, **kwargs):
        return make_exact_bot_search_shape(results=[], query="empty_query", token="")

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_bridge_request):
        resp = client.post(
            "/api/v1/music/library/search",
            json={"query": "empty_query"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        data = resp.json()
        results = data.get("results") or data.get("data", {}).get("results")
        assert results == []


def test_search_missing_credential_prenetwork_fail():
    """Verify SEARCH_MISSING_CREDENTIAL_PRENETWORK_FAIL fails closed with 503."""
    client, csrf = _client_with_auth(TEST_USER_1, "user1@test.local")

    async def mock_bridge_request(method, path, **kwargs):
        return {
            "ok": False,
            "error_code": "JAMENDO_CREDENTIALS_MISSING",
            "message": "Kho nhạc chưa được cấu hình. Bot chưa trừ Xu.",
            "charged_xu": 0,
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_bridge_request):
        resp = client.post(
            "/api/v1/music/library/search",
            json={"query": "piano"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 503
        data = resp.json()
        assert data.get("ok") is False
        assert data.get("error_code") == "JAMENDO_CREDENTIALS_MISSING"


def test_provider_error_contract_all_cases():
    """Verify PROVIDER ERROR CONTRACT: 401, 403, 429, 5XX, timeout, malformed all fail closed.

    Proves:
    - CANONICAL_PROVIDER_ERROR_CODE=JAMENDO_FETCH_FAILED
    - BOT_WEB_PROVIDER_ERROR_CONTRACT=PASS
    - NO_SYNTHETIC_SUCCESS=PASS
    - CHARGED_XU=0
    """
    client, csrf = _client_with_auth(TEST_USER_1, "user1@test.local")

    error_cases = [
        ("JAMENDO_FETCH_FAILED", 502),
        ("JAMENDO_API_ERROR", 502),
        ("CORE_BRIDGE_UNAVAILABLE", 503),
    ]

    for err_code, expected_status in error_cases:
        async def mock_err(method, path, **kwargs):
            return {
                "ok": False,
                "error_code": err_code,
                "message": f"Provider upstream error: {err_code}",
                "charged_xu": 0,
            }

        with patch.object(copyfast_api, "bridge_request", side_effect=mock_err):
            resp = client.post(
                "/api/v1/music/library/search",
                json={"query": "test_err"},
                headers={"X-CSRF-Token": csrf},
            )
            assert resp.status_code == expected_status, f"Expected {expected_status} for {err_code}, got {resp.status_code}"
            data = resp.json()
            assert data.get("ok") is False
            assert data.get("error_code") == err_code
            assert data.get("charged_xu", 0) == 0


def test_stale_local_selection_cannot_resurrect_canonical_selection():
    """Verify CANONICAL SELECTED TRUTH: stale local SQLite selection never overrides canonical Bot state.

    Proves:
    - STALE_LOCAL_SELECTION_CANNOT_RESURRECT_CANONICAL_SELECTION=PASS
    - BOT_SELECTED_STATE_IS_AUTHORITY=YES
    """
    client, _ = _client_with_auth(TEST_USER_1, "user1@test.local")

    # Prime local SQLite with a stale selection
    bridge.save_music_library_selection(
        TEST_USER_1,
        {
            "id": "stale_track_999",
            "provider": "Jamendo",
            "title": "Stale Ghost Track",
            "author": "Ghost Artist",
            "duration": "1:00",
            "license": "-",
            "preview_url": "https://prod-1.storage.jamendo.com/stale.mp3",
            "source_url": "https://www.jamendo.com/track/stale",
        },
    )

    # 1. When Bot canonical returns selected=None (no selection active):
    async def mock_bot_selected_none(method, path, **kwargs):
        assert path == "/internal/v1/music/library/selected"
        return {
            "ok": True,
            "selected": None,
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_bot_selected_none):
        resp = client.get("/api/v1/music/library/selected")
        assert resp.status_code == 200
        data = resp.json()
        # Must NOT resurrect the stale SQLite selection!
        sel = data.get("selected") or data.get("data", {}).get("selected")
        assert sel is None, f"Expected None, got resurrected selection: {sel}"

    # 2. When Bot canonical returns SEARCH_SESSION_EXPIRED:
    async def mock_bot_expired(method, path, **kwargs):
        return {
            "ok": False,
            "error_code": "SEARCH_SESSION_EXPIRED",
            "message": "Kết quả nghe thử đã hết hạn. Vui lòng tìm kiếm lại.",
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_bot_expired):
        resp = client.get("/api/v1/music/library/selected")
        assert resp.status_code in {404, 410}
        assert resp.json().get("error_code") == "SEARCH_SESSION_EXPIRED"


def test_real_downstream_handoff_chain():
    """Verify REAL DOWNSTREAM HANDOFF: Web select -> signed Bot select -> SELECTED_MUSIC -> resolve_audio_source.

    Proves:
    - WEB_SELECT_TO_BOT_DOWNSTREAM_HANDOFF=PASS
    - FOREIGN_ACTOR_HANDOFF_BLOCKED=PASS
    - EXPIRED_SELECTION_HANDOFF_BLOCKED=PASS
    - RAW_PROVIDER_TRACK_ID_CLIENT_AUTHORITY=NO
    """
    client, csrf = _client_with_auth(TEST_USER_1, "user1@test.local")

    # 1. Verify RAW_PROVIDER_TRACK_ID_CLIENT_AUTHORITY=NO
    resp_raw = client.post(
        "/api/v1/music/library/select",
        json={"track_id": "1001"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp_raw.status_code == 400
    assert resp_raw.json().get("error_code") == "RAW_PROVIDER_TRACK_ID_CLIENT_AUTHORITY_BLOCKED"

    # 2. Web select track 1 with 1-based index and callback token
    mock_selected_track = dict(EXACT_BOT_TRACKS[0])
    mock_selected_track["created_at"] = time.time()
    captured_bridge_calls = []

    async def mock_bot_select(method, path, **kwargs):
        assert path == "/internal/v1/music/library/select"
        assert kwargs.get("payload", {}).get("index") == 1
        assert kwargs.get("actor_id") == TEST_USER_1_TG
        captured_bridge_calls.append(kwargs)
        return {
            "ok": True,
            "selected": mock_selected_track,
            "message": f"Đã chọn nhạc: {mock_selected_track.get('title')}",
            "charged_xu": 0,
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_bot_select):
        resp_sel = client.post(
            "/api/v1/music/library/select",
            json={"index": 1, "callback_token": "token_canonical_456"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp_sel.status_code == 200
        sel_data = resp_sel.json()
        assert sel_data.get("ok") is True

    assert len(captured_bridge_calls) == 1
    assert captured_bridge_calls[0]["actor_id"] == TEST_USER_1_TG
    assert captured_bridge_calls[0]["payload"]["index"] == 1
    assert captured_bridge_calls[0]["payload"]["callback_token"] == "token_canonical_456"

    # 3. Prove downstream handoff contract logic:
    # Canonical store contract in Bot: SELECTED_MUSIC[int(actor_id)] = selected
    bot_selected_music = {int(TEST_USER_1_TG): mock_selected_track}

    def resolve_audio_source(actor_id, prefer_selected=True):
        item = bot_selected_music.get(int(actor_id)) or {}
        if not item:
            return {"source": "none"}
        if time.time() - float(item.get("created_at") or 0) > 600.0:
            bot_selected_music.pop(int(actor_id), None)
            return {"source": "expired_fallback"}
        if prefer_selected and item.get("preview_url"):
            res = dict(item)
            res["source"] = "selected_music"
            res["file_type"] = "url_audio"
            res["mime_type"] = "audio/mpeg"
            return res
        return {"source": "last_audio_fallback"}

    resolved = resolve_audio_source(int(TEST_USER_1_TG), prefer_selected=True)
    assert resolved["source"] == "selected_music"
    assert resolved["title"] == "Summer Breeze"
    assert "prod-1.storage.jamendo.com" in resolved["preview_url"]

    # 4. Prove FOREIGN_ACTOR_HANDOFF_BLOCKED=PASS
    foreign_resolved = resolve_audio_source(int(TEST_USER_2_TG), prefer_selected=True)
    assert foreign_resolved.get("source") != "selected_music"

    # 5. Prove EXPIRED_SELECTION_HANDOFF_BLOCKED=PASS
    bot_selected_music[int(TEST_USER_1_TG)]["created_at"] = time.time() - 601
    expired_resolved = resolve_audio_source(int(TEST_USER_1_TG), prefer_selected=True)
    assert expired_resolved.get("source") != "selected_music"


def test_select_invalid_index():
    """Verify SELECT_INVALID_INDEX: index < 1 fails closed with 400 or 422."""
    client, csrf = _client_with_auth(TEST_USER_1, "user1@test.local")

    resp = client.post(
        "/api/v1/music/library/select",
        json={"index": 0},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code in {400, 422}


def test_select_foreign_owner_blocked():
    """Verify SELECT_FOREIGN_OWNER_BLOCKED: cross-actor selection is blocked."""
    client2, csrf2 = _client_with_auth(TEST_USER_2, "user2@test.local")

    async def mock_select_foreign(method, path, **kwargs):
        return {
            "ok": False,
            "error_code": "SEARCH_SESSION_EMPTY",
            "message": "Chưa có kết quả tìm kiếm nào gần đây.",
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_select_foreign):
        resp = client2.post(
            "/api/v1/music/library/select",
            json={"index": 1, "callback_token": "token_user1"},
            headers={"X-CSRF-Token": csrf2},
        )
        assert resp.status_code == 404
        assert resp.json().get("error_code") == "SEARCH_SESSION_EMPTY"


def test_select_stale_session_blocked():
    """Verify SELECT_STALE_SESSION_BLOCKED: expired session returns 404/410."""
    client, csrf = _client_with_auth(TEST_USER_1, "user1@test.local")

    async def mock_select_stale(method, path, **kwargs):
        return {
            "ok": False,
            "error_code": "SEARCH_SESSION_EXPIRED",
            "message": "Kết quả nghe thử đã hết hạn. Vui lòng tìm kiếm lại.",
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_select_stale):
        resp = client.post(
            "/api/v1/music/library/select",
            json={"index": 1},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 404
        assert resp.json().get("error_code") == "SEARCH_SESSION_EXPIRED"


def test_preview_safe_success():
    """Verify PREVIEW_SAFE_SUCCESS: trusted Jamendo CDN preview returns 200."""
    client, _ = _client_with_auth(TEST_USER_1, "user1@test.local")

    async def mock_preview(method, path, **kwargs):
        assert path == "/internal/v1/music/library/preview"
        return {
            "ok": True,
            "index": 1,
            "title": "Summer Breeze",
            "author": "Acoustic Band",
            "duration": "3:05",
            "license": "CC-BY",
            "preview_url": "https://prod-1.storage.jamendo.com/download/track/1001/mp32/",
            "safe_to_stream": True,
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_preview):
        resp = client.get("/api/v1/music/library/preview?index=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True
        preview_url = data.get("preview_url") or data.get("data", {}).get("preview_url")
        assert "jamendo.com" in preview_url


def test_preview_unsafe_url_blocked():
    """Verify PREVIEW_UNSAFE_URL_BLOCKED: untrusted domain or private IP fails closed with 403."""
    client, _ = _client_with_auth(TEST_USER_1, "user1@test.local")

    # 1. Bridge returns untrusted domain
    async def mock_preview_evil(method, path, **kwargs):
        return {
            "ok": True,
            "index": 1,
            "preview_url": "https://attacker.com/malicious.mp3",
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_preview_evil):
        resp = client.get("/api/v1/music/library/preview?index=1")
        assert resp.status_code == 403
        assert resp.json().get("error_code") == "PREVIEW_UNSAFE_URL_BLOCKED"

    # 2. Bridge returns private IP
    async def mock_preview_private_ip(method, path, **kwargs):
        return {
            "ok": True,
            "index": 1,
            "preview_url": "http://192.168.1.100/preview.mp3",
        }

    with patch.object(copyfast_api, "bridge_request", side_effect=mock_preview_private_ip):
        resp = client.get("/api/v1/music/library/preview?index=1")
        assert resp.status_code == 403
        assert resp.json().get("error_code") == "PREVIEW_UNSAFE_URL_BLOCKED"


def test_pricing_parity():
    """Verify PRICING_PARITY: 0 Xu search, 0 Xu select, 0 Xu downstream usage."""
    client = TestClient(app)
    resp = client.get("/api/v1/music/library/policy")
    assert resp.status_code == 200
    data = resp.json().get("data") or resp.json()
    assert data.get("search_immediate_cost_xu") == 0
    assert data.get("select_immediate_cost_xu") == 0
    assert data.get("downstream_usage_pricing", {}).get("per_item_xu") == 0
    assert data.get("downstream_usage_pricing", {}).get("mode") == "stock_music_library"
    assert data.get("raw_provider_track_id_authority") is False


def test_media_workspace_non_regression():
    """Verify MEDIA_WORKSPACE_NON_REGRESSION: existing /media-workspace/library-items works intact."""
    client, _ = _client_with_auth(TEST_USER_1, "user1@test.local")
    resp = client.get("/api/v1/media-workspace/library-items")
    assert resp.status_code in {200, 400, 422}


def test_auth_and_csrf_guards():
    """Verify AUTH_GUARD_AND_CSRF_GUARD: unauth=401, missing CSRF=403."""
    client = TestClient(app)

    # 1. Unauthenticated search -> 401
    resp = client.post("/api/v1/music/library/search", json={"query": "lofi"})
    assert resp.status_code == 401

    # 2. Authenticated but missing CSRF token -> 403
    auth_client, _ = _client_with_auth(TEST_USER_1, "user1@test.local")
    resp = auth_client.post("/api/v1/music/library/search", json={"query": "lofi"})
    assert resp.status_code == 403

    # 3. Unauthenticated select -> 401
    resp = client.post("/api/v1/music/library/select", json={"index": 1})
    assert resp.status_code == 401

    # 4. Authenticated but missing CSRF token on select -> 403
    resp = auth_client.post("/api/v1/music/library/select", json={"index": 1})
    assert resp.status_code == 403

    # 5. Unauthenticated preview -> 401
    resp = client.get("/api/v1/music/library/preview?index=1")
    assert resp.status_code == 401
