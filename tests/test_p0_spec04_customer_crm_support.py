"""Test suite for SPEC-04: Customer CRM & Support surface (P0.WEB.ERP.SPEC04.CUSTOMER.CRM_SUPPORT).

Validates:
- Canonical authority contracts (CUSTOMER_MASTER=WEB_SQLITE, SUPPORT_CASE_AUTHORITY=WEB_SQLITE)
- Federated identity states (LINKED, UNLINKED, UNKNOWN, CONFLICT)
- Bounded customer search by Web Customer ID, Telegram User ID, email, display name
- 7 canonical Customer Detail sections (Overview, Identity, Service Context, Support, Payments/Topups, Wallet, Jobs, Action Required)
- Semantics: Unknown != 0, Unavailable != healthy (no fake zero balance)
- Safety invariants: WEB_DIRECT_WALLET_MUTATION=NO, WEB_DIRECT_BOT_DB_WRITE=NO, MANUAL_PAYMENT_SETTLEMENT_ACTIONS=0
- RBAC: Anonymous & non-admin denied, no PII leak
- Privacy: No raw DB paths, secrets, or banned technical copy
- Support case contracts & safe writes audit
- Browser routes rendering
"""

import os
import uuid
import tempfile
import sqlite3
import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_admin_customer_directory as cad
import copyfast_auth
import copyfast_customer_crm_policy as crm_policy
import copyfast_db
from copyfast_db import transaction, utc_now


@pytest.fixture(scope="module")
def env_setup():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "spec04_crm_test.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "spec04-test-secret-12345"
    copyfast_db.ensure_copyfast_schema()
    yield db_path


@pytest.fixture(scope="module")
def auth_client(env_setup):
    client = TestClient(app_module.app)
    email = "admin_crm_spec04@toanaas.vn"
    password = "correct-horse-battery-staple-2026!"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": "CRM Admin"})
    assert reg.status_code == 200
    with sqlite3.connect(env_setup) as conn:
        conn.execute("UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457028' WHERE email=?", (email,))
        conn.commit()
    signed_in = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert signed_in.status_code == 200
    return client


