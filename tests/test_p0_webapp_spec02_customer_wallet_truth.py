"""Empirical verification test suite for SPEC-02: CUSTOMER WALLET, BILLING AND TOPUP TRUTH.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.SPEC02.CUSTOMER.WALLET.BILLING.TOPUP.TRUTH

Checks and Invariants:
1. displayed wallet balance == canonical bot wallet balance via loopback bridge
2. 0 != NO_DATA != UNAVAILABLE != ERROR != STALE
3. Forbidden: fake zero, localStorage balance, optimistic credit, UI approved before ledger, fake receipt
4. Strict bridge-only architecture: zero direct Bot SQLite reads from Web App
5. Admin ERP feature gate enforced in _bridge
6. Unlinked account behavior: explicit unlinked status, never fake 0
7. Bridge unavailable behavior: fail-closed guarded error, never fake 0
8. Bot user not initialized behavior: explicit unverified status, never fake 0
9. Real wallet reconciliation discrepancy: fails closed on ledger mismatch
10. Topup packages and pricing catalog availability via bridge
11. Manual topup creation, idempotency, pending_admin_review state, no optimistic credit
12. PayOS order flow and status projection
13. Purged derived fake-zero metrics: UNKNOWN_BALANCE => UNKNOWN_TIER (never Newbie)
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

MODULES = (
    "app", "config", "db", "copyfast_db", "copyfast_auth", "copyfast_bridge",
    "copyfast_registry", "copyfast_api", "copyfast_mfa", "copyfast_pages",
)

CUSTOMER_EMAIL = "wallet-customer@toanaas.vn"
CUSTOMER_PASSWORD = "WalletCustomer123!@#"
TELEGRAM_USER_ID = "7126457028"


def _setup_app_client(tmp_path, monkeypatch) -> tuple[TestClient, Path, Path]:
    session_db_path = tmp_path / "spec02-session.db"
    system_db_path = tmp_path / "toandaas_system.db"

    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(session_db_path))
    monkeypatch.setenv("DB_FILE", str(system_db_path))
    monkeypatch.setenv("DB_PATH", str(system_db_path))
    monkeypatch.setenv("WEB_SESSION_SECRET", "spec02-test-session-secret-key-32b")
    monkeypatch.setenv("BOT_USERNAME", "toanaasbot")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("CORE_BRIDGE_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    monkeypatch.setenv("WEBAPP_LINK_CALLBACK_TOKEN", "bridge-test-token")
    monkeypatch.setenv("WEBAPP_LINK_CALLBACK_HMAC_SECRET", "bridge-test-hmac")
    monkeypatch.setenv("WEBAPP_TELEGRAM_BOT_LINK_ENABLED", "true")
    monkeypatch.setenv("MANUAL_BANK_CODE", "ACB")
    monkeypatch.setenv("MANUAL_BANK_NAME", "Asia Commercial Bank")
    monkeypatch.setenv("MANUAL_BANK_ACCOUNT", "123456789")
    monkeypatch.setenv("MANUAL_BANK_OWNER", "NGUYEN MANH TOAN")
    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)

    for name in MODULES:
        sys.modules.pop(name, None)

    # Initialize system DB schema
    db_mod = importlib.import_module("db")
    db_mod.init_db()

    # Ensure schema matches VPS (total_spent on users)
    with sqlite3.connect(str(system_db_path)) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "total_spent" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN total_spent INTEGER DEFAULT 0")
        conn.commit()

    application = importlib.import_module("app").app
    return TestClient(application), session_db_path, system_db_path


def _register_and_login(client: TestClient, email: str, password: str) -> dict:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "display_name": "Wallet User"})
    assert reg.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    return me.json()["data"]["account"]


def _link_telegram(session_db_path: Path, email: str, telegram_uid: str):
    conn = sqlite3.connect(str(session_db_path))
    conn.execute("UPDATE web_accounts SET canonical_user_id=? WHERE email=?", (telegram_uid, email))
    conn.commit()
    conn.close()


def test_wallet_endpoints_do_not_access_bot_sqlite_directly():
    """Blocker 2: Architecture is strictly Web -> loopback bridge -> Bot read model API.

    No direct SQLite connection (`from db import db_connect`) is allowed in wallet routes.
    """
    copyfast_api = importlib.import_module("copyfast_api")
    wallet_source = inspect.getsource(copyfast_api.wallet)
    wallet_history_source = inspect.getsource(copyfast_api.wallet_history)

    for src, fn_name in ((wallet_source, "wallet"), (wallet_history_source, "wallet_history")):
        assert "db_connect" not in src, f"{fn_name} must not import or call db_connect"
        assert "sqlite3" not in src, f"{fn_name} must not use sqlite3 directly"
        assert "credit_events" not in src, f"{fn_name} must not query credit_events table directly"
        assert "_bridge" in src, f"{fn_name} must delegate strictly to _bridge"


def test_admin_erp_feature_gate_in_bridge(tmp_path, monkeypatch):
    """Blocker 1: Admin ERP feature gate restored in _bridge()."""
    copyfast_api = importlib.import_module("copyfast_api")

    monkeypatch.setenv("WEBAPP_ADMIN_ERP_ENABLED", "false")
    fake_request = type("FakeReq", (), {"headers": {}})()
    account = {"canonical_user_id": TELEGRAM_USER_ID, "role": "admin"}

    import asyncio
    res = asyncio.run(
        copyfast_api._bridge(
            "GET",
            "/internal/v1/admin/overview",
            account=account,
            request=fake_request,
        )
    )
    assert res["ok"] is False
    assert res["status"] == "guarded"
    assert res["error_code"] == "WEBAPP_ADMIN_ERP_DISABLED"


def test_canonical_wallet_balance_and_ledger_via_bridge(tmp_path, monkeypatch):
    """Blocker 3: Canonical Bot wallet and history projected via bridge."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        _link_telegram(session_db, CUSTOMER_EMAIL, TELEGRAM_USER_ID)

        copyfast_api = importlib.import_module("copyfast_api")
        monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)

        async def mock_bridge(method, path, **kwargs):
            if path == "/internal/v1/wallet":
                return {
                    "ok": True,
                    "status": "read_only",
                    "message": "Số dư ví canonical đã sẵn sàng.",
                    "data": {
                        "balance_xu": 150,
                        "total_spent_xu": 50,
                        "is_vip": False,
                        "source": "canonical_ledger",
                        "reconciliation": {
                            "reconciled": True,
                            "status": "reconciled",
                            "snapshot_credits": 150,
                            "ledger_credits": 150,
                            "discrepancy": 0,
                        },
                    },
                }
            if path == "/internal/v1/wallet/history":
                return {
                    "ok": True,
                    "status": "read_only",
                    "message": "Lịch sử biến động Xu canonical.",
                    "data": {
                        "items": [
                            {"created_at": "2026-09-02 14:00:00", "event_type": "video_render", "delta_xu": -50, "balance_after_xu": 150},
                            {"created_at": "2026-09-01 10:00:00", "event_type": "trial_grant", "delta_xu": 200, "balance_after_xu": 200},
                        ]
                    },
                }
            return {"ok": False, "status": "guarded", "error_code": "NOT_FOUND"}

        monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge)

        # Call GET /api/v1/wallet
        wallet_res = client.get("/api/v1/wallet")
        assert wallet_res.status_code == 200
        wallet_data = wallet_res.json()

        assert wallet_data["ok"] is True, f"Wallet endpoint failed: {wallet_data}"
        assert wallet_data["status"] == "read_only"
        assert wallet_data["data"]["balance_xu"] == 150
        assert wallet_data["data"]["total_spent_xu"] == 50
        assert wallet_data["data"]["is_vip"] is False
        assert wallet_data["data"]["reconciliation"]["reconciled"] is True
        assert wallet_data["data"]["reconciliation"]["discrepancy"] == 0

        # Call GET /api/v1/wallet/history
        history_res = client.get("/api/v1/wallet/history")
        assert history_res.status_code == 200
        history_data = history_res.json()

        assert history_data["ok"] is True, f"History endpoint failed: {history_data}"
        assert history_data["status"] == "read_only"
        items = history_data["data"]["items"]
        assert len(items) == 2
        assert items[0]["event_type"] == "video_render"
        assert items[0]["delta_xu"] == -50


