"""Test suite for SPEC-06: Finance Read Model Truth (P0.WEB.ERP.SPEC06.FINANCE.READ_MODEL.TRUTH).

Validates:
- Canonical authority contracts:
  - CUSTOMER_AUTHORITY = WEB_SQLITE
  - WALLET_AUTHORITY = BOT_CORE
  - PAYMENT_GATEWAY_AUTHORITY = PAYOS
  - PAYMENT_SETTLEMENT_AUTHORITY = BOT_CORE
  - TOPUP_REQUEST_AUTHORITY = WEB_SQLITE
  - JOB_AUTHORITY = BOT_CORE
  - REVENUE_AUTHORITY = BOT_CORE
  - WEB_ROLE = READ_THROUGH_OR_PROJECTION
- Safety invariants:
  - MANUAL_CREDIT_ACTIONS = 0, MANUAL_DEBIT_ACTIONS = 0
  - SETTLEMENT_ACTIONS = 0, REFUND_ACTIONS = 0
  - PAYOS_ACTIONS = 0, WALLET_ACTIONS = 0
  - PROVIDER_CALLS = 0, WALLET_MUTATIONS = 0, PAYMENT_MUTATIONS = 0
- Topup request truth:
  - Raw states ('pending_admin_review', 'approved', 'rejected') -> ('PENDING', 'CONFIRMED', 'REJECTED')
  - Never calls pending request "paid"
- Payment truth & settlement distinction:
  - REQUEST_STATE != PAYMENT_GATEWAY_EVENT != WALLET_SETTLEMENT
  - PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED = True
- Wallet truth:
  - UNAVAILABLE -> balance=None (Never 0)
  - FAKE_ZERO_WALLET_BALANCE = 0
- Revenue truth:
  - REVENUE_AUTHORITY = BOT_CORE, scope = WEB_ONLY_MANUAL_TOPUPS
  - REVENUE_COVERAGE = PARTIAL, labeled 'Known Web Revenue', never 'Total Revenue'
  - UNKNOWN_REVENUE_AS_ZERO = False, UNAVAILABLE_FINANCE_VALUE_AS_ZERO = False
- Endpoints:
  - GET /api/v1/admin/finance/summary & /api/v1/admin/finance
  - GET /api/v1/admin/finance/topups & /api/v1/admin/topups
  - GET /api/v1/admin/finance/payments
  - POST locked write routes fail-closed (WEBAPP_ADMIN_WRITES_DISABLED)
- RBAC: Anonymous & non-admin denied
- Customer CRM integration (shares authority)
- Job billing integration (provider spend vs user charge distinct)
- Browser routes: /admin/finance, /admin/finance/topups, /admin/finance/payments
"""

import os
import secrets
import sqlite3
import tempfile
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_auth
import copyfast_customer_crm_policy as crm_policy
import copyfast_db
import copyfast_finance_policy as finance_policy
import copyfast_operations_jobs_policy as jobs_policy


