"""Test suite for SPEC A: Manual Topup Fail-Closed without fake wallet credit.

Verifies:
1. When Bot Core bridge is unconfigured, confirm returns HTTP 503 WALLET_CREDIT_BRIDGE_UNAVAILABLE.
2. Request remains pending_admin_review in Web SQLite.
3. No fake ledger_event_id (local-credit-*) is ever generated or persisted.
4. Response does not claim Xu was credited.
5. Bridge timeout/5xx/network error keeps request pending and does not mark approved.
6. Missing/invalid bridge ledger receipt keeps request pending and does not mark approved.
7. Approval succeeds ONLY when Bot Core returns a real ledger event ID.
8. Customer create/patch have zero wallet mutation side effects.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_db
from copyfast_db import create_web_manual_topup_request, get_web_manual_topup_for_admin


@pytest.fixture(scope="module")
def test_env():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "failclosed_test.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "failclosed-test-secret-99999"
    os.environ["WEBAPP_ADMIN_ERP_ENABLED"] = "true"
    os.environ["WEBAPP_ADMIN_WRITES_ENABLED"] = "true"
    copyfast_db.ensure_copyfast_schema()
    yield db_path


@pytest.fixture(scope="module")
def admin_client(test_env):
    client = TestClient(app_module.app)
    admin_email = "admin_safety_ops@toanaas.vn"
    admin_pwd = "AdminPassword2026!"
    reg = client.post("/api/v1/auth/register", json={"email": admin_email, "password": admin_pwd, "display_name": "Safety Ops Admin"})
    assert reg.status_code == 200
    with sqlite3.connect(test_env) as conn:
        conn.execute("UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457028' WHERE email=?", (admin_email,))
        conn.commit()
    login = client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_pwd})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf
    return client


def _create_sample_topup(test_env: str, suffix: str, amount: int = 100_000, canonical_user_id: str | None = None) -> tuple[str, str]:
    user_email = f"user_{suffix}@toanaas.vn"
    account_id = f"00000000-0000-4000-8000-{hashlib.md5(suffix.encode()).hexdigest()[:12]}"
    actual_canonical_id = str(canonical_user_id or f"canon_{hashlib.md5(suffix.encode()).hexdigest()[:10]}")
    with sqlite3.connect(test_env) as conn:
        conn.execute(
            "INSERT INTO web_accounts (id, email, display_name, password_hash, role_cache, canonical_user_id, created_at, updated_at) "
            "VALUES (?, ?, 'Payer', 'mock_hash', 'user', ?, datetime('now'), datetime('now'))",
            (account_id, user_email, actual_canonical_id),
        )
        conn.commit()

    idemp_hash = hashlib.sha256(f"test-idemp-{suffix}".encode()).hexdigest()
    fp_hash = hashlib.sha256(f"test-fp-{suffix}".encode()).hexdigest()

    created = create_web_manual_topup_request(
        account_id=account_id,
        amount_vnd=amount,
        method="bank_acb_vietqr",
        reference=f"REF-{suffix}",
        idempotency_key_hash=idemp_hash,
        request_fingerprint=fp_hash,
    )
    return created["request_id"], account_id


def test_manual_topup_confirm_bridge_unconfigured_returns_503(admin_client, test_env, monkeypatch):
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: False)
    req_id, _ = _create_sample_topup(test_env, "unconfigured_503")

    draft_res = admin_client.post(f"/api/v1/admin/payments/manual/{req_id}/approve/draft")
    assert draft_res.status_code == 200
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-unconf-1"},
    )
    assert confirm_res.status_code == 503
    body = confirm_res.json()
    assert body["ok"] is False
    assert body["status"] == "guarded"
    assert body["error_code"] == "WALLET_CREDIT_BRIDGE_UNAVAILABLE"


def test_manual_topup_bridge_unconfigured_keeps_request_pending(admin_client, test_env, monkeypatch):
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: False)
    req_id, _ = _create_sample_topup(test_env, "keeps_pending")

    draft_res = admin_client.post(f"/api/v1/admin/payments/manual/{req_id}/approve/draft")
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-unconf-2"},
    )

    detail_res = admin_client.get(f"/api/v1/admin/payments/manual/{req_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()["data"]
    assert data["status"] == "pending_admin_review"
    assert data.get("decision_at") in (None, "")


def test_manual_topup_bridge_unconfigured_does_not_create_local_credit_id(admin_client, test_env, monkeypatch):
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: False)
    req_id, _ = _create_sample_topup(test_env, "no_local_credit")

    draft_res = admin_client.post(f"/api/v1/admin/payments/manual/{req_id}/approve/draft")
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-unconf-3"},
    )

    with sqlite3.connect(test_env) as conn:
        row = conn.execute("SELECT ledger_event_id, approved_xu, status FROM web_manual_topup_requests WHERE id=?", (int(req_id.split("-")[1]),)).fetchone()
        assert row[0] is None or row[0] == ""
        assert row[1] is None or row[1] == 0
        assert row[2] == "pending_admin_review"


def test_manual_topup_bridge_unconfigured_does_not_claim_wallet_success(admin_client, test_env, monkeypatch):
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: False)
    req_id, _ = _create_sample_topup(test_env, "no_claim_success")

    draft_res = admin_client.post(f"/api/v1/admin/payments/manual/{req_id}/approve/draft")
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-unconf-4"},
    )
    msg = confirm_res.json()["message"].lower()
    assert "thành công" not in msg
    assert "đã cộng" not in msg
    assert "chưa khả dụng" in msg or "chưa cộng xu" in msg


def test_manual_topup_bridge_timeout_does_not_mark_approved(admin_client, test_env, monkeypatch):
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)

    async def mock_timeout(method, path, **kwargs):
        return {
            "ok": False,
            "status": "guarded",
            "message": "Kết nối máy chủ Bot Core bị quá thời gian.",
            "error_code": "CORE_BRIDGE_TIMEOUT",
        }

    monkeypatch.setattr(copyfast_api, "bridge_request", mock_timeout)
    req_id, _ = _create_sample_topup(test_env, "bridge_timeout")

    draft_res = admin_client.post(f"/api/v1/admin/payments/manual/{req_id}/approve/draft")
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-timeout-1"},
    )
    assert confirm_res.status_code == 504
    assert confirm_res.json()["ok"] is False
    assert confirm_res.json()["error_code"] == "CORE_BRIDGE_TIMEOUT"

    detail = admin_client.get(f"/api/v1/admin/payments/manual/{req_id}").json()["data"]
    assert detail["status"] == "pending_admin_review"


def test_manual_topup_bridge_5xx_does_not_mark_approved(admin_client, test_env, monkeypatch):
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)

    async def mock_5xx(method, path, **kwargs):
        return {
            "ok": False,
            "status": "guarded",
            "message": "Bot Core Ledger gặp sự cố nội bộ.",
            "error_code": "CORE_BRIDGE_UNAVAILABLE",
        }

    monkeypatch.setattr(copyfast_api, "bridge_request", mock_5xx)
    req_id, _ = _create_sample_topup(test_env, "bridge_5xx")

    draft_res = admin_client.post(f"/api/v1/admin/payments/manual/{req_id}/approve/draft")
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-5xx-00001"},
    )
    assert confirm_res.status_code == 503
    assert confirm_res.json()["ok"] is False

    detail = admin_client.get(f"/api/v1/admin/payments/manual/{req_id}").json()["data"]
    assert detail["status"] == "pending_admin_review"


def test_manual_topup_invalid_bridge_receipt_does_not_mark_approved(admin_client, test_env, monkeypatch):
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)

    async def mock_invalid_receipt(method, path, **kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "ok",
            "data": {},
        }

    monkeypatch.setattr(copyfast_api, "bridge_request", mock_invalid_receipt)
    req_id, _ = _create_sample_topup(test_env, "invalid_receipt")

    draft_res = admin_client.post(f"/api/v1/admin/payments/manual/{req_id}/approve/draft")
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-invalid-0001"},
    )
    assert confirm_res.status_code == 502
    assert confirm_res.json()["ok"] is False
    assert confirm_res.json()["error_code"] == "WALLET_CREDIT_RECEIPT_MISSING"

    detail = admin_client.get(f"/api/v1/admin/payments/manual/{req_id}").json()["data"]
    assert detail["status"] == "pending_admin_review"


def test_manual_topup_success_path_requires_real_bridge_receipt(admin_client, test_env, monkeypatch):
    monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)

    async def mock_success(method, path, **kwargs):
        return {
            "ok": True,
            "status": "completed",
            "message": "Đã cộng Xu",
            "data": {"tx_id": "bot-ledger-real-tx-882200"},
        }

    monkeypatch.setattr(copyfast_api, "bridge_request", mock_success)
    req_id, _ = _create_sample_topup(test_env, "success_real_receipt", amount=80_000)

    draft_res = admin_client.post(f"/api/v1/admin/payments/manual/{req_id}/approve/draft")
    assert draft_res.status_code == 200
    receipt = draft_res.json()["data"]["confirmation_receipt"]

    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{req_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-success-1"},
    )
    assert confirm_res.status_code == 200
    body = confirm_res.json()
    assert body["ok"] is True
    assert body["status"] == "approved"
    assert body["data"]["status"] == "approved"
    assert body["data"]["approved_xu"] == 800
    assert body["data"]["ledger_event_id"] == "bot-ledger-real-tx-882200"

    detail = admin_client.get(f"/api/v1/admin/payments/manual/{req_id}").json()["data"]
    assert detail["status"] == "approved"
    assert detail["ledger_event_id"] == "bot-ledger-real-tx-882200"


def test_customer_create_still_has_no_wallet_side_effect(admin_client, test_env):
    email = "cust_side_effect_check@toanaas.vn"
    res = admin_client.post(
        "/api/v1/admin/customers",
        json={
            "email": email,
            "display_name": "No Wallet Mutation Cust",
            "role": "user",
            "password": "Password123!",
        },
    )
    assert res.status_code == 201
    assert res.json()["ok"] is True
    with sqlite3.connect(test_env) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "users" not in tables
        assert "wallets" not in tables
        user_id = res.json()["data"]["id"]
        topup_count = conn.execute("SELECT count(*) FROM web_manual_topup_requests WHERE account_id=?", (user_id,)).fetchone()[0]
        assert topup_count == 0


def test_customer_patch_still_has_no_wallet_side_effect(admin_client, test_env):
    email = "cust_patch_check@toanaas.vn"
    create_res = admin_client.post(
        "/api/v1/admin/customers",
        json={"email": email, "display_name": "Before Patch", "role": "user", "password": "Password123!"},
    )
    cust_id = create_res.json()["data"]["id"]

    patch_res = admin_client.patch(
        f"/api/v1/admin/customers/{cust_id}",
        json={"display_name": "After Patch", "is_active": True},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["ok"] is True
    with sqlite3.connect(test_env) as conn:
        topup_count = conn.execute("SELECT count(*) FROM web_manual_topup_requests WHERE account_id=?", (cust_id,)).fetchone()[0]
        assert topup_count == 0