def test_unlinked_account_does_not_return_fake_zero(tmp_path, monkeypatch):
    """Invariant: 0 != NO_DATA != UNAVAILABLE != ERROR != STALE. Unlinked account must return explicit unlinked status."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "unlinked-user@toanaas.vn", CUSTOMER_PASSWORD)

        wallet_res = client.get("/api/v1/wallet")
        assert wallet_res.status_code == 200
        data = wallet_res.json()

        # Must not return ok=True with fake 0 Xu
        assert data["ok"] is False
        assert data["status"] in ("unlinked", "guarded")
        assert data.get("error_code") in ("ACCOUNT_TELEGRAM_UNLINKED", "CORE_BRIDGE_NOT_CONFIGURED", "TELEGRAM_LINK_REQUIRED")


def test_bridge_unavailable_fails_closed_without_fake_zero(tmp_path, monkeypatch):
    """Invariant: When bridge is unconfigured/down, fail closed honestly (never fake 0 Xu)."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        _link_telegram(session_db, CUSTOMER_EMAIL, TELEGRAM_USER_ID)

        # Bridge unconfigured
        wallet_res = client.get("/api/v1/wallet")
        assert wallet_res.status_code == 200
        data = wallet_res.json()

        assert data["ok"] is False
        assert data["status"] == "guarded"
        assert data["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"

        history_res = client.get("/api/v1/wallet/history")
        assert history_res.status_code == 200
        h_data = history_res.json()
        assert h_data["ok"] is False
        assert h_data["status"] == "guarded"


def test_remove_web_owned_fake_pricing_packages_when_bridge_unavailable(tmp_path, monkeypatch):
    """Mission 1: Web App must NOT own fake canonical pricing/packages. When bridge is down, fail closed honestly."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "catalog-user@toanaas.vn", CUSTOMER_PASSWORD)

        res_pkg = client.get("/api/v1/packages")
        assert res_pkg.status_code == 200
        pkg_data = res_pkg.json()
        assert pkg_data["ok"] is False
        assert pkg_data["status"] == "guarded"
        assert pkg_data["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"

        res_pricing = client.get("/api/v1/pricing")
        assert res_pricing.status_code == 200
        pricing_data = res_pricing.json()
        assert pricing_data["ok"] is False
        assert pricing_data["status"] == "guarded"
        assert pricing_data["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"


def test_real_wallet_reconciliation_discrepancy_fails_closed_via_bridge(tmp_path, monkeypatch):
    """Mission 3: Discrepancy detected by Bot read model fails closed on Web App."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "recon-user@toanaas.vn", CUSTOMER_PASSWORD)
        _link_telegram(session_db, "recon-user@toanaas.vn", "8881234567")

        copyfast_api = importlib.import_module("copyfast_api")
        monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)

        async def mock_discrepancy(method, path, **kwargs):
            return {
                "ok": False,
                "status": "guarded",
                "message": "Phát hiện sai lệch đối soát giữa số dư ví và sổ cái giao dịch.",
                "data": {
                    "balance_xu": 300,
                    "total_spent_xu": 0,
                    "is_vip": False,
                    "source": "canonical_ledger",
                    "reconciliation": {
                        "reconciled": False,
                        "status": "unreconciled_discrepancy",
                        "snapshot_credits": 300,
                        "ledger_credits": 200,
                        "discrepancy": 100,
                    },
                },
                "error_code": "WALLET_LEDGER_UNRECONCILED",
            }

        monkeypatch.setattr(copyfast_api, "bridge_request", mock_discrepancy)

        res_unreconciled = client.get("/api/v1/wallet")
        assert res_unreconciled.status_code == 200
        unrec_data = res_unreconciled.json()
        assert unrec_data["ok"] is False
        assert unrec_data["status"] == "guarded"
        assert unrec_data["error_code"] == "WALLET_LEDGER_UNRECONCILED"
        assert unrec_data["data"]["reconciliation"]["reconciled"] is False
        assert unrec_data["data"]["reconciliation"]["discrepancy"] == 100


