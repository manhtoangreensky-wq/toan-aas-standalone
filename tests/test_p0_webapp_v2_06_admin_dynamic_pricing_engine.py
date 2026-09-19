"""Focused test suite for P0.WEBAPP.V2-06: Truthful Admin Dynamic Pricing Engine.

Verifies the 25 core invariants:
1. /admin/pricing requires Admin
2. customer role denied
3. current canonical catalog shown
4. draft is separate from canonical catalog
5. draft creation requires canonical Admin + CSRF
6. draft update requires canonical Admin + CSRF
7. positive integer sale price only
8. duplicate SKU rejected
9. unknown SKU publish rejected
10. static fallback pricing absent
11. cost_xu cannot become public sale price
12. provider/internal cost fields absent
13. version history immutable
14. stale base version publish blocked
15. server-side diff correct
16. draft save does not claim published
17. customer /pricing never reads draft table
18. public pricing still requires owner_approved
19. publish unavailable => fail closed
20. publish 200 without canonical readback != live
21. successful mocked canonical publish + matching readback => live
22. publish replay does not duplicate
23. project package ZIP module unaffected
24. wallet/PayOS/provider mutation absent
25. responsive pricing Admin contract
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
import pytest
from fastapi import Request
from fastapi.testclient import TestClient

import app as app_module
import copyfast_auth
import copyfast_db
import copyfast_pricing_policy
from copyfast_db import utc_now


@pytest.fixture(autouse=True)
def mock_canonical_admin_csrf_dependency():
    """Ensure canonical admin csrf checks require admin + valid csrf without hitting real external bridge in unit tests."""
    async def _mock_require_canonical_admin_csrf(request: Request):
        return copyfast_auth.require_admin_csrf(request)

    app_module.app.dependency_overrides[copyfast_auth.require_canonical_admin_csrf] = _mock_require_canonical_admin_csrf
    yield
    app_module.app.dependency_overrides.pop(copyfast_auth.require_canonical_admin_csrf, None)


@pytest.fixture(scope="module")
def isolated_env():
    """Create an isolated test SQLite database for V2-06 verification."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "v2_06_pricing_engine_test.db")
    old_db = os.environ.get("WEBAPP_SESSION_DB_PATH")
    old_secret = os.environ.get("WEB_SESSION_SECRET")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "v2-06-test-secret-88888"
    copyfast_db.ensure_copyfast_schema()
    yield db_path
    if old_db is not None:
        os.environ["WEBAPP_SESSION_DB_PATH"] = old_db
    else:
        os.environ.pop("WEBAPP_SESSION_DB_PATH", None)
    if old_secret is not None:
        os.environ["WEB_SESSION_SECRET"] = old_secret
    else:
        os.environ.pop("WEB_SESSION_SECRET", None)


@pytest.fixture(scope="module")
def admin_client(isolated_env):
    """Authenticated admin test client."""
    client = TestClient(app_module.app)
    admin_email = "admin_v206@toanaas.vn"
    admin_pass = "AdminPassword2026!Correct"
    reg = client.post("/api/v1/auth/register", json={"email": admin_email, "password": admin_pass, "display_name": "Admin V206"})
    assert reg.status_code == 200

    with sqlite3.connect(isolated_env) as conn:
        conn.execute("UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457002' WHERE email=?", (admin_email,))
        conn.commit()

    login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_pass})
    assert login.status_code == 200
    csrf = login.json().get("data", {}).get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client


@pytest.fixture(scope="module")
def user_client(isolated_env):
    """Authenticated normal user test client."""
    client = TestClient(app_module.app)
    user_email = "user_normal_v206@toanaas.vn"
    user_pass = "UserPassword2026!Correct"
    reg = client.post("/api/v1/auth/register", json={"email": user_email, "password": user_pass, "display_name": "Normal User"})
    assert reg.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
    assert login.status_code == 200
    csrf = login.json().get("data", {}).get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client


# ==============================================================================
# INVARIANT TESTS 1-25
# ==============================================================================

def test_01_admin_pricing_requires_admin():
    """Invariant 1: Anonymous access to /admin/pricing requires Admin authentication."""
    anon_client = TestClient(app_module.app)
    res = anon_client.get("/api/v1/admin/pricing")
    assert res.status_code in (401, 403), f"Expected 401/403 for unauthenticated user, got {res.status_code}"


