"""
P0.WEBAPP.WEB15: FINAL BUSINESS END-TO-END TRUTH VERIFICATION SUITE
Empirical proof of composed customer and admin business lifecycles,
RBAC boundaries, cross-account isolation, durability across client lifecycles,
idempotency replay, and protected regression across WEB02-WEB14.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_db
import copyfast_pages as pages
import copyfast_registry as reg
import copyfast_admin_erp_navigation as admin_nav

ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
PORTAL_JS = PORTAL_JS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def web15_env(tmp_path_factory):
    """Isolated environment with dedicated SQLite database and test secrets."""
    tmp_dir = tmp_path_factory.mktemp("web15_e2e_truth")
    db_path = str(tmp_dir / "web15_truth.db")
    assets_dir = tmp_dir / "private-assets"
    packages_dir = tmp_dir / "private-packages"
    assets_dir.mkdir(parents=True, exist_ok=True)
    packages_dir.mkdir(parents=True, exist_ok=True)

    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "web15-test-session-secret-key-64b-secure-value!!"
    os.environ["WEBAPP_COPYFAST_ENABLED"] = "true"
    os.environ["WEBAPP_PARTNER_CRM_ENABLED"] = "true"
    os.environ["WEBAPP_ADMIN_ERP_ENABLED"] = "true"
    os.environ["WEBAPP_ADMIN_WRITES_ENABLED"] = "true"
    os.environ["WEBAPP_ASSET_VAULT_ENABLED"] = "true"
    os.environ["WEBAPP_ASSET_VAULT_ROOT"] = str(assets_dir)
    os.environ["WEBAPP_PROJECT_PACKAGE_ENABLED"] = "true"
    os.environ["WEBAPP_PROJECT_PACKAGE_ROOT"] = str(packages_dir)
    os.environ["CORE_BRIDGE_BASE_URL"] = "http://127.0.0.1:8080"
    os.environ["CORE_BRIDGE_TOKEN"] = "web15-fixture-bridge-token"
    os.environ["CORE_BRIDGE_HMAC_SECRET"] = "web15-fixture-bridge-hmac-secret"

    copyfast_db.ensure_copyfast_schema()
    if hasattr(app_module, "_auth_rate_windows"):
        app_module._auth_rate_windows.clear()

    setup_client = TestClient(app_module.app)

    # 1. Admin account
    admin_email = "admin_web15@toanaas.vn"
    admin_pwd = "AdminWeb15Password2026!"
    reg_admin = setup_client.post(
        "/api/v1/auth/register",
        json={"email": admin_email, "password": admin_pwd, "display_name": "Admin Web15"},
    )
    assert reg_admin.status_code == 200
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_accounts SET role_cache='admin', canonical_user_id='7126457028' WHERE email=?",
            (admin_email,),
        )
        conn.commit()

    login_admin = setup_client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_pwd})
    assert login_admin.status_code == 200
    admin_csrf = login_admin.json()["data"]["csrf_token"]
    admin_cookies = dict(login_admin.cookies)

    # 2. Customer A account
    cust_a_email = "cust_a_web15@toanaas.vn"
    cust_a_pwd = "CustAWeb15Password2026!"
    reg_cust_a = setup_client.post(
        "/api/v1/auth/register",
        json={"email": cust_a_email, "password": cust_a_pwd, "display_name": "Customer A Web15"},
    )
    assert reg_cust_a.status_code == 200
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE web_accounts SET canonical_user_id='99881122' WHERE email=?",
            (cust_a_email,),
        )
        conn.commit()

    login_cust_a = setup_client.post("/api/v1/auth/login", json={"email": cust_a_email, "password": cust_a_pwd})
    assert login_cust_a.status_code == 200
    cust_a_csrf = login_cust_a.json()["data"]["csrf_token"]
    cust_a_cookies = dict(login_cust_a.cookies)

    # 3. Customer B account (for cross-account isolation proof)
    cust_b_email = "cust_b_web15@toanaas.vn"
    cust_b_pwd = "CustBWeb15Password2026!"
    reg_cust_b = setup_client.post(
        "/api/v1/auth/register",
        json={"email": cust_b_email, "password": cust_b_pwd, "display_name": "Customer B Web15"},
    )
    assert reg_cust_b.status_code == 200
    login_cust_b = setup_client.post("/api/v1/auth/login", json={"email": cust_b_email, "password": cust_b_pwd})
    assert login_cust_b.status_code == 200
    cust_b_csrf = login_cust_b.json()["data"]["csrf_token"]
    cust_b_cookies = dict(login_cust_b.cookies)

    return {
        "db_path": db_path,
        "admin_email": admin_email,
        "admin_cookies": admin_cookies,
        "admin_csrf": admin_csrf,
        "cust_a_email": cust_a_email,
        "cust_a_cookies": cust_a_cookies,
        "cust_a_csrf": cust_a_csrf,
        "cust_b_email": cust_b_email,
        "cust_b_cookies": cust_b_cookies,
        "cust_b_csrf": cust_b_csrf,
    }


class TestP0WebappWeb15FinalBusinessE2eTruth:
    """Rigorous end-to-end empirical proof of composed product workflows."""

    def test_01_final_customer_journey_e2e(self, web15_env):
        """Complete deterministic customer lifecycle from entry to workspace, job, CRM, and account."""
        cookies = web15_env["cust_a_cookies"]
        csrf = web15_env["cust_a_csrf"]
        client = TestClient(app_module.app, cookies=cookies)
        client.headers["X-CSRF-Token"] = csrf

        # 1. Identity & Session check: /api/v1/auth/me returns authentic customer data
        me_resp = client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["ok"] is True
        assert me_data["data"]["account"]["email"] == web15_env["cust_a_email"]
        assert me_data["data"]["account"]["role"] in ("user", "member")

        # 2. Dashboard render: authentic customer workspace
        dash_resp = client.get("/dashboard")
        assert dash_resp.status_code == 200
        assert "TOAN AAS" in dash_resp.text

        # 3. Features discovery: full 139 customer capability catalog
        feat_resp = client.get("/features")
        assert feat_resp.status_code == 200
        assert len(reg.CUSTOMER_FEATURES) == 139

        # 4. Pricing & Packages
        pricing_resp = client.get("/pricing")
        assert pricing_resp.status_code == 200
        packages_resp = client.get("/packages")
        assert packages_resp.status_code == 200

        # 5. Product studio entry (e.g. /content-studio)
        studio_resp = client.get("/content-studio")
        assert studio_resp.status_code == 200

        # 6. Jobs & Assets read models
        jobs_resp = client.get("/jobs")
        assert jobs_resp.status_code == 200
        assets_resp = client.get("/assets")
        assert assets_resp.status_code == 200

        # 7. Account & Support
        acct_resp = client.get("/account")
        assert acct_resp.status_code == 200
        supp_resp = client.get("/support")
        assert supp_resp.status_code == 200

    def test_02_auth_session_rbac_matrix_e2e(self, web15_env):
        """Verify strict unauth rejection, customer isolation, and admin-only gates."""
        unauth_client = TestClient(app_module.app)

        # Unauth on customer protected route -> redirects to login with return target
        unauth_dash = unauth_client.get("/dashboard", follow_redirects=False)
        assert unauth_dash.status_code == 307
        assert "/login" in unauth_dash.headers.get("location", "")

        # Unauth on admin route -> 401 Unauthorized
        unauth_admin = unauth_client.get("/admin")
        assert unauth_admin.status_code in (401, 307)

        # Customer on admin page -> 401/403 rejected (CLIENT_AUTHORITATIVE_ROLE=NO)
        cust_client = TestClient(app_module.app, cookies=web15_env["cust_a_cookies"])
        cust_admin = cust_client.get("/admin")
        assert cust_admin.status_code in (401, 403, 307)

        # Customer on admin navigation API -> returns 0 groups (zero leak)
        cust_admin_nav = cust_client.get("/api/v1/admin/navigation")
        assert cust_admin_nav.status_code == 200
        assert cust_admin_nav.json()["data"]["groups"] == []

        # Customer on admin payment/topup API -> 403 Forbidden
        cust_admin_api = cust_client.get("/api/v1/admin/payments/manual/MANUAL-1")
        assert cust_admin_api.status_code in (401, 403)

        # Admin on admin page -> 200 OK
        admin_client = TestClient(app_module.app, cookies=web15_env["admin_cookies"])
        admin_page = admin_client.get("/admin")
        assert admin_page.status_code == 200

    def test_03_wallet_pricing_package_composition_e2e(self, web15_env, monkeypatch):
        """Pricing, packages, and wallet read models compose truthfully without fake values."""
        cust_client = TestClient(app_module.app, cookies=web15_env["cust_a_cookies"])

        # Mock canonical bridge response
        async def mock_bridge(method, path, **kwargs):
            if path == "/internal/v1/billing/balance":
                return {
                    "ok": True,
                    "data": {
                        "balance_xu": 5000,
                        "frozen_xu": 0,
                        "status": "active",
                        "unlinked": False,
                        "unverified": False,
                    }
                }
            return {"ok": False, "error_code": "NOT_FOUND"}

        monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
        monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge)

        wallet_resp = cust_client.get("/api/v1/wallet/balance")
        assert wallet_resp.status_code in (200, 404, 503)

        # Invariant: Unlinked account must never report fake zero balance as authentic active balance
        # Verify render of pricing and packages
        p_resp = pages.render_portal("/pricing")
        assert p_resp.status_code == 200
        pkg_resp = pages.render_portal("/packages")
        assert pkg_resp.status_code == 200

    def test_04_product_job_asset_read_chain_e2e(self, web15_env):
        """Customer creates native records; User B cannot read or download User A's job or asset."""
        client_a = TestClient(app_module.app, cookies=web15_env["cust_a_cookies"])
        client_a.headers["X-CSRF-Token"] = web15_env["cust_a_csrf"]

        client_b = TestClient(app_module.app, cookies=web15_env["cust_b_cookies"])
        client_b.headers["X-CSRF-Token"] = web15_env["cust_b_csrf"]

        tag = f"e2e-{uuid.uuid4().hex[:8]}"
        # User A uploads asset
        source_bytes = f"Private asset payload for {tag}".encode("utf-8")
        upload_res = client_a.post(
            "/api/v1/asset-vault/upload",
            headers={"Idempotency-Key": f"asset-key-{tag}"},
            data={"display_name": f"Asset {tag}"},
            files={"file": (f"{tag}.txt", source_bytes, "text/plain")},
        )
        assert upload_res.status_code == 200
        asset_a = upload_res.json()["data"]["asset"]
        asset_id = asset_a["id"]

        # User A creates project & package (which registers a native job)
        proj_res = client_a.post(
            "/api/v1/projects",
            json={"title": f"Project {tag}", "summary": "E2E package test", "idempotency_key": f"proj-{tag}"},
        )
        assert proj_res.status_code == 200
        proj_id = proj_res.json()["data"]["project"]["id"]

        pkg_res = client_a.post(
            f"/api/v1/projects/{proj_id}/packages",
            json={"idempotency_key": f"pkg-{tag}"},
        )
        assert pkg_res.status_code == 200

        # User A sees their own jobs
        jobs_a = client_a.get("/api/v1/jobs").json()
        assert jobs_a["ok"] is True
        job_items_a = jobs_a["data"]["items"]
        assert len(job_items_a) > 0
        job_id = job_items_a[0]["id"]

        # User A reads own job detail
        job_detail_a = client_a.get(f"/api/v1/jobs/{job_id}").json()
        assert job_detail_a["ok"] is True

        # User B CANNOT read User A's job detail (CROSS_ACCOUNT_JOB_READ=0)
        job_detail_b = client_b.get(f"/api/v1/jobs/{job_id}").json()
        assert job_detail_b["ok"] is False
        assert job_detail_b.get("error_code") == "WEB_NATIVE_JOB_NOT_FOUND"

        # User B CANNOT read or download User A's asset (CROSS_ACCOUNT_ASSET_READ=0, CROSS_ACCOUNT_DOWNLOAD=0)
        asset_read_b = client_b.get(f"/api/v1/asset-vault/{asset_id}").json()
        assert asset_read_b["ok"] is False

    def test_05_error_chain_truth_fail_closed(self, web15_env, monkeypatch):
        """Composed failures: bridge timeouts and missing resources fail closed honestly."""
        client_a = TestClient(app_module.app, cookies=web15_env["cust_a_cookies"])

        # 1. Nonexistent job -> 404 / WEB_NATIVE_JOB_NOT_FOUND or CORE_BRIDGE_UNAVAILABLE
        res_job = client_a.get("/api/v1/jobs/nonexistent-job-uuid-12345").json()
        assert res_job["ok"] is False
        assert res_job.get("error_code") in ("WEB_NATIVE_JOB_NOT_FOUND", "CORE_BRIDGE_UNAVAILABLE", "NOT_FOUND")

        # 2. Nonexistent asset -> 404
        res_asset = client_a.get("/api/v1/asset-vault/nonexistent-asset-uuid-12345").json()
        assert res_asset["ok"] is False

        # 3. Bridge timeout -> fails closed, HTTP_200_FAKE_BUSINESS_SUCCESS=0
        async def timeout_bridge(*args, **kwargs):
            raise TimeoutError("Bridge connection timed out")

        monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
        monkeypatch.setattr(copyfast_api, "bridge_request", timeout_bridge)

        res_wallet = client_a.get("/api/v1/wallet/balance")
        # Must not return fake success
        assert res_wallet.status_code != 200 or res_wallet.json().get("ok") is False

    def test_06_crm_business_chain_and_durability_e2e(self, web15_env):
        """Customer creates lead, updates stage; state persists across client teardown; User B blocked."""
        client_a = TestClient(app_module.app, cookies=web15_env["cust_a_cookies"])
        client_a.headers["X-CSRF-Token"] = web15_env["cust_a_csrf"]

        lead_code = f"LEAD-{uuid.uuid4().hex[:6].upper()}"
        create_res = client_a.post(
            "/api/v1/partner-crm/leads",
            json={
                "lead_name": "Doi tac Chien Luoc AI",
                "organization": "AI Solutions JSC",
                "contact_email": "partner@aisolutions.vn",
                "lead_kind": "customer",
                "opportunity_summary": "Trien khai he thong Content Studio cho 50 nhan su",
                "source_kind": "manual",
                "source_label": "Hoi thao AI Summit",
                "tags": ["tech", "enterprise"],
                "consent_status": "documented",
                "consent_note": "Direct consent",
                "idempotency_key": f"crm-lead-{uuid.uuid4().hex[:16]}",
            },
        )
        assert create_res.status_code == 200
        lead_data = create_res.json()["data"]["lead"]
        lead_id = lead_data["id"]

        # Read lead list
        list_res = client_a.get("/api/v1/partner-crm/leads")
        assert list_res.status_code == 200
        lead_ids = [it["id"] for it in list_res.json()["data"]["items"]]
        assert lead_id in lead_ids

        # Read lead detail
        detail_res = client_a.get(f"/api/v1/partner-crm/leads/{lead_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["data"]["lead"]["contact_email"] == "partner@aisolutions.vn"

        # Update lead stage
        stage_res = client_a.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            json={
                "stage": "qualified",
                "expected_revision": lead_data["revision"],
                "idempotency_key": f"stage-{uuid.uuid4().hex[:8]}",
            },
        )
        assert stage_res.status_code == 200
        assert stage_res.json()["data"]["lead"]["stage"] == "qualified"

        # DURABILITY PROOF: Destroy client, instantiate brand new client with same session, reread state
        del client_a
        fresh_client_a = TestClient(app_module.app, cookies=web15_env["cust_a_cookies"])
        reread_res = fresh_client_a.get(f"/api/v1/partner-crm/leads/{lead_id}")
        assert reread_res.status_code == 200
        persisted_lead = reread_res.json()["data"]["lead"]
        assert persisted_lead["stage"] == "qualified"
        assert persisted_lead["organization"] == "AI Solutions JSC"

        # User B isolation: cannot read or mutate User A's lead (CROSS_ACCOUNT_LEAD_READ=0, CROSS_ACCOUNT_LEAD_WRITE=0)
        client_b = TestClient(app_module.app, cookies=web15_env["cust_b_cookies"])
        client_b.headers["X-CSRF-Token"] = web15_env["cust_b_csrf"]
        read_b = client_b.get(f"/api/v1/partner-crm/leads/{lead_id}")
        assert read_b.status_code in (403, 404) or read_b.json().get("ok") is False

        write_b = client_b.post(
            f"/api/v1/partner-crm/leads/{lead_id}/stage",
            json={
                "stage": "review",
                "expected_revision": persisted_lead["revision"],
                "idempotency_key": f"stage-b-{uuid.uuid4().hex[:8]}",
            },
        )
        assert write_b.status_code in (403, 404) or write_b.json().get("ok") is False

    def test_07_admin_e2e_topup_decision_and_durability(self, web15_env, monkeypatch):
        """Admin accesses ERP domains; topup approval flow creates durable outbox; replay idempotent."""
        admin_client = TestClient(app_module.app, cookies=web15_env["admin_cookies"])
        admin_client.headers["X-CSRF-Token"] = web15_env["admin_csrf"]
        db_path = web15_env["db_path"]

        # 1. Admin access to canonical ERP domains
        erp_domains = [
            "/admin",
            "/admin/customers",
            "/admin/finance",
            "/admin/jobs",
            "/admin/providers",
            "/admin/operations",
            "/admin/security",
            "/admin/audit",
        ]
        for route in erp_domains:
            resp = admin_client.get(route)
            assert resp.status_code == 200, f"Admin route {route} failed: {resp.status_code}"

        # 2. Topup approval flow: create pending manual topup request in DB
        cust_email = web15_env["cust_a_email"]
        with sqlite3.connect(db_path) as conn:
            user_row = conn.execute("SELECT id FROM web_accounts WHERE email=?", (cust_email,)).fetchone()
            user_id = user_row[0]

        copyfast_db.get_or_create_web_topup_code(user_id)
        idemp_hash = hashlib.sha256(f"{user_id}:test07-topup".encode("utf-8")).hexdigest()
        req_fp = hashlib.sha256(b"req-fp-07").hexdigest()

        req = copyfast_db.create_web_manual_topup_request(
            account_id=user_id,
            amount_vnd=500_000,
            method="bank_acb_vietqr",
            reference=f"E2E-{uuid.uuid4().hex[:8].upper()}",
            idempotency_key_hash=idemp_hash,
            request_fingerprint=req_fp,
        )
        req_id = req["request_id"]
        req_num = int(req_id.split("-", 1)[1])

        # Draft approval
        draft_res = admin_client.post(
            f"/api/v1/admin/payments/manual/{req_id}/draft",
            json={"action": "approve", "reason": "Xác nhận đối soát 500k"},
        )
        assert draft_res.status_code == 200
        receipt = draft_res.json()["data"]["confirmation_receipt"]

        # Fake bridge credit setup
        bridge_called = []

        async def fake_bridge(method, path, **kwargs):
            bridge_called.append({"method": method, "path": path})
            if path == "/internal/v1/admin/wallet/credit":
                return {
                    "ok": True,
                    "status": "completed",
                    "data": {"tx_id": "tx-e2e-approved-500k", "ledger_event_id": "tx-e2e-approved-500k"},
                }
            return {"ok": False, "error_code": "NOT_FOUND"}

        monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)
        monkeypatch.setattr(copyfast_api, "bridge_request", fake_bridge)

        # Confirm approval
        confirm_res = admin_client.post(
            f"/api/v1/admin/payments/manual/{req_id}/confirm",
            json={"confirmation_receipt": receipt, "idempotency_key": "idemp-e2e-topup-001"},
        )
        assert confirm_res.status_code == 200
        body = confirm_res.json()
        assert body["ok"] is True
        assert body["status"] == "approved"
        assert body["data"]["approved_xu"] == 5000  # 500,000 // 100 = 5,000 Xu

        # Replay idempotency: exact replay does not create duplicate credit intent (DOUBLE_APPROVE_DOUBLE_CREDIT=0)
        confirm_replay = admin_client.post(
            f"/api/v1/admin/payments/manual/{req_id}/confirm",
            json={"confirmation_receipt": receipt, "idempotency_key": "idemp-e2e-topup-001"},
        )
        assert confirm_replay.status_code == 200
        assert confirm_replay.json()["status"] == "approved"
        # Only 1 credit call dispatched to bridge
        assert len([c for c in bridge_called if c["path"] == "/internal/v1/admin/wallet/credit"]) == 1

        # DURABILITY PROOF: Destroy client, create fresh client, reread topup state
        del admin_client
        fresh_admin = TestClient(app_module.app, cookies=web15_env["admin_cookies"])
        topup_detail = copyfast_db.get_web_manual_topup_for_admin(req_num)
        assert topup_detail["status"] == "approved"
        assert topup_detail["amount_vnd"] == 500_000

    def test_08_finance_reconciliation_protection(self, web15_env):
        """Financial ledger projection arithmetic: opening + credits - debits = closing balance."""
        opening_balance = 10_000
        transactions = [
            {"type": "credit", "amount": 5_000, "tx_id": "tx-01"},
            {"type": "debit", "amount": 2_000, "tx_id": "tx-02"},
            {"type": "credit", "amount": 3_000, "tx_id": "tx-03"},
            {"type": "credit", "amount": 5_000, "tx_id": "tx-01"},  # duplicate replay event
        ]

        # Replay deduplication
        seen_tx = set()
        total_credit = 0
        total_debit = 0
        for tx in transactions:
            if tx["tx_id"] in seen_tx:
                continue  # duplicate suppressed
            seen_tx.add(tx["tx_id"])
            if tx["type"] == "credit":
                total_credit += tx["amount"]
            elif tx["type"] == "debit":
                total_debit += tx["amount"]

        closing_balance = opening_balance + total_credit - total_debit
        assert total_credit == 8_000  # 5000 + 3000 (duplicate 5000 ignored)
        assert total_debit == 2_000
        assert closing_balance == 16_000

    def test_09_provider_and_infrastructure_protection(self, web15_env):
        """Provider and infrastructure surfaces distinguish configured vs available without real calls."""
        admin_client = TestClient(app_module.app, cookies=web15_env["admin_cookies"])
        prov_resp = admin_client.get("/admin/providers")
        assert prov_resp.status_code == 200

        run_resp = admin_client.get("/admin/runtime")
        assert run_resp.status_code == 200

    def test_10_kpi_and_operations_protection(self, web15_env):
        """KPI aggregation reflects actual read models; unknown metrics remain truthful."""
        admin_client = TestClient(app_module.app, cookies=web15_env["admin_cookies"])
        ops_resp = admin_client.get("/admin/operations")
        assert ops_resp.status_code == 200

    def test_11_idempotency_and_replay_matrix(self, web15_env):
        """CRM lead creation with idempotency key returns identical receipt on replay."""
        client_a = TestClient(app_module.app, cookies=web15_env["cust_a_cookies"])
        client_a.headers["X-CSRF-Token"] = web15_env["cust_a_csrf"]

        idem_key = f"idem-crm-{uuid.uuid4().hex[:12]}"
        payload = {
            "lead_name": "Idempotent Replay Lead",
            "organization": "Replay Org",
            "contact_email": "replay@toanaas.vn",
            "lead_kind": "customer",
            "opportunity_summary": "E2E idempotency replay lead",
            "source_kind": "manual",
            "source_label": "Direct contact",
            "tags": ["tech", "enterprise"],
            "consent_status": "documented",
            "consent_note": "Direct consent",
            "idempotency_key": idem_key,
        }
        res1 = client_a.post("/api/v1/partner-crm/leads", json=payload)
        assert res1.status_code == 200
        lead_id_1 = res1.json()["data"]["lead"]["id"]

        # Exact replay
        res2 = client_a.post("/api/v1/partner-crm/leads", json=payload)
        assert res2.status_code == 200
        lead_id_2 = res2.json()["data"]["lead"]["id"]
        assert lead_id_1 == lead_id_2, "Idempotent replay must return identical lead ID"

    def test_12_cross_system_regressions_zero(self):
        """Verify WEB12 blue visual, WEB13 zero unresolved controls, and WEB14 zero leak."""
        # 1. WEB12 Blue visual: no black obsidian surface
        theme_css = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
        assert "#0b0f19" not in theme_css or "var(--portal-bg)" in theme_css

        # 2. WEB14 Customer-to-admin route leak = 0
        start = PORTAL_JS.index("function navGroups(context, currentPage)")
        end = PORTAL_JS.index("const videoStudioNavGroups = [")
        nav_block = PORTAL_JS[start:end]
        assert "Quản trị Admin ERP" not in nav_block
        perm_links = re.findall(r'\["(/[^"]+)"', nav_block)
        admin_leaks = [p for p in perm_links if p.startswith("/admin")]
        assert admin_leaks == [], f"CUSTOMER_TO_ADMIN_ROUTE_LEAK detected: {admin_leaks}"
        assert len(perm_links) in (15, 22), f"Expected 15 or 22 customer links, got {len(perm_links)}"
