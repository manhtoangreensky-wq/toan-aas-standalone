"""Locale and safety contracts for the owner-scoped Job Detail page.

Only fixed customer-facing interface copy belongs in the delivery catalogue.
Job identifiers, feature names, timestamps, Xu/refund values, lifecycle state,
and signed delivery URLs stay canonical dynamic data at their existing escape
and ownership boundaries.
"""

from __future__ import annotations

from pathlib import Path
import re

from fastapi import HTTPException
import pytest

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


DETAIL_KEYS = frozenset(
    {
        "jobDetail.title", "jobDetail.idNote",
        "jobDetail.field.feature", "jobDetail.field.status",
        "jobDetail.field.created", "jobDetail.field.updated",
        "jobDetail.field.estimatedXu", "jobDetail.field.ledgerXu",
        "jobDetail.field.refund", "jobDetail.field.errorCategory",
        "jobDetail.field.output", "jobDetail.field.delivery",
        "jobDetail.empty.title", "jobDetail.empty.body",
        "jobDetail.protection.title", "jobDetail.protection.body",
        "jobDetail.protection.currentState", "jobDetail.protection.waitingState",
        "jobs.output.title", "jobs.output.emptySubtitle", "jobs.output.listSubtitle",
        "jobs.output.emptyTitle", "jobs.output.emptyBody",
        "jobs.output.listEmptyTitle", "jobs.output.listEmptyBody",
        "lifecycle.kicker", "lifecycle.title", "lifecycle.body",
        "lifecycle.job", "lifecycle.output", "lifecycle.outputBody",
        "lifecycle.delivery", "lifecycle.deliveryBody",
        "lifecycle.next", "lifecycle.nextCompleted",
        "action.download", "action.support", "action.assets", "action.track",
        "status.delivery.noMatchingAsset",
        "state.draft", "state.awaitingConfirm", "state.queued", "state.processing",
        "state.completed", "state.failed", "state.cancelled", "state.refunded",
        "state.guarded", "state.unknown",
        "recovery.title.deliveryPending", "recovery.title.problem",
        "recovery.description.deliveryPending", "recovery.description.problem",
        "recovery.subject.deliveryPending", "recovery.subject.problem",
        "recovery.reason.deliveryPending", "recovery.reason.problem",
        "recovery.reason.disabled", "recovery.field.job", "recovery.field.workflow",
        "recovery.field.status", "recovery.field.subject", "recovery.field.detail",
        "recovery.placeholder", "recovery.help", "recovery.submit",
    }
)


def _catalogue_keys(locale: str) -> set[str]:
    match = re.search(
        rf"Object\.assign\(DELIVERY_CENTER_MESSAGES\.{re.escape(locale)}, \{{(?P<body>.*?)\n  \}}\);",
        I18N,
        flags=re.DOTALL,
    )
    assert match, f"Missing delivery catalogue for {locale}"
    return set(re.findall(r'^\s*"deliveryCenter\.([^"]+)"\s*:', match.group("body"), flags=re.MULTILINE))


def _section(start: str, end: str) -> str:
    offset = PORTAL.index(start)
    return PORTAL[offset:PORTAL.index(end, offset + len(start))]


def test_job_detail_catalogue_has_equal_reviewed_vi_en_zh_keys() -> None:
    catalogues = {locale: _catalogue_keys(locale) for locale in ("vi", "en", "zh")}

    assert catalogues["vi"] == catalogues["en"] == catalogues["zh"]
    assert DETAIL_KEYS <= catalogues["vi"]
    for key in DETAIL_KEYS:
        assert I18N.count(f'"deliveryCenter.{key}"') == 3


def test_job_detail_first_paint_uses_safe_generic_localized_metadata() -> None:
    expected = {
        "vi": (
            "Chi tiết job · TOAN AAS",
            "Xem chi tiết job canonical thuộc quyền sở hữu đã xác minh; delivery chỉ mở qua URL ký tạm thời.",
        ),
        "en": (
            "Job details · TOAN AAS",
            "Review owner-scoped canonical job details; delivery opens only through a temporary signed URL.",
        ),
        "zh": (
            "任务详情 · TOAN AAS",
            "查看已验证所有权范围内的 canonical 任务详情；交付仅通过临时签名 URL 打开。",
        ),
    }
    opaque_id = b"opaque-123"

    assert "JOB_DETAIL_PATH" in PAGES
    for locale, (title, description) in expected.items():
        response = render_portal("/jobs/wnj:v1:opaque-123", interface_locale=locale)
        assert response.status_code == 200
        assert f"<title>{title}</title>".encode("utf-8") in response.body
        assert f'<meta name="description" content="{description}">'.encode("utf-8") in response.body
        title_match = re.search(br"<title>(.*?)</title>", response.body)
        description_match = re.search(br'<meta name="description" content="([^"]*)">', response.body)
        assert title_match and description_match
        assert opaque_id not in title_match.group(1) + description_match.group(1)

    # The route is deliberately narrow: a URL-encoded markup payload is never
    # treated as a detail identifier.
    with pytest.raises(HTTPException):
        render_portal("/jobs/%3Cscript%3E", interface_locale="en")


