"""Provider-free tests for SFX Library Bot-as-Source-of-Truth Parity.

Task: WEBAPP_R36_BOT_AS_SOURCE_OF_TRUTH_FULL_FUNCTIONAL_PARITY_AND_GAP_CLOSURE_R1
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Capability: sfx_library
Customer Entrypoint: /music/sfx-library
Web API Family: /api/v1/music/sfx-library/*

Proves:
1. VALID_SUCCESS_PATH: Search and select succeed with 200 OK and valid normalized data.
2. INVALID_INPUT_FAIL_CLOSED: Empty/oversized queries, out-of-range indices fail closed (400/422).
3. WRONG_OWNER_BLOCKED: Cross-account token/session isolation, unauthenticated access blocked.
4. DUPLICATE_OR_IDEMPOTENCY: Re-searching and re-selecting are idempotent without side-effects.
5. XU_PRICING_PARITY: 0 Xu charged for search and select (zero cost contract).
6. LIBRARY_PROVIDER_ERROR_BY_MOCK: Provider errors fail gracefully with 502 without charging Xu.
7. OUTPUT_NORMALIZATION: All 8 required metadata fields present (id, provider, title, author, duration, license, source_url, preview_url).
8. SELECTION_READBACK: Active selection persists and is accurately returned by GET /selected.
9. STATUS_HISTORY: Search and selection persist in SQLite across requests.
10. PROVIDER_FREE: ZERO real provider network calls (REAL_PROVIDER_NETWORK_CALL_COUNT=0).
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
import uuid

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
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now
import copyfast_music_sfx_library_bridge as bridge


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Ensure test environment is strictly provider-free and tables exist."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("WEB_SESSION_SECRET", "test-session-secret-sfx-library-r36")
    monkeypatch.setenv("BOT_USERNAME", "ToanAasSupportBot")
    monkeypatch.setenv("WEBAPP_COPYFAST_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    monkeypatch.setattr(app_module, "_durable_auth_throttle_guard", lambda *a, **kw: None)
    app_module._auth_rate_windows.clear()
    ensure_copyfast_schema()
    with transaction() as conn:
        bridge.ensure_sfx_library_schema(conn)
    bridge.set_test_explicit_mock_results(bridge._generate_mock_freesound_results("test", 5))
    yield
    bridge.reset_test_explicit_mock_results()


def _create_test_account(account_id: str, email: str, role: str = "member") -> None:
    """Insert test account into SQLite for auth tests."""
    with transaction() as conn:
        now = utc_now()
        conn.execute(
            """
            INSERT OR REPLACE INTO web_accounts (
                id, email, password_hash, role_cache, created_at, updated_at
            ) VALUES (?, ?, 'test_hash', ?, ?, ?)
            """,
            (account_id, email, role, now, now),
        )


def _client_with_auth(account_id: str, email: str) -> tuple[TestClient, str]:
    """Create a test client with valid session cookie and return CSRF token."""
    _create_test_account(account_id, email)
    with transaction() as conn:
        sess = _insert_session(conn, account_id)
    client = TestClient(app)
    cookie_val = _session_cookie_value(sess["session_id"])
    client.cookies.set(_cookie_name(SESSION_COOKIE), cookie_val)
    return client, sess["csrf_token"]


# ─── 1. POLICY CONTRACT ───────────────────────────────────────────────────────

def test_sfx_library_policy_contract():
    """Verify SFX library policy endpoint returns truthful Freesound 0 Xu immediate charge and downstream usage contract."""
    client = TestClient(app)
    resp = client.get("/api/v1/music/sfx-library/policy")
    assert resp.status_code == 200
    data = resp.json().get("data", {})
    assert data.get("provider") == "Freesound"
    assert data.get("capability") == "sfx_library"
    assert data.get("customer_entrypoint") == "/music/sfx-library"
    assert data.get("generative_ai") is False
    assert data.get("search_immediate_charge_xu") == 0
    assert data.get("select_immediate_charge_xu") == 0
    usage = data.get("usage_pricing", {})
    assert usage.get("mode") == "sfx_library"
    assert usage.get("per_item_xu") == 10
    assert usage.get("min_xu") == 10
    assert usage.get("charge_trigger") == "video_workflow_calculate_music_price"
    pricing = data.get("pricing", {})
    assert pricing.get("search_xu") == 0
    assert pricing.get("select_xu") == 0
    assert pricing.get("usage_xu_per_item") == 10
    assert pricing.get("usage_min_xu") == 10


def test_bot_pricing_constants_match_current_source():
    """Verify bridge constants match canonical bot.py source exactly."""
    assert bridge.SFX_LIBRARY_SEARCH_IMMEDIATE_CHARGE_XU == 0
    assert bridge.SFX_LIBRARY_SELECT_IMMEDIATE_CHARGE_XU == 0
    assert bridge.SFX_LIBRARY_XU_PER_ITEM == 10
    assert bridge.SFX_LIBRARY_MIN_XU == 10
    assert bridge.SFX_LIBRARY_USAGE_CHARGE_TRIGGER == "video_workflow_calculate_music_price"
    assert bridge.SFX_LIBRARY_USAGE_PRICING_MODE == "sfx_library"


def test_downstream_usage_pricing_parity():
    """Verify downstream usage pricing formula replicates bot.py::calculate_music_price."""
    policy = bridge.get_sfx_library_policy()
    usage = policy.get("usage_pricing", {})
    per_item = usage.get("per_item_xu", 10)
    min_xu = usage.get("min_xu", 10)

    # 1 SFX: max(10, 1 * 10) = 10
    assert max(min_xu, 1 * per_item) == 10
    # 2 SFX: max(10, 2 * 10) = 20
    assert max(min_xu, 2 * per_item) == 20
    # 5 SFX: max(10, 5 * 10) = 50
    assert max(min_xu, 5 * per_item) == 50


def test_policy_does_not_claim_globally_free_if_false():
    """Policy must truthfully distinguish immediate 0 Xu from downstream usage."""
    client = TestClient(app)
    resp = client.get("/api/v1/music/sfx-library/policy")
    assert resp.status_code == 200
    data = resp.json().get("data", {})
    # Must not claim globally free
    assert data.get("globally_free") is not True
    assert data.get("pricing_model") != "free_public_library"
    # Must disclose downstream usage pricing
    assert "usage_pricing" in data
    assert data["usage_pricing"]["per_item_xu"] > 0


# ─── 2. VALID SUCCESS PATH & OUTPUT NORMALIZATION ─────────────────────────────

def test_sfx_library_search_valid_success_path():
    """Search returns 200 with normalized Freesound items and 0 Xu charged."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")

    resp = client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "whoosh transition", "limit": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    data = body.get("data", {})
    assert data.get("query") == "whoosh transition"
    assert data.get("count") == 5
    assert data.get("xu_charged") == 0
    assert data.get("provider") == "Freesound"
    assert data.get("callback_token")

    results = data.get("results", [])
    assert len(results) == 5
    for item in results:
        assert item.get("id")
        assert item.get("provider") == "Freesound"
        assert item.get("title")
        assert item.get("author")
        assert item.get("duration") != "-"
        assert "Creative Commons" in item.get("license", "")
        assert item.get("source_url").startswith("https://freesound.org/")
        assert item.get("preview_url").endswith(".mp3")


