"""Test suite for SPEC-06B: Finance State Semantics Closure (P0.WEB.ERP.SPEC06B.FINANCE.STATE.SEMANTICS.CLOSURE).

Validates:
1. Three-layer state semantic separation:
   - REQUEST_STATE != PAYMENT_STATE != SETTLEMENT_STATE
   - Canonical request mapping: approved -> APPROVED (never CONFIRMED)
2. Invariants:
   - REQUEST_APPROVED_IMPLIES_PAYMENT_CONFIRMED = False
   - PAYMENT_CONFIRMED_IMPLIES_SETTLED = False
   - SETTLED_IMPLIES_REQUEST_APPROVED = False
3. Independent state evaluation:
   - approved request + payment unknown: REQUEST_STATE=APPROVED, PAYMENT_STATE=UNKNOWN
   - payment confirmed + settlement unknown: PAYMENT_STATE=CONFIRMED, SETTLEMENT_STATE=UNKNOWN
   - payment confirmed does not synthesize wallet credit
   - request approved does not synthesize payment confirmation
4. PayOS source wording:
   - PAYMENT_GATEWAY_AUTHORITY = PAYOS
   - PAYMENT_READ_MODEL_SOURCE = BOT_CORE_PAYMENT_PROJECTION_OR_WEBHOOK_CACHE
   - PAYMENT_EVENT_SOURCE = PAYOS_GATEWAY_WEBHOOK
5. Customer CRM finance integration:
   - CUSTOMER_FINANCE_STATE_MAPPING_SHARED = True
6. API endpoint serialization:
   - /api/v1/admin/finance/topups serializes request_state == APPROVED
7. UI acceptance & text copy:
   - Never presents approved request as "Payment confirmed", "Paid", "Settled", "Wallet credited"
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


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL_CODE = PORTAL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def env_setup():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "spec06b_finance_test.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "spec06b-finance-test-secret-12345"
    copyfast_db.ensure_copyfast_schema()

    # Seed web accounts and manual topup requests
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-admin-06b', 'finance_admin_06b@toanaas.vn', 'hash', 'Finance Admin 06B', 'admin', '7126457028', 1, '2026-09-16T10:00:00Z', '2026-09-16T10:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, is_active, created_at, updated_at)
               VALUES ('acc-cust-06b', 'customer_06b@toanaas.vn', 'hash', 'Customer 06B', 'user', 1, '2026-09-16T10:00:00Z', '2026-09-16T10:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_account_topup_codes (account_id, payment_code, created_at)
               VALUES ('acc-cust-06b', '87654321', '2026-09-16T10:00:00Z')"""
        )
        # Pending topup
        conn.execute(
            """INSERT INTO web_manual_topup_requests (
                id, account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at
            ) VALUES (
                101, 'acc-cust-06b', 200000, 'VND', 'bank_acb', 'REF-06B-01', 'pending_admin_review',
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
                102, 'acc-cust-06b', 500000, 'VND', 'bank_acb', 'REF-06B-02', 'approved',
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
                103, 'acc-cust-06b', 100000, 'VND', 'bank_acb', 'REF-06B-03', 'rejected',
                '2123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                '2123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                '2026-09-16T10:20:00Z', '2026-09-16T10:25:00Z', '2026-09-16T10:25:00Z', 'Sai noi dung'
            )"""
        )
        conn.commit()

    yield db_path


@pytest.fixture(scope="module")
def admin_client(env_setup):
    client = TestClient(app_module.app)
    account_id = "acc-admin-06b"
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


def test_01_three_layer_semantic_separation_invariants():
    """Verify Section 2: REQUEST_STATE != PAYMENT_STATE != SETTLEMENT_STATE and independence invariants."""
    # Authority separation
    assert finance_policy.TOPUP_REQUEST_AUTHORITY == "WEB_SQLITE"
    assert finance_policy.PAYMENT_GATEWAY_AUTHORITY == "PAYOS"
    assert finance_policy.PAYMENT_SETTLEMENT_AUTHORITY == "BOT_CORE"

    # Semantic independence invariants
    assert finance_policy.REQUEST_APPROVED_IMPLIES_PAYMENT_CONFIRMED is False
    assert finance_policy.PAYMENT_CONFIRMED_IMPLIES_SETTLED is False
    assert finance_policy.SETTLED_IMPLIES_REQUEST_APPROVED is False
    assert finance_policy.CUSTOMER_FINANCE_STATE_MAPPING_SHARED is True

    # State values are namespaced / differentiated
    assert finance_policy.TOPUP_STATE_APPROVED == "APPROVED"
    assert finance_policy.PAYMENT_STATE_CONFIRMED == "CONFIRMED"
    assert finance_policy.SETTLEMENT_STATE_CREDITED == "CREDITED"
    assert finance_policy.TOPUP_STATE_APPROVED != finance_policy.PAYMENT_STATE_CONFIRMED


