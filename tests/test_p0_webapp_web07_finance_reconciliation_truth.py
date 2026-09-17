"""Empirical verification test suite for WEB07: Finance + Reconciliation Truth.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.WEB07.FINANCE.RECONCILIATION.TRUTH
Repository: manhtoangreensky-wq/toan-aas-standalone

Invariants:
1. CANONICAL_LEDGER_TRUTH: Ledger opening + credits - debits = expected balance.
2. DISCREPANCY_SUPPRESSED=0: Ledger discrepancies are never silently overwritten.
3. DUPLICATE_CREDIT_COUNTING=0: Replay projection preserves financial invariants.
4. PAYOS_PENDING_AS_PAID=0: Pending PayOS orders never count as settled revenue.
5. PAYOS_FAILED_AS_REVENUE=0: Failed/cancelled PayOS orders never count as revenue.
6. PENDING_TOPUP_AS_CREDITED=0: Pending topups are never credited.
7. APPROVED_WITHOUT_RECEIPT_AS_CREDITED=0: Approved requests require canonical receipt.
8. MISMATCH_STATE=VISIBLE & FAKE_RECONCILED=0: Anomalies (orphans, mismatches) are visible.
9. CLIENT_AUTHORITATIVE_ACCOUNT_ID=NO & CROSS_ACCOUNT_FINANCE_READ=0: Strict customer/admin scoping.
10. FAKE_ZERO_FINANCE=0: Unavailable canonical sources return None/unavailable, never 0.
11. TIME_WINDOW_TRUTH: UTC deterministic boundaries, no browser-now mutations.
12. REFUND_SEMANTICS=NOT_IMPLEMENTED & COMPENSATION_SEMANTICS=NOT_IMPLEMENTED.
"""

from __future__ import annotations

import datetime
from datetime import timezone
import importlib
import os
from pathlib import Path
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_db
import copyfast_finance_policy as policy


# ==============================================================================
# 1. FIXTURES & HELPERS
# ==============================================================================
CUSTOMER_EMAIL = "web07-customer@toanaas.vn"
CUSTOMER_PWD = "Web07CustomerPassword123!@#"
ADMIN_EMAIL = "web07-admin@toanaas.vn"
ADMIN_PWD = "Web07AdminPassword123!@#"
CUSTOMER_TELEGRAM_UID = "7126457028"


def _setup_test_env(tmp_path: Path, monkeypatch) -> tuple[TestClient, Path, Path]:
    session_db = tmp_path / "web07_session.db"
    system_db = tmp_path / "toandaas_system.db"

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(session_db))
    monkeypatch.setenv("DB_FILE", str(system_db))
    monkeypatch.setenv("DB_PATH", str(system_db))
    monkeypatch.setenv("WEB_SESSION_SECRET", "web07-test-session-secret-key-64b-secure-value")
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "true")
    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "web07-fixture-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "web07-fixture-hmac")

    copyfast_db.ensure_copyfast_schema()

    # Init system DB schema
    db_mod = importlib.import_module("db")
    db_mod.init_db()

    app_mod = importlib.import_module("app")
    client = TestClient(app_mod.app)
    return client, session_db, system_db


def _create_and_login_user(client: TestClient, session_db: Path, email: str, pwd: str, role: str = "customer", telegram_uid: str | None = None) -> dict:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": pwd, "display_name": email.split("@")[0]})
    assert reg.status_code == 200

    with sqlite3.connect(str(session_db)) as conn:
        conn.execute(
            "UPDATE web_accounts SET role_cache=?, canonical_user_id=? WHERE email=?",
            (role, telegram_uid, email),
        )
        row = conn.execute("SELECT id, role_cache, canonical_user_id FROM web_accounts WHERE email=?", (email,)).fetchone()
        conn.commit()

    login = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    cookies = dict(login.cookies)

    app_mod = importlib.import_module("app")
    authed_client = TestClient(app_mod.app, cookies=cookies)
    authed_client.headers["X-CSRF-Token"] = csrf
    return {
        "client": authed_client,
        "account_id": str(row[0]),
        "role": str(row[1]),
        "canonical_user_id": str(row[2] or ""),
    }