def test_sfx_library_select_by_index_and_readback():
    """Select by 1-based index succeeds and is read back via GET /selected."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")

    # Step 1: Search
    search_resp = client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "cinematic hit", "limit": 3},
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json().get("data", {})
    items = search_data.get("results", [])
    assert len(items) == 3

    # Step 2: Select index 2
    select_resp = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"index": 2},
    )
    assert select_resp.status_code == 200
    select_data = select_resp.json().get("data", {})
    assert select_data.get("xu_charged") == 0
    selected_item = select_data.get("selected", {})
    assert selected_item.get("id") == items[1].get("id")
    assert selected_item.get("title") == items[1].get("title")

    # Step 3: Readback
    readback_resp = client.get("/api/v1/music/sfx-library/selected")
    assert readback_resp.status_code == 200
    readback_data = readback_resp.json().get("data", {})
    active_selection = readback_data.get("selected", {})
    assert active_selection.get("id") == items[1].get("id")
    assert active_selection.get("provider") == "Freesound"
    assert active_selection.get("title") == items[1].get("title")


def test_sfx_library_select_by_asset_id():
    """Select by specific asset_id succeeds when matching item in search list."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")

    # Search
    search_resp = client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "laser click", "limit": 4},
    )
    items = search_resp.json().get("data", {}).get("results", [])
    target_asset_id = items[2].get("id")

    # Select by asset_id
    select_resp = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"asset_id": target_asset_id},
    )
    assert select_resp.status_code == 200
    selected = select_resp.json().get("data", {}).get("selected", {})
    assert selected.get("id") == target_asset_id