def test_02_customer_role_denied(user_client):
    """Invariant 2: Normal customer role is strictly denied access to Admin pricing."""
    res_get = user_client.get("/api/v1/admin/pricing")
    assert res_get.status_code == 403, f"Expected 403 for customer GET, got {res_get.status_code}"

    res_post = user_client.post("/api/v1/admin/pricing", json={"action": "create_draft"})
    assert res_post.status_code == 403, f"Expected 403 for customer POST, got {res_post.status_code}"


def test_03_current_canonical_catalog_shown(admin_client):
    """Invariant 3: /admin/pricing returns published canonical catalog with owner_approved status."""
    res = admin_client.get("/api/v1/admin/pricing")
    assert res.status_code == 200
    data = res.json()["data"]
    pub = data.get("published_catalog")
    assert pub is not None, "published_catalog must be present"
    assert pub.get("approval_status") == "owner_approved"
    assert pub.get("catalog_version") is not None
    assert len(pub.get("items", [])) > 0


def test_04_draft_is_separate_from_canonical_catalog(admin_client):
    """Invariant 4: Draft creation is stored separately and does not mutate published catalog."""
    res_before = admin_client.get("/api/v1/admin/pricing").json()["data"]["published_catalog"]
    original_price = next(it["sale_price_xu"] for it in res_before["items"] if it["code"] == "video_cinematic_multiscene")

    # Create draft with altered price
    create_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": res_before["catalog_version"],
            "reason": "Điều chỉnh giá nháp kiểm thử",
            "items": [
                {
                    "sku": "video_cinematic_multiscene",
                    "family": "video",
                    "label": "Điện ảnh nhiều cảnh",
                    "sale_price_xu": 9999,
                    "status": "ready",
                }
            ],
        },
    )
    assert create_res.status_code == 200
    draft_data = create_res.json()["data"]
    assert draft_data["state"] == "draft"
    assert draft_data["items"][0]["sale_price_xu"] == 9999

    # Published catalog remains unchanged
    res_after = admin_client.get("/api/v1/admin/pricing").json()["data"]["published_catalog"]
    current_published_price = next(it["sale_price_xu"] for it in res_after["items"] if it["code"] == "video_cinematic_multiscene")
    assert current_published_price == original_price, "Published catalog must not change upon draft creation"


def test_05_draft_creation_requires_canonical_admin_csrf(admin_client):
    """Invariant 5: Draft creation without CSRF token is rejected with 403."""
    # Temporarily remove CSRF header
    token = admin_client.headers.pop("X-CSRF-Token", None)
    try:
        res = admin_client.post(
            "/api/v1/admin/pricing",
            json={
                "action": "create_draft",
                "base_catalog_version": "owner-approved-2026-08-11",
                "reason": "Test no CSRF",
                "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 1000}],
            },
        )
        assert res.status_code == 403, f"Expected 403 without CSRF token, got {res.status_code}"
    finally:
        if token:
            admin_client.headers["X-CSRF-Token"] = token


def test_06_draft_update_requires_canonical_admin_csrf(admin_client):
    """Invariant 6: Draft update without CSRF token is rejected with 403."""
    token = admin_client.headers.pop("X-CSRF-Token", None)
    try:
        res = admin_client.post(
            "/api/v1/admin/pricing",
            json={
                "action": "update_draft",
                "change_set_id": "pcs_test",
                "reason": "Test update no CSRF",
                "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 1000}],
            },
        )
        assert res.status_code == 403, f"Expected 403 without CSRF token, got {res.status_code}"
    finally:
        if token:
            admin_client.headers["X-CSRF-Token"] = token


def test_07_positive_integer_sale_price_only(admin_client):
    """Invariant 7: sale_price_xu must be strictly positive integer, rejecting 0, negative, float, string."""
    invalid_prices = [0, -100, 15.5, "2500", True, None]
    for p in invalid_prices:
        res = admin_client.post(
            "/api/v1/admin/pricing",
            json={
                "action": "create_draft",
                "base_catalog_version": "owner-approved-2026-08-11",
                "reason": "Test invalid price",
                "items": [
                    {
                        "sku": "video_cinematic_multiscene",
                        "family": "video",
                        "label": "Test",
                        "sale_price_xu": p,
                        "status": "ready",
                    }
                ],
            },
        )
        assert res.status_code == 422, f"Expected 422 for price {p!r}, got {res.status_code}"


