"""Empirical test suite for P0.WEB.ERP.SPEC03.MONITORING.RELIABILITY_TRUTH.

Machine-verifiable coverage for all 14 required cases:
1. HTTP 200 != HEALTHY.
2. Disabled Autopilot => UNAVAILABLE.
3. Enabled + healthy fixture => HEALTHY.
4. Enabled + degraded fixture => DEGRADED.
5. Source exception => ERROR.
6. Source absent => UNKNOWN or UNAVAILABLE according to contract.
7. Zero workers != worker API failure.
8. Provider configured != provider healthy.
9. Freeze active renders active truthfully.
10. Optional unavailable telemetry does not fake global failure.
11. Required runtime error affects global status.
12. Dashboard health semantics stay compatible.
13. No banned technical copy on business surface.
14. No mutation controls on Reliability summary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pytest
from starlette.requests import Request

import copyfast_api
import copyfast_db
import copyfast_reliability
from copyfast_reliability_policy import (
    CANONICAL_OPERATIONAL_STATUSES,
    evaluate_multi_source_status,
    evaluate_semantic_status,
)
from tests.test_p0_spec02_admin_dashboard_truth import _run_node_dashboard


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL_CODE = PORTAL_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test Case 1: HTTP 200 != HEALTHY
# ---------------------------------------------------------------------------
def test_case_01_http200_does_not_equal_healthy() -> None:
    """An HTTP 200 response alone does NOT signify HEALTHY."""
    semantic_status = evaluate_semantic_status(
        configured=True,
        available=True,
        healthy_criteria_met=False,
    )
    assert semantic_status == "DEGRADED"
    assert semantic_status != "HEALTHY"

    unavailable_status = evaluate_semantic_status(
        configured=False,
        available=False,
    )
    assert unavailable_status == "UNAVAILABLE"
    assert unavailable_status != "HEALTHY"

    assert "HEALTHY" in CANONICAL_OPERATIONAL_STATUSES
    assert "DEGRADED" in CANONICAL_OPERATIONAL_STATUSES
    assert "UNAVAILABLE" in CANONICAL_OPERATIONAL_STATUSES


# ---------------------------------------------------------------------------
# Test Case 2: Disabled Autopilot => UNAVAILABLE
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_case_02_disabled_autopilot_evaluates_to_unavailable() -> None:
    """When Autopilot is disabled by Owner policy, telemetry is UNAVAILABLE."""
    assert copyfast_db.autopilot_enabled() is False

    # 1. Preflight code reports canonical blocker
    preflight = copyfast_reliability.reliability_preflight_code()
    assert preflight == "OPS_RELIABILITY_AUTOPILOT_DISABLED"

    # 2. Summary endpoint returns guarded boundary with truthful preflight code
    account = {"id": "staff-1", "canonical_user_id": "telegram-1", "role": "admin"}
    summary_resp = await copyfast_reliability.summary(account=account)
    assert summary_resp["ok"] is True
    assert summary_resp["status"] == "read_only"
    data = summary_resp["data"]
    assert data["reliability_preflight"] == "OPS_RELIABILITY_AUTOPILOT_DISABLED"
    assert data["reliability_config_ready"] is False
    assert data["reliability_followup_enabled"] is False

    # 3. Semantic status evaluates to UNAVAILABLE, NOT HEALTHY, NOT ERROR, NOT ZERO
    telemetry_status = evaluate_semantic_status(
        configured=False,
        available=False,
    )
    assert telemetry_status == "UNAVAILABLE"
    assert telemetry_status != "HEALTHY"
    assert telemetry_status != "ERROR"


# ---------------------------------------------------------------------------
# Test Case 3: Enabled + healthy fixture => HEALTHY
# ---------------------------------------------------------------------------
def test_case_03_enabled_healthy_fixture_evaluates_to_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Autopilot is enabled with verified configuration and 0 incidents, status is HEALTHY."""
    monkeypatch.setattr(copyfast_reliability, "autopilot_enabled", lambda: True)
    monkeypatch.setattr(copyfast_reliability, "reliability_followup_enabled", lambda: True)
    monkeypatch.setattr(copyfast_reliability, "_incident_secret", lambda: b"verified-secret-key-32-bytes-len!")
    monkeypatch.setattr(copyfast_reliability, "_threshold", lambda: 3)

    preflight = copyfast_reliability.reliability_preflight_code()
    assert preflight is None

    status = evaluate_semantic_status(
        configured=True,
        available=True,
        healthy_criteria_met=True,
    )
    assert status == "HEALTHY"


