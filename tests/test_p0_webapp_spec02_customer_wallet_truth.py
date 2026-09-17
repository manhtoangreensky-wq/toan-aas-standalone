"""Empirical verification test suite for SPEC-02: CUSTOMER WALLET, BILLING AND TOPUP TRUTH.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.SPEC02.CUSTOMER.WALLET.BILLING.TOPUP.TRUTH

Checks and Invariants:
1. displayed wallet balance == canonical bot wallet balance (users.credits)
2. 0 != NO_DATA != UNAVAILABLE != ERROR != STALE
3. Forbidden: fake zero, localStorage balance, optimistic credit, UI approved before ledger, fake receipt
4. Bridge unavailable behavior: seamless read-through projection to canonical system SQLite database
5. Unlinked account behavior: explicit unlinked status, never fake 0
6. Database unavailable behavior: guarded error, never fake 0
7. Topup packages and pricing catalog availability
8. Manual topup creation, idempotency, pending_admin_review state, no optimistic credit
9. PayOS order flow and status projection
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
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


def test_first_red_displayed_wallet_balance_and_ledger_truth(tmp_path, monkeypatch):
    """PROVE FIRST-RED: When Bridge lacks /wallet endpoint, Web App must project canonical balance and ledger from system DB."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        _link_telegram(session_db, CUSTOMER_EMAIL, TELEGRAM_USER_ID)

        # Seed canonical data in system DB without any schema mutations
        sys_conn = sqlite3.connect(str(system_db))
        sys_conn.execute(
            "INSERT OR REPLACE INTO users (user_id, username, credits, is_vip, join_date) "
            "VALUES (?, 'toan_test', 150, 0, '2026-09-01 10:00:00')",
            (TELEGRAM_USER_ID,)
        )
        sys_conn.execute(
            "INSERT INTO credit_events (user_id, delta, balance_after, event_type, ref_id, note, created_at) "
            "VALUES (?, 200, 200, 'trial_grant', 'trial-001', 'Tặng 200 Xu trải nghiệm', '2026-09-01 10:00:00')",
            (TELEGRAM_USER_ID,)
        )
        sys_conn.execute(
            "INSERT INTO credit_events (user_id, delta, balance_after, event_type, ref_id, note, created_at) "
            "VALUES (?, -50, 150, 'video_render', 'job-001', 'Tạo video ngắn', '2026-09-02 14:00:00')",
            (TELEGRAM_USER_ID,)
        )
        sys_conn.commit()
        sys_conn.close()

        # Call GET /api/v1/wallet
        wallet_res = client.get("/api/v1/wallet")
        assert wallet_res.status_code == 200
        wallet_data = wallet_res.json()

        assert wallet_data["ok"] is True, f"Wallet endpoint failed: {wallet_data}"
        assert wallet_data["status"] in ("read_only", "ready", "completed")
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
        assert history_data["status"] in ("read_only", "ready", "completed")
        items = history_data["data"]["items"]
        assert len(items) == 2


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


def test_database_unavailable_does_not_return_fake_zero(tmp_path, monkeypatch):
    """Invariant: When database fails, return guarded error, never fake 0."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "db-fail-user@toanaas.vn", CUSTOMER_PASSWORD)
        _link_telegram(session_db, "db-fail-user@toanaas.vn", "9999999999")

        import config
        monkeypatch.setattr(config.settings, "DB_FILE", "/invalid/nonexistent/path/db.sqlite")

        wallet_res = client.get("/api/v1/wallet")
        assert wallet_res.status_code == 200
        data = wallet_res.json()

        assert data["ok"] is False
        assert data["status"] in ("guarded", "failed")
        if isinstance(data.get("data"), dict):
            assert "balance_xu" not in data["data"] or data["data"]["balance_xu"] is None


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


def test_real_wallet_reconciliation_and_discrepancy_detection(tmp_path, monkeypatch):
    """Mission 3: Real wallet reconciliation between users.credits and credit_events ledger."""
    client, session_db, system_db = _setup_app_client(tmp_path, monkeypatch)

    with client:
        _register_and_login(client, "recon-user@toanaas.vn", CUSTOMER_PASSWORD)
        _link_telegram(session_db, "recon-user@toanaas.vn", "8881234567")

        # 1. State: users.credits = 300, but latest credit_event balance_after = 200 (DISCREPANCY!)
        with sqlite3.connect(str(system_db)) as sys_conn:
            sys_conn.execute(
                "INSERT OR REPLACE INTO users (user_id, username, credits, is_vip, join_date) "
                "VALUES ('8881234567', 'recon_test', 300, 0, '2026-09-01 10:00:00')"
            )
            sys_conn.execute(
                "INSERT INTO credit_events (user_id, delta, balance_after, event_type, created_at) "
                "VALUES ('8881234567', 200, 200, 'grant', '2026-09-01 10:00:00')"
            )
            sys_conn.commit()

        # Discrepancy must fail closed with guarded status!
        res_unreconciled = client.get("/api/v1/wallet")
        assert res_unreconciled.status_code == 200
        unrec_data = res_unreconciled.json()
        assert unrec_data["ok"] is False
        assert unrec_data["status"] == "guarded"
        assert unrec_data["error_code"] == "WALLET_LEDGER_UNRECONCILED"
        assert unrec_data["data"]["reconciliation"]["reconciled"] is False
        assert unrec_data["data"]["reconciliation"]["discrepancy"] == 100

        # 2. Fix the discrepancy by recording the missing 100 Xu ledger event
        with sqlite3.connect(str(system_db)) as sys_conn:
            sys_conn.execute(
                "INSERT INTO credit_events (user_id, delta, balance_after, event_type, created_at) "
                "VALUES ('8881234567', 100, 300, 'topup_reconciled', '2026-09-02 10:00:00')"
            )
            sys_conn.commit()

        # Now reconciled!
        res_reconciled = client.get("/api/v1/wallet")
        assert res_reconciled.status_code == 200
        rec_data = res_reconciled.json()
        assert rec_data["ok"] is True
        assert rec_data["data"]["balance_xu"] == 300
        assert rec_data["data"]["reconciliation"]["reconciled"] is True
        assert rec_data["data"]["reconciliation"]["discrepancy"] == 0


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

        # 1. Initial state: 200 Xu, reconciled with ledger
        with sqlite3.connect(str(system_db)) as sys_conn:
            sys_conn.execute("INSERT OR REPLACE INTO users (user_id, credits) VALUES (?, 200)", (TELEGRAM_USER_ID,))
            sys_conn.execute("INSERT INTO credit_events (user_id, delta, balance_after, event_type, created_at) VALUES (?, 200, 200, 'initial', '2026-09-01 10:00:00')", (TELEGRAM_USER_ID,))
            sys_conn.commit()

        w1 = client.get("/api/v1/wallet").json()
        assert w1["ok"] is True
        assert w1["data"]["balance_xu"] == 200
        assert w1["data"]["reconciliation"]["reconciled"] is True

        # 2. Canonical event happens (e.g. 150 Xu added via bot or confirmed topup)
        with sqlite3.connect(str(system_db)) as sys_conn:
            sys_conn.execute("UPDATE users SET credits=350 WHERE user_id=?", (TELEGRAM_USER_ID,))
            sys_conn.execute("INSERT INTO credit_events (user_id, delta, balance_after, event_type, created_at) VALUES (?, 150, 350, 'topup_confirmed', '2026-09-02 12:00:00')", (TELEGRAM_USER_ID,))
            sys_conn.commit()

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