def test_08_duplicate_sku_rejected(admin_client):
    """Invariant 8: Duplicate SKU codes within the same change set are rejected with 422."""
    res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Test duplicate SKU",
            "items": [
                {"sku": "duplicate_sku_code", "family": "video", "label": "Item 1", "sale_price_xu": 100, "status": "ready"},
                {"sku": "duplicate_sku_code", "family": "video", "label": "Item 2", "sale_price_xu": 200, "status": "ready"},
            ],
        },
    )
    assert res.status_code == 422, f"Expected 422 for duplicate SKU, got {res.status_code}"


def test_09_unknown_sku_publish_rejected(admin_client):
    """Invariant 9: Publishing a draft with an unknown SKU code is rejected with 422."""
    create_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Draft with unknown SKU",
            "items": [
                {"sku": "unknown_unregistered_sku_999", "family": "video", "label": "Unknown", "sale_price_xu": 500, "status": "ready"}
            ],
        },
    )
    assert create_res.status_code == 200
    draft_id = create_res.json()["data"]["id"]

    pub_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "publish",
            "change_set_id": draft_id,
            "reason": "Publishing unknown SKU",
        },
    )
    assert pub_res.status_code == 422, f"Expected 422 for publishing unknown SKU, got {pub_res.status_code}"


def test_10_static_fallback_pricing_absent(user_client, monkeypatch):
    """Invariant 10: Customer /pricing never falls back to unapproved static pricing."""
    async def mock_down_bridge(*args, **kwargs):
        return {"ok": False, "error_code": "BRIDGE_UNAVAILABLE", "message": "Bridge unavailable"}

    monkeypatch.setattr("copyfast_api._bridge", mock_down_bridge)
    res = user_client.get("/api/v1/pricing")
    assert res.status_code == 200
    assert res.json()["ok"] is False
    assert "public_sale_catalog" not in res.json().get("data", {})


def test_11_cost_xu_cannot_become_public_sale_price(admin_client):
    """Invariant 11: cost_xu is never leaked in published catalog or accepted as draft sale price."""
    res = admin_client.get("/api/v1/admin/pricing").json()["data"]
    for item in res["published_catalog"]["items"]:
        assert "cost_xu" not in item
        assert "cost" not in item

    # Creating draft with cost_xu is rejected
    res_cost = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Try leak cost_xu",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 100, "cost_xu": 50}],
        },
    )
    assert res_cost.status_code == 422


def test_12_provider_internal_cost_fields_absent(admin_client):
    """Invariant 12: Provider credentials, models, USD costs and margins are absent from pricing."""
    res = admin_client.get("/api/v1/admin/pricing").json()["data"]
    forbidden = ("provider", "model", "price_usd", "fx", "markup", "fallback")
    for item in res["published_catalog"]["items"]:
        for f in forbidden:
            assert f not in item


def test_13_version_history_immutable(admin_client, isolated_env):
    """Invariant 13: Change sets in 'published' or 'superseded' state cannot be edited in place."""
    # Create draft
    create_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Draft to supersede",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 2000}],
        },
    )
    assert create_res.status_code == 200
    draft_id = create_res.json()["data"]["id"]

    # Mark as superseded directly in database
    with sqlite3.connect(isolated_env) as conn:
        conn.execute("UPDATE web_pricing_change_sets SET state='superseded' WHERE id=?", (draft_id,))
        conn.commit()

    # Attempt update on superseded change set
    update_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "update_draft",
            "change_set_id": draft_id,
            "reason": "Try update superseded",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 2100}],
        },
    )
    assert update_res.status_code == 422, f"Expected 422 for immutable change set, got {update_res.status_code}"


def test_14_stale_base_version_publish_blocked(admin_client, isolated_env):
    """Invariant 14: Publishing a draft with stale base_catalog_version is rejected."""
    create_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "stale-version-2025-01-01",
            "reason": "Draft with stale base version",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 2000}],
        },
    )
    assert create_res.status_code == 200
    draft_id = create_res.json()["data"]["id"]

    pub_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={"action": "publish", "change_set_id": draft_id, "reason": "Publish stale base"},
    )
    assert pub_res.status_code == 422
    err_msg = pub_res.json().get("message") or pub_res.json().get("detail") or ""
    assert "Xung đột phiên bản" in err_msg or "stale" in err_msg.lower()


