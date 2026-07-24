"""Focused contracts for fail-closed customer Support Desk recovery reads."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "SUPPORT_RECOVERY_READ_MODEL_CONTRACT.md").read_text(encoding="utf-8")


def _source_between(start: str, end: str) -> str:
    return INTEGRATION[INTEGRATION.index(start):INTEGRATION.index(end, INTEGRATION.index(start))]


def test_customer_support_receipts_are_validated_before_private_rendering() -> None:
    for helper in (
        "function supportSummaryProjection",
        "function supportCustomerCaseListProjection",
        "function supportCustomerMessageProjection",
        "function supportCustomerCaseDetailProjection",
        "function supportEvidenceProjection",
    ):
        assert helper in INTEGRATION

    summary = _source_between("function supportSummaryProjection", "function supportCustomerCaseListProjection")
    for requirement in (
        'data.delivery !== "web_view_only"',
        "supportReadNonNegativeInteger",
        "expectedActive",
    ):
        assert requirement in summary

    listing = _source_between("function supportCustomerCaseListProjection", "function supportCustomerMessageProjection")
    for requirement in (
        "supportCasePublicProjection",
        "new Set(items.map((item) => item.id)).size !== items.length",
        "data.has_more",
        "expectedNextOffset",
    ):
        assert requirement in listing

    evidence = _source_between("function supportEvidenceProjection", "function supportCustomerCaseDetailProjection")
    assert "supportReadTimestamp(item && item.created_at, false)" in evidence

    detail = _source_between("function supportCustomerCaseDetailProjection", "// Advisor content")
    for requirement in (
        'data.delivery !== "web_view_only"',
        "caseItem.id !== String(expectedCaseId)",
        "data.events.every(supportEventIsSafe)",
        "supportEvidenceProjection",
    ):
        assert requirement in detail


def test_customer_support_hydration_clears_stale_views_and_fails_closed() -> None:
    desk = _source_between("async function hydrateSupportDesk", "async function hydrateSupportCase")
    assert 'supportReadState: "loading"' in desk
    assert "supportSummaryProjection(summaryResult)" in desk
    assert "supportCustomerCaseListProjection(casesResult, filter, offset)" in desk
    assert 'throw new Error("Phản hồi Support Desk chưa được máy chủ xác minh.")' in desk
    assert "supportCases: caseProjection.items" in desk

    detail = _source_between("async function hydrateSupportCase", "async function hydrateSupportAdmin")
    assert 'supportCaseDetail: {}, supportAttachmentAssets: [], supportCaseTriage: {}, supportReadState: "loading"' in detail
    assert "supportCustomerCaseDetailProjection(result, caseId)" in detail
    assert "supportCaseDetail: detail" in detail
    assert 'supportReadState: "failed"' in detail


def test_recovery_ui_explains_next_step_without_claiming_external_work() -> None:
    renderer = PORTAL[PORTAL.index("function renderSupportRecoveryPlan"):PORTAL.index("function renderSupportCaseCards")]
    for state in ("waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"):
        assert f"{state}:" in renderer
    for requirement in (
        'data-portal-action="support-cases-refresh"',
        'href="#support-case-reply"',
        "Case không tự tạo hoàn tiền",
        "Web không hiển thị hoặc suy đoán trạng thái provider",
    ):
        assert requirement in renderer

    detail = PORTAL[PORTAL.index("function renderSupportCaseDetail"):PORTAL.index("function operationsDisplayState")]
    assert 'id="support-case-reply"' in detail
    assert "renderSupportRecoveryPlan(context, caseItem)" in detail
    assert "Thử tải lại" in detail

    for selector in (
        ".portal-support-recovery",
        ".portal-support-recovery-actions .portal-button { min-height: 44px;",
        "#support-case-reply { scroll-margin-top: 20px; }",
    ):
        assert selector in CSS


def test_support_recovery_contract_keeps_financial_and_delivery_boundaries_explicit() -> None:
    for phrase in (
        "does not read Telegram ticket history",
        "Xu ledger",
        "PayOS orders",
        "Malformed mandatory data fails closed",
        "No financial result is claimed",
        "cache scope",
    ):
        assert phrase in CONTRACT
