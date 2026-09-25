"""Focused empirical verification test suite for WEB03 Admin Topup Approval Truth.

Task: TASK=P0.WEBAPP.WEB03.ADMIN.TOPUP.WALLET.APPROVAL.TRUTH
Master Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Repository: manhtoangreensky-wq/toan-aas-standalone

Invariants:
1. ADMIN_RBAC_TRUTH: Admin role required for queue/draft/confirm; customer gets 403; unauth gets 401.
2. REQUEST_IDENTITY_IMMUTABLE & REQUEST_AMOUNT_IMMUTABLE: Browser payload cannot tamper with user, amount, or request.
3. DURABLE_DECISION & DURABLE_OUTBOX: Exactly 1 decision receipt row and 1 credit operation outbox row in SQLite.
4. EXACTLY_ONE_CREDIT_INTENT & DOUBLE_APPROVE_DOUBLE_CREDIT=0: Replay confirmation never causes double credit.
5. BOT_UNAVAILABLE_FAKE_SUCCESS=0: Bridge timeout/5xx/missing receipt fails closed, request stays pending.
6. CANONICAL_RECEIPT_REQUIRED: Request only becomes approved upon genuine Bot ledger receipt.
7. REJECTION_CREDIT_CALLS=0: Rejection path never calls Bot credit.
8. TERMINAL_STATE_FLIP=0: No approve after reject, no reject after approve.
9. DIRECT_BOT_WALLET_SQLITE_WRITE=0 & LOCAL_FAKE_BALANCE_INCREMENT=0: Web never directly mutates Bot SQLite.
10. ADMIN_LIST_DETAIL_TRUTH: List and detail reflect SQLite state without client derivation.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_db
from copyfast_db import (
    create_web_manual_topup_request,
    get_web_manual_topup_for_admin,
    ensure_copyfast_schema,
)


@pytest.fixture(scope="module")
def web03_env(tmp_path_factory):
    original_env = {
        "WEBAPP_SESSION_DB_PATH": os.environ.get("WEBAPP_SESSION_DB_PATH"),
        "WEB_SESSION_SECRET": os.environ.get("WEB_SESSION_SECRET"),
        "WEBAPP_ADMIN_ERP_ENABLED": os.environ.get("WEBAPP_ADMIN_ERP_ENABLED"),
        "WEBAPP_ADMIN_WRITES_ENABLED": os.environ.get("WEBAPP_ADMIN_WRITES_ENABLED"),
        "CORE_BRIDGE_BASE_URL": os.environ.get("CORE_BRIDGE_BASE_URL"),
        "CORE_BRIDGE_TOKEN": os.environ.get("CORE_BRIDGE_TOKEN"),
        "CORE_BRIDGE_HMAC_SECRET": os.environ.get("CORE_BRIDGE_HMAC_SECRET"),
    }
    tmp_dir = tmp_path_factory.mktemp("web03_approval_truth")
    db_path = str(tmp_dir / "web03_truth.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "web03-test-session-secret-key-64b-secure-value"
    os.environ["WEBAPP_ADMIN_ERP_ENABLED"] = "true"
    os.environ["WEBAPP_ADMIN_WRITES_ENABLED"] = "true"
    os.environ["CORE_BRIDGE_BASE_URL"] = "http://127.0.0.1:8080"
    os.environ["CORE_BRIDGE_TOKEN"] = "web03-fixture-bridge-token"
    os.environ["CORE_BRIDGE_HMAC_SECRET"] = "web03-fixture-bridge-hmac-secret"

    copyfast_db.ensure_copyfast_schema()
    if hasattr(app_module, "_auth_rate_windows"):
        app_module._auth_rate_windows.clear()

    # Base setup client
    setup_client = TestClient(app_module.app)

    # 1. Register and setup Admin account
    admin_email = "admin_web03@toanaas.vn"
    admin_pwd = "AdminWeb03Password2026!"
    reg_admin = setup_client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "password": admin_pwd, "display_name": "Admin Web03"},
    )
    assert reg_admin.status_code == 200
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457028' WHERE email=?",
            (admin_email,),
        )
        admin_id = str(conn.execute("SELECT id FROM web_accounts WHERE email=?", (admin_email,)).fetchone()[0])
        conn.commit()

    login_admin = setup_client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_pwd})
    assert login_admin.status_code == 200
    admin_csrf = login_admin.json()["data"]["csrf_token"]
    admin_cookies = dict(login_admin.cookies)

    # Admin client with bound cookies and CSRF header
    admin_client = TestClient(app_module.app, cookies=admin_cookies)
    admin_client.headers["X-CSRF-Token"] = admin_csrf

    # 2. Register and setup Customer account
    cust_email = "customer_web03@toanaas.vn"
    cust_pwd = "CustWeb03Password2026!"
    reg_cust = setup_client.post(
        "/api/v1/auth/register",
        json={"email": cust_email, "password": cust_pwd, "display_name": "Customer Web03"},
    )
    assert reg_cust.status_code == 200
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_accounts SET canonical_user_id='88889999' WHERE email=?",
            (cust_email,),
        )
        cust_id = str(conn.execute("SELECT id FROM web_accounts WHERE email=?", (cust_email,)).fetchone()[0])
        conn.commit()

    login_cust = setup_client.post("/api/v1/auth/login", json={"email": cust_email, "password": cust_pwd})
    assert login_cust.status_code == 200
    cust_csrf = login_cust.json()["data"]["csrf_token"]
    cust_cookies = dict(login_cust.cookies)

    # Customer client with bound cookies and CSRF header
    cust_client = TestClient(app_module.app, cookies=cust_cookies)
    cust_client.headers["X-CSRF-Token"] = cust_csrf

    # 3. Unauthenticated client
    unauth_client = TestClient(app_module.app)

    yield {
        "admin_client": admin_client,
        "cust_client": cust_client,
        "unauth_client": unauth_client,
        "db_path": db_path,
        "admin_id": admin_id,
        "admin_email": admin_email,
        "cust_id": cust_id,
        "cust_email": cust_email,
    }
    if hasattr(app_module, "_auth_rate_windows"):
        app_module._auth_rate_windows.clear()
    for k, v in original_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _create_customer_and_topup(
    db_path: str,
    suffix: str,
    amount_vnd: int = 100_000,
    canonical_user_id: str | None = "default",
) -> tuple[str, str, str]:
    account_id = f"00000000-0000-4000-8000-{hashlib.md5(suffix.encode()).hexdigest()[:12]}"
    user_email = f"user_{suffix}@toanaas.vn"
    canon_id = f"canon_{suffix}" if canonical_user_id == "default" else canonical_user_id
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO web_accounts (id, email, display_name, password_hash, role_cache, canonical_user_id, created_at, updated_at) "
            "VALUES (?, ?, 'Customer', 'mock_hash', 'user', ?, datetime('now'), datetime('now'))",
            (account_id, user_email, canon_id),
        )
        conn.commit()

    idemp_hash = hashlib.sha256(f"web03-idemp-{suffix}".encode()).hexdigest()
    fp_hash = hashlib.sha256(f"web03-fp-{suffix}".encode()).hexdigest()
    created = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=amount_vnd,
        method="bank_acb_vietqr",
        reference=f"REF-WEB03-{suffix}",
        idempotency_key_hash=idemp_hash,
        request_fingerprint=fp_hash,
    )
    return created["request_id"], account_id, str(canon_id or "")


def test_admin_rbac_truth(web03_env, monkeypatch):
    """Sections 4: Prove Admin vs Customer vs Unauth vs Flags RBAC behavior."""
    admin_client = web03_env["admin_client"]
    cust_client = web03_env["cust_client"]
    unauth_client = web03_env["unauth_client"]
    db_path = web03_env["db_path"]

    req_id, _, _ = _create_customer_and_topup(db_path, "rbac_test", amount_vnd=50_000)

    # 1. Authenticated Admin -> 200 OK
    res_list = admin_client.get("/api/v1/admin/payments/manual")
    assert res_list.status_code == 200
    assert res_list.json()["ok"] is True

    res_detail = admin_client.get(f"/api/v1/admin/payments/manual/{req_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["ok"] is True

    res_draft = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/draft",
        json={"action": "approve", "reason": "Admin test draft"},
    )
    assert res_draft.status_code == 200
    assert res_draft.json()["status"] == "awaiting_confirm"

    # 2. Normal Customer -> 403 Forbidden
    res_cust_list = cust_client.get("/api/v1/admin/payments/manual")
    assert res_cust_list.status_code == 403

    res_cust_detail = cust_client.get(f"/api/v1/admin/payments/manual/{req_id}")
    assert res_cust_detail.status_code == 403

    res_cust_draft = cust_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/draft",
        json={"action": "approve", "reason": "Customer attempt"},
    )
    assert res_cust_draft.status_code == 403

    res_cust_compat = cust_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Customer compat attempt"},
    )
    assert res_cust_compat.status_code == 403

    # 3. Unauthenticated -> 401 Unauthorized
    res_unauth_list = unauth_client.get("/api/v1/admin/payments/manual")
    assert res_unauth_list.status_code == 401

    res_unauth_detail = unauth_client.get(f"/api/v1/admin/payments/manual/{req_id}")
    assert res_unauth_detail.status_code == 401

    res_unauth_draft = unauth_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/draft",
        json={"action": "approve", "reason": "Unauth attempt"},
    )
    assert res_unauth_draft.status_code == 401

    # 4. Feature flags disabled
    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
    res_disabled_erp = admin_client.get("/api/v1/admin/payments/manual")
    assert res_disabled_erp.status_code == 200
    assert res_disabled_erp.json()["error_code"] == "WEBAPP_MANUAL_ADMIN_DISABLED"

    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ADMIN_WRITES_ENABLED", "false")
    res_disabled_writes = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/draft",
        json={"action": "approve", "reason": "Writes disabled test"},
    )
    assert res_disabled_writes.status_code == 200
    assert res_disabled_writes.json()["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"


def test_request_identity_and_amount_immutability(web03_env, monkeypatch):
    """Section 5: Browser approval payload cannot tamper with user, amount, or request."""
    admin_client = web03_env["admin_client"]
    db_path = web03_env["db_path"]

    req_id, _, _ = _create_customer_and_topup(db_path, "tamper_test", amount_vnd=100_000)

    # Attempt to inject extra fields in draft (tampered user_id, amount)
    tampered_draft = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/draft",
        json={
            "action": "approve",
            "reason": "Tamper test",
            "user_id": "forged-target-9999",
            "amount_xu": 999999,
        },
    )
    # Pydantic extra="forbid" rejects with 422
    assert tampered_draft.status_code == 422

    # Valid draft
    valid_draft = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/draft",
        json={"action": "approve", "reason": "Hợp lệ"},
    )
    assert valid_draft.status_code == 200
    receipt = valid_draft.json()["data"]["confirmation_receipt"]

    # Attempt to inject extra fields in confirm
    tampered_confirm = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/confirm",
        json={
            "confirmation_receipt": receipt,
            "idempotency_key": "idemp-tamper-key-001",
            "canonical_user_id": "forged-user-id",
            "amount_xu": 888888,
        },
    )
    assert tampered_confirm.status_code == 422


def test_durable_approval_decision_and_outbox(web03_env, monkeypatch):
    """Section 6 & 7: Exactly one durable decision and one outbox row in SQLite."""
    admin_client = web03_env["admin_client"]
    db_path = web03_env["db_path"]

    req_id, _, canon_user = _create_customer_and_topup(db_path, "durable_test", amount_vnd=200_000)
    req_num = int(req_id.split("-", 1)[1])

    # Pre-check: 0 decision receipts, 0 credit operations
    with sqlite3.connect(db_path) as conn:
        d_cnt = conn.execute("SELECT COUNT(*) FROM web_manual_topup_approve_receipts WHERE manual_topup_id = ?", (req_num,)).fetchone()[0]
        o_cnt = conn.execute("SELECT COUNT(*) FROM web_manual_topup_credit_operations WHERE manual_topup_id = ?", (req_num,)).fetchone()[0]
        assert d_cnt == 0
        assert o_cnt == 0

    # Draft approval
    draft_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/draft",
        json={"action": "approve", "reason": "Duyệt topup 200k"},
    )
    assert draft_res.status_code == 200
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    with sqlite3.connect(db_path) as conn:
        d_cnt = conn.execute("SELECT COUNT(*) FROM web_manual_topup_approve_receipts WHERE manual_topup_id = ?", (req_num,)).fetchone()[0]
        assert d_cnt == 1  # DECISION_ROWS = 1

    # Fake bridge setup
    outbound_calls = []

    async def fake_bridge_request(method, path, **kwargs):
        outbound_calls.append({"method": method, "path": path, "kwargs": kwargs})
        if path == "/internal/v1/admin/wallet/credit":
            return {
                "ok": True,
                "status": "completed",
                "message": "Credited in Bot Core Ledger",
                "data": {"tx_id": "core-tx-durable-001", "ledger_event_id": "core-tx-durable-001"},
            }
        return {"ok": False, "error_code": "NOT_FOUND"}

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge_request)
    if hasattr(app_module, "copyfast_api"):
        monkeypatch.setattr(app_module.copyfast_api, "bridge_configured", lambda: True)
        monkeypatch.setattr(app_module.copyfast_api, "bridge_request", fake_bridge_request)

    # Confirm approval
    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-durable-confirm-01"},
    )
    assert confirm_res.status_code == 200
    body = confirm_res.json()
    assert body["ok"] is True
    assert body["status"] == "approved"
    assert body["data"]["approved_xu"] == 2000  # 200,000 // 100 = 2,000 Xu
    assert body["data"]["ledger_event_id"] == "core-tx-durable-001"

    # Verify Durable rows in SQLite
    with sqlite3.connect(db_path) as conn:
        d_cnt = conn.execute("SELECT COUNT(*) FROM web_manual_topup_approve_receipts WHERE manual_topup_id = ?", (req_num,)).fetchone()[0]
        o_cnt = conn.execute("SELECT COUNT(*) FROM web_manual_topup_credit_operations WHERE manual_topup_id = ?", (req_num,)).fetchone()[0]
        assert d_cnt == 1  # DECISION_ROWS = 1
        assert o_cnt == 1  # OUTBOX_ROWS = 1

        op_row = conn.execute(
            "SELECT status, ledger_event_id, amount_xu, canonical_user_id, idempotency_key FROM web_manual_topup_credit_operations WHERE manual_topup_id = ?",
            (req_num,),
        ).fetchone()
        assert op_row[0] == "local_approval_persisted"
        assert op_row[1] == "core-tx-durable-001"
        assert op_row[2] == 2000
        assert op_row[3] == canon_user
        assert op_row[4] == f"web:admin:manual_topup:{req_id}"

    # Verify outbound call shape
    assert len(outbound_calls) == 1
    call = outbound_calls[0]
    assert call["method"] == "POST"
    assert call["path"] == "/internal/v1/admin/wallet/credit"
    payload = call["kwargs"]["payload"]
    assert payload["canonical_user_id"] == canon_user
    assert payload["amount_xu"] == 2000
    assert payload["idempotency_key"] == f"web:admin:manual_topup:{req_id}"
    assert "actor_id" in call["kwargs"]

    # Replay approval confirm (Exact replay)
    replay_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-durable-confirm-01"},
    )
    assert replay_res.status_code == 200
    assert replay_res.json()["data"]["idempotent_replay"] is True
    # Zero second credit call
    assert len(outbound_calls) == 1  # DOUBLE_APPROVE_DOUBLE_CREDIT = 0


def test_bot_unavailable_and_timeout_fail_closed(web03_env, monkeypatch):
    """Section 8: Bot unavailable, timeout, 5xx, or malformed receipt fails closed without fake success."""
    admin_client = web03_env["admin_client"]
    db_path = web03_env["db_path"]

    # 1. Timeout simulation
    req_timeout, _, _ = _create_customer_and_topup(db_path, "timeout_test", amount_vnd=70_000)
    req_num_to = int(req_timeout.split("-", 1)[1])

    draft_to = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_timeout}/draft",
        json={"action": "approve", "reason": "Timeout test"},
    )
    assert draft_to.status_code == 200
    receipt_to = draft_to.json()["data"]["confirmation_receipt"]

    async def timeout_bridge(*args, **kwargs):
        raise httpx.ReadTimeout("Connection timed out to Core Bridge")

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", timeout_bridge)
    if hasattr(app_module, "copyfast_api"):
        monkeypatch.setattr(app_module.copyfast_api, "bridge_configured", lambda: True)
        monkeypatch.setattr(app_module.copyfast_api, "bridge_request", timeout_bridge)

    confirm_to = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_timeout}/confirm",
        json={"confirmation_receipt": receipt_to, "idempotency_key": "idemp-to-key-01"},
    )
    assert confirm_to.status_code == 504
    assert confirm_to.json()["error_code"] == "CORE_BRIDGE_TIMEOUT"

    # Request remains pending_admin_review in DB; operation status is reconcile_required
    with sqlite3.connect(db_path) as conn:
        status = conn.execute("SELECT status FROM web_manual_topup_requests WHERE id = ?", (req_num_to,)).fetchone()[0]
        assert status == "pending_admin_review"
        op_status = conn.execute("SELECT status FROM web_manual_topup_credit_operations WHERE manual_topup_id = ?", (req_num_to,)).fetchone()[0]
        assert op_status == "reconcile_required"

    # 2. Bot 5xx simulation
    req_5xx, _, _ = _create_customer_and_topup(db_path, "five_xx_test", amount_vnd=80_000)
    req_num_5xx = int(req_5xx.split("-", 1)[1])

    draft_5xx = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_5xx}/draft",
        json={"action": "approve", "reason": "5xx test"},
    )
    assert draft_5xx.status_code == 200
    receipt_5xx = draft_5xx.json()["data"]["confirmation_receipt"]

    async def bot_5xx_bridge(*args, **kwargs):
        return {"ok": False, "error_code": "CORE_BRIDGE_UNAVAILABLE", "message": "Bot ledger service down"}

    monkeypatch.setattr(copyfast_api, "bridge_request", bot_5xx_bridge)
    if hasattr(app_module, "copyfast_api"):
        monkeypatch.setattr(app_module.copyfast_api, "bridge_request", bot_5xx_bridge)

    confirm_5xx = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_5xx}/confirm",
        json={"confirmation_receipt": receipt_5xx, "idempotency_key": "idemp-5xx-key-01"},
    )
    assert confirm_5xx.status_code == 503
    assert confirm_5xx.json()["error_code"] == "CORE_BRIDGE_UNAVAILABLE"

    with sqlite3.connect(db_path) as conn:
        status = conn.execute("SELECT status FROM web_manual_topup_requests WHERE id = ?", (req_num_5xx,)).fetchone()[0]
        assert status == "pending_admin_review"

    # 3. Malformed / Missing receipt simulation
    req_bad_rcpt, _, _ = _create_customer_and_topup(db_path, "bad_rcpt_test", amount_vnd=90_000)
    req_num_br = int(req_bad_rcpt.split("-", 1)[1])

    draft_br = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_bad_rcpt}/draft",
        json={"action": "approve", "reason": "Bad receipt test"},
    )
    assert draft_br.status_code == 200
    receipt_br = draft_br.json()["data"]["confirmation_receipt"]

    async def bot_bad_receipt_bridge(*args, **kwargs):
        return {"ok": True, "data": {"tx_id": "local-credit-fake-12345"}}

    monkeypatch.setattr(copyfast_api, "bridge_request", bot_bad_receipt_bridge)
    if hasattr(app_module, "copyfast_api"):
        monkeypatch.setattr(app_module.copyfast_api, "bridge_request", bot_bad_receipt_bridge)

    confirm_br = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_bad_rcpt}/confirm",
        json={"confirmation_receipt": receipt_br, "idempotency_key": "idemp-br-key-01"},
    )
    assert confirm_br.status_code == 502
    assert confirm_br.json()["error_code"] == "WALLET_CREDIT_RECEIPT_MISSING"

    with sqlite3.connect(db_path) as conn:
        status = conn.execute("SELECT status FROM web_manual_topup_requests WHERE id = ?", (req_num_br,)).fetchone()[0]
        assert status == "pending_admin_review"


def test_rejection_path_zero_bot_credit_calls(web03_env, monkeypatch):
    """Section 11: Rejecting a pending manual topup must NOT call Bot credit."""
    admin_client = web03_env["admin_client"]
    db_path = web03_env["db_path"]

    req_id, _, _ = _create_customer_and_topup(db_path, "reject_test", amount_vnd=150_000)
    req_num = int(req_id.split("-", 1)[1])

    bridge_calls = []

    async def track_bridge(*args, **kwargs):
        bridge_calls.append(args)
        return {"ok": True}

    monkeypatch.setattr(copyfast_api, "bridge_request", track_bridge)
    if hasattr(app_module, "copyfast_api"):
        monkeypatch.setattr(app_module.copyfast_api, "bridge_request", track_bridge)

    # Draft rejection
    draft_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/draft",
        json={"action": "reject", "reason": "Không thấy tiền nổi trên sao kê VCB"},
    )
    assert draft_res.status_code == 200
    assert draft_res.json()["data"]["action"] == "reject"
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    # Confirm rejection
    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-reject-key-01"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "rejected"

    # Zero Bot credit calls
    assert len(bridge_calls) == 0  # BOT_CREDIT_CALLS = 0

    # Verify SQLite status
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, decision_reason, decided_by_account_id FROM web_manual_topup_requests WHERE id = ?",
            (req_num,),
        ).fetchone()
        assert row[0] == "rejected"
        assert row[1] == "Không thấy tiền nổi trên sao kê VCB"
        assert row[2] == web03_env["admin_id"]

    # Replay rejection confirm -> idempotent
    replay_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-reject-key-01"},
    )
    assert replay_res.status_code == 200
    assert replay_res.json()["data"]["idempotent_replay"] is True
    assert len(bridge_calls) == 0


def test_replay_and_idempotency_matrix_terminal_states(web03_env, monkeypatch):
    """Section 10: Terminal states cannot flip (NO_TERMINAL_STATE_FLIP)."""
    admin_client = web03_env["admin_client"]
    db_path = web03_env["db_path"]

    # 1. Test Approve after Reject -> 409 MANUAL_ADMIN_NOT_PENDING
    req_rej, _, _ = _create_customer_and_topup(db_path, "term_rej_test", amount_vnd=50_000)
    d_rej = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_rej}/draft",
        json={"action": "reject", "reason": "Từ chối giao dịch sai nội dung"},
    )
    rcpt_rej = d_rej.json()["data"]["confirmation_receipt"]
    admin_client.post(
        f"/api/v1/admin/payments/manual/{req_rej}/confirm",
        json={"confirmation_receipt": rcpt_rej, "idempotency_key": "idemp-term-rej-01"},
    )

    # Now attempt to draft approve on rejected request
    app_after_rej = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_rej}/draft",
        json={"action": "approve", "reason": "Cố duyệt lại request đã từ chối"},
    )
    assert app_after_rej.status_code == 409
    assert app_after_rej.json()["error_code"] == "MANUAL_ADMIN_NOT_PENDING"

    # 2. Test Reject after Approve -> 409 MANUAL_ADMIN_NOT_PENDING
    req_app, _, _ = _create_customer_and_topup(db_path, "term_app_test", amount_vnd=60_000)

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(
        copyfast_api,
        "bridge_request",
        AsyncMock(return_value={"ok": True, "data": {"tx_id": "core-tx-term-app-99"}}),
    )
    if hasattr(app_module, "copyfast_api"):
        monkeypatch.setattr(app_module.copyfast_api, "bridge_configured", lambda: True)
        monkeypatch.setattr(
            app_module.copyfast_api,
            "bridge_request",
            AsyncMock(return_value={"ok": True, "data": {"tx_id": "core-tx-term-app-99"}}),
        )

    d_app = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_app}/draft",
        json={"action": "approve", "reason": "Duyệt thành công"},
    )
    rcpt_app = d_app.json()["data"]["confirmation_receipt"]
    c_app = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_app}/confirm",
        json={"confirmation_receipt": rcpt_app, "idempotency_key": "idemp-term-app-01"},
    )
    assert c_app.status_code == 200

    # Now attempt to draft reject on approved request
    rej_after_app = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_app}/draft",
        json={"action": "reject", "reason": "Cố từ chối request đã duyệt"},
    )
    assert rej_after_app.status_code == 409
    assert rej_after_app.json()["error_code"] == "MANUAL_ADMIN_NOT_PENDING"


def test_unknown_and_invalid_request_fail_closed(web03_env):
    """Section 12: Missing, malformed, or unlinked request fails closed."""
    admin_client = web03_env["admin_client"]
    db_path = web03_env["db_path"]

    # 1. Non-existent request
    res_404 = admin_client.get("/api/v1/admin/payments/manual/MANUAL-999999")
    assert res_404.status_code == 404
    assert res_404.json()["error_code"] == "MANUAL_ADMIN_NOT_FOUND"

    res_draft_404 = admin_client.post(
        "/api/v1/admin/payments/manual/MANUAL-999999/draft",
        json={"action": "approve", "reason": "Non-existent"},
    )
    assert res_draft_404.status_code == 404

    # 2. Malformed request IDs
    for malformed in ("MANUAL-0", "MANUAL-abc", "INVALID-123"):
        res_malformed = admin_client.get(f"/api/v1/admin/payments/manual/{malformed}")
        assert res_malformed.status_code == 404

    # 3. Unlinked user topup approval fails closed with 422
    req_unlinked, _, _ = _create_customer_and_topup(db_path, "unlinked_test", amount_vnd=50_000, canonical_user_id=None)
    draft_un = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_unlinked}/draft",
        json={"action": "approve", "reason": "Unlinked draft"},
    )
    assert draft_un.status_code == 200
    rcpt_un = draft_un.json()["data"]["confirmation_receipt"]

    confirm_un = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_unlinked}/confirm",
        json={"confirmation_receipt": rcpt_un, "idempotency_key": "idemp-unlinked-01"},
    )
    assert confirm_un.status_code == 422
    assert confirm_un.json()["error_code"] == "WALLET_CREDIT_USER_UNLINKED"


def test_admin_list_and_detail_truth(web03_env):
    """Section 13: List & detail reflect durable DB state, never client derivation."""
    admin_client = web03_env["admin_client"]
    db_path = web03_env["db_path"]

    req_p, _, _ = _create_customer_and_topup(db_path, "queue_truth_test", amount_vnd=30_000)

    # Inspect pending list
    res_list = admin_client.get("/api/v1/admin/payments/manual?status=pending")
    assert res_list.status_code == 200
    items = res_list.json()["data"]["items"]
    found = [it for it in items if it["request_id"] == req_p]
    assert len(found) == 1
    assert found[0]["status"] == "pending_admin_review"
    assert found[0]["amount_vnd"] == 30_000

    # Inspect detail
    res_det = admin_client.get(f"/api/v1/admin/payments/manual/{req_p}")
    assert res_det.status_code == 200
    detail = res_det.json()["data"]
    assert detail["request_id"] == req_p
    assert detail["status"] == "pending_admin_review"
    assert detail["amount_vnd"] == 30_000
    assert detail.get("ledger_event_id") in (None, "")


def test_canonical_credit_authority_and_no_direct_bot_sqlite_write():
    """Section 3: Web repo has 0 direct SQLite writes to Bot Core wallet/credits."""
    api_text = copyfast_api.__file__
    with open(api_text, encoding="utf-8") as f:
        api_code = f.read()

    db_text = copyfast_db.__file__
    with open(db_text, encoding="utf-8") as f:
        db_code = f.read()

    # Web must NEVER directly mutate bot tables: 'UPDATE users SET credits', 'INSERT INTO credit_events'
    assert "UPDATE users SET credits" not in api_code
    assert "UPDATE users SET credits" not in db_code
    assert "INSERT INTO credit_events" not in api_code
    assert "INSERT INTO credit_events" not in db_code


def test_10_full_e2e_customer_create_admin_approve_and_customer_refresh(web03_env, monkeypatch):
    """Section 20 Full E2E Lifecycle Truth:
    1. Customer checks wallet balance (initially 0 Xu).
    2. Customer submits manual topup request (500,000 VND -> 5,000 Xu).
    3. Customer sees request pending_admin_review with generated request_id.
    4. Admin sees request in pending review queue (/api/v1/admin/payments/manual?status=pending).
    5. Admin clicks 'Duyệt & Cộng Xu' -> Step 1: Draft approval creates confirmation receipt.
    6. Admin confirms approval modal -> Step 2: Confirm approval credits Xu via Bot Core Ledger bridge.
    7. Double-click & replay idempotency: Admin confirms again with same idempotency key -> returns idempotent replay.
    8. Customer reads request status -> approved.
    9. Customer refreshes wallet balance & history -> reflects credited Xu from Bot ledger.
    10. Admin detail shows status approved with immutable audit fields.
    """
    admin_client = web03_env["admin_client"]
    cust_client = web03_env["cust_client"]
    db_path = web03_env["db_path"]

    # Mock Bot Core Bridge for wallet and credit
    customer_balance = {"xu": 0, "history": []}
    bridge_calls = []

    async def fake_bridge(method, path, **kwargs):
        bridge_calls.append({"method": method, "path": path, "kwargs": kwargs})
        if path == "/internal/v1/admin/wallet/credit":
            payload = kwargs.get("payload") or {}
            amt = payload.get("amount_xu", 0)
            customer_balance["xu"] += amt
            event_id = "core-tx-e2e-approved-999"
            customer_balance["history"].append({
                "id": event_id,
                "event_type": "manual_topup_credit",
                "delta_xu": amt,
                "balance_after_xu": customer_balance["xu"],
                "reason": payload.get("reason", ""),
                "created_at": "2026-09-25T10:00:00Z",
            })
            return {
                "ok": True,
                "status": "completed",
                "message": "Credited in Bot Core Ledger",
                "data": {"tx_id": event_id, "ledger_event_id": event_id},
            }
        elif path == "/internal/v1/wallet":
            return {
                "ok": True,
                "status": "available",
                "data": {
                    "balance_xu": customer_balance["xu"],
                    "currency": "XU",
                    "status": "active",
                },
            }
        elif path == "/internal/v1/wallet/history":
            return {
                "ok": True,
                "status": "available",
                "data": {
                    "items": customer_balance["history"],
                    "total": len(customer_balance["history"]),
                },
            }
        return {"ok": False, "error_code": "NOT_FOUND"}

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)
    monkeypatch.setattr(copyfast_api, "_manual_payment_destinations", lambda: {
        "bank_acb_vietqr": {
            "label": "ACB VietQR",
            "currency": "VND",
            "mode": "transfer",
            "display_ready": True,
            "request_enabled": True,
        }
    })
    if hasattr(app_module, "copyfast_api"):
        monkeypatch.setattr(app_module.copyfast_api, "bridge_configured", lambda: True)
        monkeypatch.setattr(app_module.copyfast_api, "bridge_request", fake_bridge)
        monkeypatch.setattr(app_module.copyfast_api, "_manual_payment_destinations", lambda: {
            "bank_acb_vietqr": {
                "label": "ACB VietQR",
                "currency": "VND",
                "mode": "transfer",
                "display_ready": True,
                "request_enabled": True,
            }
        })

    # 1. Customer checks initial wallet balance (0 Xu)
    init_wallet = cust_client.get("/api/v1/wallet")
    assert init_wallet.status_code == 200
    assert init_wallet.json()["data"]["balance_xu"] == 0

    # 2. Customer creates manual topup request (500,000 VND -> 5,000 Xu)
    create_res = cust_client.post(
        "/api/v1/payments/manual",
        json={
            "amount_vnd": 500_000,
            "method": "bank_acb_vietqr",
            "reference": "REF-E2E-FULL-LIFECYCLE-001",
            "idempotency_key": "idemp-cust-e2e-full-001",
        },
    )
    assert create_res.status_code == 200
    create_data = create_res.json()["data"]
    request_id = create_data["request_id"]
    assert create_data["status"] == "pending_admin_review"
    assert create_data["amount_vnd"] == 500_000

    # 3. Customer checks individual topup status
    cust_view = cust_client.get(f"/api/v1/payments/manual/{request_id}")
    assert cust_view.status_code == 200
    assert cust_view.json()["data"]["status"] == "pending_admin_review"

    # 4. Admin views pending queue and finds the request
    admin_queue = admin_client.get("/api/v1/admin/payments/manual?status=pending")
    assert admin_queue.status_code == 200
    found = [it for it in admin_queue.json()["data"]["items"] if it["request_id"] == request_id]
    assert len(found) == 1
    assert found[0]["status"] == "pending_admin_review"

    # 5. Admin clicks "Duyệt & Cộng Xu" -> Step 1: Draft approval
    draft_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{request_id}/draft",
        json={"action": "approve", "reason": "Xác nhận đã nhận chuyển khoản ngân hàng 500.000đ"},
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()["data"]
    assert draft_data["action"] == "approve"
    assert draft_data["approved_xu"] == 5000
    receipt = draft_data["confirmation_receipt"]
    assert receipt

    # 6. Admin confirms in modal -> Step 2: Confirm approval & credit Xu
    confirm_key = "idemp-admin-confirm-e2e-001"
    credit_calls_before = len([c for c in bridge_calls if c["path"] == "/internal/v1/admin/wallet/credit"])
    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{request_id}/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": confirm_key},
    )
    assert confirm_res.status_code == 200
    confirm_body = confirm_res.json()
    assert confirm_body["ok"] is True
    assert confirm_body["status"] == "approved"
    assert confirm_body["data"]["approved_xu"] == 5000
    assert confirm_body["data"]["ledger_event_id"] == "core-tx-e2e-approved-999"

    credit_calls_after = len([c for c in bridge_calls if c["path"] == "/internal/v1/admin/wallet/credit"])
    assert credit_calls_after == credit_calls_before + 1

    # 7. Double-click & replay idempotency: Admin confirms again with same idempotency key
    replay_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{request_id}/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": confirm_key},
    )
    assert replay_res.status_code == 200
    assert replay_res.json()["data"]["idempotent_replay"] is True
    assert len([c for c in bridge_calls if c["path"] == "/internal/v1/admin/wallet/credit"]) == credit_calls_after

    # 8. Customer checks request status -> approved
    cust_view_approved = cust_client.get(f"/api/v1/payments/manual/{request_id}")
    assert cust_view_approved.status_code == 200
    assert cust_view_approved.json()["data"]["status"] == "approved"

    # 9. Customer refreshes wallet balance & history -> 5,000 Xu credited!
    refreshed_wallet = cust_client.get("/api/v1/wallet")
    assert refreshed_wallet.status_code == 200
    assert refreshed_wallet.json()["data"]["balance_xu"] == 5000

    refreshed_history = cust_client.get("/api/v1/wallet/history")
    assert refreshed_history.status_code == 200
    history_items = refreshed_history.json()["data"]["items"]
    assert len(history_items) == 1
    assert history_items[0]["delta_xu"] == 5000
    assert history_items[0]["balance_after_xu"] == 5000

    # 10. Admin checks detail -> status approved, audit fields immutable
    admin_detail = admin_client.get(f"/api/v1/admin/payments/manual/{request_id}")
    assert admin_detail.status_code == 200
    detail_data = admin_detail.json()["data"]
    assert detail_data["status"] == "approved"
    assert detail_data["ledger_event_id"] == "core-tx-e2e-approved-999"
    assert detail_data["decision_reason"] == "Xác nhận đã nhận chuyển khoản ngân hàng 500.000đ"
    assert detail_data["approved_xu"] == 5000