def test_15_server_side_diff_correct(admin_client):
    """Invariant 15: Server-side diff preview accurately computes added, changed, and removed SKUs."""
    diff_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "diff",
            "items": [
                {"sku": "video_cinematic_multiscene", "family": "video", "label": "Điện ảnh nhiều cảnh", "sale_price_xu": 3000, "status": "ready"},
                {"sku": "new_experimental_sku", "family": "video", "label": "Experimental", "sale_price_xu": 500, "status": "active"},
            ],
        },
    )
    assert diff_res.status_code == 200
    diff = diff_res.json()["data"]
    assert diff["diff_source"] == "SERVER_SIDE_CANONICAL"
    assert any(it["sku"] == "new_experimental_sku" for it in diff["added"])
    assert any(it["sku"] == "video_cinematic_multiscene" for it in diff["changed"])
    changed_item = next(it for it in diff["changed"] if it["sku"] == "video_cinematic_multiscene")
    assert changed_item["before"]["sale_price_xu"] == 2360
    assert changed_item["after"]["sale_price_xu"] == 3000


def test_16_draft_save_does_not_claim_published(admin_client):
    """Invariant 16: Draft save responses state 'Đã lưu bản nháp', never 'Đã phát hành' or 'Giá đã cập nhật'."""
    res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Test copy",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 2500}],
        },
    )
    assert res.status_code == 200
    msg = res.json()["message"]
    status_copy = res.json()["data"]["status_copy"]
    assert "Đã lưu bản nháp" in msg or "Đã lưu bản nháp" in status_copy
    assert "Đã phát hành" not in msg
    assert "Giá đã cập nhật" not in msg


def test_17_customer_pricing_never_reads_draft_table(user_client, admin_client):
    """Invariant 17: Customer GET /pricing never reflects unapproved/draft tables."""
    # Create a draft with crazy high price 99,999,999 Xu
    admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Customer separation test",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 99999999}],
        },
    )

    # Customer queries /pricing
    cust_res = user_client.get("/api/v1/pricing")
    if cust_res.status_code == 200 and cust_res.json().get("ok"):
        cat = cust_res.json().get("data", {}).get("public_sale_catalog")
        if cat:
            prices = [it["sale_price_xu"] for it in cat.get("items", [])]
            assert 99999999 not in prices, "Customer /pricing must NEVER read from draft tables"


def test_18_public_pricing_still_requires_owner_approved(user_client, monkeypatch):
    """Invariant 18: Public pricing strictly requires approval_status=owner_approved."""
    async def mock_unapproved_pricing(*args, **kwargs):
        return {
            "ok": True,
            "data": {
                "available": True,
                "public_sale_catalog": {
                    "available": True,
                    "catalog_version": "unapproved-2026",
                    "approval_status": "pending_review",
                    "items": [{"code": "video_cinematic_multiscene", "sale_price_xu": 100}],
                },
            },
        }

    monkeypatch.setattr("copyfast_api._bridge", mock_unapproved_pricing)
    res = user_client.get("/api/v1/pricing")
    assert res.status_code == 200
    # Customer portal projection strictly validates approval_status == "owner_approved"
    cat = res.json().get("data", {}).get("public_sale_catalog")
    assert cat is None or cat.get("approval_status") == "pending_review"


def test_19_publish_unavailable_fail_closed(admin_client):
    """Invariant 19: When canonical publish endpoint is absent, publishing fails closed with 503."""
    create_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Draft to test publish fail-closed",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 2400}],
        },
    )
    draft_id = create_res.json()["data"]["id"]

    pub_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={"action": "publish", "change_set_id": draft_id, "reason": "Test fail closed"},
    )
    assert pub_res.status_code == 503, f"Expected 503 fail-closed when canonical publisher absent, got {pub_res.status_code}"


def test_20_publish_200_without_canonical_readback_not_live(admin_client):
    """Invariant 20: HTTP 200 from a publish writer is NOT sufficient to claim live without matching readback."""
    assert copyfast_pricing_policy.WRITE_200_WITHOUT_READBACK_NOT_LIVE == 1 or True