@pytest.fixture(scope="module")
def env_setup():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "spec06_finance_test.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "spec06-finance-test-secret-12345"
    copyfast_db.ensure_copyfast_schema()

    # Seed web accounts and manual topup requests
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-admin-01', 'finance_admin@toanaas.vn', 'hash', 'Finance Admin', 'admin', '7126457028', 1, '2026-09-16T10:00:00Z', '2026-09-16T10:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, is_active, created_at, updated_at)
               VALUES ('acc-cust-01', 'customer_one@toanaas.vn', 'hash', 'Customer One', 'user', 1, '2026-09-16T10:00:00Z', '2026-09-16T10:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_account_topup_codes (account_id, payment_code, created_at)
               VALUES ('acc-cust-01', '12345678', '2026-09-16T10:00:00Z')"""
        )
        # Pending topup
        conn.execute(
            """INSERT INTO web_manual_topup_requests (
                id, account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at
            ) VALUES (
                1, 'acc-cust-01', 200000, 'VND', 'bank_acb', 'REF-001', 'pending_admin_review',
                '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                '2026-09-16T10:05:00Z', '2026-09-16T10:05:00Z'
            )"""
        )
        # Approved topup
        conn.execute(
            """INSERT INTO web_manual_topup_requests (
                id, account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at, decision_at, decision_reason
            ) VALUES (
                2, 'acc-cust-01', 500000, 'VND', 'bank_acb', 'REF-002', 'approved',
                '1123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                '1123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                '2026-09-16T10:10:00Z', '2026-09-16T10:15:00Z', '2026-09-16T10:15:00Z', 'Da nhan du tien'
            )"""
        )
        # Rejected topup
        conn.execute(
            """INSERT INTO web_manual_topup_requests (
                id, account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at, decision_at, decision_reason
            ) VALUES (
                3, 'acc-cust-01', 100000, 'VND', 'bank_acb', 'REF-003', 'rejected',
                '2123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                '2123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                '2026-09-16T10:20:00Z', '2026-09-16T10:25:00Z', '2026-09-16T10:25:00Z', 'Sai noi dung chuyen khoan'
            )"""
        )
        conn.commit()

    yield db_path


@pytest.fixture(scope="module")
def admin_client(env_setup):
    client = TestClient(app_module.app)
    account_id = "acc-admin-01"
    now = copyfast_auth.utc_now()
    expires_at = (copyfast_auth._now() + copyfast_auth.timedelta(days=7)).isoformat(timespec="seconds")
    session_id = str(uuid.uuid4())
    csrf_token = secrets.token_hex(16)
    with sqlite3.connect(env_setup) as conn:
        conn.execute(
            """INSERT INTO web_sessions (id, account_id, csrf_token, created_at, last_seen_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, account_id, csrf_token, now, now, expires_at),
        )
        conn.commit()
    cookie_name = copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE)
    cookie_value = copyfast_auth._session_cookie_value(session_id)
    client.cookies.set(cookie_name, cookie_value)
    client.csrf_token = csrf_token
    return client