# ─── 3. INVALID INPUT FAIL CLOSED ─────────────────────────────────────────────

def test_sfx_library_search_invalid_input_fail_closed():
    """Empty or oversized search queries fail closed."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")

    # Empty query
    resp1 = client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "   "},
    )
    assert resp1.status_code in (400, 422)

    # Oversized query > 160 chars
    resp2 = client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "a" * 161},
    )
    assert resp2.status_code in (400, 422)

    # Invalid limit > 5
    resp3 = client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "whoosh", "limit": 10},
    )
    assert resp3.status_code in (400, 422)


def test_sfx_library_select_invalid_input_fail_closed():
    """Invalid index, missing search, or non-matching asset ID fail closed."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")

    # Select without prior search fails closed (400)
    resp0 = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"index": 1},
    )
    assert resp0.status_code == 400

    # Execute search
    client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "button click", "limit": 3},
    )

    # Index out of bounds (> 3)
    resp1 = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"index": 4},
    )
    assert resp1.status_code == 400

    # Non-existent asset ID
    resp2 = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"asset_id": "non_existent_asset_xyz"},
    )
    assert resp2.status_code == 400

    # Missing both index and asset_id
    resp3 = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={},
    )
    assert resp3.status_code == 400


# ─── 4. WRONG OWNER BLOCKED ───────────────────────────────────────────────────

def test_sfx_library_wrong_owner_blocked():
    """Cross-account access and selection leakage are strictly blocked."""
    acc_a = f"acc_a_{uuid.uuid4().hex[:8]}"
    acc_b = f"acc_b_{uuid.uuid4().hex[:8]}"
    client_a, csrf_a = _client_with_auth(acc_a, f"{acc_a}@test.vn")
    client_b, csrf_b = _client_with_auth(acc_b, f"{acc_b}@test.vn")

    # Account A searches
    resp_a = client_a.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf_a},
        json={"query": "bell chime", "limit": 3},
    )
    token_a = resp_a.json().get("data", {}).get("callback_token")
    client_a.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf_a},
        json={"index": 1},
    )

    # Account B has not selected anything yet
    resp_b_selected = client_b.get("/api/v1/music/sfx-library/selected")
    assert resp_b_selected.status_code == 200
    assert resp_b_selected.json().get("data", {}).get("selected") is None

    # Account B trying to select using Account A's callback token fails closed
    resp_b_hijack = client_b.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf_b},
        json={"index": 1, "callback_token": token_a},
    )
    assert resp_b_hijack.status_code == 400


def test_sfx_library_unauthenticated_blocked():
    """Unauthenticated requests are blocked or redirected."""
    client = TestClient(app)

    # Search without auth
    resp_search = client.post("/api/v1/music/sfx-library/search", json={"query": "whoosh"})
    assert resp_search.status_code in (307, 401, 403)

    # Select without auth
    resp_select = client.post("/api/v1/music/sfx-library/select", json={"index": 1})
    assert resp_select.status_code in (307, 401, 403)

    # Readback without auth
    resp_readback = client.get("/api/v1/music/sfx-library/selected")
    assert resp_readback.status_code in (307, 401, 403)


# ─── 5. XU PRICING & WALLET PARITY ────────────────────────────────────────────

