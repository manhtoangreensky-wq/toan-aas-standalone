"""High-risk policy boundaries for the future Operations Autopilot."""

import pytest

from copyfast_autopilot_policy import (
    complaint_triage,
    incident_fingerprint,
    may_auto_close_incident,
    retry_delay_seconds,
    safe_playbook_allowed,
)


def test_financial_or_external_complaints_never_become_automatic_execution() -> None:
    financial = complaint_triage(category="refund", priority="urgent", state="new", age_minutes=31)
    assert financial["risk"] == "financial"
    assert financial["disposition"] == "awaiting_operator"
    assert financial["required_role"] == "support_manager"
    assert financial["sla_status"] == "breached"
    external = complaint_triage(category="video_error", priority="high", state="waiting_provider", age_minutes=90)
    assert external["risk"] == "external_dependency"
    assert external["calls_external_system"] is False
    for triage in (financial, external):
        assert triage["changes_case_state"] is False
        assert triage["creates_customer_reply"] is False
        assert triage["mutates_money"] is False
    unknown = complaint_triage(category="unrecognized-value", priority="normal", state="new", age_minutes=1)
    assert unknown["risk"] == "unclassified"
    assert unknown["disposition"] == "awaiting_operator"


def test_playbooks_are_allowlisted_and_circuit_breaker_inputs_are_bounded() -> None:
    assert safe_playbook_allowed("health_probe", feature_enabled=True, remediation_enabled=True) is True
    assert safe_playbook_allowed("approval_expiry_reconciliation", feature_enabled=True, remediation_enabled=True) is True
    assert safe_playbook_allowed("incident_recovery_reconciliation", feature_enabled=True, remediation_enabled=True) is True
    assert safe_playbook_allowed("payment_refund", feature_enabled=True, remediation_enabled=True) is False
    assert safe_playbook_allowed("customer_reply", feature_enabled=True, remediation_enabled=True) is False
    assert safe_playbook_allowed("health_probe", feature_enabled=True, remediation_enabled=False) is False
    assert safe_playbook_allowed("incident_recovery_reconciliation", feature_enabled=False, remediation_enabled=True) is False
    assert safe_playbook_allowed("incident_recovery_reconciliation", feature_enabled=True, remediation_enabled=False) is False
    assert [retry_delay_seconds(index) for index in range(1, 7)] == [60, 120, 240, 480, 900, 900]
    assert may_auto_close_incident(healthy_streak=2, required_streak=3, has_pending_approval=False) is False
    assert may_auto_close_incident(healthy_streak=3, required_streak=3, has_pending_approval=True) is False
    assert may_auto_close_incident(healthy_streak=3, required_streak=3, has_pending_approval=False) is True


def test_incident_fingerprint_is_opaque_stable_and_rejects_invalid_kinds() -> None:
    first = incident_fingerprint(kind="database_readiness", scope="production-web", error_code="SQLITE_BUSY", secret="i" * 32)
    assert first == incident_fingerprint(kind="database_readiness", scope="production-web", error_code="SQLITE_BUSY", secret="i" * 32)
    assert len(first) == 64
    assert "SQLITE_BUSY" not in first
    with pytest.raises(ValueError):
        incident_fingerprint(kind="../../unsafe", scope="production-web", secret="i" * 32)
    with pytest.raises(ValueError):
        incident_fingerprint(kind="database_readiness", scope="production-web", secret="too-short")