def test_bot_user_not_initialized_via_bridge(tmp_path, monkeypatch):
    """Invariant: Uninitialized Bot user returns explicit unverified status, never fake 0."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "new-user@toanaas.vn", CUSTOMER_PASSWORD)
        _link_telegram(session_db, "new-user@toanaas.vn", "9991234567")

        copyfast_api = importlib.import_module("copyfast_api")
        monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)

        async def mock_uninitialized(method, path, **kwargs):
            return {
                "ok": False,
                "status": "unverified",
                "message": "Tài khoản Telegram chưa kích hoạt trong hệ thống Bot.",
                "data": None,
                "error_code": "BOT_USER_NOT_INITIALIZED",
            }

        monkeypatch.setattr(copyfast_api, "bridge_request", mock_uninitialized)

        res = client.get("/api/v1/wallet")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is False
        assert data["status"] == "unverified"
        assert data["error_code"] == "BOT_USER_NOT_INITIALIZED"


def test_manual_topup_idempotency_and_no_optimistic_credit(tmp_path, monkeypatch):
    """Manual topup creates pending_admin_review, enforces idempotency, and never gives optimistic credit."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "topup-user@toanaas.vn", CUSTOMER_PASSWORD)
        _link_telegram(session_db, "topup-user@toanaas.vn", TELEGRAM_USER_ID)

        # Seed initial credits = 100
        sys_conn = sqlite3.connect(str(system_db))
        sys_conn.execute("INSERT OR REPLACE INTO users (user_id, credits) VALUES (?, 100)", (TELEGRAM_USER_ID,))
        sys_conn.commit()
        sys_conn.close()

        me = client.get("/api/v1/auth/me").json()
        csrf_token = me["data"]["csrf_token"]

        # 1. Create manual topup
        payload = {
            "amount_vnd": 50000,
            "method": "bank_acb",
            "reference": "TOPUP50KTEST",
            "idempotency_key": "topup-key-unique-001",
        }
        res = client.post(
            "/api/v1/payments/manual",
            json=payload,
            headers={"X-CSRF-Token": csrf_token},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        assert body["status"] == "pending_admin_review"
        req_id = body["data"]["request_id"]

        # 2a. Duplicate click / network retry with identical payload returns the exact same record without creating new row
        res_replay = client.post(
            "/api/v1/payments/manual",
            json=payload,
            headers={"X-CSRF-Token": csrf_token},
        )
        assert res_replay.status_code == 200
        assert res_replay.json()["data"]["request_id"] == req_id
        assert res_replay.json()["data"]["idempotent_replay"] is True

        # Verify only 1 row exists in DB
        with sqlite3.connect(str(session_db)) as s_conn:
            count = s_conn.execute("SELECT COUNT(*) FROM web_manual_topup_requests").fetchone()[0]
            assert count == 1, f"Expected 1 topup request, found {count}"

        # 2b. Reusing same idempotency key with DIFFERENT amount must be rejected (409 conflict)
        conflicting_payload = dict(payload)
        conflicting_payload["amount_vnd"] = 100000
        res_conflict = client.post(
            "/api/v1/payments/manual",
            json=conflicting_payload,
            headers={"X-CSRF-Token": csrf_token},
        )
        assert res_conflict.status_code == 409
        assert res_conflict.json()["error_code"] == "MANUAL_TOPUP_IDEMPOTENCY_CONFLICT"

        # 3. Invariant: NO OPTIMISTIC CREDIT! Balance must strictly remain 100!
        sys_conn = sqlite3.connect(str(system_db))
        current_credits = sys_conn.execute("SELECT credits FROM users WHERE user_id=?", (TELEGRAM_USER_ID,)).fetchone()[0]
        sys_conn.close()
        assert current_credits == 100, f"Optimistic credit detected! Expected 100, got {current_credits}"

        # 4. Check status endpoint
        res_status = client.get(f"/api/v1/payments/manual/{req_id}/status")
        assert res_status.status_code == 200
        assert res_status.json()["data"]["status"] == "pending_admin_review"


def test_wallet_refresh_reconciles_ledger_and_balance(tmp_path, monkeypatch):
    """Reconciliation invariant: DISPLAYED_BALANCE_XU == CANONICAL_BOT_WALLET_BALANCE on refresh."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "refresh-user@toanaas.vn", CUSTOMER_PASSWORD)
        _link_telegram(session_db, "refresh-user@toanaas.vn", TELEGRAM_USER_ID)

        copyfast_api = importlib.import_module("copyfast_api")
        monkeypatch.setattr(copyfast_api, "bridge_configured", lambda: True)

        current_balance = {"balance": 200}
        history_items = [
            {"created_at": "2026-09-01 10:00:00", "event_type": "initial", "delta_xu": 200, "balance_after_xu": 200}
        ]

        async def dynamic_bridge(method, path, **kwargs):
            if path == "/internal/v1/wallet":
                b = current_balance["balance"]
                return {
                    "ok": True,
                    "status": "read_only",
                    "message": "Số dư ví canonical đã sẵn sàng.",
                    "data": {
                        "balance_xu": b,
                        "total_spent_xu": 0,
                        "is_vip": False,
                        "source": "canonical_ledger",
                        "reconciliation": {
                            "reconciled": True,
                            "status": "reconciled",
                            "snapshot_credits": b,
                            "ledger_credits": b,
                            "discrepancy": 0,
                        },
                    },
                }
            if path == "/internal/v1/wallet/history":
                return {
                    "ok": True,
                    "status": "read_only",
                    "message": "Lịch sử biến động Xu canonical.",
                    "data": {"items": list(history_items)},
                }
            return {"ok": False, "status": "guarded"}

        monkeypatch.setattr(copyfast_api, "bridge_request", dynamic_bridge)

        # 1. Initial state: 200 Xu, reconciled with ledger
        w1 = client.get("/api/v1/wallet").json()
        assert w1["ok"] is True
        assert w1["data"]["balance_xu"] == 200
        assert w1["data"]["reconciliation"]["reconciled"] is True

        # 2. Canonical event happens in Bot (e.g. 150 Xu added via bot or confirmed topup)
        current_balance["balance"] = 350
        history_items.insert(0, {
            "created_at": "2026-09-02 12:00:00",
            "event_type": "topup_confirmed",
            "delta_xu": 150,
            "balance_after_xu": 350,
        })

        # 3. Web App refresh immediately reflects updated canonical balance
        w2 = client.get("/api/v1/wallet").json()
        assert w2["ok"] is True
        assert w2["data"]["balance_xu"] == 350
        assert w2["data"]["reconciliation"]["reconciled"] is True

        h2 = client.get("/api/v1/wallet/history").json()
        assert h2["ok"] is True
        assert len(h2["data"]["items"]) == 2
        assert h2["data"]["items"][0]["event_type"] == "topup_confirmed"
        assert h2["data"]["items"][0]["delta_xu"] == 150
        assert h2["data"]["items"][0]["balance_after_xu"] == 350


def test_payos_order_validation_and_status(tmp_path, monkeypatch):
    """PayOS order creation enforces package selection, stores in DB with canonical schema, and checks status without optimistic credit."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "payos-user@toanaas.vn", CUSTOMER_PASSWORD)
        _link_telegram(session_db, "payos-user@toanaas.vn", TELEGRAM_USER_ID)

        # Seed initial credits = 100
        with sqlite3.connect(str(system_db)) as sys_conn:
            sys_conn.execute("INSERT OR REPLACE INTO users (user_id, credits) VALUES (?, 100)", (TELEGRAM_USER_ID,))
            sys_conn.commit()

        me = client.get("/api/v1/auth/me").json()
        csrf_token = me["data"]["csrf_token"]

        # 1. Missing package_id fails
        res_invalid = client.post(
            "/api/v1/payments/create",
            json={"payment_type": "topup_xu", "package_id": "", "idempotency_key": "payos-key-001"},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert res_invalid.status_code == 200
        assert res_invalid.json()["ok"] is False

        # 2. Insert test order directly in payos_orders using canonical schema (NO payment_type or package_id column)
        with sqlite3.connect(str(system_db)) as sys_conn:
            sys_conn.execute(
                "INSERT INTO payos_orders (order_code, user_id, amount, xu, status, created_at) "
                "VALUES ('888888', ?, 50000, 500, 'PENDING', '2026-09-01 10:00:00')",
                (TELEGRAM_USER_ID,)
            )
            sys_conn.commit()

        # 3. Query status endpoint
        res_status = client.get("/api/v1/payments/888888")
        assert res_status.status_code == 200
        body = res_status.json()
        assert body["ok"] is True
        assert body["data"]["status"] == "PENDING"
        assert body["data"]["amount_vnd"] == 50000
        assert body["data"]["xu"] == 500

        # Invariant: NO OPTIMISTIC CREDIT! Balance remains 100!
        with sqlite3.connect(str(system_db)) as sys_conn:
            credits = sys_conn.execute("SELECT credits FROM users WHERE user_id=?", (TELEGRAM_USER_ID,)).fetchone()[0]
            assert credits == 100


def test_no_hardcoded_fake_balances_in_portal_js():
    """Verify portal.js contains no hardcoded fallback balances or fake zero projections."""
    portal_js_path = Path("static/portal/portal.js")
    content = portal_js_path.read_text(encoding="utf-8")
    assert "{ balance_xu: 100 }" not in content
    assert "balance_xu: 100," not in content
    assert "balance_xu : 100" not in content
    assert "balance_xu !== undefined ? context.wallet.balance_xu : 100" not in content
    assert "Number(wallet && wallet.balance_xu !== undefined ? wallet.balance_xu : 0)" not in content


def test_portal_js_unknown_wallet_metrics_contract():
    """Blocker 4 Invariant: UNKNOWN_BALANCE => UNKNOWN_TIER_PROGRESS (never 0 VND -> Newbie)."""
    script = (
        "const fs = require('fs');\n"
        "const code = fs.readFileSync('static/portal/portal.js', 'utf8');\n"
        "const fn = new Function(code.slice(code.indexOf('const MEMBER_TIER_CANONICAL ='), code.indexOf('function renderMembership')) + '\\nreturn getMemberTierInfo;');\n"
        "const getTier = fn();\n"
        "const nullRes = getTier(null);\n"
        "if (nullRes.isKnown !== false || nullRes.currentTier.badge !== '—' || nullRes.progressPercent !== null || nullRes.paidVnd !== null) {\n"
        "  console.error('FAILED null check:', nullRes);\n"
        "  process.exit(1);\n"
        "}\n"
        "const undefRes = getTier(undefined);\n"
        "if (undefRes.isKnown !== false || undefRes.currentTier.badge !== '—' || undefRes.progressPercent !== null) {\n"
        "  console.error('FAILED undefined check:', undefRes);\n"
        "  process.exit(1);\n"
        "}\n"
        "const zeroRes = getTier(0);\n"
        "if (zeroRes.isKnown !== true || zeroRes.currentTier.badge !== '🌱 Newbie' || zeroRes.paidVnd !== 0) {\n"
        "  console.error('FAILED zero check:', zeroRes);\n"
        "  process.exit(1);\n"
        "}\n"
        "console.log('TIER_CONTRACT_VERIFIED_OK');\n"
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    assert "TIER_CONTRACT_VERIFIED_OK" in result.stdout


def test_bridge_signature_actor_id_binding():
    """Blocker 1 & SPEC-P0: CoreBridgeClient._headers binds actor_id into HMAC signature when provided."""
    import hashlib
    import hmac
    from copyfast_bridge import CoreBridgeClient

    client = CoreBridgeClient(
        base_url="http://127.0.0.1:8080",
        token="test-token",
        hmac_secret="test-hmac-secret",
    )

    # Case 1: actor_id is present -> signature message includes .<actor_id>
    headers = client._headers("GET", "/internal/v1/wallet", b"", request_id="req-123", actor_id="7126457028")
    assert headers["X-TOAN-AAS-Actor-ID"] == "7126457028"
    ts = headers["X-TOAN-AAS-Timestamp"]
    digest = hashlib.sha256(b"").hexdigest()
    expected_msg = f"{ts}.req-123.GET./internal/v1/wallet.{digest}.7126457028".encode("utf-8")
    expected_sig = hmac.new(b"test-hmac-secret", expected_msg, hashlib.sha256).hexdigest()
    assert headers["X-TOAN-AAS-Signature"] == expected_sig

    # Case 2: actor_id is empty -> signature message does not include trailing actor
    headers_no_actor = client._headers("GET", "/internal/v1/pricing", b"", request_id="req-456", actor_id="")
    assert "X-TOAN-AAS-Actor-ID" not in headers_no_actor
    ts2 = headers_no_actor["X-TOAN-AAS-Timestamp"]
    expected_msg2 = f"{ts2}.req-456.GET./internal/v1/pricing.{digest}".encode("utf-8")
    expected_sig2 = hmac.new(b"test-hmac-secret", expected_msg2, hashlib.sha256).hexdigest()
    assert headers_no_actor["X-TOAN-AAS-Signature"] == expected_sig2


def test_bridge_sanitize_envelope_preserves_unverified_and_unlinked():
    """Blocker 1: _sanitize_envelope must allow unverified and unlinked statuses from Bot Core."""
    from copyfast_bridge import _sanitize_envelope

    env_unverified = _sanitize_envelope({"ok": False, "status": "unverified", "error_code": "BOT_USER_NOT_INITIALIZED"})
    assert env_unverified["status"] == "unverified"
    assert env_unverified["error_code"] == "BOT_USER_NOT_INITIALIZED"

    env_unlinked = _sanitize_envelope({"ok": False, "status": "unlinked", "error_code": "ACCOUNT_TELEGRAM_UNLINKED"})
    assert env_unlinked["status"] == "unlinked"
    assert env_unlinked["error_code"] == "ACCOUNT_TELEGRAM_UNLINKED"


def test_portal_js_no_balance_derived_paid_vnd():
    """Blocker 2 Invariant: portal.js must never derive total_paid_vnd from balance_xu * 100."""
    portal_js_path = Path("static/portal/portal.js")
    content = portal_js_path.read_text(encoding="utf-8")
    assert "balance_xu * 100" not in content
    assert "balance_xu*100" not in content


def test_pricing_endpoint_is_actorless(tmp_path, monkeypatch):
    """P0.WEBAPP.WEB02: /api/v1/pricing must send actorless HMAC and no user_id in query."""
    import hashlib
    import hmac
    import httpx

    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)
    import copyfast_bridge

    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-bridge-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-bridge-secret")

    captured_requests = []

    async def mock_bot_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        sig_header = request.headers.get("X-TOAN-AAS-Signature", "")
        ts_header = request.headers.get("X-TOAN-AAS-Timestamp", "")
        req_id_header = request.headers.get("X-TOAN-AAS-Request-ID", "")
        path = request.url.path

        assert path == "/internal/v1/pricing"
        # Bot catalog contract: actorless HMAC signature
        digest = hashlib.sha256(request.content or b"").hexdigest()
        expected_msg = f"{ts_header}.{req_id_header}.GET.{path}.{digest}".encode("utf-8")
        expected_sig = hmac.new(b"test-bridge-secret", expected_msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(sig_header, expected_sig):
            return httpx.Response(
                401,
                json={"detail": {"ok": False, "error_code": "SIGNATURE_INVALID", "message": "Signature invalid"}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "status": "read_only", "data": {"image_tiers": [{"name": "Standard", "cost_xu": 10}]}},
        )

    mock_transport = httpx.MockTransport(mock_bot_handler)
    real_client_init = copyfast_bridge.CoreBridgeClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = mock_transport
        real_client_init(self, *args, **kwargs)

    monkeypatch.setattr(copyfast_bridge.CoreBridgeClient, "__init__", patched_init)

    with client:
        _register_and_login(client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        _link_telegram(session_db, CUSTOMER_EMAIL, TELEGRAM_USER_ID)

        res = client.get("/api/v1/pricing")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["status"] == "read_only"

        assert len(captured_requests) == 1
        req = captured_requests[0]
        # Exact requirements: actorless
        assert "x-toan-aas-actor-id" not in req.headers
        assert "user_id=" not in str(req.url)
        # Server-to-server HMAC headers preserved
        assert req.headers.get("Authorization") == "Bearer test-bridge-token"
        assert req.headers.get("X-TOAN-AAS-Timestamp")
        assert req.headers.get("X-TOAN-AAS-Request-ID")
        assert req.headers.get("X-TOAN-AAS-Signature")


def test_packages_endpoint_is_actorless(tmp_path, monkeypatch):
    """P0.WEBAPP.WEB02: /api/v1/packages must send actorless HMAC and no user_id in query."""
    import hashlib
    import hmac
    import httpx

    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)
    import copyfast_bridge

    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-bridge-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-bridge-secret")

    captured_requests = []

    async def mock_bot_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        sig_header = request.headers.get("X-TOAN-AAS-Signature", "")
        ts_header = request.headers.get("X-TOAN-AAS-Timestamp", "")
        req_id_header = request.headers.get("X-TOAN-AAS-Request-ID", "")
        path = request.url.path

        assert path == "/internal/v1/packages"
        # Bot catalog contract: actorless HMAC signature
        digest = hashlib.sha256(request.content or b"").hexdigest()
        expected_msg = f"{ts_header}.{req_id_header}.GET.{path}.{digest}".encode("utf-8")
        expected_sig = hmac.new(b"test-bridge-secret", expected_msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(sig_header, expected_sig):
            return httpx.Response(
                401,
                json={"detail": {"ok": False, "error_code": "SIGNATURE_INVALID", "message": "Signature invalid"}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "status": "read_only", "data": {"packages": [{"code": "PKG_1", "xu": 100}]}},
        )

    mock_transport = httpx.MockTransport(mock_bot_handler)
    real_client_init = copyfast_bridge.CoreBridgeClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = mock_transport
        real_client_init(self, *args, **kwargs)

    monkeypatch.setattr(copyfast_bridge.CoreBridgeClient, "__init__", patched_init)

    with client:
        _register_and_login(client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        _link_telegram(session_db, CUSTOMER_EMAIL, TELEGRAM_USER_ID)

        res = client.get("/api/v1/packages")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["status"] == "read_only"

        assert len(captured_requests) == 1
        req = captured_requests[0]
        # Exact requirements: actorless
        assert "x-toan-aas-actor-id" not in req.headers
        assert "user_id=" not in str(req.url)
        # Server-to-server HMAC headers preserved
        assert req.headers.get("Authorization") == "Bearer test-bridge-token"
        assert req.headers.get("X-TOAN-AAS-Timestamp")
        assert req.headers.get("X-TOAN-AAS-Request-ID")
        assert req.headers.get("X-TOAN-AAS-Signature")


def test_wallet_endpoints_remain_actor_bound(tmp_path, monkeypatch):
    """P0.WEBAPP.WEB02: /api/v1/wallet and /api/v1/wallet/history remain actor-bound."""
    import hashlib
    import hmac
    import httpx

    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)
    import copyfast_bridge

    monkeypatch.setenv("CORE_BRIDGE_BASE_URL", "http://127.0.0.1:8080")
    monkeypatch.setenv("CORE_BRIDGE_TOKEN", "test-bridge-token")
    monkeypatch.setenv("CORE_BRIDGE_HMAC_SECRET", "test-bridge-secret")

    captured_requests = []

    async def mock_bot_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        sig_header = request.headers.get("X-TOAN-AAS-Signature", "")
        ts_header = request.headers.get("X-TOAN-AAS-Timestamp", "")
        req_id_header = request.headers.get("X-TOAN-AAS-Request-ID", "")
        actor_header = request.headers.get("X-TOAN-AAS-Actor-ID", "")
        path = request.url.path

        # Bot wallet contract: actor-bound HMAC signature
        digest = hashlib.sha256(request.content or b"").hexdigest()
        expected_msg = f"{ts_header}.{req_id_header}.GET.{path}.{digest}.{actor_header}".encode("utf-8")
        expected_sig = hmac.new(b"test-bridge-secret", expected_msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(sig_header, expected_sig):
            return httpx.Response(
                401,
                json={"detail": {"ok": False, "error_code": "SIGNATURE_INVALID", "message": "Signature invalid"}},
            )

        if path == "/internal/v1/wallet":
            return httpx.Response(
                200,
                json={"ok": True, "status": "read_only", "data": {"balance_xu": 150, "total_spent_xu": 0, "is_vip": False, "source": "canonical_ledger", "reconciliation": {"reconciled": True, "status": "reconciled", "snapshot_credits": 150, "ledger_credits": 150, "discrepancy": 0}}},
            )
        if path == "/internal/v1/wallet/history":
            return httpx.Response(
                200,
                json={"ok": True, "status": "read_only", "data": {"items": [{"created_at": "2026-09-01", "event_type": "trial_grant", "delta_xu": 150, "balance_after_xu": 150}]}},
            )
        return httpx.Response(404, json={"ok": False})

    mock_transport = httpx.MockTransport(mock_bot_handler)
    real_client_init = copyfast_bridge.CoreBridgeClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = mock_transport
        real_client_init(self, *args, **kwargs)

    monkeypatch.setattr(copyfast_bridge.CoreBridgeClient, "__init__", patched_init)

    with client:
        _register_and_login(client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        _link_telegram(session_db, CUSTOMER_EMAIL, TELEGRAM_USER_ID)

        # 1. Wallet endpoint
        res_wallet = client.get("/api/v1/wallet")
        assert res_wallet.status_code == 200
        data_wallet = res_wallet.json()
        assert data_wallet["ok"] is True
        assert data_wallet["data"]["balance_xu"] == 150

        # 2. Wallet history endpoint
        res_history = client.get("/api/v1/wallet/history")
        assert res_history.status_code == 200
        data_history = res_history.json()
        assert data_history["ok"] is True

        assert len(captured_requests) == 2
        for req in captured_requests:
            # Must remain actor-bound
            assert req.headers.get("x-toan-aas-actor-id") == TELEGRAM_USER_ID
            assert f"user_id={TELEGRAM_USER_ID}" in str(req.url)


def test_admin_routes_preserve_admin_actor_gate(tmp_path, monkeypatch):
    """P0.WEBAPP.WEB02: Admin routes preserve actor identity in _bridge()."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)
    import copyfast_api

    captured_bridge_calls = []

    async def mock_bridge_request(method, path, *, payload=None, params=None, request_id=None, actor_id="", owner_id=""):
        captured_bridge_calls.append({
            "method": method,
            "path": path,
            "actor_id": actor_id,
            "params": params,
        })
        return {"ok": True, "status": "read_only", "data": {}}

    monkeypatch.setattr(copyfast_api, "bridge_request", mock_bridge_request)

    fake_request = type("FakeReq", (), {"headers": {}})()
    admin_account = {"canonical_user_id": TELEGRAM_USER_ID, "role": "admin"}

    import asyncio
    asyncio.run(
        copyfast_api._bridge(
            "GET",
            "/internal/v1/admin/overview",
            account=admin_account,
            request=fake_request,
        )
    )

    assert len(captured_bridge_calls) == 1
    call = captured_bridge_calls[0]
    assert call["actor_id"] == TELEGRAM_USER_ID
    assert call["params"]["user_id"] == TELEGRAM_USER_ID


def test_fail_closed_if_bridge_secrets_missing(tmp_path, monkeypatch):
    """P0.WEBAPP.WEB02: Fail closed if bridge secrets / base URL are unconfigured."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    monkeypatch.delenv("CORE_BRIDGE_BASE_URL", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_TOKEN", raising=False)
    monkeypatch.delenv("CORE_BRIDGE_HMAC_SECRET", raising=False)

    with client:
        _register_and_login(client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        _link_telegram(session_db, CUSTOMER_EMAIL, TELEGRAM_USER_ID)

        res = client.get("/api/v1/pricing")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is False
        assert data["error_code"] == "CORE_BRIDGE_NOT_CONFIGURED"
