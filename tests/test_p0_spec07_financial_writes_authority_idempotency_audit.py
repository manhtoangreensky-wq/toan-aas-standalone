"""Focused machine-testable financial writes authority and idempotency tests (SPEC-07).

Program: P0.WEB.ERP.PRODUCTION_COMPLETION
Spec: P0.WEB.ERP.SPEC07.FINANCIAL.WRITES.AUTHORITY.IDEMPOTENCY.AUDIT
Mode: OWNER-GOVERNED | AUDIT-FIRST | READ-ONLY | FIRST-RED-ONLY
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import uuid

import pytest
from starlette.testclient import TestClient

import app as app_module
import copyfast_auth
import copyfast_db
import copyfast_finance_policy as fp

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = REPO_ROOT / "reports" / "audit" / "P0-SPEC07-FINANCIAL-WRITES-AUTHORITY-IDEMPOTENCY-MATRIX.json"
REPORT_PATH = REPO_ROOT / "reports" / "audit" / "P0-SPEC07-FINANCIAL-WRITES-AUTHORITY-IDEMPOTENCY-AUDIT.md"
CHECKLIST_PATH = REPO_ROOT / "reports" / "audit" / "P0-WEB-ERP-MASTER-CHECKLIST.md"


@pytest.fixture(scope="module")
def env_setup():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "spec07_finance_test.db")
    os.environ["WEBAPP_SESSION_DB_PATH"] = db_path
    os.environ["WEB_SESSION_SECRET"] = "spec07-finance-test-secret-12345"
    copyfast_db.ensure_copyfast_schema()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT INTO web_accounts (id, email, password_hash, display_name, role_cache, canonical_user_id, is_active, created_at, updated_at)
               VALUES ('acc-admin-spec07', 'admin_spec07@toanaas.vn', 'hash', 'Finance Admin', 'admin', '7126457028', 1, '2026-09-16T10:00:00Z', '2026-09-16T10:00:00Z')"""
        )
        conn.commit()

    yield db_path