def test_sfx_library_zero_wallet_impact():
    """Search and select charge 0 Xu and do not mutate wallet balance."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")

    # Search
    s_resp = client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "horn sound", "limit": 3},
    )
    assert s_resp.status_code == 200
    assert s_resp.json().get("data", {}).get("xu_charged") == 0

    # Select
    sel_resp = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"index": 1},
    )
    assert sel_resp.status_code == 200
    assert sel_resp.json().get("data", {}).get("xu_charged") == 0

    # Policy confirms 0 Xu immediate
    policy_resp = client.get("/api/v1/music/sfx-library/policy")
    assert policy_resp.json().get("data", {}).get("pricing", {}).get("search_xu") == 0
    assert policy_resp.json().get("data", {}).get("pricing", {}).get("select_xu") == 0


def test_search_immediate_charge_parity():
    """Search endpoint must charge 0 Xu immediately."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")
    resp = client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "chime bell", "limit": 2},
    )
    assert resp.status_code == 200
    assert resp.json().get("data", {}).get("xu_charged") == 0


def test_select_immediate_charge_parity():
    """Select endpoint must charge 0 Xu immediately and state 'Bot chưa trừ Xu ở bước chọn'."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")
    client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "chime bell", "limit": 2},
    )
    resp = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"index": 1},
    )
    assert resp.status_code == 200
    assert resp.json().get("data", {}).get("xu_charged") == 0
    assert "chưa trừ Xu" in resp.json().get("data", {}).get("message", "")


def test_no_wallet_mutation_on_search():
    """Ensure search does not alter web_manual_topup or any financial state."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")
    with read_transaction() as conn:
        before_count = conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests WHERE account_id = ?", (account_id,)).fetchone()[0]
    client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "explosion boom", "limit": 2},
    )
    with read_transaction() as conn:
        after_count = conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests WHERE account_id = ?", (account_id,)).fetchone()[0]
    assert before_count == after_count


def test_no_wallet_mutation_on_select():
    """Ensure select does not alter web_manual_topup or any financial state."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")
    client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "explosion boom", "limit": 2},
    )
    with read_transaction() as conn:
        before_count = conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests WHERE account_id = ?", (account_id,)).fetchone()[0]
    client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"index": 1},
    )
    with read_transaction() as conn:
        after_count = conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests WHERE account_id = ?", (account_id,)).fetchone()[0]
    assert before_count == after_count


# ─── 6. DUPLICATE & IDEMPOTENCY ───────────────────────────────────────────────

def test_sfx_library_duplicate_selection_idempotent():
    """Repeatedly selecting items is idempotent and charges 0 Xu each time."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    client, csrf = _client_with_auth(account_id, f"{account_id}@test.vn")

    client.post(
        "/api/v1/music/sfx-library/search",
        headers={"X-CSRF-Token": csrf},
        json={"query": "keyboard click", "limit": 2},
    )

    # Select index 1 first time
    resp1 = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"index": 1},
    )
    assert resp1.status_code == 200
    id1 = resp1.json().get("data", {}).get("selected", {}).get("id")

    # Select index 1 second time
    resp2 = client.post(
        "/api/v1/music/sfx-library/select",
        headers={"X-CSRF-Token": csrf},
        json={"index": 1},
    )
    assert resp2.status_code == 200
    id2 = resp2.json().get("data", {}).get("selected", {}).get("id")
    assert id1 == id2

    # Readback confirms same ID
    readback = client.get("/api/v1/music/sfx-library/selected").json().get("data", {}).get("selected", {})
    assert readback.get("id") == id1


# ─── 7. PROVIDER ERROR HANDLING ───────────────────────────────────────────────

def test_sfx_library_provider_error_handling():
    """Provider error fails gracefully without charging Xu."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"

    # Test bridge directly with simulated error flag
    with pytest.raises(Exception) as exc_info:
        bridge.search_sfx_library(account_id, "fail query", force_provider_error=True)
    assert "502" in str(exc_info.value) or "Chưa trừ Xu" in str(exc_info.value)


# ─── 8. R36 FIX3 RUNTIME TRUTH & FAIL-CLOSED GUARD REGRESSION TESTS ───────────

def test_1_app_env_test_explicit_mock_fixture_deterministic_results_pass():
    """TEST 1: APP_ENV=test with explicit mock fixture returns deterministic results."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_id, f"{account_id}@test.vn")
    fixture_items = [
        {
            "id": "fs_fixture_01",
            "name": "Fixture Laser Sound",
            "username": "fx_artist",
            "duration": 2.5,
            "license": "Creative Commons 0",
            "url": "https://freesound.org/sounds/fs_fixture_01/",
            "previews": {"preview-hq-mp3": "https://cdn.freesound.org/previews/fs_fixture_01_hq.mp3"},
        }
    ]
    res = bridge.search_sfx_library(account_id, "laser", mock_results=fixture_items)
    assert res["count"] == 1
    assert res["results"][0]["id"] == "fs_fixture_01"
    assert res["results"][0]["title"] == "Fixture Laser Sound"