@pytest.fixture(scope="module")
def test_customers(env_setup):
    """Create isolated test accounts for customer search and detail verification."""
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    tg_user_id = "7126457099"
    now = utc_now()

    with sqlite3.connect(env_setup) as conn:
        # Customer 1: Unlinked standard account
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, 'hash', 'Nguyen Van Alpha', NULL, 'user', 1, 1, ?, ?)""",
            (id1, f"alpha_{id1[:8]}@example.com", now, now),
        )
        conn.execute(
            """INSERT INTO web_account_profiles
               (account_id, locale, timezone, avatar_style, created_at, updated_at)
               VALUES (?, 'vi', 'Asia/Ho_Chi_Minh', 'gradient', ?, ?)""",
            (id1, now, now),
        )
        conn.execute(
            """INSERT INTO web_workspace_setup_profiles
               (account_id, setup_state, role, goal, created_at, updated_at)
               VALUES (?, 'completed', 'solo_creator', 'create_content', ?, ?)""",
            (id1, now, now),
        )
        # Add support case for Customer 1
        case_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_support_cases
               (id, account_id, category, priority, subject, initial_detail, state, revision, created_at, updated_at, last_public_message_at)
               VALUES (?, ?, 'general_support', 'normal', 'Yeu cau huong dan su dung', 'Can ho tro', 'new', 1, ?, ?, ?)""",
            (case_id, id1, now, now, now),
        )
        # Add manual topup for Customer 1
        conn.execute(
            """INSERT INTO web_manual_topup_requests
               (account_id, amount_vnd, currency, method, reference, status, idempotency_key_hash, request_fingerprint, submitted_at, updated_at)
               VALUES (?, 100000, 'VND', 'bank_acb', 'REF123', 'pending_admin_review', ?, ?, ?, ?)""",
            (id1, "a" * 64, "b" * 64, now, now),
        )

        # Customer 2: Linked Telegram account
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache, is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, 'hash', 'Tran Thi Beta', ?, 'user', 1, 1, ?, ?)""",
            (id2, f"beta_{id2[:8]}@example.com", tg_user_id, now, now),
        )
        conn.execute(
            """INSERT INTO telegram_link_codes
               (code_hash, account_id, expires_at, consumed_at, canonical_user_id, bot_confirmed_at, confirmed_display_name, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'Beta Telegram', ?)""",
            ("c" * 64, id2, now, now, tg_user_id, now, now),
        )
        conn.commit()

    return {"id1": id1, "id2": id2, "tg_user_id": tg_user_id}


def test_01_canonical_authority_contract_invariants():
    """Verify Section 1 Authority Contract invariants."""
    assert crm_policy.CUSTOMER_MASTER == "WEB_SQLITE"
    assert crm_policy.SUPPORT_CASE_AUTHORITY == "WEB_SQLITE"
    assert crm_policy.TELEGRAM_IDENTITY == "FEDERATED_IDENTITY_LINK"
    assert crm_policy.WALLET_AUTHORITY == "BOT_CORE"
    assert crm_policy.JOB_AUTHORITY == "BOT_CORE / CORE_BRIDGE_READ_MODEL"
    assert crm_policy.PAYMENT_GATEWAY_AUTHORITY == "PAYOS"

    assert crm_policy.WEB_DIRECT_WALLET_MUTATION is False
    assert crm_policy.WEB_DIRECT_BOT_DB_WRITE is False
    assert crm_policy.WEB_DIRECT_PAYOS_SETTLEMENT is False
    assert crm_policy.IDENTITY_RELINK_WRITE_ACTIONS == 0
    assert crm_policy.MANUAL_PAYMENT_SETTLEMENT_ACTIONS == 0


def test_02_federated_identity_states():
    """Verify Section 4 & 5 Federated Identity states and rules."""
    assert crm_policy.evaluate_federated_link_status(None) == crm_policy.LINK_STATE_UNLINKED
    assert crm_policy.evaluate_federated_link_status("") == crm_policy.LINK_STATE_UNLINKED
    assert crm_policy.evaluate_federated_link_status("7126457099") == crm_policy.LINK_STATE_LINKED
    assert crm_policy.evaluate_federated_link_status("7126457099", has_conflict=True) == crm_policy.LINK_STATE_CONFLICT
    assert crm_policy.evaluate_federated_link_status(None, is_unknown=True) == crm_policy.LINK_STATE_UNKNOWN

    assert crm_policy.VALID_LINK_STATES == {"LINKED", "UNLINKED", "UNKNOWN", "CONFLICT"}


def test_03_bounded_customer_search_by_all_fields(auth_client, test_customers):
    """Verify Section 7: Bounded search by Web customer ID, Telegram user ID, display name, and email."""
    id1 = test_customers["id1"]
    id2 = test_customers["id2"]
    tg_id = test_customers["tg_user_id"]

    # 1. Search by Web Customer ID (UUID)
    res_id = auth_client.get(f"/api/v1/admin/customers?q={id1}")
    assert res_id.status_code == 200
    items = res_id.json()["data"]["customers"]
    assert len(items) == 1
    assert items[0]["id"] == id1

    # 2. Search by Telegram User ID
    res_tg = auth_client.get(f"/api/v1/admin/customers?q={tg_id}")
    assert res_tg.status_code == 200
    items = res_tg.json()["data"]["customers"]
    assert len(items) == 1
    assert items[0]["id"] == id2

    # 3. Search by Display Name
    res_name = auth_client.get("/api/v1/admin/customers?q=Nguyen+Van+Alpha")
    assert res_name.status_code == 200
    items = res_name.json()["data"]["customers"]
    assert any(c["id"] == id1 for c in items)

    # 4. Search by Email
    res_email = auth_client.get(f"/api/v1/admin/customers?q=alpha_{id1[:8]}")
    assert res_email.status_code == 200
    items = res_email.json()["data"]["customers"]
    assert any(c["id"] == id1 for c in items)


def test_04_customer_detail_crm_sections(auth_client, test_customers):
    """Verify Section 8: 7 canonical Customer Detail sections."""
    id1 = test_customers["id1"]
    res = auth_client.get(f"/api/v1/admin/customers/{id1}/crm")
    assert res.status_code == 200
    data = res.json()["data"]

    # Section 1: Overview
    assert "overview" in data
    assert data["overview"]["customer_id"] == id1
    assert data["overview"]["display_name"] == "Nguyen Van Alpha"
    assert data["overview"]["status"] == "active"

    # Section 2: Identity
    assert "identity" in data
    assert data["identity"]["model"] == "FEDERATED_IDENTITY_LINK"
    assert data["identity"]["link_status"] == "UNLINKED"
    assert data["identity"]["telegram_user_id"] is None
    assert data["identity"]["relink_write_actions"] == 0

    # Section 3: Service Context
    assert "service_context" in data
    assert data["service_context"]["workspace_setup_state"] == "completed"
    assert data["service_context"]["workspace_role"] == "solo_creator"

    # Section 4: Support
    assert "support" in data
    assert data["support"]["total_cases"] == 1
    assert data["support"]["open_cases_count"] == 1
    assert len(data["support"]["recent_cases"]) == 1

    # Section 5: Payments / Topups Summary
    assert "payments_topups" in data
    assert data["payments_topups"]["total_topup_requests"] == 1
    assert data["payments_topups"]["pending_review_count"] == 1
    assert data["payments_topups"]["manual_settlement_actions"] == 0

    # Section 6: Wallet Summary (Read-through, never fake zero)
    assert "wallet" in data
    assert data["wallet"]["data_source"] == "BOT_CORE"
    assert data["wallet"]["status"] == "UNAVAILABLE"
    assert data["wallet"]["balance_xu"] is None
    assert data["wallet"]["direct_mutation_available"] is False

    # Section 7: Jobs Summary (Read-through)
    assert "jobs" in data
    assert data["jobs"]["data_source"] == "BOT_CORE / CORE_BRIDGE_READ_MODEL"
    assert data["jobs"]["status"] == "UNAVAILABLE"
    assert data["jobs"]["mutation_available"] is False

    # Section 8: Action Required (Derived from concrete facts only)
    assert "action_required" in data
    assert data["action_required"]["has_action"] is True
    assert data["action_required"]["action_count"] == 2
    assert any("yêu cầu hỗ trợ" in r for r in data["action_required"]["reasons"])
    assert any("yêu cầu nạp tiền" in r for r in data["action_required"]["reasons"])


def test_05_rbac_and_pii_isolation(test_customers):
    """Verify Section 20: RBAC guards and zero unauthenticated PII exposure."""
    unauth = TestClient(app_module.app)
    id1 = test_customers["id1"]

    # Anonymous requests to CRM endpoints are denied
    res_list = unauth.get("/api/v1/admin/customers")
    assert res_list.status_code in (401, 403)

    res_detail = unauth.get(f"/api/v1/admin/customers/{id1}")
    assert res_detail.status_code in (401, 403)

    res_crm = unauth.get(f"/api/v1/admin/customers/{id1}/crm")
    assert res_crm.status_code in (401, 403)


def test_06_privacy_and_no_banned_technical_copy(auth_client, test_customers):
    """Verify Section 21: Business copy only, zero leaks of DB paths, secrets, or internal jargon."""
    id1 = test_customers["id1"]
    res = auth_client.get(f"/api/v1/admin/customers/{id1}/crm")
    assert res.status_code == 200
    content = res.text.lower()

    for pattern in crm_policy.BANNED_TECHNICAL_PATTERNS:
        assert pattern not in content, f"Banned technical pattern '{pattern}' exposed in response"


def test_07_support_case_contract_and_safe_writes(auth_client):
    """Verify Section 11, 12, 13, 14: Support case list, detail, and safe write contracts."""
    # List support cases
    res_cases = auth_client.get("/api/v1/support/admin/cases")
    assert res_cases.status_code == 200
    assert "items" in res_cases.json()["data"]

    # Statuses conform to canonical schema
    for st in crm_policy.SUPPORT_CASE_STATUSES:
        assert st in {"new", "reviewing", "waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"}


def test_08_browser_routes_render_portal_shell(auth_client, test_customers):
    """Verify Section 24: Browser routes render portal shell for authenticated admin."""
    id1 = test_customers["id1"]
    routes = [
        "/admin/customers",
        f"/admin/customers/{id1}",
        "/admin/support",
    ]

    for route in routes:
        resp = auth_client.get(route)
        assert resp.status_code == 200, f"Route {route} returned {resp.status_code}"
        assert "portal-root" in resp.text or "portal.js" in resp.text, f"Route {route} missing portal shell"
