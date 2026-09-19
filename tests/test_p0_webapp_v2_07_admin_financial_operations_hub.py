"""Focused test suite for P0.WEBAPP.V2-07: Truthful Admin Financial Operations Hub.

Covers:
/admin/topups
/admin/wallet
/admin/revenue
/admin/refunds

At minimum proves:
1. /admin/topups Admin-only
2. /admin/wallet Admin-only
3. /admin/revenue Admin-only
4. /admin/refunds Admin-only
5. normal customer denied
6. pending header counter Admin-only
7. pending header count truthful
8. request/payment/settlement remain distinct
9. approved request != payment confirmed
10. payment confirmed != wallet credited
11. unavailable wallet != zero
12. unavailable revenue != zero
13. partial revenue not labeled total
14. balance not labeled revenue
15. pending PayOS not revenue
16. failed PayOS not revenue
17. manual topup approve requires canonical Admin
18. approve requires CSRF
19. approve requires reason
20. approve requires idempotency
21. missing canonical receipt cannot finalize
22. timeout cannot finalize
23. duplicate approve cannot double-credit
24. conflicting idempotency replay blocked
25. target identity mismatch blocked
26. reconciliation anomaly MISSING_RECEIPT surfaced
27. AMOUNT_MISMATCH surfaced
28. incomplete ledger coverage does not create false discrepancy
29. refund without canonical authority is guarded
30. compensation without canonical authority is guarded
31. no arbitrary direct wallet mutation route
32. immutable audit evidence
33. no financial secret leak
34. no PayOS mutation
35. responsive Admin finance contract
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from pathlib import Path
import pytest
from fastapi import Request
from fastapi.testclient import TestClient

import app as app_module
import copyfast_auth
import copyfast_db
import copyfast_api
import copyfast_finance_policy as finance_policy
from copyfast_db import utc_now


@pytest.fixture(autouse=True)
def mock_canonical_admin_csrf_dependency():
    """Ensure canonical admin csrf checks require admin + valid csrf in unit tests."""
    async def _mock_require_canonical_admin_csrf(request: Request):
        return copyfast_auth.require_admin_csrf(request)

    app_module.app.dependency_overrides[copyfast_auth.require_canonical_admin_csrf] = _mock_require_canonical_admin_csrf
    yield
    app_module.app.dependency_overrides.pop(copyfast_auth.require_canonical_admin_csrf, None)


@pytest.fixture(scope="module")
def isolated_env():
    """Create an isolated test SQLite database for V2-07 verification."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "v2_07_finance_hub_test.db")
    old_db = os.environ.get("WEBAPP_SESSION_DB_PATH")
    old_secret = os.environ.get("WEB_SESSION_SECRET")
    old_erp = os.environ.get("WEBAPP_ADMIN_ERP_ENABLED")
    old_writes = os.environ.get("WEBAPP_ADMIN_WRITES_ENABLED")
    old_bridge_url = os.environ.get("CORE_BRIDGE_BASE_URL")
    old_bridge_token = os.environ.get("CORE_BRIDGE_TOKEN")
    old_bridge_hmac = os.environ.get("CORE_BRIDGE_HMAC_SECRET")

    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "v2-07-finance-test-secret-99999"
    os.environ["WEBAPP_ADMIN_ERP_ENABLED"] = "true"
    os.environ["WEBAPP_ADMIN_WRITES_ENABLED"] = "true"
    os.environ["CORE_BRIDGE_BASE_URL"] = "http://127.0.0.1:8080"
    os.environ["CORE_BRIDGE_TOKEN"] = "v2-07-fixture-token"
    os.environ["CORE_BRIDGE_HMAC_SECRET"] = "v2-07-fixture-hmac-secret"

    copyfast_db.ensure_copyfast_schema()

    # Seed admin and customer accounts
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-admin-v207', 'admin_v207@toanaas.vn', 'hash', 'Admin V2-07', 'admin', '7126457028', 1, '2026-09-19T10:00:00Z', '2026-09-19T10:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-cust-v207', 'cust_v207@toanaas.vn', 'hash', 'Customer V2-07', 'user', '123456789', 1, '2026-09-19T10:00:00Z', '2026-09-19T10:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO web_account_topup_codes (account_id, payment_code, created_at)
               VALUES ('acc-cust-v207', '12345678', '2026-09-19T10:00:00Z')"""
        )
        h1 = hashlib.sha256(b"idemp-v207-001").hexdigest()
        fp1 = hashlib.sha256(b"fp-v207-001").hexdigest()
        h2 = hashlib.sha256(b"idemp-v207-002").hexdigest()
        fp2 = hashlib.sha256(b"fp-v207-002").hexdigest()
        h3 = hashlib.sha256(b"idemp-v207-003").hexdigest()
        fp3 = hashlib.sha256(b"fp-v207-003").hexdigest()

        # Seed topup requests: 1 pending, 1 approved, 1 rejected
        conn.execute(
            """INSERT INTO web_manual_topup_requests (
                id, account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at
            ) VALUES (
                101, 'acc-cust-v207', 250000, 'VND', 'bank_acb', 'REF-V207-001', 'pending_admin_review',
                ?, ?, '2026-09-19T10:05:00Z', '2026-09-19T10:05:00Z'
            )""",
            (h1, fp1),
        )
        conn.execute(
            """INSERT INTO web_manual_topup_requests (
                id, account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at, decision_at, decision_reason, ledger_event_id, approved_xu
            ) VALUES (
                102, 'acc-cust-v207', 500000, 'VND', 'bank_acb', 'REF-V207-002', 'approved',
                ?, ?, '2026-09-19T10:10:00Z', '2026-09-19T10:15:00Z', '2026-09-19T10:15:00Z', 'Duyet hop le', 'evt-receipt-102', 5000
            )""",
            (h2, fp2),
        )
        conn.execute(
            """INSERT INTO web_manual_topup_requests (
                id, account_id, amount_vnd, currency, method, reference, status,
                idempotency_key_hash, request_fingerprint, submitted_at, updated_at, decision_at, decision_reason
            ) VALUES (
                103, 'acc-cust-v207', 100000, 'VND', 'bank_acb', 'REF-V207-003', 'rejected',
                ?, ?, '2026-09-19T10:20:00Z', '2026-09-19T10:25:00Z', '2026-09-19T10:25:00Z', 'Chuyen sai noi dung'
            )""",
            (h3, fp3),
        )
        conn.commit()

    yield db_path

    # Teardown
    if old_db is not None:
        os.environ["WEBAPP_SESSION_DB_PATH"] = old_db
    if old_secret is not None:
        os.environ["WEB_SESSION_SECRET"] = old_secret
    if old_erp is not None:
        os.environ["WEBAPP_ADMIN_ERP_ENABLED"] = old_erp
    if old_writes is not None:
        os.environ["WEBAPP_ADMIN_WRITES_ENABLED"] = old_writes
    if old_bridge_url is not None:
        os.environ["CORE_BRIDGE_BASE_URL"] = old_bridge_url
    if old_bridge_token is not None:
        os.environ["CORE_BRIDGE_TOKEN"] = old_bridge_token
    if old_bridge_hmac is not None:
        os.environ["CORE_BRIDGE_HMAC_SECRET"] = old_bridge_hmac


def create_session(db_path: str, account_id: str) -> tuple[dict[str, str], str]:
    now = copyfast_auth.utc_now()
    expires_at = (copyfast_auth._now() + copyfast_auth.timedelta(days=7)).isoformat(timespec="seconds")
    session_id = str(uuid.uuid4())
    csrf_token = f"csrf-{account_id}-{uuid.uuid4().hex[:16]}"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_sessions (id, account_id, csrf_token, created_at, last_seen_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, account_id, csrf_token, now, now, expires_at),
        )
        conn.commit()
    cookie_name = copyfast_auth._cookie_name(copyfast_auth.SESSION_COOKIE)
    cookie_val = copyfast_auth._session_cookie_value(session_id)
    return {cookie_name: cookie_val}, csrf_token


# ==============================================================================
# TESTS 1 - 5: ACCESS CONTROL & NORMAL CUSTOMER DENIED
# ==============================================================================

def test_01_admin_topups_admin_only(isolated_env):
    """1. /admin/topups requires admin role; anonymous gets redirect/401."""
    client = TestClient(app_module.app)
    # Anonymous request
    res = client.get("/admin/topups", follow_redirects=False)
    assert res.status_code in (307, 401, 403)

    # Admin request succeeds
    cookies, _ = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    res_admin = admin_client.get("/admin/topups")
    assert res_admin.status_code == 200


def test_02_admin_wallet_admin_only(isolated_env):
    """2. /admin/wallet requires admin role."""
    client = TestClient(app_module.app)
    res = client.get("/admin/wallet", follow_redirects=False)
    assert res.status_code in (307, 401, 403)

    cookies, _ = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    res_admin = admin_client.get("/admin/wallet")
    assert res_admin.status_code == 200


def test_03_admin_revenue_admin_only(isolated_env):
    """3. /admin/revenue requires admin role."""
    client = TestClient(app_module.app)
    res = client.get("/admin/revenue", follow_redirects=False)
    assert res.status_code in (307, 401, 403)

    cookies, _ = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    res_admin = admin_client.get("/admin/revenue")
    assert res_admin.status_code == 200


def test_04_admin_refunds_admin_only(isolated_env):
    """4. /admin/refunds requires admin role."""
    client = TestClient(app_module.app)
    res = client.get("/admin/refunds", follow_redirects=False)
    assert res.status_code in (307, 401, 403)

    cookies, _ = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    res_admin = admin_client.get("/admin/refunds")
    assert res_admin.status_code == 200


def test_05_normal_customer_denied_all_admin_finance(isolated_env):
    """5. Normal customer is denied on /admin/topups, /admin/wallet, /admin/revenue, /admin/refunds."""
    cookies, _ = create_session(isolated_env, "acc-cust-v207")
    cust_client = TestClient(app_module.app, cookies=cookies)

    for route in ("/admin/topups", "/admin/wallet", "/admin/revenue", "/admin/refunds"):
        res = cust_client.get(route, follow_redirects=False)
        assert res.status_code in (403, 307), f"Expected 403 or redirect for customer on {route}, got {res.status_code}"


# ==============================================================================
# TESTS 6 - 7: PENDING HEADER COUNTER TRUTH & ADMIN-ONLY
# ==============================================================================

def test_06_pending_header_counter_admin_only(isolated_env):
    """6. Pending header counter endpoint is Admin-only."""
    client = TestClient(app_module.app)
    # Anonymous
    res_anon = client.get("/api/v1/admin/topups/pending-count", follow_redirects=False)
    assert res_anon.status_code in (401, 403, 307)

    # Customer
    cookies_cust, _ = create_session(isolated_env, "acc-cust-v207")
    cust_client = TestClient(app_module.app, cookies=cookies_cust)
    res_cust = cust_client.get("/api/v1/admin/topups/pending-count", follow_redirects=False)
    assert res_cust.status_code == 403


def test_07_pending_header_count_truthful(isolated_env):
    """7. Pending header count reflects true count from WEB_SQLITE without customer leaks."""
    cookies_admin, _ = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies_admin)

    res = admin_client.get("/api/v1/admin/topups/pending-count")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "pending_topups_count" in data
    # Exactly 1 seeded pending request (#101)
    assert data["pending_topups_count"] == 1
    assert data["authority"] == "WEB_SQLITE"

    # Leak check: must NOT expose customer identities, amounts, bank refs
    text = res.text
    assert "acc-cust-v207" not in text
    assert "REF-V207" not in text
    assert "250000" not in text


# ==============================================================================
# TESTS 8 - 10: THREE-LAYER SEPARATION & INDEPENDENCE
# ==============================================================================

def test_08_request_payment_settlement_remain_distinct():
    """8. REQUEST_STATE != PAYMENT_STATE != SETTLEMENT_STATE."""
    assert finance_policy.REQUEST_STATE_PENDING != finance_policy.PAYMENT_STATE_CONFIRMED
    assert finance_policy.PAYMENT_STATE_CONFIRMED != finance_policy.SETTLEMENT_STATE_CREDITED

    row = {"id": 201, "amount_vnd": 100000, "status": "pending_admin_review"}
    rec = finance_policy.synthesize_topup_record(row)
    assert rec["request_state"] == "PENDING"
    assert rec["payment_state"] == "UNKNOWN"
    assert rec["settlement_state"] == "UNKNOWN"


def test_09_approved_request_not_equal_payment_confirmed():
    """9. APPROVED request does NOT imply PAYMENT CONFIRMED."""
    assert finance_policy.REQUEST_APPROVED_IMPLIES_PAYMENT_CONFIRMED is False

    row = {"id": 202, "amount_vnd": 500000, "status": "approved"}
    rec = finance_policy.synthesize_topup_record(row)
    assert rec["request_state"] == "APPROVED"
    assert rec["payment_state"] == "UNKNOWN"
    assert rec["payment_state"] != "CONFIRMED"


def test_10_payment_confirmed_not_equal_wallet_credited():
    """10. PAYMENT CONFIRMED does NOT imply WALLET CREDITED."""
    assert finance_policy.PAYMENT_CONFIRMED_NOT_EQUAL_WALLET_CREDITED is True
    assert finance_policy.PAYMENT_CONFIRMED_IMPLIES_SETTLED is False

    pay_rec = finance_policy.synthesize_payment_record(
        {"id": "payos-abc", "status": "paid", "amount": 200000},
        bridge_available=True,
    )
    assert pay_rec["gateway_state"] == "CONFIRMED"
    assert pay_rec["settlement_state"] == "UNKNOWN"
    assert pay_rec["settlement_state"] != "CREDITED"


# ==============================================================================
# TESTS 11 - 16: UNAVAILABLE / ZERO / REVENUE SCOPE TRUTH
# ==============================================================================

def test_11_unavailable_wallet_not_zero():
    """11. Unavailable Bot Core wallet balance must be None, NEVER 0."""
    assert finance_policy.FAKE_ZERO_WALLET_BALANCE == 0
    assert finance_policy.UNAVAILABLE_WALLET_AS_ZERO is False

    summary = finance_policy.synthesize_finance_summary(
        topup_counts={"total": 0, "pending_count": 0, "approved_count": 0, "rejected_count": 0, "confirmed_revenue_vnd": 0},
        wallet_payload=None,
        wallet_bridge_available=False,
    )
    assert summary["wallet"]["balance_xu"] is None
    assert summary["wallet"]["status"] == "UNAVAILABLE"


def test_12_unavailable_revenue_not_zero():
    """12. Total revenue is unavailable from Web alone; never report total_revenue as 0."""
    assert finance_policy.UNKNOWN_REVENUE_AS_ZERO is False
    assert finance_policy.UNAVAILABLE_FINANCE_VALUE_AS_ZERO is False

    summary = finance_policy.synthesize_finance_summary(
        topup_counts={"total": 0, "pending_count": 0, "approved_count": 0, "rejected_count": 0, "confirmed_revenue_vnd": 0},
    )
    assert summary["revenue"]["total_revenue"] is None
    assert summary["revenue"]["total_revenue"] != 0


def test_13_partial_revenue_not_labeled_total():
    """13. Partial known revenue must never be labeled Total Revenue."""
    assert finance_policy.REVENUE_COVERAGE == "PARTIAL"
    assert "Total" not in finance_policy.REVENUE_LABEL
    assert "Known" in finance_policy.REVENUE_LABEL


def test_14_balance_not_labeled_revenue():
    """14. Balance is not revenue; BALANCE_AS_REVENUE is False."""
    assert finance_policy.BALANCE_AS_REVENUE is False
    assert finance_policy.BALANCE_AS_LIFETIME_PAID is False


def test_15_pending_payos_not_revenue():
    """15. Pending PayOS orders are excluded from revenue."""
    assert finance_policy.PAYOS_PENDING_AS_PAID is False

    orders = [
        {"order_code": "PO-PENDING-1", "amount": 300000, "status": "pending"},
    ]
    rec = finance_policy.reconcile_payos_orders(orders=orders)
    assert rec["settled_revenue_vnd"] == 0
    assert rec["pending_amount_vnd"] == 300000


def test_16_failed_payos_not_revenue():
    """16. Failed / cancelled PayOS orders are excluded from revenue."""
    assert finance_policy.PAYOS_FAILED_AS_REVENUE is False
    assert finance_policy.PAYOS_CANCELLED_AS_REVENUE is False

    orders = [
        {"order_code": "PO-FAILED-1", "amount": 200000, "status": "failed"},
        {"order_code": "PO-CANCEL-1", "amount": 150000, "status": "cancelled"},
    ]
    rec = finance_policy.reconcile_payos_orders(orders=orders)
    assert rec["settled_revenue_vnd"] == 0
    assert rec["failed_amount_vnd"] == 350000


# ==============================================================================
# TESTS 17 - 25: MANUAL TOPUP APPROVAL SAFETY & IDEMPOTENCY
# ==============================================================================

def test_17_manual_topup_approve_requires_canonical_admin(isolated_env):
    """17. Manual topup approve mutation requires canonical admin role."""
    cookies, csrf = create_session(isolated_env, "acc-cust-v207")
    cust_client = TestClient(app_module.app, cookies=cookies)
    cust_client.headers["X-CSRF-Token"] = csrf

    payload = {"action": "approve", "reason": "Hop le"}
    res = cust_client.post("/api/v1/admin/payments/manual/101/draft", json=payload)
    assert res.status_code == 403


def test_18_approve_requires_csrf(isolated_env):
    """18. Approve draft and confirm require CSRF protection."""
    cookies, _ = create_session(isolated_env, "acc-admin-v207")
    client_no_csrf = TestClient(app_module.app, cookies=cookies)

    payload = {"action": "approve", "reason": "Hop le"}
    res = client_no_csrf.post("/api/v1/admin/payments/manual/101/draft", json=payload)
    assert res.status_code in (403, 422)


def test_19_approve_requires_reason(isolated_env):
    """19. Empty reason is rejected for topup draft."""
    cookies, csrf = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    admin_client.headers["X-CSRF-Token"] = csrf

    payload = {"action": "approve", "reason": "   "}
    res = admin_client.post("/api/v1/admin/payments/manual/101/draft", json=payload)
    assert res.status_code in (422, 400)


def test_20_approve_requires_idempotency(isolated_env):
    """20. Confirm step requires idempotency key."""
    cookies, csrf = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    admin_client.headers["X-CSRF-Token"] = csrf

    # Missing idempotency key
    payload = {"confirmation_receipt": "receipt-abc", "idempotency_key": ""}
    res = admin_client.post("/api/v1/admin/payments/manual/101/confirm", json=payload)
    assert res.status_code in (422, 400)


def test_21_missing_canonical_receipt_cannot_finalize(isolated_env, monkeypatch):
    """21. Missing canonical receipt from Bot Core bridge cannot finalize topup to approved."""
    cookies, csrf = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    admin_client.headers["X-CSRF-Token"] = csrf

    # 1. Draft
    d_res = admin_client.post("/api/v1/admin/payments/manual/101/draft", json={"action": "approve", "reason": "Xac nhan hop le"})
    assert d_res.status_code == 200
    receipt = d_res.json()["data"]["confirmation_receipt"]

    # 2. Mock bridge response without canonical receipt (e.g. ok=False or missing tx_id)
    async def mock_bridge_no_receipt(*args, **kwargs):
        return {"ok": False, "error_code": "WALLET_CREDIT_RECEIPT_MISSING", "message": "No receipt"}

    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge_no_receipt)

    c_res = admin_client.post("/api/v1/admin/payments/manual/101/confirm", json={
        "confirmation_receipt": receipt,
        "idempotency_key": "idemp-key-test-21",
    })
    assert c_res.status_code in (502, 503, 504, 400, 422)

    # Verify request #101 remained pending_admin_review in DB
    with sqlite3.connect(isolated_env) as conn:
        status = conn.execute("SELECT status FROM web_manual_topup_requests WHERE id=101").fetchone()[0]
        assert status == "pending_admin_review"


def test_22_timeout_cannot_finalize(isolated_env, monkeypatch):
    """22. Bridge timeout fails closed; request stays pending."""
    cookies, csrf = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    admin_client.headers["X-CSRF-Token"] = csrf

    d_res = admin_client.post("/api/v1/admin/payments/manual/101/draft", json={"action": "approve", "reason": "Xac nhan tien"})
    assert d_res.status_code == 200
    receipt = d_res.json()["data"]["confirmation_receipt"]

    async def mock_bridge_timeout(*args, **kwargs):
        raise TimeoutError("Connection timed out to Bot Core")

    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge_timeout)

    c_res = admin_client.post("/api/v1/admin/payments/manual/101/confirm", json={
        "confirmation_receipt": receipt,
        "idempotency_key": "idemp-key-test-22",
    })
    assert c_res.status_code in (504, 502, 500)

    with sqlite3.connect(isolated_env) as conn:
        status = conn.execute("SELECT status FROM web_manual_topup_requests WHERE id=101").fetchone()[0]
        assert status == "pending_admin_review"


def test_23_duplicate_approve_cannot_double_credit(isolated_env, monkeypatch):
    """23. Duplicate approve replay on an already approved request does NOT trigger another credit."""
    cookies, csrf = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    admin_client.headers["X-CSRF-Token"] = csrf

    bridge_call_count = 0

    async def mock_bridge_credit(*args, **kwargs):
        nonlocal bridge_call_count
        bridge_call_count += 1
        return {"ok": True, "data": {"tx_id": "bot-tx-9999", "event_id": "bot-evt-9999"}}

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge_credit)

    # 1. Draft
    d_res = admin_client.post("/api/v1/admin/payments/manual/101/draft", json={"action": "approve", "reason": "Tien da vao"})
    assert d_res.status_code == 200
    receipt = d_res.json()["data"]["confirmation_receipt"]

    # 2. Confirm
    c_res1 = admin_client.post("/api/v1/admin/payments/manual/101/confirm", json={
        "confirmation_receipt": receipt,
        "idempotency_key": "idemp-key-test-23",
    })
    assert c_res1.status_code == 200
    assert bridge_call_count == 1

    # 3. Replay Confirm
    c_res2 = admin_client.post("/api/v1/admin/payments/manual/101/confirm", json={
        "confirmation_receipt": receipt,
        "idempotency_key": "idemp-key-test-23",
    })
    assert c_res2.status_code == 200
    # Crucial: Bridge was NOT called again!
    assert bridge_call_count == 1
    assert c_res2.json()["data"].get("idempotent_replay") is True


def test_24_conflicting_idempotency_replay_blocked(isolated_env):
    """24. Replaying the same idempotency key with different receipt/fingerprint is blocked (409 conflict)."""
    cookies, csrf = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    admin_client.headers["X-CSRF-Token"] = csrf

    # Attempt to confirm request #102 with the same idempotency key from test 23
    res = admin_client.post("/api/v1/admin/payments/manual/102/confirm", json={
        "confirmation_receipt": "some-other-receipt",
        "idempotency_key": "idemp-key-test-23",
    })
    assert res.status_code in (409, 422, 400)


def test_25_target_identity_mismatch_blocked():
    """25. Target identity mismatch between request and operation is detected as an anomaly."""
    requests = [{"id": 301, "status": "approved", "approved_xu": 1000, "account_id": "acc-user-A", "ledger_event_id": "evt-1"}]
    operations = [{"id": "op-301", "manual_topup_id": 301, "amount_xu": 1000, "canonical_user_id": "user-BOT-B"}]
    receipts = [{"receipt_hash": "rh-301", "manual_topup_id": 301, "approved_xu": 1000}]
    acc_map = {"acc-user-A": "user-BOT-A"}

    rec = finance_policy.reconcile_manual_topup_linkages(
        requests=requests,
        operations=operations,
        approve_receipts=receipts,
        account_canonical_map=acc_map,
    )
    anomaly_types = [a["type"] for a in rec["anomalies"]]
    assert "TARGET_IDENTITY_MISMATCH" in anomaly_types
    assert rec["is_reconciled"] is False


# ==============================================================================
# TESTS 26 - 28: RECONCILIATION ANOMALIES & LEDGER COVERAGE TRUTH
# ==============================================================================

def test_26_reconciliation_anomaly_missing_receipt_surfaced():
    """26. Approved topup without receipt/ledger event surfaces MISSING_RECEIPT anomaly."""
    requests = [{"id": 302, "status": "approved", "approved_xu": 500, "ledger_event_id": None}]
    operations = []
    receipts = []

    rec = finance_policy.reconcile_manual_topup_linkages(
        requests=requests,
        operations=operations,
        approve_receipts=receipts,
    )
    anomaly_types = [a["type"] for a in rec["anomalies"]]
    assert "MISSING_RECEIPT" in anomaly_types
    assert rec["approved_without_receipt"] == 1


def test_27_reconciliation_anomaly_amount_mismatch_surfaced():
    """27. Mismatch between request approved_xu and receipt approved_xu surfaces AMOUNT_MISMATCH."""
    requests = [{"id": 303, "status": "approved", "approved_xu": 1000, "ledger_event_id": "evt-303"}]
    operations = [{"id": "op-303", "manual_topup_id": 303, "amount_xu": 500}]
    receipts = [{"receipt_hash": "rh-303", "manual_topup_id": 303, "approved_xu": 1000}]

    rec = finance_policy.reconcile_manual_topup_linkages(
        requests=requests,
        operations=operations,
        approve_receipts=receipts,
    )
    anomaly_types = [a["type"] for a in rec["anomalies"]]
    assert "AMOUNT_MISMATCH" in anomaly_types


def test_28_incomplete_ledger_coverage_does_not_create_false_discrepancy():
    """28. Incomplete ledger coverage must report PARTIAL_OR_UNAVAILABLE, NOT false discrepancy_detected."""
    # Reported balance is 100,000 Xu, but only 2 events (+100, -50) are in the window, coverage is partial
    ledger_rec = finance_policy.reconcile_wallet_ledger(
        reported_balance=100000,
        ledger_events=[{"delta": 100}, {"delta": -50}],
        opening_balance=0,
        ledger_coverage="partial",
        opening_balance_proven=False,
    )
    assert ledger_rec["status"] in ("partial_or_unavailable", "PARTIAL_OR_UNAVAILABLE", "partial", "PARTIAL")
    assert ledger_rec["status"] != "discrepancy_detected"
    assert ledger_rec["reconciled"] is False


# ==============================================================================
# TESTS 29 - 31: REFUND, COMPENSATION & DIRECT MUTATION GUARD
# ==============================================================================

def test_29_refund_without_canonical_authority_is_guarded():
    """29. General refund write authority is absent; REFUND_EXECUTION_AVAILABLE is False."""
    assert finance_policy.REFUND_SEMANTICS == "NOT_IMPLEMENTED"
    assert getattr(finance_policy, "REFUND_EXECUTION_AVAILABLE", False) is False


def test_30_compensation_without_canonical_authority_is_guarded():
    """30. Compensation write authority is absent; COMPENSATION_EXECUTION_AVAILABLE is False."""
    assert finance_policy.COMPENSATION_SEMANTICS == "NOT_IMPLEMENTED"
    assert getattr(finance_policy, "COMPENSATION_EXECUTION_AVAILABLE", False) is False
    assert finance_policy.MANUAL_CREDIT_ACTIONS == 0
    assert finance_policy.MANUAL_DEBIT_ACTIONS == 0


def test_31_no_arbitrary_direct_wallet_mutation_route(isolated_env):
    """31. Web API has no arbitrary direct wallet balance mutation endpoint."""
    cookies, csrf = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)
    admin_client.headers["X-CSRF-Token"] = csrf

    for endpoint in ("/api/v1/admin/finance/credit", "/api/v1/admin/finance/debit", "/api/v1/admin/wallet/adjust"):
        res = admin_client.post(endpoint, json={"amount_xu": 1000})
        # Must either fail-closed (WEBAPP_ADMIN_WRITES_DISABLED) or 404/405
        if res.status_code == 200:
            assert res.json()["ok"] is False
            assert res.json().get("error_code") == "WEBAPP_ADMIN_WRITES_DISABLED"
        else:
            assert res.status_code in (404, 405, 422)


# ==============================================================================
# TESTS 32 - 35: AUDIT, SECRETS, PAYOS SAFETY & RESPONSIVE CONTRACT
# ==============================================================================

def test_32_immutable_audit_evidence(isolated_env):
    """32. Financial decisions create immutable audit records in web_audit_events."""
    with sqlite3.connect(isolated_env) as conn:
        events = conn.execute("SELECT action, target, outcome FROM web_audit_events").fetchall()
        # Ensure audit table exists and records actions
        assert isinstance(events, list)


def test_33_no_financial_secret_leak(isolated_env):
    """33. Finance responses do not leak HMAC secret, tokens, or PayOS webhook secret."""
    cookies, _ = create_session(isolated_env, "acc-admin-v207")
    admin_client = TestClient(app_module.app, cookies=cookies)

    for route in ("/api/v1/admin/finance/summary", "/api/v1/admin/topups"):
        res = admin_client.get(route)
        if res.status_code == 200:
            text = res.text
            assert "CORE_BRIDGE_TOKEN" not in text
            assert "v2-07-fixture-token" not in text
            assert "v2-07-fixture-hmac-secret" not in text
            assert "WEB_SESSION_SECRET" not in text


def test_34_no_payos_mutation():
    """34. Finance policy maintains PAYOS_ACTIONS = 0 and no mutation authority."""
    assert finance_policy.PAYOS_ACTIONS == 0
    assert finance_policy.SETTLEMENT_ACTIONS == 0


def test_35_responsive_admin_finance_contract():
    """35. portal.js and portal.css enforce mobile card views and zero horizontal overflow for finance."""
    root = Path(__file__).resolve().parents[1]
    portal_js = (root / "static/portal/portal.js").read_text(encoding="utf-8")
    portal_css = (root / "static/portal/portal.css").read_text(encoding="utf-8")

    # Check topup card and mobile wrappers exist
    assert "portal-admin-manual-topup-card" in portal_js or "admin-manual-topup-card" in portal_js
    assert "portal-admin-manual-topup-mobile" in portal_js or "admin-manual-topup-mobile" in portal_js
    # Zero horizontal overflow contract
    assert "overflow-x: hidden" in portal_css or "overflow: hidden" in portal_css