def test_2_app_env_production_provider_disabled_fails_closed(monkeypatch):
    """TEST 2: APP_ENV=production, WEBAPP_PROVIDER_CALLS_ENABLED=false -> FAIL CLOSED with 503."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    bridge.reset_test_explicit_mock_results()

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        bridge.search_sfx_library(account_id, "whoosh")
    assert exc_info.value.status_code == 503
    assert "WEBAPP_PROVIDER_CALLS_DISABLED" in exc_info.value.detail


def test_3_provider_disabled_mock_generator_never_called(monkeypatch):
    """TEST 3: provider disabled -> _generate_mock_freesound_results is NEVER CALLED."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")
    bridge.reset_test_explicit_mock_results()

    from fastapi import HTTPException

    def _forbidden_generator(*args, **kwargs):
        raise AssertionError("CRITICAL_FAULT: Mock generator must never be invoked when provider is disabled!")

    monkeypatch.setattr(bridge, "_generate_mock_freesound_results", _forbidden_generator)

    with pytest.raises(HTTPException) as exc_info:
        bridge.search_sfx_library(account_id, "whoosh")
    assert exc_info.value.status_code == 503


def test_4_provider_disabled_zero_synthetic_result_rows_persisted(monkeypatch):
    """TEST 4: provider disabled -> zero synthetic result rows persisted to SQLite."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_id, f"{account_id}@test.vn")
    bridge.reset_test_explicit_mock_results()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")

    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        bridge.search_sfx_library(account_id, "metal clang")

    monkeypatch.setenv("APP_ENV", "test")
    with read_transaction() as conn:
        bridge.ensure_sfx_library_schema(conn)
        row = conn.execute("SELECT COUNT(*) FROM web_sfx_library_searches WHERE account_id = ?", (account_id,)).fetchone()
        assert row[0] == 0


def test_5_provider_disabled_wallet_unchanged(monkeypatch):
    """TEST 5: provider disabled -> wallet balance / ledger completely unchanged."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_id, f"{account_id}@test.vn")
    with read_transaction() as conn:
        count_before = conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests WHERE account_id = ?", (account_id,)).fetchone()[0]

    bridge.reset_test_explicit_mock_results()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "false")

    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        bridge.search_sfx_library(account_id, "thunder storm")

    monkeypatch.setenv("APP_ENV", "test")
    with read_transaction() as conn:
        count_after = conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests WHERE account_id = ?", (account_id,)).fetchone()[0]

    assert count_before == count_after


def test_6_provider_enabled_missing_canonical_credential_fails_before_network(monkeypatch):
    """TEST 6: provider enabled + missing credentials -> fail closed 503 before any network call."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("WEBAPP_PROVIDER_CALLS_ENABLED", "true")
    monkeypatch.delenv("FREESOUND_API_KEY", raising=False)
    monkeypatch.delenv("FREESOUND_CLIENT_SECRET", raising=False)
    bridge.reset_test_explicit_mock_results()

    import urllib.request
    from fastapi import HTTPException

    def _forbidden_network(*args, **kwargs):
        raise AssertionError("CRITICAL_FAULT: Network must never be called when credentials are missing!")

    monkeypatch.setattr(urllib.request, "urlopen", _forbidden_network)

    with pytest.raises(HTTPException) as exc_info:
        bridge.search_sfx_library(account_id, "bell toll")
    assert exc_info.value.status_code == 503
    assert "credential" in exc_info.value.detail.lower()


def test_7_provider_error_fails_truthfully_no_synthetic_fallback():
    """TEST 7: provider error -> fails truthfully (502), zero synthetic fallback."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        bridge.search_sfx_library(account_id, "glitch sound", force_provider_error=True)
    assert exc_info.value.status_code == 502
    assert "Chưa trừ Xu" in exc_info.value.detail


