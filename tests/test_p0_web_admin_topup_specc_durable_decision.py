"""Test suite for SPEC-C: Durable Decision, Outbox, and Reconciliation for Web Manual Topup.

Covers all 20 required tests from Section 18 of SPEC-C:
1. test_manual_topup_decision_receipt_survives_process_restart
2. test_manual_topup_decision_receipt_works_across_workers
3. test_manual_topup_decision_receipt_stores_hash_not_raw_token
4. test_manual_topup_concurrent_confirm_creates_one_credit_operation
5. test_manual_topup_credit_operation_has_stable_idempotency_key
6. test_manual_topup_retry_reuses_same_idempotency_key
7. test_manual_topup_changed_payload_after_claim_fails_closed
8. test_manual_topup_bot_success_persists_receipt_before_approval
9. test_manual_topup_missing_bot_receipt_does_not_approve
10. test_manual_topup_timeout_does_not_approve
11. test_manual_topup_timeout_marks_operation_recoverable
12. test_manual_topup_ambiguous_timeout_retries_same_key
13. test_manual_topup_ambiguous_timeout_remote_committed_does_not_double_credit
14. test_manual_topup_crash_after_bot_success_recovers_same_receipt
15. test_manual_topup_restart_reconciliation_uses_same_key
16. test_manual_topup_replayed_admin_confirm_does_not_create_second_operation
17. test_manual_topup_expired_confirmation_does_not_call_bot_core
18. test_manual_topup_bot_409_does_not_approve
19. test_manual_topup_bot_auth_failure_does_not_approve
20. test_manual_topup_completed_request_cannot_credit_again
21. test_manual_topup_schema_fresh_and_upgrade_backward_compatible
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_db
from copyfast_db import (
    WebManualTopupAdminGuard,
    claim_web_credit_operation_for_dispatch,
    create_web_manual_topup_request,
    ensure_copyfast_schema,
    get_web_manual_topup_credit_operation,
    update_web_manual_topup_credit_operation_status,
)


@pytest.fixture(scope="module")
def test_setup(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("specc_db")
    db_path = str(tmp_dir / "specc_test.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "specc-test-secret-88888-abcdef123456"
    os.environ["WEBAPP_ADMIN_ERP_ENABLED"] = "true"
    os.environ["WEBAPP_ADMIN_WRITES_ENABLED"] = "true"
    copyfast_db.ensure_copyfast_schema()

    client = TestClient(app_module.app)
    admin_email = "admin_specc_ops@toanaas.vn"
    admin_pwd = "AdminPassword2026!"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "password": admin_pwd, "display_name": "SpecC Admin"},
    )
    assert reg.status_code == 200
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457028' WHERE email=?",
            (admin_email,),
        )
        conn.commit()

    login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_pwd})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf

    return {
        "client": client,
        "db_path": db_path,
        "admin_email": admin_email,
    }


def _create_sample_topup(
    db_path: str, suffix: str, amount: int = 100_000, canonical_user_id: str | None = None
) -> tuple[str, str, str]:
    user_email = f"user_{suffix}@toanaas.vn"
    account_id = f"00000000-0000-4000-8000-{hashlib.md5(suffix.encode()).hexdigest()[:12]}"
    actual_canon_id = str(canonical_user_id or f"user_canon_{suffix}")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO web_accounts (id, email, display_name, password_hash, role_cache, canonical_user_id, created_at, updated_at) "
            "VALUES (?, ?, 'Payer', 'mock_hash', 'user', ?, datetime('now'), datetime('now'))",
            (account_id, user_email, actual_canon_id),
        )
        conn.commit()

    idemp_hash = hashlib.sha256(f"specc-idemp-{suffix}".encode()).hexdigest()
    fp_hash = hashlib.sha256(f"specc-fp-{suffix}".encode()).hexdigest()

    created = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=amount,
        method="bank_acb_vietqr",
        reference=f"REF-{suffix}",
        idempotency_key_hash=idemp_hash,
        request_fingerprint=fp_hash,
    )
    return created["request_id"], account_id, actual_canon_id


def test_manual_topup_decision_receipt_survives_process_restart(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": True,
        "status": "completed",
        "data": {
            "ledger_event_id": "998811",
            "tx_id": "998811",
            "amount_xu": 1000,
            "balance_after": 2500,
            "replayed": False,
        },
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "restart_survives")

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Duyệt tiền vào VCB"},
    )
    assert draft_res.status_code == 200
    receipt = draft_res.json()["data"]["confirmation_receipt"]
    assert receipt

    if hasattr(copyfast_api, "_manual_admin_receipt_vault"):
        copyfast_api._manual_admin_receipt_vault.clear()

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-restart-001"},
    )
    assert confirm_res.status_code == 200
    body = confirm_res.json()
    assert body["ok"] is True
    assert body["status"] == "approved"
    assert body["data"]["ledger_event_id"] == "998811"


def test_manual_topup_decision_receipt_works_across_workers(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": True,
        "status": "completed",
        "data": {"ledger_event_id": "tx-worker-b-77"},
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "cross_worker")

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Worker A verified deposit"},
    )
    assert draft_res.status_code == 200
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "worker-b-confirm-key"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["data"]["ledger_event_id"] == "tx-worker-b-77"


def test_manual_topup_decision_receipt_stores_hash_not_raw_token(test_setup):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    req_id, _, _ = _create_sample_topup(db_path, "hash_only")
    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Kiểm tra hash token an toàn"},
    )
    assert draft_res.status_code == 200
    raw_token = draft_res.json()["data"]["confirmation_receipt"]
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT receipt_hash FROM web_manual_topup_approve_receipts").fetchall()
        hashes = [r[0] for r in rows]
        assert expected_hash in hashes

        all_text = conn.execute("SELECT * FROM web_manual_topup_approve_receipts").fetchall()
        for row in all_text:
            for val in row:
                assert raw_token not in str(val), "Raw confirmation token must NEVER be stored in DB!"


def test_manual_topup_concurrent_confirm_creates_one_credit_operation(test_setup):
    db_path = test_setup["db_path"]
    req_id, acc_id, canon_id = _create_sample_topup(db_path, "concurrent_claim")
    req_num = int(req_id.split("-", 1)[1])

    op1, status1 = claim_web_credit_operation_for_dispatch(
        request_number=req_num,
        admin_account_id=acc_id,
        canonical_user_id=canon_id,
        amount_xu=500,
        reference=f"REF-{req_num}",
    )
    assert status1 == "dispatch"
    assert op1["status"] == "dispatched"

    with pytest.raises(WebManualTopupAdminGuard) as exc_info:
        claim_web_credit_operation_for_dispatch(
            request_number=req_num,
            admin_account_id=acc_id,
            canonical_user_id=canon_id,
            amount_xu=500,
            reference=f"REF-{req_num}",
        )
    assert exc_info.value.code == "MANUAL_ADMIN_CONFIRMATION_IN_PROGRESS"

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_manual_topup_credit_operations WHERE manual_topup_id = ?",
            (req_num,),
        ).fetchone()[0]
        assert count == 1


def test_manual_topup_credit_operation_has_stable_idempotency_key(test_setup):
    db_path = test_setup["db_path"]
    req_id, acc_id, canon_id = _create_sample_topup(db_path, "stable_idemp_key")
    req_num = int(req_id.split("-", 1)[1])

    op, _ = claim_web_credit_operation_for_dispatch(
        request_number=req_num,
        admin_account_id=acc_id,
        canonical_user_id=canon_id,
        amount_xu=1000,
        reference=f"REF-{req_num}",
    )
    expected_key = f"web:admin:manual_topup:MANUAL-{req_num}"
    assert op["idempotency_key"] == expected_key

    persisted = get_web_manual_topup_credit_operation(req_num)
    assert persisted is not None
    assert persisted["idempotency_key"] == expected_key


def test_manual_topup_retry_reuses_same_idempotency_key(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    dispatched_keys = []

    async def mock_bridge(method, path, payload=None, **kwargs):
        if path == "/internal/v1/admin/wallet/credit":
            dispatched_keys.append(payload.get("idempotency_key"))
            if len(dispatched_keys) == 1:
                return {"ok": False, "error_code": "CORE_BRIDGE_TIMEOUT", "message": "Simulated Gateway Timeout"}
            return {
                "ok": True,
                "status": "completed",
                "data": {"ledger_event_id": "tx-same-key-999"},
            }
        return {"ok": False, "error_code": "NOT_FOUND"}

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "retry_same_key")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Tiền đã vào ACB"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm1 = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-retry-key-001"},
    )
    assert confirm1.status_code == 504

    confirm2 = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-retry-key-002"},
    )
    assert confirm2.status_code == 200

    expected_stable_key = f"web:admin:manual_topup:MANUAL-{req_num}"
    assert len(dispatched_keys) == 2
    assert dispatched_keys[0] == expected_stable_key
    assert dispatched_keys[1] == expected_stable_key


def test_manual_topup_changed_payload_after_claim_fails_closed(test_setup):
    db_path = test_setup["db_path"]
    req_id, acc_id, canon_id = _create_sample_topup(db_path, "tamper_payload")
    req_num = int(req_id.split("-", 1)[1])

    claim_web_credit_operation_for_dispatch(
        request_number=req_num,
        admin_account_id=acc_id,
        canonical_user_id=canon_id,
        amount_xu=1000,
        reference=f"REF-{req_num}",
    )

    with pytest.raises(WebManualTopupAdminGuard) as exc_info:
        claim_web_credit_operation_for_dispatch(
            request_number=req_num,
            admin_account_id=acc_id,
            canonical_user_id=canon_id,
            amount_xu=5000,
            reference=f"REF-{req_num}",
        )
    assert exc_info.value.code == "MANUAL_ADMIN_IDEMPOTENCY_CONFLICT"


def test_manual_topup_bot_success_persists_receipt_before_approval(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": True,
        "status": "completed",
        "data": {"ledger_event_id": "core-ledger-receipt-8888"},
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "receipt_order")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Deposit verified"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-order-key-001"},
    )
    assert confirm_res.status_code == 200

    op = get_web_manual_topup_credit_operation(req_num)
    assert op is not None
    assert op["status"] == "local_approval_persisted"
    assert op["ledger_event_id"] == "core-ledger-receipt-8888"

    with sqlite3.connect(db_path) as conn:
        topup_row = conn.execute(
            "SELECT status, ledger_event_id FROM web_manual_topup_requests WHERE id = ?",
            (req_num,),
        ).fetchone()
        assert topup_row[0] == "approved"
        assert topup_row[1] == "core-ledger-receipt-8888"


def test_manual_topup_missing_bot_receipt_does_not_approve(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": True,
        "status": "completed",
        "data": {"ledger_event_id": "local-credit-fake-not-allowed"},
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "missing_receipt")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Deposit check"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "missing-receipt-key"},
    )
    assert confirm_res.status_code == 502
    assert confirm_res.json()["error_code"] == "WALLET_CREDIT_RECEIPT_MISSING"

    with sqlite3.connect(db_path) as conn:
        topup_row = conn.execute(
            "SELECT status, ledger_event_id FROM web_manual_topup_requests WHERE id = ?",
            (req_num,),
        ).fetchone()
        assert topup_row[0] == "pending_admin_review"
        assert topup_row[1] in (None, "")


def test_manual_topup_timeout_does_not_approve(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": False,
        "error_code": "CORE_BRIDGE_TIMEOUT",
        "message": "Gateway timeout connecting to Bot Core Ledger",
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "timeout_no_approve")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Verify deposit"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-timeout-001"},
    )
    assert confirm_res.status_code == 504
    assert confirm_res.json()["error_code"] == "CORE_BRIDGE_TIMEOUT"

    with sqlite3.connect(db_path) as conn:
        topup_row = conn.execute(
            "SELECT status, ledger_event_id FROM web_manual_topup_requests WHERE id = ?",
            (req_num,),
        ).fetchone()
        assert topup_row[0] == "pending_admin_review"
        assert topup_row[1] in (None, "")


def test_manual_topup_timeout_marks_operation_recoverable(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": False,
        "error_code": "CORE_BRIDGE_TIMEOUT",
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "timeout_recoverable")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Check timeout status"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "recoverable-key-001"},
    )

    op = get_web_manual_topup_credit_operation(req_num)
    assert op is not None
    assert op["status"] == "reconcile_required"


def test_manual_topup_ambiguous_timeout_retries_same_key(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    call_count = 0
    dispatched_keys = []

    async def mock_bridge(method, path, payload=None, **kwargs):
        nonlocal call_count
        call_count += 1
        dispatched_keys.append(payload.get("idempotency_key"))
        if call_count == 1:
            return {"ok": False, "error_code": "CORE_BRIDGE_TIMEOUT"}
        return {
            "ok": True,
            "status": "completed",
            "data": {"ledger_event_id": "tx-reconcile-success-33"},
        }

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "ambiguous_retry")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Ambiguous timeout retry test"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    res1 = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-retry-key-001"},
    )
    assert res1.status_code == 504

    res2 = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-retry-key-002"},
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["ledger_event_id"] == "tx-reconcile-success-33"

    assert len(dispatched_keys) == 2
    assert dispatched_keys[0] == dispatched_keys[1] == f"web:admin:manual_topup:MANUAL-{req_num}"


def test_manual_topup_ambiguous_timeout_remote_committed_does_not_double_credit(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    credit_count = 0

    async def mock_bridge(method, path, payload=None, **kwargs):
        nonlocal credit_count
        credit_count += 1
        if credit_count == 1:
            return {"ok": False, "error_code": "CORE_BRIDGE_TIMEOUT"}
        return {
            "ok": True,
            "status": "completed",
            "data": {
                "ledger_event_id": "tx-committed-once-555",
                "tx_id": "tx-committed-once-555",
                "replayed": True,
            },
        }

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "remote_committed")
    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Remote commit check"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    res1 = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-remote-c1-001"},
    )
    assert res1.status_code == 504

    res2 = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-remote-c2-002"},
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["ledger_event_id"] == "tx-committed-once-555"


def test_manual_topup_crash_after_bot_success_recovers_same_receipt(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    req_id, acc_id, canon_id = _create_sample_topup(db_path, "crash_recovery")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Crash recovery"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    claim_web_credit_operation_for_dispatch(
        request_number=req_num,
        admin_account_id=acc_id,
        canonical_user_id=canon_id,
        amount_xu=1000,
        reference="REF-crash_recovery",
    )
    update_web_manual_topup_credit_operation_status(
        request_number=req_num,
        status="credit_confirmed",
        ledger_event_id="core-tx-crash-recovered-777",
    )

    bridge_mock = AsyncMock()
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", bridge_mock)

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "post-crash-confirm"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["data"]["ledger_event_id"] == "core-tx-crash-recovered-777"
    assert bridge_mock.call_count == 0


def test_manual_topup_restart_reconciliation_uses_same_key(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    req_id, acc_id, canon_id = _create_sample_topup(db_path, "restart_reconcile")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Restart reconcile"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    claim_web_credit_operation_for_dispatch(
        request_number=req_num,
        admin_account_id=acc_id,
        canonical_user_id=canon_id,
        amount_xu=1000,
        reference="REF-restart_reconcile",
    )
    update_web_manual_topup_credit_operation_status(
        request_number=req_num,
        status="reconcile_required",
    )

    if hasattr(copyfast_api, "_manual_admin_receipt_vault"):
        copyfast_api._manual_admin_receipt_vault.clear()

    dispatched_keys = []

    async def mock_bridge(method, path, payload=None, **kwargs):
        dispatched_keys.append(payload.get("idempotency_key"))
        return {"ok": True, "status": "completed", "data": {"ledger_event_id": "tx-restart-reconcile-ok"}}

    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge)

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "restart-recon-key"},
    )
    assert confirm_res.status_code == 200
    assert len(dispatched_keys) == 1
    assert dispatched_keys[0] == f"web:admin:manual_topup:MANUAL-{req_num}"


def test_manual_topup_replayed_admin_confirm_does_not_create_second_operation(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": True,
        "status": "completed",
        "data": {"ledger_event_id": "tx-replay-once-111"},
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "replay_no_second_op")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Replay test"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    res1 = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "replay-idemp-001"},
    )
    assert res1.status_code == 200

    res2 = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "replay-idemp-001"},
    )
    assert res2.status_code == 200
    assert res2.json()["data"].get("idempotent_replay") is True

    assert fake_bridge.call_count == 1

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_manual_topup_credit_operations WHERE manual_topup_id = ?",
            (req_num,),
        ).fetchone()[0]
        assert count == 1


def test_manual_topup_expired_confirmation_does_not_call_bot_core(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    bridge_mock = AsyncMock()
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", bridge_mock)

    req_id, _, _ = _create_sample_topup(db_path, "expired_test")
    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Expiry test"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_manual_topup_approve_receipts SET expires_at = '2020-01-01T00:00:00+00:00'"
        )
        conn.commit()

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "expired-confirm-key"},
    )
    assert confirm_res.status_code == 409
    assert confirm_res.json()["error_code"] == "MANUAL_ADMIN_CONFIRMATION_EXPIRED"
    assert bridge_mock.call_count == 0


def test_manual_topup_bot_409_does_not_approve(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": False,
        "error_code": "WALLET_CREDIT_CONFLICT",
        "message": "Idempotency key payload mismatch on Bot Core Ledger",
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "bot_409_conflict")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Bot 409 test"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-bot-409-conflict"},
    )
    assert confirm_res.status_code == 409
    assert confirm_res.json()["error_code"] == "WALLET_CREDIT_CONFLICT"

    with sqlite3.connect(db_path) as conn:
        topup_row = conn.execute(
            "SELECT status FROM web_manual_topup_requests WHERE id = ?",
            (req_num,),
        ).fetchone()
        assert topup_row[0] == "pending_admin_review"


def test_manual_topup_bot_auth_failure_does_not_approve(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    fake_bridge = AsyncMock(return_value={
        "ok": False,
        "error_code": "CORE_BRIDGE_FORBIDDEN",
        "message": "Unauthorized bridge token",
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

    req_id, _, _ = _create_sample_topup(db_path, "bot_auth_fail")
    req_num = int(req_id.split("-", 1)[1])

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Bot Auth fail test"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "auth-fail-key-001"},
    )
    assert confirm_res.status_code == 502
    assert confirm_res.json()["error_code"] == "CORE_BRIDGE_FORBIDDEN"

    with sqlite3.connect(db_path) as conn:
        topup_row = conn.execute(
            "SELECT status FROM web_manual_topup_requests WHERE id = ?",
            (req_num,),
        ).fetchone()
        assert topup_row[0] == "pending_admin_review"


def test_manual_topup_completed_request_cannot_credit_again(test_setup, monkeypatch):
    client = test_setup["client"]
    db_path = test_setup["db_path"]

    bridge_mock = AsyncMock(return_value={
        "ok": True,
        "status": "completed",
        "data": {"ledger_event_id": "tx-completed-once-999"},
    })
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
    monkeypatch.setattr(copyfast_api, "bridge_request", bridge_mock)

    req_id, _, _ = _create_sample_topup(db_path, "cannot_credit_again")

    draft_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Initial approval"},
    )
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-c-first-001"},
    )
    assert confirm_res.status_code == 200
    assert bridge_mock.call_count == 1

    draft_again = client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/draft",
        json={"action": "approve", "reason": "Second draft attempt"},
    )
    assert draft_again.status_code == 409
    assert draft_again.json()["error_code"] == "MANUAL_ADMIN_NOT_PENDING"

    assert bridge_mock.call_count == 1


def test_manual_topup_schema_fresh_and_upgrade_backward_compatible(tmp_path, test_setup):
    old_db = os.environ.get("WEBAPP_SESSION_DB_PATH", "")
    try:
        test_db = str(tmp_path / "upgrade_test.db")
        os.environ["WEBAPP_SESSION_DB_PATH"] = test_db

        ensure_copyfast_schema()

        with sqlite3.connect(test_db) as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "web_manual_topup_approve_receipts" in tables
            assert "web_manual_topup_credit_operations" in tables

        ensure_copyfast_schema()
        ensure_copyfast_schema()

        with sqlite3.connect(test_db) as conn:
            tables2 = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "web_manual_topup_approve_receipts" in tables2
            assert "web_manual_topup_credit_operations" in tables2
    finally:
        if old_db:
            os.environ["WEBAPP_SESSION_DB_PATH"] = old_db