def test_job_detail_localizes_only_fixed_copy_and_keeps_delivery_guards() -> None:
    output_assets = _section("function renderJobOutputAssets(job, source)", "function renderJobMobileCard(item)")
    state = _section("function jobStateExplanation(item)", "function jobNeedsDeliverySupport(job, source)")
    next_action = _section("function jobDeliveryNextAction(job, source)", "function jobDeliveryStage(job, source)")
    stage = _section("function jobDeliveryStage(job, source)", "function renderJobDeliveryLifecycle(job, context, source)")
    lifecycle = _section("function renderJobDeliveryLifecycle(job, context, source)", "function renderJobRecoverySupport(job, context, source)")
    recovery = _section("function renderJobRecoverySupport(job, context, source)", "function renderJobs(page, context)")
    detail = _section("function renderJobDetail(page, context)", "function renderAssets(page, context)")

    required_calls = {
        output_assets: {
            "jobs.output.title", "jobs.output.emptySubtitle", "jobs.output.listSubtitle",
            "jobs.output.emptyTitle", "jobs.output.emptyBody",
            "jobs.output.listEmptyTitle", "jobs.output.listEmptyBody",
        },
        state: {
            "state.draft", "state.awaitingConfirm", "state.queued", "state.processing",
            "state.completed", "state.failed", "state.cancelled", "state.refunded",
            "state.guarded", "state.unknown",
        },
        next_action: {"action.download", "action.support", "action.assets", "action.track"},
        stage: {"status.delivery.noMatchingAsset"},
        lifecycle: {
            "lifecycle.kicker", "lifecycle.title", "lifecycle.body", "lifecycle.job",
            "lifecycle.output", "lifecycle.outputBody", "lifecycle.delivery",
            "lifecycle.deliveryBody", "lifecycle.next", "lifecycle.nextCompleted",
        },
        recovery: {
            "recovery.title.deliveryPending", "recovery.title.problem",
            "recovery.description.deliveryPending", "recovery.description.problem",
            "recovery.subject.deliveryPending", "recovery.subject.problem",
            "recovery.reason.deliveryPending", "recovery.reason.problem",
            "recovery.reason.disabled", "recovery.field.job", "recovery.field.workflow",
            "recovery.field.status", "recovery.field.subject", "recovery.field.detail",
            "recovery.placeholder", "recovery.help", "recovery.submit",
        },
        detail: {
            "jobDetail.title", "jobDetail.idNote", "jobDetail.field.feature",
            "jobDetail.field.status", "jobDetail.field.created", "jobDetail.field.updated",
            "jobDetail.field.estimatedXu", "jobDetail.field.ledgerXu", "jobDetail.field.refund",
            "jobDetail.field.errorCategory", "jobDetail.field.output", "jobDetail.field.delivery",
            "jobDetail.empty.title", "jobDetail.empty.body", "jobDetail.protection.title",
            "jobDetail.protection.body", "jobDetail.protection.currentState",
            "jobDetail.protection.waitingState",
        },
    }
    for renderer, keys in required_calls.items():
        for key in keys:
            assert f'deliveryCenterText("{key}"' in renderer, key

    # Localization may only change presentation. Existing exact-match and
    # signed-delivery boundaries must remain intact.
    assert "const assets = exactJobAssets(job, source);" in output_assets
    assert "assetDownloadPath(deliveryAsset)" in next_action
    assert 'href="${safeText(deliveryPath)}" rel="noreferrer"' in next_action
    assert 'href="#job-recovery-support"' in next_action
    assert 'data-portal-action="create-ticket"' in recovery
    assert 'data-portal-route="/jobs/${safeText(jobId)}"' in recovery
    assert "safeText(jobId)" in recovery
    assert "const record = safeText(page.recordId" in detail
    assert "encodeURIComponent" in PORTAL
    assert "fetch(" not in output_assets + state + next_action + stage + lifecycle + recovery + detail