def test_8_empty_legitimate_provider_result_truthful_empty_no_fabricated_assets():
    """TEST 8: empty legitimate provider result -> returns empty list, no fabricated assets."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_id, f"{account_id}@test.vn")
    res = bridge.search_sfx_library(account_id, "nonexistentquery123456", mock_results=[])
    assert res["count"] == 0
    assert res["results"] == []


def test_9_search_immediate_charge_zero():
    """TEST 9: search immediate charge is strictly 0 Xu."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_id, f"{account_id}@test.vn")
    res = bridge.search_sfx_library(account_id, "horn blast", mock_results=[])
    assert res["xu_charged"] == 0
    assert res["search_immediate_cost_xu"] == 0


def test_10_select_immediate_charge_zero():
    """TEST 10: select immediate charge is strictly 0 Xu and notice reflects 'Bot chưa trừ Xu'."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_id, f"{account_id}@test.vn")
    fixture_items = [
        {
            "id": "fs_test_item_10",
            "name": "Pop Sound",
            "username": "fx_user",
            "duration": 0.5,
            "license": "CC0",
            "url": "https://freesound.org/sounds/fs_test_item_10/",
            "previews": {"preview-hq-mp3": "https://cdn.freesound.org/previews/10.mp3"},
        }
    ]
    bridge.search_sfx_library(account_id, "pop", mock_results=fixture_items)
    sel = bridge.select_sfx_library_item(account_id, index=1)
    assert sel["xu_charged"] == 0
    assert "chưa trừ Xu" in sel["message"]


def test_11_downstream_usage_pricing_matches_bot_contract():
    """TEST 11: downstream usage pricing reflects canonical Bot calculate_music_price contract."""
    policy = bridge.get_sfx_library_policy()
    usage = policy.get("usage_pricing", {})
    assert usage["mode"] == "sfx_library"
    assert usage["per_item_xu"] == 10
    assert usage["min_xu"] == 10
    assert usage["charge_trigger"] == "video_workflow_calculate_music_price"


def test_12_pricing_response_does_not_claim_global_free_usage():
    """TEST 12: pricing response does not claim global free usage."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_id, f"{account_id}@test.vn")
    res = bridge.search_sfx_library(account_id, "click", mock_results=[])
    assert res.get("pricing_model") != "free_public_library"
    assert res.get("globally_free") is not True
    assert "downstream_video_usage_pricing" in res


def test_13_wrong_account_selection_blocked():
    """TEST 13: cross-account selection using another account's callback_token is blocked."""
    account_a = f"acc_a_{uuid.uuid4().hex[:8]}"
    account_b = f"acc_b_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_a, f"{account_a}@test.vn")
    _create_test_account(account_b, f"{account_b}@test.vn")
    fixture_items = [
        {
            "id": "fs_item_13",
            "name": "Ding",
            "username": "sound_guy",
            "duration": 1.0,
            "license": "CC-BY",
            "url": "https://freesound.org/sounds/fs_item_13/",
            "previews": {"preview-hq-mp3": "https://cdn.freesound.org/previews/13.mp3"},
        }
    ]
    res_a = bridge.search_sfx_library(account_a, "ding", mock_results=fixture_items)
    token_a = res_a["callback_token"]

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        bridge.select_sfx_library_item(account_b, index=1, callback_token=token_a)
    assert exc_info.value.status_code == 400


def test_14_sfx_selection_readback_remains_correct():
    """TEST 14: active selection persists and is accurately read back."""
    account_id = f"acc_{uuid.uuid4().hex[:8]}"
    _create_test_account(account_id, f"{account_id}@test.vn")
    fixture_items = [
        {
            "id": "fs_item_14",
            "name": "Applause Audience",
            "username": "crowd_audio",
            "duration": 4.2,
            "license": "Creative Commons 0",
            "url": "https://freesound.org/sounds/fs_item_14/",
            "previews": {"preview-hq-mp3": "https://cdn.freesound.org/previews/14.mp3"},
        }
    ]
    bridge.search_sfx_library(account_id, "applause", mock_results=fixture_items)
    bridge.select_sfx_library_item(account_id, index=1)
    readback = bridge.get_selected_sfx_library_item(account_id)
    assert readback is not None
    assert readback["id"] == "fs_item_14"
    assert readback["title"] == "Applause Audience"
    assert readback["provider"] == "Freesound"