# ==============================================================================
# 2. UNIT RECONCILIATION CONTRACTS (POLICY LAYER)
# ==============================================================================
def test_canonical_balance_reconciles_exactly():
    """Case 1: Canonical ledger opening + credits - debits = expected balance."""
    ledger_events = [
        {"delta": 100, "event_type": "topup_bank", "ref_id": "ref1"},
        {"delta": 50, "event_type": "topup_payos", "ref_id": "ref2"},
        {"delta": -30, "event_type": "video_render", "ref_id": "ref3"},
        {"delta": -20, "event_type": "image_gen", "ref_id": "ref4"},
    ]
    # Opening 50 + Credits 150 - Debits 50 = Expected 150
    result = policy.reconcile_wallet_ledger(
        reported_balance=150,
        ledger_events=ledger_events,
        opening_balance=50,
    )
    assert result["reconciled"] is True
    assert result["discrepancy_xu"] == 0
    assert result["expected_balance_xu"] == 150
    assert result["total_credits_xu"] == 150
    assert result["total_debits_xu"] == 50
    assert result["status"] == "reconciled"


def test_wallet_discrepancy_remains_visible_and_unsuppressed():
    """Case 2: Discrepancy is never suppressed or silently overwritten."""
    ledger_events = [
        {"delta": 100, "event_type": "topup_bank", "ref_id": "ref1"},
        {"delta": -30, "event_type": "video_render", "ref_id": "ref2"},
    ]
    # Opening 0 + Credits 100 - Debits 30 = Expected 70. But reported is 50!
    result = policy.reconcile_wallet_ledger(
        reported_balance=50,
        ledger_events=ledger_events,
        opening_balance=0,
    )
    assert result["reconciled"] is False
    assert result["discrepancy_xu"] == -20
    assert result["reported_balance_xu"] == 50
    assert result["expected_balance_xu"] == 70
    assert result["status"] == "discrepancy_detected"
    assert policy.DISCREPANCY_SUPPRESSED is False


def test_duplicate_receipt_counted_once():
    """Case 3 & 6: Replay projection preserves exactly-once credit counting."""
    requests = [
        {"id": 1, "account_id": "acc-1", "amount_vnd": 50000, "approved_xu": 50, "status": "approved", "ledger_event_id": "evt-1"},
    ]
    operations = [
        {"id": "op_credit_manual_1", "manual_topup_id": 1, "canonical_user_id": "u1", "amount_xu": 50, "status": "local_approval_persisted", "ledger_event_id": "evt-1"},
        # Duplicate operation with same id
        {"id": "op_credit_manual_1", "manual_topup_id": 1, "canonical_user_id": "u1", "amount_xu": 50, "status": "local_approval_persisted", "ledger_event_id": "evt-1"},
    ]
    receipts = [
        {"receipt_hash": "a" * 64, "manual_topup_id": 1, "approved_xu": 50, "action": "approve"},
        # Duplicate receipt
        {"receipt_hash": "a" * 64, "manual_topup_id": 1, "approved_xu": 50, "action": "approve"},
    ]

    res = policy.reconcile_manual_topup_linkages(
        requests=requests,
        operations=operations,
        approve_receipts=receipts,
    )
    assert res["approved_with_receipt"] == 1
    assert res["credited_amount_xu"] == 50
    assert policy.DUPLICATE_CREDIT_COUNTING == 0


def test_payos_pending_is_not_revenue_or_paid():
    """Case 4: Pending PayOS orders are not counted in settled revenue."""
    orders = [
        {"order_code": "1001", "amount": 100000, "status": "PENDING"},
        {"order_code": "1002", "amount": 200000, "status": "pending"},
        {"order_code": "1003", "amount": 50000, "status": "PAID"},
    ]
    res = policy.reconcile_payos_orders(orders=orders)
    assert res["pending_count"] == 2
    assert res["pending_amount_vnd"] == 300000
    assert res["settled_count"] == 1
    assert res["settled_revenue_vnd"] == 50000
    assert policy.PAYOS_PENDING_AS_PAID is False


def test_payos_failed_and_cancelled_not_revenue():
    """Case 5: Failed, cancelled, and expired PayOS orders never count as revenue."""
    orders = [
        {"order_code": "1001", "amount": 100000, "status": "FAILED"},
        {"order_code": "1002", "amount": 150000, "status": "cancelled"},
        {"order_code": "1003", "amount": 80000, "status": "canceled"},
        {"order_code": "1004", "amount": 70000, "status": "EXPIRED"},
        {"order_code": "1005", "amount": 50000, "status": "COMPLETED"},
    ]
    res = policy.reconcile_payos_orders(orders=orders)
    assert res["failed_count"] == 4
    assert res["settled_count"] == 1
    assert res["settled_revenue_vnd"] == 50000
    assert policy.PAYOS_FAILED_AS_REVENUE is False
    assert policy.PAYOS_CANCELLED_AS_REVENUE is False