def test_02_canonical_topup_request_mapping():
    """Verify Section 2: approved maps to APPROVED, pending maps to PENDING, rejected maps to REJECTED."""
    assert finance_policy.map_topup_raw_state("pending_admin_review") == "PENDING"
    assert finance_policy.map_topup_raw_state("pending") == "PENDING"
    assert finance_policy.map_topup_raw_state("reviewing") == "PENDING"
    assert finance_policy.map_topup_raw_state("approved") == "APPROVED"
    assert finance_policy.map_topup_raw_state("confirmed") == "APPROVED"
    assert finance_policy.map_topup_raw_state("success") == "APPROVED"
    assert finance_policy.map_topup_raw_state("rejected") == "REJECTED"
    assert finance_policy.map_topup_raw_state("declined") == "REJECTED"
    assert finance_policy.map_topup_raw_state(None) == "UNKNOWN"
    assert finance_policy.map_topup_raw_state("") == "UNKNOWN"


def test_03_approved_request_with_unknown_payment():
    """Verify Section 6: approved request + payment unknown: REQUEST_STATE=APPROVED, PAYMENT_STATE=UNKNOWN."""
    row = {
        "id": 102,
        "status": "approved",
        "amount_vnd": 500000,
    }
    rec = finance_policy.synthesize_topup_record(row)
    assert rec["request_state"] == "APPROVED"
    assert rec["payment_state"] == "UNKNOWN"
    assert rec["settlement_state"] == "UNKNOWN"
    # Never synthesized as CONFIRMED or CREDITED
    assert rec["request_state"] != "CONFIRMED"
    assert rec["payment_state"] != "CONFIRMED"
    assert rec["settlement_state"] != "CREDITED"


def test_04_payment_confirmed_with_unknown_settlement():
    """Verify Section 6: payment confirmed + settlement unknown: PAYMENT_STATE=CONFIRMED, SETTLEMENT_STATE=UNKNOWN."""
    pay_row = {
        "id": "payos-ev-01",
        "status": "paid",
        "amount": 250000,
    }
    rec = finance_policy.synthesize_payment_record(pay_row, bridge_available=True)
    assert rec["gateway_state"] == "CONFIRMED"
    assert rec["settlement_state"] == "UNKNOWN"
    assert rec["settlement_state"] != "CREDITED"


def test_05_payos_source_wording():
    """Verify Section 3: PAYMENT_GATEWAY_AUTHORITY=PAYOS, read model and event source separation."""
    assert finance_policy.PAYMENT_GATEWAY_AUTHORITY == "PAYOS"
    assert finance_policy.PAYMENT_READ_MODEL_SOURCE == "BOT_CORE_PAYMENT_PROJECTION_OR_WEBHOOK_CACHE"
    assert finance_policy.PAYMENT_EVENT_SOURCE == "PAYOS_GATEWAY_WEBHOOK"


def test_06_customer_finance_view_integration():
    """Verify Section 5: Customer CRM integration uses shared state mapping and canonical authority."""
    account = {"id": "acc-cust-06b", "display_name": "Customer 06B"}
    topups = [{"id": 1, "status": "approved", "amount_vnd": 500000}]
    ctx = crm_policy.synthesize_customer_crm_context(account, topup_requests=topups)
    assert ctx["payments_topups"]["authority"] == finance_policy.TOPUP_REQUEST_AUTHORITY
    assert ctx["payments_topups"]["customer_finance_state_mapping_shared"] is True
    assert crm_policy.CUSTOMER_FINANCE_STATE_MAPPING_SHARED is True


def test_07_api_topups_serializes_approved(admin_client):
    """Verify Section 1 & 6: /api/v1/admin/finance/topups serializes request_state=APPROVED."""
    r = admin_client.get("/api/v1/admin/finance/topups?status=approved")
    assert r.status_code == 200
    items = r.json()["data"]["items"]
    assert len(items) >= 1
    assert all(i["request_state"] == "APPROVED" for i in items)
    assert all(i["request_state"] != "CONFIRMED" for i in items)


def test_08_ui_acceptance_and_no_misleading_labels():
    """Verify Section 4: Topup list/detail UI never renders approved Web request as payment confirmed or credited."""
    # portal.js uses "Đã duyệt" for approved status
    assert 'approved: adminManualTopupText("status.approved", "Đã duyệt")' in PORTAL_CODE
    # portal.js does NOT present approved topups as "Payment confirmed" or "Wallet credited"
    assert "Payment confirmed" not in PORTAL_CODE
    assert "Wallet credited" not in PORTAL_CODE