@pytest.fixture(scope="module")
def matrix() -> dict:
    assert MATRIX_PATH.exists(), f"Financial writes authority matrix missing at {MATRIX_PATH}"
    with open(MATRIX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def admin_client(env_setup):
    client = TestClient(app_module.app)
    account_id = "acc-admin-spec07"
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


# ==============================================================================
# 1. CANONICAL AUTHORITIES CONTRACT AUDIT
# ==============================================================================
def test_spec07_canonical_authorities(matrix: dict) -> None:
    """Verify core canonical authority definitions in matrix and policy."""
    auth = matrix["canonical_authorities"]
    assert auth["WALLET_AUTHORITY"] == "BOT_CORE"
    assert auth["PAYMENT_GATEWAY_AUTHORITY"] == "PAYOS"
    assert auth["PAYMENT_SETTLEMENT_AUTHORITY"] == "BOT_CORE"
    assert auth["TOPUP_REQUEST_AUTHORITY"] == "WEB_SQLITE"
    assert auth["REVENUE_AUTHORITY"] == "BOT_CORE"
    assert auth["WEB_ROLE"] == "READ_THROUGH_OR_PROJECTION"

    # Match policy constants
    assert fp.WALLET_AUTHORITY == "BOT_CORE"
    assert fp.PAYMENT_GATEWAY_AUTHORITY == "PAYOS"
    assert fp.PAYMENT_SETTLEMENT_AUTHORITY == "BOT_CORE"
    assert fp.TOPUP_REQUEST_AUTHORITY == "WEB_SQLITE"
    assert fp.REVENUE_AUTHORITY == "BOT_CORE"
    assert fp.WEB_ROLE == "READ_THROUGH_OR_PROJECTION"


def test_spec07_safety_invariants(matrix: dict) -> None:
    """Verify inviolable zero-mutation safety invariants."""
    inv = matrix["safety_invariants"]
    assert inv["WEB_DIRECT_WALLET_MUTATION"] is False
    assert inv["WEB_DIRECT_BOT_DB_WRITE"] is False
    assert inv["MANUAL_CREDIT_ACTIONS"] == 0
    assert inv["MANUAL_DEBIT_ACTIONS"] == 0
    assert inv["SETTLEMENT_ACTIONS"] == 0
    assert inv["REFUND_ACTIONS"] == 0
    assert inv["PAYOS_ACTIONS"] == 0
    assert inv["WALLET_ACTIONS"] == 0
    assert inv["ZERO_WALLET_MUTATIONS_ON_READ_OR_REJECT"] is True


# ==============================================================================
# 2. FINANCIAL WRITE ACTIONS SPECIFICATION AUDIT
# ==============================================================================
def test_spec07_financial_write_actions_completeness(matrix: dict) -> None:
    """Verify all required financial write actions are specified with complete contracts."""
    actions = {item["action"]: item for item in matrix["write_actions"]}
    required_actions = {
        "MANUAL_CREDIT",
        "MANUAL_DEBIT",
        "PAYMENT_SETTLEMENT",
        "REFUND",
        "TOPUP_REQUEST_APPROVE",
        "TOPUP_REQUEST_REJECT",
        "PAYOS_CHECKOUT_CREATE",
    }
    assert required_actions.issubset(set(actions.keys())), f"Missing actions: {required_actions - set(actions.keys())}"

    for act_name, act in actions.items():
        assert act["action"] == act_name
        assert act["authority"] in {"BOT_CORE", "PAYOS", "WEB_SQLITE"}
        assert act["write_owner"] is not None and len(act["write_owner"]) > 0
        assert act["required_identity"] is not None and len(act["required_identity"]) > 0
        assert act["required_prestate"] is not None and len(act["required_prestate"]) > 0
        assert act["idempotency_key_source"] is not None and len(act["idempotency_key_source"]) > 0
        assert act["audit_receipt_source"] is not None and len(act["audit_receipt_source"]) > 0
        assert act["recovery_contract"] is not None and len(act["recovery_contract"]) > 0
        assert act["fail_closed_guard"] is not None and len(act["fail_closed_guard"]) > 0


def test_spec07_core_financial_writes_ownership(matrix: dict) -> None:
    """Core financial writes (credit, debit, settlement, refund) must strictly belong to BOT_CORE."""
    actions = {item["action"]: item for item in matrix["write_actions"]}

    # Manual Credit
    credit = actions["MANUAL_CREDIT"]
    assert credit["authority"] == "BOT_CORE"
    assert "BOT_CORE" in credit["write_owner"]
    assert credit["web_direct_mutation_allowed"] is False
    assert "CANONICAL_ADMIN" in credit["required_identity"]

    # Manual Debit
    debit = actions["MANUAL_DEBIT"]
    assert debit["authority"] == "BOT_CORE"
    assert "BOT_CORE" in debit["write_owner"]
    assert debit["web_direct_mutation_allowed"] is False
    assert "CANONICAL_ADMIN" in debit["required_identity"]

    # Settlement
    settle = actions["PAYMENT_SETTLEMENT"]
    assert settle["authority"] == "BOT_CORE"
    assert "BOT_CORE" in settle["write_owner"]
    assert settle["web_direct_mutation_allowed"] is False

    # Refund
    refund = actions["REFUND"]
    assert refund["authority"] == "BOT_CORE"
    assert "BOT_CORE" in refund["write_owner"]
    assert refund["web_direct_mutation_allowed"] is False


def test_spec07_topup_request_authority_boundary(matrix: dict) -> None:
    """Topup request lifecycle is Web SQLite, but does NOT mutate wallet or synthesize payment."""
    actions = {item["action"]: item for item in matrix["write_actions"]}

    approve = actions["TOPUP_REQUEST_APPROVE"]
    assert approve["authority"] == "WEB_SQLITE"
    assert approve["wallet_mutation_direct"] is False
    assert approve["synthesizes_payment_confirmation"] is False

    reject = actions["TOPUP_REQUEST_REJECT"]
    assert reject["authority"] == "WEB_SQLITE"
    assert reject["wallet_mutation_direct"] is False
    assert reject["idempotency_replay_supported"] is True


# ==============================================================================
# 3. CURRENT WRITE SURFACE INVENTORY AUDIT
# ==============================================================================
def test_spec07_write_surface_inventory(matrix: dict) -> None:
    """Verify inventory of existing routes capable of credit/debit/approve/settle/refund/payment."""
    inv = matrix["write_surface_inventory"]
    routes = {item["endpoint"]: item for item in inv}

    required_endpoints = {
        "/api/v1/admin/finance/credit",
        "/api/v1/admin/finance/debit",
        "/api/v1/admin/finance/settle",
        "/api/v1/admin/finance/refund",
        "/api/v1/admin/jobs/{job_id}/refund",
        "/api/v1/admin/payments/manual/{request_id}/draft",
        "/api/v1/admin/payments/manual/{request_id}/confirm",
        "/api/v1/payments/manual",
        "/api/v1/payments/create",
    }
    assert required_endpoints.issubset(set(routes.keys())), f"Missing routes: {required_endpoints - set(routes.keys())}"

    for ep in ["/api/v1/admin/finance/credit", "/api/v1/admin/finance/debit", "/api/v1/admin/finance/settle", "/api/v1/admin/finance/refund"]:
        assert routes[ep]["current_state"] == "LOCKED_FAIL_CLOSED"
        assert routes[ep]["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"


# ==============================================================================
# 4. LIVE API FAIL-CLOSED BEHAVIORAL AUDIT
# ==============================================================================
def test_spec07_admin_finance_routes_fail_closed(admin_client) -> None:
    """Direct admin finance POST endpoints must return WEBAPP_ADMIN_WRITES_DISABLED fail-closed."""
    endpoints = [
        "/api/v1/admin/finance/credit",
        "/api/v1/admin/finance/debit",
        "/api/v1/admin/finance/settle",
        "/api/v1/admin/finance/refund",
    ]
    for ep in endpoints:
        resp = admin_client.post(ep, json={"test": "audit"})
        assert resp.status_code == 200, f"Expected 200 envelope from {ep}, got {resp.status_code}"
        payload = resp.json()
        assert payload["ok"] is False, f"Expected ok=False from {ep}"
        assert payload["error_code"] == "WEBAPP_ADMIN_WRITES_DISABLED"
        assert payload["status"] == "guarded"


# ==============================================================================
# 5. IDEMPOTENCY & AUDIT RECEIPT CONTRACTS
# ==============================================================================
def test_spec07_idempotency_contracts(matrix: dict) -> None:
    """Verify idempotency contracts comply with TOAN AAS system design."""
    contracts = matrix["idempotency_contracts"]
    assert contracts["key_scope_format"] is not None
    assert contracts["duplicate_payload_policy"] == "IDEMPOTENT_REPLAY_CACHED_RESULT"
    assert contracts["conflicting_payload_policy"] == "REJECT_WITH_409_CONFLICT"
    assert contracts["in_progress_policy"] == "GUARD_WITH_409_OR_425"
    assert contracts["two_phase_confirmation_receipt_ttl_seconds"] == 300


def test_spec07_master_checklist_aligned() -> None:
    """Verify Master Checklist records SPEC-07 as part of production completion."""
    assert CHECKLIST_PATH.exists(), f"Checklist missing at {CHECKLIST_PATH}"
    content = CHECKLIST_PATH.read_text(encoding="utf-8")
    assert "SPEC-07" in content
    assert "Topup / Payment Write Safety" in content
