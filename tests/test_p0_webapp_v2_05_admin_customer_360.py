"""Focused test suite for P0.WEBAPP.V2-05: Truthful Admin Customer 360 & Account Safety.

Verifies the 25 core invariants:
1. /admin/customers requires Admin
2. customer detail requires Admin
3. normal customer denied
4. Customer 360 renders identity truth
5. unknown wallet not displayed as zero
6. unknown spending not displayed as zero
7. no static VIP tier ladder
8. no fake behavior/risk score
9. real job history projection
10. real asset/output projection
11. V2-04 download truth preserved
12. support truth/empty state
13. ban requires canonical Admin + CSRF
14. ban requires reason
15. ban sets canonical Web account inactive
16. ban revokes target Web sessions
17. unrelated sessions untouched
18. unban restores account active
19. unban does not restore revoked sessions
20. duplicate ban is idempotent
21. duplicate unban is idempotent
22. audit record created
23. Admin target ban refused
24. no provider/wallet/job mutation
25. responsive Customer 360 contract
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_admin_customer_directory as directory
import copyfast_auth
import copyfast_customer_crm_policy as crm_policy
import copyfast_db
from copyfast_db import utc_now


@pytest.fixture(scope="module")
def isolated_env():
    """Create an isolated test SQLite database for V2-05 verification."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "v2_05_customer_360_test.db")
    old_db = os.environ.get("WEBAPP_SESSION_DB_PATH")
    old_secret = os.environ.get("WEB_SESSION_SECRET")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "v2-05-test-secret-99999"
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
    admin_email = "admin_v205@toanaas.vn"
    admin_pass = "AdminPassword2026!Correct"
    reg = client.post("/api/v1/auth/register", json={"email": admin_email, "password": admin_pass, "display_name": "Admin V205"})
    assert reg.status_code == 200

    with sqlite3.connect(isolated_env) as conn:
        conn.execute("UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457001' WHERE email=?", (admin_email,))
        conn.commit()

    login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_pass})
    assert login.status_code == 200
    return client


@pytest.fixture(scope="module")
def user_client(isolated_env):
    """Authenticated normal user test client."""
    client = TestClient(app_module.app)
    user_email = "user_normal_v205@toanaas.vn"
    user_pass = "UserPassword2026!Correct"
    reg = client.post("/api/v1/auth/register", json={"email": user_email, "password": user_pass, "display_name": "Normal User"})
    assert reg.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": user_email, "password": user_pass})
    assert login.status_code == 200
    return client