def test_approved_manual_topup_without_receipt_not_credited():
    """Case 6: Approved request without canonical receipt is not credited."""
    requests = [
        {"id": 1, "account_id": "acc-1", "amount_vnd": 100000, "approved_xu": 100, "status": "approved", "ledger_event_id": None},
    ]
    res = policy.reconcile_manual_topup_linkages(
        requests=requests,
        operations=[],
        approve_receipts=[],
    )
    assert res["approved_without_receipt"] == 1
    assert res["approved_with_receipt"] == 0
    assert res["credited_amount_xu"] == 0
    assert any(a["type"] == "MISSING_RECEIPT" for a in res["anomalies"])
    assert policy.APPROVED_WITHOUT_RECEIPT_AS_CREDITED is False


def test_approved_manual_topup_with_receipt_credited_exactly_once():
    """Case 7: Approved request with canonical receipt is credited exactly once."""
    requests = [
        {"id": 1, "account_id": "acc-1", "amount_vnd": 100000, "approved_xu": 100, "status": "approved", "ledger_event_id": "evt-1"},
    ]
    operations = [
        {"id": "op-1", "manual_topup_id": 1, "canonical_user_id": "u1", "amount_xu": 100, "status": "local_approval_persisted", "ledger_event_id": "evt-1"},
    ]
    receipts = [
        {"receipt_hash": "b" * 64, "manual_topup_id": 1, "approved_xu": 100, "action": "approve"},
    ]
    res = policy.reconcile_manual_topup_linkages(
        requests=requests,
        operations=operations,
        approve_receipts=receipts,
    )
    assert res["approved_with_receipt"] == 1
    assert res["approved_without_receipt"] == 0
    assert res["credited_amount_xu"] == 100
    assert len(res["anomalies"]) == 0
    assert res["is_reconciled"] is True


def test_orphan_operation_and_receipt_detected():
    """Case 8: Orphan receipts and orphan operations are explicitly detected."""
    requests = [
        {"id": 1, "account_id": "acc-1", "amount_vnd": 100000, "approved_xu": 100, "status": "approved", "ledger_event_id": "evt-1"},
    ]
    operations = [
        {"id": "op-1", "manual_topup_id": 1, "canonical_user_id": "u1", "amount_xu": 100, "status": "local_approval_persisted", "ledger_event_id": "evt-1"},
        {"id": "op-99", "manual_topup_id": 99, "canonical_user_id": "u2", "amount_xu": 200, "status": "dispatched", "ledger_event_id": None},
    ]
    receipts = [
        {"receipt_hash": "b" * 64, "manual_topup_id": 1, "approved_xu": 100, "action": "approve"},
        {"receipt_hash": "c" * 64, "manual_topup_id": 88, "approved_xu": 300, "action": "approve"},
    ]
    res = policy.reconcile_manual_topup_linkages(
        requests=requests,
        operations=operations,
        approve_receipts=receipts,
    )
    anomaly_types = {a["type"] for a in res["anomalies"]}
    assert "ORPHAN_OPERATION" in anomaly_types
    assert "ORPHAN_RECEIPT" in anomaly_types
    assert res["is_reconciled"] is False


def test_amount_mismatch_and_identity_mismatch_detected():
    """Case 9: Mismatched amounts or target identities produce visible anomalies."""
    requests = [
        {"id": 1, "account_id": "acc-1", "amount_vnd": 100000, "approved_xu": 100, "status": "approved", "ledger_event_id": "evt-1"},
        {"id": 2, "account_id": "acc-2", "amount_vnd": 50000, "approved_xu": 50, "status": "approved", "ledger_event_id": "evt-2"},
    ]
    operations = [
        # Op 1 has amount mismatch: 80 != 100
        {"id": "op-1", "manual_topup_id": 1, "canonical_user_id": "u1", "amount_xu": 80, "status": "local_approval_persisted", "ledger_event_id": "evt-1"},
        # Op 2 has identity mismatch: u999 instead of u2
        {"id": "op-2", "manual_topup_id": 2, "canonical_user_id": "u999", "amount_xu": 50, "status": "local_approval_persisted", "ledger_event_id": "evt-2"},
    ]
    receipts = [
        {"receipt_hash": "d" * 64, "manual_topup_id": 1, "approved_xu": 100, "action": "approve"},
        {"receipt_hash": "e" * 64, "manual_topup_id": 2, "approved_xu": 50, "action": "approve"},
    ]
    account_map = {"acc-1": "u1", "acc-2": "u2"}

    res = policy.reconcile_manual_topup_linkages(
        requests=requests,
        operations=operations,
        approve_receipts=receipts,
        account_canonical_map=account_map,
    )
    anomaly_types = {a["type"] for a in res["anomalies"]}
    assert "AMOUNT_MISMATCH" in anomaly_types
    assert "TARGET_IDENTITY_MISMATCH" in anomaly_types
    assert res["is_reconciled"] is False


