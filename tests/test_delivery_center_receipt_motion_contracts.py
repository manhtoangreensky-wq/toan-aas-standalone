"""Contracts for receipt-driven, presentation-only Delivery Center motion."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "DELIVERY_CENTER_RECORD_IDENTITY_CONTRACT.md").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def test_receipt_hint_is_derived_from_safe_id_status_snapshots_only_after_validation() -> None:
    helper = _section(
        INTEGRATION,
        "function deliveryReadSnapshot(items)",
        "function setMusicDirectionPresetSubmissionStatus(message)",
    )
    jobs = _section(INTEGRATION, 'if (action === "refresh-jobs")', 'if (action === "refresh-assets")')
    assets = _section(INTEGRATION, 'if (action === "refresh-assets")', 'if (action === "admin-audit-filter"')

    assert "function deliveryReadReceiptPresentation(kind, items)" in helper
    assert "isSafeDeliveryReadRecord(item)" in helper
    assert "item.id" in helper
    assert "item.status" in helper
    assert "base()[collection]" in helper
    assert "if (!before.has(id) || before.get(id) !== status)" in helper
    assert "deliveryReadItemsOrThrow(result, \"Job Center\")" in jobs
    assert "deliveryReadReceiptPresentation(\"jobs\", items)" in jobs
    assert "deliveryReadItemsOrThrow(result, \"Assets\")" in assets
    assert "deliveryReadReceiptPresentation(\"assets\", items)" in assets


def test_receipt_helper_is_memory_only_and_cannot_mutate_delivery_or_navigation() -> None:
    helper = _section(
        INTEGRATION,
        "function deliveryReadSnapshot(items)",
        "function setMusicDirectionPresetSubmissionStatus(message)",
    )

    for forbidden in ("fetch(", "localStorage", "sessionStorage", "scrollIntoView", "scrollTo(", "history.", "download_ready", "delivery_ready"):
        assert forbidden not in helper
    assert "presentation-only" in CONTRACT
    assert "`completed`, `output_available`, output metadata and a file download are" in CONTRACT
    assert "merely leaving the bounded window does not animate." in CONTRACT


def test_portal_marks_only_the_matching_delivery_surface_and_consumes_it_after_mount() -> None:
    jobs = _section(PORTAL, "function renderJobs(page, context)", "function renderJobDetail(page, context)")
    assets = _section(PORTAL, "function renderAssets(page, context)", "function validVaultAssetId(value)")
    consumer = _section(PORTAL, "function consumeDeliveryReadReceipt(main)", "function mountPortal(override)")

    assert "function deliveryReadReceiptAttribute(context, kind)" in PORTAL
    assert 'data-delivery-receipt="${safeText(kind)}"' in PORTAL
    assert "deliveryReadReceiptAttribute(context, \"jobs\")" in jobs
    assert "deliveryReadReceiptAttribute(context, \"assets\")" in assets
    assert "removeAttribute(\"data-delivery-receipt\")" in consumer
    assert "animationend" in consumer
    for forbidden in ("fetch(", "localStorage", "sessionStorage", "scrollIntoView", "scrollTo(", "history."):
        assert forbidden not in consumer


def test_receipt_motion_is_short_token_based_and_static_for_reduced_motion() -> None:
    assert "@keyframes portal-delivery-receipt-confirmed" in THEME
    assert ".portal-page.portal-delivery-page [data-delivery-receipt]" in THEME
    assert "animation: portal-delivery-receipt-confirmed 200ms" in THEME
    reduced = _section(THEME, "@media (prefers-reduced-motion: reduce)", "/* Final light Finance Operations Planning surface */")
    assert "[data-delivery-receipt]" in reduced
    assert "animation: none" in reduced


def test_manual_delivery_refresh_discards_out_of_order_responses_before_any_merge() -> None:
    jobs = _section(INTEGRATION, 'if (action === "refresh-jobs")', 'if (action === "refresh-assets")')
    assets = _section(INTEGRATION, 'if (action === "refresh-assets")', 'if (action === "admin-audit-filter"')

    for refresh in (jobs, assets):
        assert "const requestEpoch = ++canonicalHydrationEpoch;" in refresh
        assert "const sessionEpoch = canonicalSessionEpoch;" in refresh
        assert "const isCurrent = () => canonicalRequestIsCurrent(requestEpoch, sessionEpoch, route);" in refresh
        assert "if (!isCurrent()) return;" in refresh
        assert "if (isCurrent()) setActionBusy(action, route, false);" in refresh
        response = refresh.index("const result = await api")
        post_response_guard = refresh.index("if (!isCurrent()) return;", response)
        assert response < post_response_guard < refresh.index("deliveryReadItemsOrThrow")


def test_job_poller_cannot_overwrite_a_newer_manual_jobs_refresh() -> None:
    poller = _section(INTEGRATION, "function isJobPollingRoute(path)", "function paymentIdFromData(data)")
    jobs = _section(INTEGRATION, 'if (action === "refresh-jobs")', 'if (action === "refresh-assets")')

    assert "let jobPollEpoch = 0;" in INTEGRATION
    assert "function invalidateJobPolling()" in poller
    assert "function jobPollRequestIsCurrent(requestEpoch, sessionEpoch, path)" in poller
    assert "const requestEpoch = ++jobPollEpoch;" in poller
    assert "const sessionEpoch = canonicalSessionEpoch;" in poller
    assert "const isCurrent = () => jobPollRequestIsCurrent(requestEpoch, sessionEpoch, path);" in poller
    poll_response = poller.index('const result = await api("/jobs");')
    assert poll_response < poller.index("if (!isCurrent()) return;", poll_response) < poller.index("merge({ jobs: items });")
    assert jobs.index("invalidateJobPolling();") < jobs.index('const result = await api("/jobs");')


def test_current_manual_jobs_refresh_failure_restores_active_job_polling() -> None:
    jobs = _section(INTEGRATION, 'if (action === "refresh-jobs")', 'if (action === "refresh-assets")')
    error_branch = jobs[jobs.index("} catch (error) {"):jobs.index("} finally {")]

    assert "if (!isCurrent()) return;" in error_branch
    assert "scheduleJobPolling(route, base().jobs);" in error_branch
    assert error_branch.index("if (!isCurrent()) return;") < error_branch.index("scheduleJobPolling(route, base().jobs);")


def test_manual_delivery_refresh_busy_state_survives_a_filter_remount_without_persisting() -> None:
    jobs = _section(INTEGRATION, 'if (action === "refresh-jobs")', 'if (action === "refresh-assets")')
    assets = _section(INTEGRATION, 'if (action === "refresh-assets")', 'if (action === "admin-audit-filter"')
    job_page = _section(PORTAL, "function renderJobs(page, context)", "function renderJobDetail(page, context)")
    asset_page = _section(PORTAL, "function renderAssets(page, context)", "function validVaultAssetId(value)")

    assert "function normalizeDeliveryReadRefresh(value)" in PORTAL
    assert "function deliveryReadRefreshBusy(context, kind)" in PORTAL
    assert "deliveryReadRefresh: normalizeDeliveryReadRefresh(source.deliveryReadRefresh)" in PORTAL
    assert "function setDeliveryReadRefreshState(kind, route, requestEpoch)" in INTEGRATION
    assert "function clearDeliveryReadRefreshState(kind, route, requestEpoch)" in INTEGRATION
    assert 'setDeliveryReadRefreshState("jobs", route, requestEpoch);' in jobs
    assert 'clearDeliveryReadRefreshState("jobs", route, requestEpoch);' in jobs
    assert 'setDeliveryReadRefreshState("assets", route, requestEpoch);' in assets
    assert 'clearDeliveryReadRefreshState("assets", route, requestEpoch);' in assets
    assert 'const refreshBusy = deliveryReadRefreshBusy(context, "jobs");' in job_page
    assert 'const refreshBusy = deliveryReadRefreshBusy(context, "assets");' in asset_page
    for forbidden in ("localStorage", "sessionStorage", "fetch(", "history."):
        assert forbidden not in _section(INTEGRATION, "function setDeliveryReadRefreshState", "function setMusicDirectionPresetSubmissionStatus")


def test_hydration_invalidates_an_unresolved_delivery_refresh_busy_marker() -> None:
    hydrate_start = INTEGRATION.index("async function hydrate()")
    first_fetch = INTEGRATION.index("const [catalogResponse", hydrate_start)
    hydration = INTEGRATION[hydrate_start:first_fetch]

    assert "function invalidateDeliveryReadRefreshState()" in INTEGRATION
    assert "++canonicalHydrationEpoch;" in hydration
    assert "invalidateDeliveryReadRefreshState();" in hydration
    assert hydrate_start + hydration.index("++canonicalHydrationEpoch;") < hydrate_start + hydration.index("invalidateDeliveryReadRefreshState();") < first_fetch