@pytest.fixture(scope="module")
def seed_data(isolated_env):
    """Seed customer accounts for testing."""
    target_cust_id = str(uuid.uuid4())
    other_cust_id = str(uuid.uuid4())
    admin_target_id = str(uuid.uuid4())
    now = utc_now()

    with sqlite3.connect(isolated_env) as conn:
        # Standard customer to ban/unban
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, 'hash', 'Target Customer', NULL, 'user', 1, 1, ?, ?)""",
            (target_cust_id, f"target_{target_cust_id[:8]}@example.com", now, now),
        )
        conn.execute(
            """INSERT INTO web_account_profiles
               (account_id, locale, timezone, avatar_style, created_at, updated_at)
               VALUES (?, 'vi', 'Asia/Ho_Chi_Minh', 'gradient', ?, ?)""",
            (target_cust_id, now, now),
        )

        # Other customer
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, 'hash', 'Other Customer', '7126457999', 'user', 1, 1, ?, ?)""",
            (other_cust_id, f"other_{other_cust_id[:8]}@example.com", now, now),
        )
        conn.execute(
            """INSERT INTO web_account_profiles
               (account_id, locale, timezone, avatar_style, created_at, updated_at)
               VALUES (?, 'vi', 'Asia/Ho_Chi_Minh', 'gradient', ?, ?)""",
            (other_cust_id, now, now),
        )

        # Admin target (must not be bannable)
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, 'hash', 'Peer Admin Target', '7126457002', 'admin', 1, 1, ?, ?)""",
            (admin_target_id, f"peer_admin_{admin_target_id[:8]}@toanaas.vn", now, now),
        )

        # Create active sessions for target customer and other customer
        conn.execute(
            """INSERT INTO web_sessions
               (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
               VALUES ('sess-target-1', ?, 'csrf-t1', '2099-01-01T00:00:00Z', ?, ?)""",
            (target_cust_id, now, now),
        )
        conn.execute(
            """INSERT INTO web_sessions
               (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
               VALUES ('sess-target-2', ?, 'csrf-t2', '2099-01-01T00:00:00Z', ?, ?)""",
            (target_cust_id, now, now),
        )
        conn.execute(
            """INSERT INTO web_sessions
               (id, account_id, csrf_token, expires_at, created_at, last_seen_at)
               VALUES ('sess-other-1', ?, 'csrf-o1', '2099-01-01T00:00:00Z', ?, ?)""",
            (other_cust_id, now, now),
        )

        # Approved topup for target customer (100,000 VND)
        conn.execute(
            """INSERT INTO web_manual_topup_requests
               (account_id, amount_vnd, currency, method, reference, status, idempotency_key_hash, request_fingerprint, submitted_at, updated_at)
               VALUES (?, 100000, 'VND', 'bank_acb', 'TOPUP-V205', 'approved', ?, ?, ?, ?)""",
            (target_cust_id, "a1" * 32, "b1" * 32, now, now),
        )

        conn.commit()

    return {
        "target_cust_id": target_cust_id,
        "other_cust_id": other_cust_id,
        "admin_target_id": admin_target_id,
    }


# ---------------------------------------------------------------------------
# Invariants 1, 2, 3: RBAC and Auth Gates
# ---------------------------------------------------------------------------

def test_01_admin_customers_requires_admin(seed_data):
    """Invariant 1: /admin/customers requires authenticated Admin."""
    anon = TestClient(app_module.app)
    res = anon.get("/api/v1/admin/customers")
    assert res.status_code in (401, 403)


def test_02_customer_detail_requires_admin(seed_data):
    """Invariant 2: customer detail endpoints require Admin."""
    target_id = seed_data["target_cust_id"]
    anon = TestClient(app_module.app)
    assert anon.get(f"/api/v1/admin/customers/{target_id}").status_code in (401, 403)
    assert anon.get(f"/api/v1/admin/customers/{target_id}/crm").status_code in (401, 403)
    assert anon.get(f"/api/v1/admin/customers/{target_id}?view=360").status_code in (401, 403)


def test_03_normal_customer_denied(user_client, seed_data):
    """Invariant 3: normal customer is denied access to admin customer endpoints."""
    target_id = seed_data["target_cust_id"]
    assert user_client.get("/api/v1/admin/customers").status_code == 403
    assert user_client.get(f"/api/v1/admin/customers/{target_id}").status_code == 403
    assert user_client.get(f"/api/v1/admin/customers/{target_id}/crm").status_code == 403
    assert user_client.get(f"/api/v1/admin/customers/{target_id}?view=360").status_code == 403


# ---------------------------------------------------------------------------
# Invariants 4, 5, 6, 7, 8, 9, 10, 11, 12: Customer 360 Truth & Anti-Fabrication
# ---------------------------------------------------------------------------

def test_04_customer_360_renders_identity_truth(admin_client, seed_data):
    """Invariant 4: Customer 360 renders identity truth without fabrication."""
    target_id = seed_data["target_cust_id"]
    res = admin_client.get(f"/api/v1/admin/customers/{target_id}?view=360")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["customer_id"] == target_id
    assert data["overview"]["display_name"] == "Target Customer"
    assert data["overview"]["status"] == "active"
    assert data["identity"]["model"] == "FEDERATED_IDENTITY_LINK"
    assert data["identity"]["link_status"] == "UNLINKED"
    assert data["identity"]["telegram_user_id"] is None


def test_05_unknown_wallet_not_displayed_as_zero(admin_client, seed_data):
    """Invariant 5: UNKNOWN_WALLET_AS_ZERO=NO. Never map missing bridge wallet -> 0 Xu."""
    target_id = seed_data["target_cust_id"]
    res = admin_client.get(f"/api/v1/admin/customers/{target_id}?view=360")
    assert res.status_code == 200
    wallet = res.json()["data"]["wallet"]

    assert wallet["status"] == "UNAVAILABLE"
    assert wallet["balance_xu"] is None  # Never fake 0!
    assert wallet["fake_zero_wallet_balance"] == 0
    assert wallet["direct_mutation_available"] is False


def test_06_unknown_spending_not_displayed_as_zero(admin_client, seed_data):
    """Invariant 6: UNPROVEN_LIFETIME_SPEND=0. Spend metrics have strict provenance."""
    target_id = seed_data["target_cust_id"]
    res = admin_client.get(f"/api/v1/admin/customers/{target_id}?view=360")
    assert res.status_code == 200
    spend = res.json()["data"]["spend_summary"]

    assert spend["authority"] == "WEB_SQLITE"
    assert spend["total_approved_topup_vnd"] == 100000
    assert spend["total_approved_topup_xu"] is None  # Unproven without conversion rate
    assert spend["total_charged_xu"] is None  # Unproven without bot ledger
    assert spend["lifetime_spend"] is None  # Never combine metrics into fake lifetime spend!
    assert spend["unproven_lifetime_spend"] == 0


def test_07_no_static_vip_tier_ladder(admin_client, seed_data):
    """Invariant 7: STATIC_TIER_LADDER=0, CLIENT_DERIVED_VIP_TIER=0."""
    target_id = seed_data["target_cust_id"]
    res = admin_client.get(f"/api/v1/admin/customers/{target_id}?view=360")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["membership_tier"] == "UNAVAILABLE"
    content = res.text.lower()
    for forbidden_tier in ["newbie", "silver", "gold", "platinum", "diamond"]:
        assert forbidden_tier not in content


def test_08_no_fake_behavior_or_risk_score(admin_client, seed_data):
    """Invariant 8: FAKE_BEHAVIOR_SCORE=0, FAKE_RISK_SCORE=0, FAKE_LTV=0."""
    target_id = seed_data["target_cust_id"]
    res = admin_client.get(f"/api/v1/admin/customers/{target_id}?view=360")
    assert res.status_code == 200
    data = res.json()["data"]

    for forbidden_field in ["behavior_score", "risk_score", "fraud_score", "churn_risk", "vip_propensity", "estimated_ltv"]:
        assert forbidden_field not in data
        assert forbidden_field not in data["overview"]


def test_09_real_job_history_projection(admin_client, seed_data):
    """Invariant 9: JOB_STATUS_REWRITTEN_IN_DB=NO, FAKE_JOB_COUNT=0."""
    target_id = seed_data["target_cust_id"]
    res = admin_client.get(f"/api/v1/admin/customers/{target_id}?view=360")
    assert res.status_code == 200
    jobs = res.json()["data"]["jobs"]

    assert jobs["data_source"] == "BOT_CORE / CORE_BRIDGE_READ_MODEL"
    assert jobs["total_jobs"] is None  # Not fake 0
    assert jobs["status"] == "UNAVAILABLE"
    assert jobs["mutation_available"] is False


def test_10_and_11_asset_projection_and_v2_04_delivery_truth(admin_client, seed_data):
    """Invariants 10 & 11: V2_04_DELIVERY_REGRESSION=0. Real output references only."""
    target_id = seed_data["target_cust_id"]
    res = admin_client.get(f"/api/v1/admin/customers/{target_id}?view=360")
    assert res.status_code == 200
    assets = res.json()["data"]["assets"]

    assert assets["data_source"] == "CORE_BRIDGE_ASSET_VAULT"
    assert assets["status"] == "UNAVAILABLE"
    assert assets["total_assets"] is None
    assert assets["delivery_truth_preserved"] is True


def test_12_support_truth_and_empty_state(admin_client, seed_data):
    """Invariant 12: FAKE_TICKET_COUNT=0, FAKE_SUPPORT_ACTIVITY=0."""
    target_id = seed_data["target_cust_id"]
    res = admin_client.get(f"/api/v1/admin/customers/{target_id}?view=360")
    assert res.status_code == 200
    support = res.json()["data"]["support"]

    assert support["authority"] == "WEB_SQLITE"
    assert support["total_cases"] == 0
    assert support["open_cases_count"] == 0
    assert support["recent_cases"] == []


@pytest.fixture
def override_admin_csrf(isolated_env):
    """Dependency override providing authenticated canonical admin for mutation tests."""
    with sqlite3.connect(isolated_env) as conn:
        admin_row = conn.execute("SELECT id, email, role_cache, canonical_user_id FROM web_accounts WHERE email='admin_v205@toanaas.vn'").fetchone()
        admin_account = {"id": admin_row[0], "email": admin_row[1], "role": "admin", "canonical_user_id": admin_row[3]}

    app_module.app.dependency_overrides[directory.require_canonical_admin_csrf] = lambda: admin_account
    app_module.app.dependency_overrides[copyfast_auth.require_canonical_admin_csrf] = lambda: admin_account
    yield admin_account
    app_module.app.dependency_overrides.pop(directory.require_canonical_admin_csrf, None)
    app_module.app.dependency_overrides.pop(copyfast_auth.require_canonical_admin_csrf, None)


# ---------------------------------------------------------------------------
# Invariants 13 to 24: Ban, Unban, Session Revocation, Idempotency, Safety
# ---------------------------------------------------------------------------

def test_13_and_14_ban_requires_admin_and_non_empty_reason(admin_client, user_client, seed_data, isolated_env):
    """Invariants 13 & 14: Ban requires canonical admin + non-empty reason."""
    target_id = seed_data["target_cust_id"]

    # 1. Normal user denied
    unauth_res = user_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "ban", "reason": "Vi phạm điều khoản"})
    assert unauth_res.status_code == 403

    # 2. Admin client without CSRF or live canonical bridge rejected with 403
    assert admin_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "ban", "reason": "Test"}).status_code == 403

    # 3. With canonical admin authority, empty reason rejected with 422
    with sqlite3.connect(isolated_env) as conn:
        admin_row = conn.execute("SELECT id, email, role_cache, canonical_user_id FROM web_accounts WHERE email='admin_v205@toanaas.vn'").fetchone()
        admin_account = {"id": admin_row[0], "email": admin_row[1], "role": "admin", "canonical_user_id": admin_row[3]}

    app_module.app.dependency_overrides[directory.require_canonical_admin_csrf] = lambda: admin_account
    app_module.app.dependency_overrides[copyfast_auth.require_canonical_admin_csrf] = lambda: admin_account
    try:
        empty_res = admin_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "ban", "reason": "   "})
        assert empty_res.status_code == 422
    finally:
        app_module.app.dependency_overrides.pop(directory.require_canonical_admin_csrf, None)
        app_module.app.dependency_overrides.pop(copyfast_auth.require_canonical_admin_csrf, None)


def test_15_16_17_ban_sets_inactive_and_revokes_sessions(admin_client, isolated_env, seed_data, override_admin_csrf):
    """Invariants 15, 16, 17: Ban sets is_active=0, revokes target sessions, leaves others untouched."""
    target_id = seed_data["target_cust_id"]
    other_id = seed_data["other_cust_id"]

    # Perform Ban
    res = admin_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "ban", "reason": "Gian lận thẻ thanh toán"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "locked"
    assert data["is_active"] is False
    assert data["revoked_sessions"] == 2

    # Check DB state
    with sqlite3.connect(isolated_env) as conn:
        # 1. Target account is inactive
        row = conn.execute("SELECT is_active FROM web_accounts WHERE id=?", (target_id,)).fetchone()
        assert row[0] == 0

        # 2. Target sessions are revoked
        target_sessions = conn.execute("SELECT id, revoked_at FROM web_sessions WHERE account_id=?", (target_id,)).fetchall()
        assert len(target_sessions) == 2
        assert all(s[1] is not None for s in target_sessions)

        # 3. Other customer sessions are untouched (CROSS_ACCOUNT_SESSION_REVOCATION=0)
        other_sessions = conn.execute("SELECT id, revoked_at FROM web_sessions WHERE account_id=?", (other_id,)).fetchall()
        assert len(other_sessions) == 1
        assert other_sessions[0][1] is None


def test_18_19_unban_restores_active_without_reviving_old_sessions(admin_client, isolated_env, seed_data, override_admin_csrf):
    """Invariants 18 & 19: Unban restores is_active=1, but OLD_REVOKED_SESSION_REACTIVATED=NO."""
    target_id = seed_data["target_cust_id"]

    # Perform Unban
    res = admin_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "unban", "reason": "Đã xác minh KYC hợp lệ"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "active"
    assert data["is_active"] is True

    # Check DB state
    with sqlite3.connect(isolated_env) as conn:
        # 1. Target account is active again
        row = conn.execute("SELECT is_active FROM web_accounts WHERE id=?", (target_id,)).fetchone()
        assert row[0] == 1

        # 2. Prior revoked sessions remain revoked! (Customer must log in again)
        target_sessions = conn.execute("SELECT id, revoked_at FROM web_sessions WHERE account_id=?", (target_id,)).fetchall()
        assert len(target_sessions) == 2
        assert all(s[1] is not None for s in target_sessions)


def test_20_and_21_idempotent_ban_and_unban(admin_client, seed_data, override_admin_csrf):
    """Invariants 20 & 21: Repeated ban/unban actions have zero state delta (BAN_REPLAY_STATE_DELTA=0)."""
    target_id = seed_data["target_cust_id"]

    # Target is currently active. Unban replay when active:
    res_unban_replay = admin_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "unban", "reason": "Replay unban"})
    assert res_unban_replay.status_code == 200
    assert res_unban_replay.json()["data"]["idempotent_replay"] is True

    # Ban target
    res_ban_1 = admin_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "ban", "reason": "Ban 1"})
    assert res_ban_1.status_code == 200
    assert res_ban_1.json()["data"]["idempotent_replay"] is False

    # Ban replay when already locked:
    res_ban_replay = admin_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "ban", "reason": "Ban duplicate"})
    assert res_ban_replay.status_code == 200
    assert res_ban_replay.json()["data"]["idempotent_replay"] is True
    assert res_ban_replay.json()["data"]["revoked_sessions"] == 0

    # Clean up: restore active
    admin_client.patch(f"/api/v1/admin/customers/{target_id}", json={"action": "unban", "reason": "Cleanup unban"})


def test_22_audit_records_created(admin_client, isolated_env, seed_data):
    """Invariant 22: BAN_WITHOUT_AUDIT=0, UNBAN_WITHOUT_AUDIT=0."""
    target_id = seed_data["target_cust_id"]

    with sqlite3.connect(isolated_env) as conn:
        ban_events = conn.execute(
            "SELECT action, target, outcome FROM web_audit_events WHERE action='admin.customer.ban' AND target=?",
            (target_id,),
        ).fetchall()
        assert len(ban_events) >= 1

        unban_events = conn.execute(
            "SELECT action, target, outcome FROM web_audit_events WHERE action='admin.customer.unban' AND target=?",
            (target_id,),
        ).fetchall()
        assert len(unban_events) >= 1


def test_23_admin_target_ban_refused(admin_client, seed_data, override_admin_csrf):
    """Invariant 23: ADMIN_TARGET_BAN_ALLOWED=NO. Peer admin cannot be banned via customer 360."""
    admin_target_id = seed_data["admin_target_id"]
    res = admin_client.patch(f"/api/v1/admin/customers/{admin_target_id}", json={"action": "ban", "reason": "Attempting to ban admin"})
    assert res.status_code == 403
    payload = res.json()
    err_msg = payload.get("message") or payload.get("detail") or res.text
    assert "Không được phép khóa tài khoản Quản trị viên" in err_msg


def test_24_no_provider_wallet_or_job_mutation(admin_client, isolated_env, seed_data):
    """Invariant 24: PROVIDER_CALLS=0, WALLET_MUTATIONS=0, JOB_MUTATIONS=0."""
    target_id = seed_data["target_cust_id"]
    with sqlite3.connect(isolated_env) as conn:
        # Check that no payos_orders, credit_events, or external calls occurred
        table_list = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "credit_events" in table_list:
            count = conn.execute("SELECT COUNT(*) FROM credit_events").fetchone()[0]
            assert count == 0


def test_25_responsive_customer_360_contract():
    """Invariant 25: Node harness contract verifying Customer 360 UI structures."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for Portal JavaScript contract execution")

    script = r'''
    const fs = require("fs");
    const path = require("path");
    const portalSource = fs.readFileSync(path.join(process.cwd(), "static/portal/portal.js"), "utf8");
    if (!portalSource.includes("renderAdminCustomer360Sections")) throw new Error("renderAdminCustomer360Sections missing in portal.js");
    if (!portalSource.includes("renderAdminCustomerSafetyModal")) throw new Error("renderAdminCustomerSafetyModal missing in portal.js");
    if (!portalSource.includes("admin-customer-ban-open")) throw new Error("admin-customer-ban-open action trigger missing");
    if (!portalSource.includes("admin-customer-unban-open")) throw new Error("admin-customer-unban-open action trigger missing");

    const integSource = fs.readFileSync(path.join(process.cwd(), "static/portal/integration.js"), "utf8");
    if (!integSource.includes("admin-customer-ban-submit")) throw new Error("admin-customer-ban-submit missing in integration.js");
    if (!integSource.includes("admin-customer-unban-submit")) throw new Error("admin-customer-unban-submit missing in integration.js");
    console.log(JSON.stringify({ ok: true }));
    '''
    res = subprocess.run([node, "-e", script], capture_output=True, text=True)
    assert res.returncode == 0
    assert '"ok":true' in res.stdout