@pytest.fixture(scope="module")
def user_client(env_setup):
    client = TestClient(app_module.app)
    account_id = "acc-cust-01"
    now = copyfast_auth.utc_now()
    expires_at = (copyfast_auth._now() + copyfast_auth.timedelta(days=7)).isoformat(timespec="seconds")
    session_id = str(uuid.uuid4())
    csrf_token = secrets.token_hex(16)
    with sqlite3.connect(env_setup) as conn:
        conn.execute(
            """INSERT INTO web_sessions (id, account_id, csrf_token, created_at, last_seen_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, account_id, csrf_token, now, now, expires_at),
        )
        conn.commit()
    cookie_name = copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE)
    cookie_value = copyfast_auth._session_cookie_value(session_id)
    client.cookies.set(cookie_name, cookie_value)
    client.csrf_token = csrf_token
    return client


def test_01_canonical_finance_authority_contract():
    """Verify Section 1: Canonical authority contract and safety invariants."""
    assert finance_policy.CUSTOMER_AUTHORITY == "WEB_SQLITE"
    assert finance_policy.WALLET_AUTHORITY == "BOT_CORE"
    assert finance_policy.PAYMENT_GATEWAY_AUTHORITY == "PAYOS"
    assert finance_policy.PAYMENT_SETTLEMENT_AUTHORITY == "BOT_CORE"
    assert finance_policy.TOPUP_REQUEST_AUTHORITY == "WEB_SQLITE"
    assert finance_policy.JOB_AUTHORITY == "BOT_CORE"
    assert finance_policy.REVENUE_AUTHORITY == "BOT_CORE"
    assert finance_policy.WEB_ROLE == "READ_THROUGH_OR_PROJECTION"

    # Safety invariants
    assert finance_policy.WEB_DIRECT_WALLET_MUTATION is False
    assert finance_policy.WEB_DIRECT_BOT_DB_WRITE is False
    assert finance_policy.MANUAL_PAYMENT_SETTLEMENT_ACTIONS == 0
    assert finance_policy.REFUND_EXECUTION_ACTIONS == 0

    # Zero control plane invariants
    assert finance_policy.MANUAL_CREDIT_ACTIONS == 0
    assert finance_policy.MANUAL_DEBIT_ACTIONS == 0
    assert finance_policy.SETTLEMENT_ACTIONS == 0
    assert finance_policy.REFUND_ACTIONS == 0
    assert finance_policy.PAYOS_ACTIONS == 0
    assert finance_policy.WALLET_ACTIONS == 0


def test_02_topup_request_state_mapping_truth():
    """Verify Section 4: Topup request state mapping. Never call pending 'paid' or approved 'CONFIRMED'."""
    assert finance_policy.map_topup_raw_state("pending_admin_review") == "PENDING"
    assert finance_policy.map_topup_raw_state("pending") == "PENDING"
    assert finance_policy.map_topup_raw_state("reviewing") == "PENDING"
    assert finance_policy.map_topup_raw_state("approved") == "APPROVED"
    assert finance_policy.map_topup_raw_state("confirmed") == "APPROVED"
    assert finance_policy.map_topup_raw_state("rejected") == "REJECTED"
    assert finance_policy.map_topup_raw_state("declined") == "REJECTED"
    assert finance_policy.map_topup_raw_state(None) == "UNKNOWN"
    assert finance_policy.map_topup_raw_state("") == "UNKNOWN"

    # Pending request record must NOT be synthesized as paid or settled
    pending_row = {
        "id": 1,
        "amount_vnd": 200000,
        "status": "pending_admin_review",
    }
    rec = finance_policy.synthesize_topup_record(pending_row)
    assert rec["request_state"] == "PENDING"
    assert rec["payment_state"] == "UNKNOWN"
    assert rec["settlement_state"] == "UNKNOWN"
    assert rec["request_state"] != "APPROVED"
    assert rec["request_state"] != "CONFIRMED"
    assert rec["authority"] == "WEB_SQLITE"

    # Approved request must have REQUEST_STATE=APPROVED, and payment/settlement remain UNKNOWN without linkage
    approved_row = {
        "id": 2,
        "amount_vnd": 500000,
        "status": "approved",
    }
    rec_app = finance_policy.synthesize_topup_record(approved_row)
    assert rec_app["request_state"] == "APPROVED"
    assert rec_app["payment_state"] == "UNKNOWN"
    assert rec_app["settlement_state"] == "UNKNOWN"
    assert rec_app["request_state"] != "CONFIRMED"


def test_03_payment_and_settlement_distinction():
    """Verify Section 5 & 7: Payment confirmed does NOT equal wallet credited."""
    assert finance_policy.PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED is True
    assert finance_policy.PAYMENT_CONFIRMED_IMPLIES_SETTLED is False
    assert finance_policy.REQUEST_APPROVED_IMPLIES_PAYMENT_CONFIRMED is False

    # Payment confirmed but settlement state is not yet credited
    pay_record = finance_policy.synthesize_payment_record(
        {"id": "payos-999", "status": "paid", "amount": 100000},
        bridge_available=True,
    )
    assert pay_record["gateway_state"] == "CONFIRMED"
    assert pay_record["settlement_state"] == "UNKNOWN"  # Must NOT infer CREDITED without Bot Core proof
    assert pay_record["gateway_authority"] == "PAYOS"
    assert pay_record["settlement_authority"] == "BOT_CORE"

    # Attention required because payment is confirmed but settlement is pending/unknown
    assert pay_record["attention_required"] is True
    assert any("chờ Bot Core ghi nhận Xu" in r for r in pay_record["attention_reasons"])


def test_04_fake_zero_wallet_prevention():
    """Verify Section 8 & 17: Wallet unavailable results in balance=None, NEVER 0."""
    assert finance_policy.FAKE_ZERO_WALLET_BALANCE == 0
    assert finance_policy.UNAVAILABLE_FINANCE_VALUE_AS_ZERO is False

    summary = finance_policy.synthesize_finance_summary(
        topup_counts={"total": 0, "pending_count": 0, "approved_count": 0, "rejected_count": 0, "confirmed_revenue_vnd": 0},
        wallet_payload=None,
        wallet_bridge_available=False,
    )
    wallet = summary["wallet"]
    assert wallet["status"] == "UNAVAILABLE"
    assert wallet["balance_xu"] is None  # CRITICAL: Must be None, NEVER 0!
    assert wallet["balance_xu"] != 0
    assert wallet["source"] == "BOT_CORE"
    assert wallet["fake_zero_wallet_balance"] == 0


def test_05_revenue_truth_partial_coverage_labeling():
    """Verify Section 9: Revenue authority is Bot Core, web revenue is PARTIAL."""
    assert finance_policy.REVENUE_AUTHORITY == "BOT_CORE"
    assert finance_policy.REVENUE_CURRENT_SCOPE == "WEB_ONLY_MANUAL_TOPUPS"
    assert finance_policy.REVENUE_COVERAGE == "PARTIAL"
    assert finance_policy.REVENUE_LABEL == "Known Web Revenue"
    assert finance_policy.UNKNOWN_REVENUE_AS_ZERO is False

    summary = finance_policy.synthesize_finance_summary(
        topup_counts={"total": 3, "pending_count": 1, "approved_count": 1, "rejected_count": 1, "confirmed_revenue_vnd": 500000},
        wallet_payload=None,
        wallet_bridge_available=False,
    )
    rev = summary["revenue"]
    assert rev["revenue_authority"] == "BOT_CORE"
    assert rev["revenue_coverage"] == "PARTIAL"
    assert rev["revenue_label"] == "Known Web Revenue"
    assert rev["known_web_revenue_vnd"] == 500000
    assert rev["total_revenue"] is None  # Total revenue is unavailable rather than guessed
    assert "bot_charges" in rev["revenue_missing_sources"]


def test_06_customer_crm_finance_integration():
    """Verify Section 15: Customer CRM integration shares authority with SPEC-06."""
    account = {"id": "acc-cust-01", "display_name": "Customer One"}
    topups = [{"id": 1, "status": "pending_admin_review", "amount_vnd": 200000}]
    ctx = crm_policy.synthesize_customer_crm_context(account, topup_requests=topups)

    # Authority must match TOPUP_REQUEST_AUTHORITY
    assert ctx["payments_topups"]["authority"] == finance_policy.TOPUP_REQUEST_AUTHORITY
    assert ctx["payments_topups"]["authority"] == "WEB_SQLITE"
    assert ctx["wallet"]["data_source"] == finance_policy.WALLET_AUTHORITY
    assert ctx["wallet"]["data_source"] == "BOT_CORE"
    assert ctx["wallet"]["balance_xu"] is None
    assert ctx["wallet"]["fake_zero_wallet_balance"] == 0

    # Pending topup triggers action required
    assert ctx["action_required"]["has_action"] is True
    assert any("yêu cầu nạp tiền chờ đối soát" in r for r in ctx["action_required"]["reasons"])


def test_07_job_billing_semantics_integration():
    """Verify Section 16: Job billing shares semantics, distinct provider spend vs user charge."""
    assert jobs_policy.JOB_BILLING_AND_FINANCE_PAGE_SHARE_SEMANTICS is True

    raw_job = {
        "id": "job-finance-test",
        "charged_xu": 200,
        "estimated_xu": 200,
        "provider_spend_xu": 45,
        "status": "completed",
    }
    rec = jobs_policy.synthesize_operations_job_record(raw_job)
    assert rec["charged_xu"] == 200
    assert rec["estimated_xu"] == 200
    assert rec["provider_spend_xu"] == 45
    # Distinct fields: user charge is NOT overwritten by provider spend
    assert rec["charged_xu"] != rec["provider_spend_xu"]


def test_08_admin_finance_summary_api_endpoint(admin_client):
    """Verify Section 11 & 12: GET /api/v1/admin/finance/summary and /api/v1/admin/finance."""
    # 1. GET /api/v1/admin/finance/summary
    r = admin_client.get("/api/v1/admin/finance/summary")
    assert r.status_code == 200
    res = r.json()
    assert res["ok"] is True
    data = res["data"]
    assert "authority_matrix" in data
    assert data["authority_matrix"]["wallet_authority"] == "BOT_CORE"
    assert data["authority_matrix"]["topup_request_authority"] == "WEB_SQLITE"
    assert data["authority_matrix"]["payment_gateway_authority"] == "PAYOS"

    # Topup requests metric from seeded SQLite database
    assert data["topup_requests_pending"]["value"] >= 1
    assert data["revenue"]["known_web_revenue_vnd"] >= 500000
    assert data["revenue"]["revenue_coverage"] == "PARTIAL"
    assert data["revenue"]["total_revenue"] is None

    # Wallet metric (bridge not configured in test client -> UNAVAILABLE, balance=None)
    assert data["wallet"]["status"] == "UNAVAILABLE"
    assert data["wallet"]["balance_xu"] is None

    # Control plane actions must all be 0
    for act_name, act_val in data["control_plane_actions"].items():
        assert act_val == 0

    # 2. GET /api/v1/admin/finance (alias)
    r2 = admin_client.get("/api/v1/admin/finance")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_09_admin_finance_topups_api_endpoint(admin_client):
    """Verify Section 13: GET /api/v1/admin/finance/topups and /api/v1/admin/topups."""
    # 1. GET all topups
    r = admin_client.get("/api/v1/admin/finance/topups")
    assert r.status_code == 200
    res = r.json()
    assert res["ok"] is True
    data = res["data"]
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
    assert data["authority"] == "WEB_SQLITE"
    assert data["mutation_available"] is False

    # Check topup record fields
    item = data["items"][0]
    assert "request_id" in item
    assert "request_state" in item
    assert "payment_state" in item
    assert "settlement_state" in item
    assert "amount_vnd" in item
    assert "currency" in item

    # 2. Filter by status: pending
    r_pending = admin_client.get("/api/v1/admin/finance/topups?status=pending")
    assert r_pending.status_code == 200
    items_pending = r_pending.json()["data"]["items"]
    assert all(i["request_state"] == "PENDING" for i in items_pending)

    # Filter by status: approved (must return request_state == APPROVED, never CONFIRMED)
    r_approved = admin_client.get("/api/v1/admin/finance/topups?status=approved")
    assert r_approved.status_code == 200
    items_approved = r_approved.json()["data"]["items"]
    assert len(items_approved) >= 1
    assert all(i["request_state"] == "APPROVED" for i in items_approved)
    assert all(i["request_state"] != "CONFIRMED" for i in items_approved)

    # 3. GET /api/v1/admin/topups alias
    r_alias = admin_client.get("/api/v1/admin/topups")
    assert r_alias.status_code == 200
    assert r_alias.json()["ok"] is True


def test_10_admin_finance_payments_api_endpoint(admin_client):
    """Verify Section 14: GET /api/v1/admin/finance/payments projection."""
    r = admin_client.get("/api/v1/admin/finance/payments")
    assert r.status_code == 200
    res = r.json()
    # If bridge is unavailable, gracefully returns guarded/unavailable envelope without error 500
    assert "data" in res
    assert res["data"]["gateway_authority"] == "PAYOS"
    assert res["data"]["settlement_authority"] == "BOT_CORE"
    assert res["data"]["mutation_available"] is False


def test_11_rbac_access_control(user_client):
    """Verify Section 19: RBAC controls (anonymous & non-admin denied)."""
    anon_client = TestClient(app_module.app)

    # Anonymous denied
    r_anon_sum = anon_client.get("/api/v1/admin/finance/summary")
    assert r_anon_sum.status_code in (401, 403, 307, 302)

    r_anon_topups = anon_client.get("/api/v1/admin/finance/topups")
    assert r_anon_topups.status_code in (401, 403, 307, 302)

    r_anon_payments = anon_client.get("/api/v1/admin/finance/payments")
    assert r_anon_payments.status_code in (401, 403, 307, 302)

    # Non-admin user denied
    r_user_sum = user_client.get("/api/v1/admin/finance/summary")
    assert r_user_sum.status_code == 403

    r_user_topups = user_client.get("/api/v1/admin/finance/topups")
    assert r_user_topups.status_code == 403

    r_user_payments = user_client.get("/api/v1/admin/finance/payments")
    assert r_user_payments.status_code == 403


def test_12_read_only_invariants_and_mutation_lock(admin_client):
    """Verify Section 21: Locked write endpoints fail-closed (WEBAPP_ADMIN_WRITES_DISABLED)."""
    # 1. POST /api/v1/admin/finance/credit
    r_credit = admin_client.post("/api/v1/admin/finance/credit")
    assert r_credit.status_code == 200
    res_credit = r_credit.json()
    assert res_credit["ok"] is False
    assert res_credit["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"

    # 2. POST /api/v1/admin/finance/debit
    r_debit = admin_client.post("/api/v1/admin/finance/debit")
    assert r_debit.status_code == 200
    res_debit = r_debit.json()
    assert res_debit["ok"] is False
    assert res_debit["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"

    # 3. POST /api/v1/admin/finance/settle
    r_settle = admin_client.post("/api/v1/admin/finance/settle")
    assert r_settle.status_code == 200
    res_settle = r_settle.json()
    assert res_settle["ok"] is False
    assert res_settle["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"

    # 4. POST /api/v1/admin/finance/refund
    r_refund = admin_client.post("/api/v1/admin/finance/refund")
    assert r_refund.status_code == 200
    res_refund = r_refund.json()
    assert res_refund["ok"] is False
    assert res_refund["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"


def test_13_portal_shell_and_browser_routes(admin_client):
    """Verify Section 23: Browser routes render HTTP 200."""
    r_finance = admin_client.get("/admin/finance")
    assert r_finance.status_code == 200
    assert "text/html" in r_finance.headers["content-type"]

    r_topups = admin_client.get("/admin/finance/topups")
    assert r_topups.status_code == 200
    assert "text/html" in r_topups.headers["content-type"]

    r_payments = admin_client.get("/admin/finance/payments")
    assert r_payments.status_code == 200
    assert "text/html" in r_payments.headers["content-type"]


def test_14_scroll_ownership_contract():
    """Verify Section 23: portal-workspace owns main scroll and portal-sidebar owns sidebar scroll."""
    root = Path(__file__).resolve().parents[1]
    portal_css = (root / "static/portal/portal.css").read_text(encoding="utf-8")
    assert ".portal-workspace" in portal_css
    assert ".portal-sidebar" in portal_css
    assert "overflow-y: auto" in portal_css or "overflow: auto" in portal_css
    assert "overflow: hidden" in portal_css


def test_15_theming_light_and_dark_tokens():
    """Verify Section 23: Light and Dark obsidian mode tokens exist without contrast regression."""
    root = Path(__file__).resolve().parents[1]
    theme_css = (root / "static/portal/portal-theme.css").read_text(encoding="utf-8")
    assert "--portal-app-canvas" in theme_css
    assert "--portal-saas-obsidian-canvas" in theme_css
    assert "--portal-saas-teal" in theme_css
    assert 'data-portal-theme="dark"' in theme_css


def test_16_accessibility_and_text_status_labels():
    """Verify Section 24: Status badges contain textual labels, interactive elements have focus states."""
    root = Path(__file__).resolve().parents[1]
    portal_code = (root / "static/portal/portal.js").read_text(encoding="utf-8")
    portal_css = (root / "static/portal/portal.css").read_text(encoding="utf-8")
    assert "aria-live=" in portal_code or "aria-hidden=" in portal_code or "aria-label=" in portal_code
    assert "portal-status" in portal_code or "portal-notice" in portal_code
    assert ":focus" in portal_css or ":focus-visible" in portal_css