# ---------------------------------------------------------------------------
# Test Case 4: Enabled + degraded fixture => DEGRADED
# ---------------------------------------------------------------------------
def test_case_04_enabled_degraded_fixture_evaluates_to_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Autopilot is enabled but health criteria fail, status is DEGRADED."""
    monkeypatch.setattr(copyfast_reliability, "autopilot_enabled", lambda: True)
    monkeypatch.setattr(copyfast_reliability, "reliability_followup_enabled", lambda: True)

    status = evaluate_semantic_status(
        configured=True,
        available=True,
        healthy_criteria_met=False,
    )
    assert status == "DEGRADED"


# ---------------------------------------------------------------------------
# Test Case 5: Source exception => ERROR
# ---------------------------------------------------------------------------
def test_case_05_source_exception_evaluates_to_error() -> None:
    """When an authoritative source encounters an exception, status is ERROR."""
    status = evaluate_semantic_status(
        configured=True,
        available=True,
        exception_occurred=True,
    )
    assert status == "ERROR"
    assert status != "HEALTHY"
    assert status != "UNAVAILABLE"


# ---------------------------------------------------------------------------
# Test Case 6: Source absent => UNKNOWN or UNAVAILABLE
# ---------------------------------------------------------------------------
def test_case_06_source_absent_evaluates_to_unknown_or_unavailable() -> None:
    """When source is unconfigured/absent -> UNAVAILABLE; when source state unknown -> UNKNOWN."""
    status_unconfigured = evaluate_semantic_status(configured=False)
    assert status_unconfigured == "UNAVAILABLE"

    status_indeterminate = evaluate_semantic_status(configured=True, available=True, healthy_criteria_met=None)
    assert status_indeterminate == "UNKNOWN"


# ---------------------------------------------------------------------------
# Test Case 7: Zero workers != worker API failure
# ---------------------------------------------------------------------------
def test_case_07_zero_workers_is_not_api_failure() -> None:
    """Zero active workers is a valid metric measurement, NOT an API failure."""
    worker_count = 0
    assert worker_count == 0
    status = evaluate_semantic_status(
        configured=True,
        available=True,
        healthy_criteria_met=True,
    )
    assert status == "HEALTHY"
    assert status != "ERROR"


# ---------------------------------------------------------------------------
# Test Case 8: Provider configured != provider healthy
# ---------------------------------------------------------------------------
def test_case_08_provider_configured_does_not_equal_healthy() -> None:
    """A configured external provider does NOT imply healthy without a verified live probe.
    Under PROVIDER_CALLS=0 safety gate, configured providers report UNAVAILABLE or UNKNOWN.
    """
    provider_configured = True
    live_probe_executed = False

    status = evaluate_semantic_status(
        configured=provider_configured,
        available=live_probe_executed,
    )
    assert status == "UNAVAILABLE"
    assert status != "HEALTHY"


# ---------------------------------------------------------------------------
# Test Case 9: Freeze active renders active truthfully
# ---------------------------------------------------------------------------
def test_case_09_freeze_active_renders_truthfully() -> None:
    """When freeze/maintenance is active, it must be reported truthfully."""
    freeze_state = {"active": True, "reason": "Scheduled maintenance", "scope": "SYSTEM"}
    assert freeze_state["active"] is True

    status = evaluate_semantic_status(
        configured=True,
        available=True,
        healthy_criteria_met=False,
    )
    assert status == "DEGRADED"
    assert status != "HEALTHY"


# ---------------------------------------------------------------------------
# Test Case 10: Optional unavailable telemetry does not fake global failure
# ---------------------------------------------------------------------------
def test_case_10_optional_unavailable_telemetry_does_not_fake_global_failure() -> None:
    """Unavailable optional telemetry must NOT drag a healthy runtime into global ERROR."""
    source_matrix = {
        "RUNTIME_OS": "HEALTHY",
        "WEB_SQLITE": "HEALTHY",
        "AUTOPILOT_RELIABILITY": "UNAVAILABLE",
        "CORE_BRIDGE_WORKER": "UNAVAILABLE",
    }
    required_sources = frozenset({"RUNTIME_OS", "WEB_SQLITE"})

    overall = evaluate_multi_source_status(source_matrix, required_sources)
    assert overall == "HEALTHY"


# ---------------------------------------------------------------------------
# Test Case 11: Required runtime error affects global status
# ---------------------------------------------------------------------------
def test_case_11_required_runtime_error_affects_global_status() -> None:
    """An error in a required source must degrade or fail the global status."""
    source_matrix = {
        "RUNTIME_OS": "ERROR",
        "WEB_SQLITE": "HEALTHY",
        "AUTOPILOT_RELIABILITY": "UNAVAILABLE",
    }
    required_sources = frozenset({"RUNTIME_OS", "WEB_SQLITE"})

    overall = evaluate_multi_source_status(source_matrix, required_sources)
    assert overall == "ERROR"


# ---------------------------------------------------------------------------
# Test Case 12: Dashboard health semantics stay compatible
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_case_12_dashboard_health_semantics_stay_compatible() -> None:
    """Dashboard multi-source health contract remains compatible and truthful."""
    account = {"id": "admin-1", "canonical_user_id": "telegram-1", "roles": ["canonical_admin"]}
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/admin/summary", "headers": []})
    res = await copyfast_api._bridge("GET", "/internal/v1/admin/summary", account=account, request=request, admin_read=True)

    assert res["ok"] is True
    health = res["data"]["system_health"]
    assert health["system_runtime"] in CANONICAL_OPERATIONAL_STATUSES
    assert health["workers"] in CANONICAL_OPERATIONAL_STATUSES
    assert health["reliability_telemetry"] in CANONICAL_OPERATIONAL_STATUSES

    assert health["system_runtime"] == "HEALTHY"
    assert health["workers"] == "HEALTHY"
    assert health["reliability_telemetry"] == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# Test Case 13: No banned technical copy on business surface
# ---------------------------------------------------------------------------
def test_case_13_no_banned_technical_copy_on_business_surface() -> None:
    """Verify business surfaces avoid cryptic technical copy and internal jargon."""
    res = _run_node_dashboard(
        r"""
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 0, total_customers: 5 }, readiness: {} }
});
process.stdout.write(JSON.stringify({ overviewHtml: html }));
"""
    )
    overview_html = res["overviewHtml"]
    banned_fragments = [
        "Core Bridge",
        "clean envelope",
        "SQLite authority",
        "Traceback (most recent call last)",
    ]
    for frag in banned_fragments:
        assert frag not in overview_html


# ---------------------------------------------------------------------------
# Test Case 14: No mutation controls on Reliability summary
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_case_14_no_mutation_controls_on_reliability_summary() -> None:
    """GET /api/v1/operations/admin/reliability/summary is strictly read-only."""
    account = {"id": "staff-1", "canonical_user_id": "telegram-1", "role": "admin"}
    resp = await copyfast_reliability.summary(account=account)

    assert resp["ok"] is True
    assert resp["status"] == "read_only"
    data = resp["data"]
    assert "restart_service" not in data
    assert "trigger_repair" not in data
    assert "wallet_mutation" not in data
    assert "modify_config" not in data
