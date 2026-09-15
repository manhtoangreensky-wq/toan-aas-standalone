"""Focused machine-testable data authority contracts for Program P0.WEB.ERP.PRODUCTION_COMPLETION (SPEC-01)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = REPO_ROOT / "reports" / "audit" / "P0-SPEC01-DATA-AUTHORITY-MATRIX.json"
CHECKLIST_PATH = REPO_ROOT / "reports" / "audit" / "P0-WEB-ERP-MASTER-CHECKLIST.md"


@pytest.fixture(scope="module")
def matrix() -> dict:
    assert MATRIX_PATH.exists(), f"Data authority matrix missing at {MATRIX_PATH}"
    with open(MATRIX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_spec01_invariants(matrix: dict) -> None:
    """Core data boundary invariants must be preserved."""
    inv = matrix["invariants"]
    assert inv["ONE_ENTITY_ONE_CANONICAL_WRITE_AUTHORITY"] is True
    assert inv["WEB_DIRECT_WALLET_MUTATION"] is False
    assert inv["TWO_WAY_SYNC_APPROVED"] is False
    assert inv["NO_NEW_CROSS_DB_WRITES"] is True
    assert inv["ZERO_IS_NOT_UNKNOWN"] is True
    assert inv["HTTP200_IS_NOT_BUSINESS_SUCCESS"] is True
    assert inv["PASSWORD_HASH_PROJECTION"] is False
    assert inv["SESSION_TOKEN_PROJECTION"] is False
    assert inv["API_SECRET_PROJECTION"] is False


def test_spec01_financial_authority_isolation(matrix: dict) -> None:
    """Wallet, Ledger, and Settlement write authority belongs strictly to Bot Core, NEVER Web."""
    entities = {e["entity"]: e for e in matrix["entities"]}

    # Wallet balance
    wallet = entities["WALLET"]
    assert wallet["canonical_system"] == "BOT_CORE_SQLITE"
    assert wallet["web_can_write"] is False
    assert wallet["bot_can_write"] is True
    assert wallet["web_representation_type"] == "PROJECTION"

    # Wallet ledger
    ledger = entities["WALLET_LEDGER"]
    assert ledger["canonical_system"] == "BOT_CORE_SQLITE"
    assert ledger["web_can_write"] is False
    assert ledger["bot_can_write"] is True

    # Topup settlement
    settlement = entities["TOPUP_SETTLEMENT"]
    assert settlement["canonical_system"] == "BOT_CORE_SQLITE"
    assert settlement["web_can_write"] is False
    assert settlement["bot_can_write"] is True

    # Topup draft is Web-owned
    draft = entities["TOPUP_DRAFT"]
    assert draft["canonical_system"] == "WEB_SQLITE"
    assert draft["web_can_write"] is True
    assert draft["bot_can_write"] is False

    # Refund settlement
    refund = entities["REFUND"]
    assert refund["canonical_system"] == "BOT_CORE_SQLITE"
    assert refund["web_can_write"] is False
    assert refund["bot_can_write"] is True


def test_spec01_single_canonical_write_authority(matrix: dict) -> None:
    """Every entity must have exactly one write authority; no uncoordinated multi-master."""
    for entity in matrix["entities"]:
        ent_name = entity["entity"]
        write_auth = entity["write_authority"]

        if entity["status"] == "PROVEN":
            assert write_auth in {
                "WEB_SQLITE",
                "BOT_CORE_SQLITE",
                "PAYMENT_GATEWAY_PAYOS",
                "RUNTIME_OS_PROCESS",
                "FILESYSTEM_GOVERNANCE",
                "STATIC_CODE_CONFIG",
                "RUNTIME_CONFIG_ENV",
            }, f"{ent_name} has invalid write authority: {write_auth}"

            # If Web has write authority, Bot must not write without an approved distributed contract
            if write_auth == "WEB_SQLITE":
                assert entity["web_can_write"] is True
                assert entity["bot_can_write"] is False, f"Conflicting write authority on {ent_name}"
            elif write_auth in {"BOT_CORE_SQLITE", "PAYMENT_GATEWAY_PAYOS", "RUNTIME_OS_PROCESS", "FILESYSTEM_GOVERNANCE", "STATIC_CODE_CONFIG", "RUNTIME_CONFIG_ENV"}:
                assert entity["web_can_write"] is False, f"Web must not write to {ent_name} directly"


def test_spec01_revenue_scope_honesty(matrix: dict) -> None:
    """Revenue current scope cannot be COMBINED_CANONICAL without proven Bot aggregation."""
    entities = {e["entity"]: e for e in matrix["entities"]}
    rev = entities["REVENUE"]
    assert rev["status"] == "PARTIAL"
    assert "WEB_ONLY" in rev["web_local_representation"]
    assert rev["canonical_system"] == "BOT_CORE_SQLITE"


def test_spec01_projection_freshness_and_unidirectional_rules(matrix: dict) -> None:
    """Every cross-system flow must be unidirectional without write-back."""
    for flow in matrix["cross_system_flows"]:
        assert flow["write_back_allowed"] is False, f"Flow for {flow['entity']} must not allow write-back"
        assert flow["max_acceptable_staleness"] is not None
        assert flow["mode"] in {"READ_THROUGH_API", "ONE_WAY_PROJECTION", "EVENT_DRIVEN_PROJECTION", "PERIODIC_PROJECTION"}


def test_spec01_owner_gates_coverage(matrix: dict) -> None:
    """Sensitive entities must link to explicit Owner Gates."""
    entities = {e["entity"]: e for e in matrix["entities"]}

    assert entities["WALLET"]["owner_gate_required"] == "GATE-D (Wallet Balance Mutations)"
    assert entities["ADMIN_ROLE"]["owner_gate_required"] == "GATE-E (RBAC Policy Modification)"
    assert entities["PROVIDER"]["owner_gate_required"] == "GATE-G (Provider Integration)"
    assert entities["BACKUP_METADATA"]["owner_gate_required"] == "GATE-C (Database Backup Trigger)"


def test_spec01_entities_completeness(matrix: dict) -> None:
    """All 33 required entities from SPEC-01 must be tracked."""
    required = {
        "ACCOUNT", "AUTH_SESSION", "CUSTOMER_PROFILE", "ADMIN_ROLE", "CRM_LEAD", "SUPPORT_CASE",
        "WALLET", "WALLET_LEDGER", "TOPUP_DRAFT", "TOPUP_SETTLEMENT", "PAYMENT", "PAYMENT_WEBHOOK", "REFUND",
        "VIDEO_JOB", "AI_JOB", "JOB_FAILURE", "WORKER_STATUS", "RUNTIME_STATUS", "FEATURE_STATUS", "FREEZE_STATE",
        "PRICING", "PACKAGE", "PROMO", "PROVIDER", "PROVIDER_COST", "REVENUE", "EXPENSE_PLAN",
        "CONTENT_CAMPAIGN", "CONTENT_CALENDAR", "CONTENT_HANDOFF", "CONTENT_APPROVAL", "PUBLISHING_CHANNEL", "ANALYTICS",
        "AUDIT_EVENT", "GOVERNANCE_DOCUMENT", "BACKUP_METADATA"
    }
    actual = {e["entity"] for e in matrix["entities"]}
    missing = required - actual
    assert not missing, f"Missing entities in SPEC-01 matrix: {missing}"
def test_spec01_owner_corrections(matrix: dict) -> None:
    """Validate the 4 canonical contract corrections mandated before SPEC-02."""
    inv = matrix["invariants"]
    meta = matrix["meta"]

    assert meta["status"] == "PASS_WITH_CONTRACT_CORRECTIONS"

    # Correction 1: Payment webhook split
    assert inv["PAYMENT_EXTERNAL_STATE_AUTHORITY"] == "PAYMENT_GATEWAY_PAYOS"
    assert inv["PAYMENT_WEBHOOK_PROCESSING_AUTHORITY"] == "BOT_CORE_BILLING"
    assert inv["PAYMENT_WEBHOOK_IDEMPOTENCY_AUTHORITY"] == "BOT_CORE_SQLITE.payos_processed"

    # Correction 2: Identity namespace & link authority
    assert inv["WEB_ACCOUNT_AUTHORITY"] == "WEB_SQLITE"
    assert inv["TELEGRAM_ACCOUNT_AUTHORITY"] == "BOT_CORE"
    assert inv["IDENTITY_LINK_AUTHORITY"] == "WEB_SQLITE.telegram_link_codes"
    assert inv["CUSTOMER_IDENTITY_MODEL"] == "FEDERATED_1_TO_1"

    # Correction 3: Monitoring multi-source authority
    assert inv["SYSTEM_RUNTIME_AUTHORITY"] == "RUNTIME_OS_PROCESS"
    assert inv["WORKER_STATUS_AUTHORITY"] == "RUNTIME_OS_PROCESS"
    assert inv["RELIABILITY_TELEMETRY_AUTHORITY"] == "BOT_CORE_AUTOPILOT"
    assert inv["MONITORING_AUTHORITY"] == "MULTI_SOURCE"

    # Correction 4: Pricing dual-definition risk
    assert inv["PRICING_VALUES_CURRENTLY_IN_SYNC"] is True
    assert inv["PRICING_SINGLE_SOURCE_OF_TRUTH"] is False
    assert inv["PRICING_DUPLICATION_RISK"] is True