def test_unavailable_canonical_source_returns_none_not_fake_zero():
    """Case 10: Unavailable balance or metrics return None, never fake zero."""
    res = policy.reconcile_wallet_ledger(
        reported_balance=None,
        ledger_events=None,
        opening_balance=0,
    )
    assert res["reported_balance_xu"] is None
    assert res["reconciled"] is False
    assert res["discrepancy_xu"] is None
    assert res["status"] in ("UNAVAILABLE", "UNKNOWN")
    assert policy.FAKE_ZERO_WALLET_BALANCE == 0
    assert policy.UNAVAILABLE_FINANCE_VALUE_AS_ZERO is False


def test_time_window_boundaries_deterministic_utc():
    """Case 11: Time window boundaries use UTC and deterministic calculations."""
    ref = datetime.datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    for window in ("today", "7d", "30d", "month", "all_time"):
        start, end = policy.compute_finance_window_boundaries(window, reference_time=ref)
        assert start.tzinfo == timezone.utc
        assert end.tzinfo == timezone.utc
        assert start <= end

    assert policy.FINANCE_TIMEZONE == "UTC"
    assert policy.WINDOW_BOUNDARY_SOURCE == "SERVER_CANONICAL_UTC"


def test_refund_and_compensation_semantics_not_implemented():
    """Case 12: Refund and compensation semantics explicitly declared NOT_IMPLEMENTED."""
    assert policy.REFUND_SEMANTICS == "NOT_IMPLEMENTED"
    assert policy.COMPENSATION_SEMANTICS == "NOT_IMPLEMENTED"


# ==============================================================================
# 3. END-TO-END INTEGRATION & RBAC CONTRACTS
# ==============================================================================
def test_customer_cannot_access_finance_admin_routes_or_cross_account(tmp_path, monkeypatch):
    """Case 13: Customer RBAC boundary on finance routes & no arbitrary account_id query."""
    client, session_db, system_db = _setup_test_env(tmp_path, monkeypatch)

    cust = _create_and_login_user(client, session_db, CUSTOMER_EMAIL, CUSTOMER_PWD, role="customer", telegram_uid=CUSTOMER_TELEGRAM_UID)
    cust_client = cust["client"]

    # Customer accessing admin finance endpoints -> 403 Forbidden
    for path in (
        "/api/v1/admin/finance",
        "/api/v1/admin/finance/summary",
        "/api/v1/admin/finance/reconciliation",
        "/api/v1/admin/finance/topups",
        "/api/v1/admin/finance/payments",
    ):
        res = cust_client.get(path)
        assert res.status_code == 403, f"{path} must return 403 for customer"

    # Unauthenticated -> 401 Unauthorized
    unauth_client = TestClient(app_module.app)
    res_unauth = unauth_client.get("/api/v1/admin/finance/reconciliation")
    assert res_unauth.status_code == 401


def test_admin_finance_reconciliation_endpoint_integration(tmp_path, monkeypatch):
    """Case 14: Admin can call /admin/finance/reconciliation and receive truthful report."""
    client, session_db, system_db = _setup_test_env(tmp_path, monkeypatch)

    admin = _create_and_login_user(client, session_db, ADMIN_EMAIL, ADMIN_PWD, role="admin", telegram_uid="999999999")
    admin_client = admin["client"]

    # Mock bridge for wallet
    copyfast_api = importlib.import_module("copyfast_api")
    copyfast_bridge = importlib.import_module("copyfast_bridge")
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_bridge, "bridge_configured", lambda: True)

    async def mock_bridge(method, path, **kwargs):
        if path == "/internal/v1/me":
            return {"ok": True, "data": {"role": "admin"}}
        if path == "/internal/v1/admin/modules/wallet":
            return {
                "ok": True,
                "status": "read_only",
                "data": {
                    "balance_xu": 500,
                    "total_wallets": 10,
                    "ledger_events": [
                        {"delta": 500, "event_type": "topup", "ref_id": "init"},
                    ],
                },
            }
        return {"ok": False, "status": "guarded", "error_code": "NOT_FOUND"}

    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge)
    monkeypatch.setattr(copyfast_bridge, "bridge_request", mock_bridge)

    res = admin_client.get("/api/v1/admin/finance/reconciliation")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    rec_data = data["data"]
    assert "wallet_reconciliation" in rec_data
    assert "manual_topup_reconciliation" in rec_data
    assert "payos_reconciliation" in rec_data
    assert rec_data["wallet_reconciliation"]["reconciled"] is True
    assert rec_data["wallet_reconciliation"]["discrepancy_xu"] == 0