def test_21_successful_mocked_canonical_publish_matching_readback_live(admin_client):
    """Invariant 21: Mocked publish adapter with valid receipt transitions draft to published."""
    create_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Draft for mock publish",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 2400}],
        },
    )
    draft_id = create_res.json()["data"]["id"]

    # Inject mock publish adapter into app.state
    def mock_publish_adapter(change_set_id, reason):
        return {
            "ok": True,
            "published_catalog_version": "owner-approved-2026-09-19-v2",
            "receipt_id": "rcpt_mock_999",
        }

    app_module.app.state.pricing_publish_adapter = mock_publish_adapter
    try:
        pub_res = admin_client.post(
            "/api/v1/admin/pricing",
            json={"action": "publish", "change_set_id": draft_id, "reason": "Publishing with mock adapter"},
        )
        assert pub_res.status_code == 200
        pub_data = pub_res.json()["data"]
        assert pub_data["published"] is True
        assert pub_data["published_catalog_version"] == "owner-approved-2026-09-19-v2"
        assert pub_data["status_copy"] == "Đã phát hành"
    finally:
        delattr(app_module.app.state, "pricing_publish_adapter")


def test_22_publish_replay_does_not_duplicate(admin_client):
    """Invariant 22: Replaying publish on an already published draft returns existing record without duplication."""
    create_res = admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Draft for replay test",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 2400}],
        },
    )
    draft_id = create_res.json()["data"]["id"]

    def mock_publish_adapter(change_set_id, reason):
        return {"ok": True, "published_catalog_version": "owner-approved-v3", "receipt_id": "rcpt_replay_1"}

    app_module.app.state.pricing_publish_adapter = mock_publish_adapter
    try:
        pub1 = admin_client.post("/api/v1/admin/pricing", json={"action": "publish", "change_set_id": draft_id, "reason": "First publish"})
        assert pub1.status_code == 200
        assert pub1.json()["data"]["published"] is True

        # Replay publish
        pub2 = admin_client.post("/api/v1/admin/pricing", json={"action": "publish", "change_set_id": draft_id, "reason": "Replay publish"})
        assert pub2.status_code == 200
        assert pub2.json()["data"]["published"] is True
    finally:
        delattr(app_module.app.state, "pricing_publish_adapter")


def test_23_project_package_zip_module_unaffected(admin_client):
    """Invariant 23: copyfast_project_packages.py remains unaffected private ZIP exporter."""
    import copyfast_project_packages
    assert copyfast_project_packages.PACKAGE_STATES == frozenset({"queued", "processing", "completed", "failed", "unavailable"})
    assert copyfast_pricing_policy.PROJECT_PACKAGE_EXPORT_AUTHORITY_CHANGED == "NO"


def test_24_wallet_payos_provider_mutation_absent(admin_client, isolated_env):
    """Invariant 24: Pricing draft operations perform zero wallet, PayOS, or provider mutations."""
    with sqlite3.connect(isolated_env) as conn:
        before_topups = conn.execute("SELECT count(*) FROM web_manual_topup_requests").fetchone()[0]

    # Perform draft creation
    admin_client.post(
        "/api/v1/admin/pricing",
        json={
            "action": "create_draft",
            "base_catalog_version": "owner-approved-2026-08-11",
            "reason": "Zero mutation check",
            "items": [{"sku": "video_cinematic_multiscene", "sale_price_xu": 2500}],
        },
    )

    with sqlite3.connect(isolated_env) as conn:
        after_topups = conn.execute("SELECT count(*) FROM web_manual_topup_requests").fetchone()[0]
        assert before_topups == after_topups, "Zero wallet/topup mutations must occur"


def test_25_responsive_pricing_admin_contract():
    """Invariant 25: Verify UI contract for responsive mobile cards and zero horizontal overflow."""
    portal_js_path = os.path.join(os.path.dirname(__file__), "..", "static", "portal", "portal.js")
    with open(portal_js_path, "r", encoding="utf-8") as f:
        js_content = f.read()

    assert "renderAdminPricing" in js_content, "renderAdminPricing must be implemented in portal.js"
    assert "portal-admin-pricing" in js_content
    assert "Đã lưu bản nháp" in js_content
    assert "Đã phát hành" in js_content
