"""Browser-boundary contracts for Support Desk resolution feedback."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_private_api_helper_forces_no_store_after_caller_options() -> None:
    helper = between(INTEGRATION, "async function api(path, options)", "function merge")

    assert 'fetch(`${API}${path}`, { credentials: "same-origin", ...options, cache: "no-store", headers })' in helper


def test_feedback_projection_is_closed_current_revision_only_and_never_accepts_a_comment() -> None:
    projection = between(INTEGRATION, "function supportResolutionFeedbackProjection", "function supportCustomerCaseDetailProjection")
    constants = between(INTEGRATION, "const SUPPORT_FEEDBACK_TERMINAL_STATES", "function validSupportCaseId")

    assert 'const SUPPORT_FEEDBACK_TERMINAL_STATES = new Set(["resolved", "closed"]);' in constants

    for required in (
        "supportReadPositiveInteger(item.rating)",
        "supportReadPositiveInteger(item.terminal_revision)",
        "revision !== caseItem.revision",
        "state !== caseItem.state",
        "SUPPORT_FEEDBACK_TERMINAL_STATES.has(state)",
        'Object.prototype.hasOwnProperty.call(item, "comment")',
        'Object.prototype.hasOwnProperty.call(item, "id")',
    ):
        assert required in projection

    detail = between(INTEGRATION, "function supportCustomerCaseDetailProjection", "// Advisor content")
    assert "resolution_feedback" in detail
    assert "supportResolutionFeedbackProjection" in detail
    assert "data.resolution_feedback !== null" in detail


def test_feedback_action_is_csrf_idempotent_revision_pinned_and_has_no_browser_authority() -> None:
    action = between(
        INTEGRATION,
        'if (action === "support-case-resolution-feedback")',
        'if (action === "support-case-attachment")',
    )
    payload = between(INTEGRATION, "function supportResolutionFeedbackPayload", "function supportReplyPayload")

    for required in (
        "support-resolution-feedback-submit",
        "supportResolutionFeedbackPayload",
        "acquireSubmission",
        "releaseSubmission",
        "expected_revision: revision",
        "confirm: true",
        "idempotency_key: submission.key",
        "/resolution-feedback",
        "await hydrateSupportCase(caseId);",
    ):
        assert required in action
    for required in (
        "rating",
        "feedback_confirmed",
        "validateWebSupportText",
        "600",
    ):
        assert required in payload
    for forbidden in ("localStorage", "sessionStorage", "account_id", "terminal_state", "submitted_at", "receipt"):
        assert forbidden not in action
        assert forbidden not in payload


def test_customer_surface_is_terminal_only_and_receipt_replaces_the_form() -> None:
    renderer = between(PORTAL, "function renderSupportResolutionFeedback", "function renderSupportCaseDetail")

    for required in (
        "data-support-resolution-feedback-form",
        "data-support-resolution-feedback-receipt",
        'data-portal-action="support-case-resolution-feedback"',
        'name="rating"',
        'name="comment"',
        'maxlength="600"',
        'name="feedback_confirmed"',
        "Đánh giá trải nghiệm hỗ trợ",
        "Tôi xác nhận gửi đánh giá cho revision hiện tại.",
        "portal-card portal-card-pad",
        "aria-live=\"polite\"",
        "data-portal-confirm",
    ):
        assert required in renderer
    assert 'state === "resolved" || state === "closed"' in renderer
    assert "if (!terminal) return \"\";" in renderer
    assert "if (receipt)" in renderer

    detail = between(PORTAL, "function renderSupportCaseDetail", "function operationsDisplayState")
    assert "renderSupportResolutionFeedback(context, caseItem, revision" in detail
    assert "${renderSupportResolutionFeedback(context, caseItem, revision, page)}${renderSupportEvidence(detail, context, caseItem, revision, false)}${replyForm}" in detail


def test_manager_quality_summary_is_role_gated_redacted_and_not_cached() -> None:
    hydration = between(INTEGRATION, "async function hydrateSupportAdmin(", "async function hydrateSupportAdminCase")
    assert 'role === "manager"' in hydration
    assert "/support/admin/care/resolution-feedback-summary?days=30" in hydration
    assert "supportAdminResolutionFeedbackSummary" in hydration

    admin = between(PORTAL, "function renderSupportAdminBase", "function renderSupportAdmin(page")
    assert "renderSupportResolutionFeedbackSummary" in admin
    quality = between(PORTAL, "function renderSupportResolutionFeedbackSummary", "function renderSupportAdminBase")
    summary = between(PORTAL, "function supportResolutionFeedbackSummary", "function renderSupportResolutionFeedbackSummary")
    assert "Customer Care Quality" in quality
    for required in ("total_responses", "average_rating", "comments_count", "rating_counts"):
        assert required in summary
    for forbidden in ("case_id", "account_id", "customer_email", "comment_text", "comment_body"):
        assert forbidden not in quality

    assert "/api/v1/support/" not in SERVICE_WORKER
    assert '"/support"' not in SERVICE_WORKER


def test_manager_quality_summary_fails_closed_for_inconsistent_aggregate_average() -> None:
    integration_projection = between(
        INTEGRATION,
        "function supportResolutionFeedbackSummaryProjection",
        "function supportReplyPayload",
    )
    portal_projection = between(
        PORTAL,
        "function supportResolutionFeedbackSummary",
        "function renderSupportResolutionFeedbackSummary",
    )

    for projection, total_name, counts_name in (
        (integration_projection, "totalResponses", "ratingCounts"),
        (portal_projection, "total", "ratingCounts"),
    ):
        assert "const weightedTotal = [1, 2, 3, 4, 5].reduce(" in projection
        assert f"rating * {counts_name}[String(rating)]" in projection
        assert f"{total_name} > 0 ? supportRoundResolutionFeedbackAverage(weightedTotal / {total_name}) : null" in projection
        assert f"{total_name} === 0 && average !== null" in projection
        assert f"{total_name} > 0 && (typeof average !== \"number\" || !Number.isFinite(average) || average !== expectedAverage)" in projection

    integration_rounding = between(
        INTEGRATION,
        "function supportRoundResolutionFeedbackAverage",
        "function supportResolutionFeedbackSummaryProjection",
    )
    portal_rounding = between(
        PORTAL,
        "function supportRoundResolutionFeedbackAverage",
        "function supportResolutionFeedbackSummary",
    )
    for rounding in (integration_rounding, portal_rounding):
        assert "toFixed(20)" in rounding
        assert "roundingDigit === 5" in rounding
        assert "cents % 2 !== 0" in rounding
