"""Test suite for Admin Manual Topup Approve, Customer Create/Update, and Pricing/Packages."""

from __future__ import annotations

import os
import tempfile
import sqlite3
import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_db
from copyfast_db import (
    create_web_manual_topup_request,
    get_web_manual_topup_for_admin,
    list_web_manual_topups_for_admin,
)


@pytest.fixture(scope="module")
def env_setup():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "admin_approve_pricing_test.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "admin-approve-test-secret-12345"
    os.environ["WEBAPP_ADMIN_ERP_ENABLED"] = "true"
    os.environ["WEBAPP_ADMIN_WRITES_ENABLED"] = "true"
    copyfast_db.ensure_copyfast_schema()
    yield db_path


@pytest.fixture(scope="module")
def admin_client(env_setup):
    client = TestClient(app_module.app)
    email = "admin_super_ops@toanaas.vn"
    password = "SuperSecretPassword2026!"
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Super Ops Admin"})
    assert reg.status_code == 200
    with sqlite3.connect(env_setup) as conn:
        conn.execute("UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457028' WHERE email=?", (email,))
        conn.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    csrf = login.json()["data"]["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf
    return client


import hashlib


def test_pricing_and_packages_endpoint(admin_client):
    res = admin_client.get("/api/v1/admin/modules/pricing")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["status"] == "read_only"
    payload = data["data"]
    assert "items" in payload
    assert "topup_packages" in payload
    assert "service_catalog" in payload
    assert payload["count"] > 0
    assert payload["write_locked"] is True

    # Check /api/v1/admin/pricing and /api/v1/admin/packages aliases
    res_pricing = admin_client.get("/api/v1/admin/pricing")
    assert res_pricing.status_code == 200
    assert res_pricing.json()["ok"] is True

    res_packages = admin_client.get("/api/v1/admin/packages")
    assert res_packages.status_code == 200
    assert res_packages.json()["ok"] is True


def test_customer_create_and_update_api(admin_client, env_setup):
    # Create customer
    new_email = "newbie_customer_2026@toanaas.vn"
    create_res = admin_client.post(
        "/api/v1/admin/customers",
        json={
            "email": new_email,
            "display_name": "Newbie Customer",
            "role": "user",
            "password": "Password123!",
            "canonical_user_id": "888777666",
        },
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["ok"] is True
    customer = created_data["data"]
    cust_id = customer["id"]
    assert customer["email"] == new_email
    assert customer["display_name"] == "Newbie Customer"
    assert customer["status"] == "active"
    assert "topup_code" in customer
    assert customer["topup_code"].isdigit() and len(customer["topup_code"]) == 8

    # Duplicate email should fail (409)
    dup_res = admin_client.post(
        "/api/v1/admin/customers",
        json={"email": new_email, "display_name": "Duplicate"},
    )
    assert dup_res.status_code == 409

    # Update customer (PATCH)
    patch_res = admin_client.patch(
        f"/api/v1/admin/customers/{cust_id}",
        json={"display_name": "Updated Newbie Name", "is_active": False},
    )
    assert patch_res.status_code == 200
    updated_data = patch_res.json()
    assert updated_data["ok"] is True
    assert updated_data["data"]["display_name"] == "Updated Newbie Name"
    assert updated_data["data"]["status"] == "locked"


def test_manual_topup_approve_lifecycle(admin_client, env_setup):
    # 1. First register a user account who requests topup
    user_email = "payer_manual_01@toanaas.vn"
    user_pwd = "PayerPassword2026!"
    with sqlite3.connect(env_setup) as conn:
        conn.execute(
            "INSERT INTO web_accounts (id, email, display_name, password_hash, role_cache, canonical_user_id, created_at, updated_at) "
            "VALUES ('00000000-0000-4000-8000-000000000099', ?, 'Payer One', 'mock_hash', 'user', '11223344', datetime('now'), datetime('now'))",
            (user_email,),
        )
        conn.commit()

    idemp_hash = hashlib.sha256(b"test-idemp-hash-99").hexdigest()
    fp_hash = hashlib.sha256(b"test-fp-hash-99").hexdigest()

    created_topup = create_web_manual_topup_request(
        account_id="00000000-0000-4000-8000-000000000099",
        amount_vnd=50000,
        method="bank_acb_vietqr",
        reference="MBVCB.12345678",
        idempotency_key_hash=idemp_hash,
        request_fingerprint=fp_hash,
    )
    request_id = created_topup["request_id"]

    # Verify pending
    detail_res = admin_client.get(f"/api/v1/admin/payments/manual/{request_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["status"] == "pending_admin_review"

    # 2. Call approve draft
    draft_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{request_id}/approve/draft",
        json={"action": "approve", "reason": "Tiền đã vào tài khoản VCB"},
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert draft_data["ok"] is True
    assert draft_data["status"] == "awaiting_confirm"
    receipt = draft_data["data"]["confirmation_receipt"]
    assert receipt
    assert draft_data["data"]["action"] == "approve"
    assert draft_data["data"]["approved_xu"] == 500  # 50,000 / 100 = 500 Xu

    # 3. Call approve confirm
    confirm_res = admin_client.post(
        f"/api/v1/admin/payments/manual/{request_id}/approve/confirm",
        json={"confirmation_receipt": receipt, "idempotency_key": "idemp-approve-test-99"},
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["ok"] is True
    assert confirm_data["status"] == "approved"
    assert confirm_data["data"]["status"] == "approved"
    assert confirm_data["data"]["approved_xu"] == 500
    assert confirm_data["data"]["ledger_event_id"].startswith("local-credit-")

    # 4. Final detail shows approved
    final_detail = admin_client.get(f"/api/v1/admin/payments/manual/{request_id}")
    assert final_detail.status_code == 200
    assert final_detail.json()["data"]["status"] == "approved"

    # 5. Check audit log in DB
    with sqlite3.connect(env_setup) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM web_audit_events WHERE action='admin.manual_topup.approve' ORDER BY rowid DESC LIMIT 1")
        audit = cur.fetchone()
        assert audit is not None
        assert audit["target"] == request_id
        assert audit["outcome"] == "approved"
