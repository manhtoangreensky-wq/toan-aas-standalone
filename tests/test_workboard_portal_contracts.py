"""Static contracts for the private Web-native Workboard portal.

The Workboard is coordination metadata only.  These checks keep its polished
portal surface tied to the signed Web API instead of drifting into a browser
store, Bot bridge, payment surface or fake automation claim.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
WORKBOARD = (ROOT / "copyfast_workboard.py").read_text(encoding="utf-8")


def _workboard_surface() -> str:
    start = PORTAL.index("// Workboard remains deliberately small")
    return PORTAL[start:PORTAL.index("function showToast", start)]


def _workboard_helpers() -> str:
    start = INTEGRATION.index("const WORKBOARD_STATES")
    return INTEGRATION[start:INTEGRATION.index("// Subtitle & Transcript Workspace", start)]


def _workboard_actions() -> str:
    start = INTEGRATION.index('if (action === "workboard-filter"')
    return INTEGRATION[start:INTEGRATION.index('if (action === "prompt-library-filter"', start)]


def test_workboard_has_private_routes_and_professional_portal_views() -> None:
    for needle in (
        'customerPage("/workboard", "Workboard"',
        'customerPage("/workboard/new", "Work item mới"',
        'path: "/workboard/:id"',
        "function renderWorkboardOverview(page, context, view)",
        "function renderWorkboardNew(page, context)",
        "function renderWorkboardDetail(page, context)",
        'case "workboard": return renderWorkboardOverview(page, context, workboardView());',
        'case "workboard-new": return renderWorkboardNew(page, context);',
        'case "workboard-detail": return renderWorkboardDetail(page, context);',
        'if (linkPath === "/workboard") return matchesRouteFamily(path, "/workboard")',
    ):
        assert needle in PORTAL
    assert "WORKBOARD_PATH" in PAGES
    assert "WORKBOARD_PATH.fullmatch(normalized)" in PAGES
    assert 'customerPage("/workboard/list"' not in PORTAL

    helpers = _workboard_helpers()
    for helper in (
        "workboardItemIdFromPath",
        "isNativeWorkboardPath",
        "workboardItemPayload",
        "workboardChecklistPayload",
        "workboardFilterPayload",
        "workboardListPath",
        "workboardListingProjection",
        "workboardBoundaryIsSafe",
        "hydrateWorkboard",
        "hydrateWorkboardItem",
        "workboardMutation",
    ):
        assert f"function {helper}" in helpers or f"async function {helper}" in INTEGRATION
    for needle in (
        "isNativeWorkboardPath(currentPath)",
        "else if (isNativeWorkboardPath(currentPath))",
    ):
        assert needle in INTEGRATION


def test_workboard_portal_enforces_the_web_native_boundary() -> None:
    helpers = _workboard_helpers()
    for flag in (
        'boundary.execution === "web_native_coordination_only"',
        'boundary.data_origin === "signed_account_web_records_only"',
        "boundary.deterministic_local_state === true",
        "boundary.bot_called === false",
        "boundary.provider_called === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_started === false",
        "boundary.payment_processed === false",
        "boundary.job_created === false",
        "boundary.publish_action_created === false",
        "boundary.notification_sent === false",
        "boundary.browser_file_upload === false",
        "boundary.external_url_import === false",
        'boundary.output_delivery === "not_applicable"',
    ):
        assert flag in helpers
    for request in (
        'api("/workboard/summary")',
        "api(workboardListPath(filter, offset))",
        'api("/workboard/events?limit=80")',
        'api("/workboard/references")',
        'api("/workboard/policy")',
        'api("/workboard/items/" + encodeURIComponent(String(itemId)))',
        'api(workboardHistoryPath(itemId, "versions", historyOptions.versionOffset))',
        'api(workboardHistoryPath(itemId, "events", historyOptions.eventOffset))',
    ):
        assert request in INTEGRATION
    assert ".every(workboardBoundaryIsSafe)" in INTEGRATION
    assert "workboardBoundaryIsSafe(data)" in INTEGRATION
    surface = _workboard_surface()
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "window.open("):
        assert forbidden not in surface
    for forbidden in (
        "import copyfast_bridge",
        "from copyfast_bridge",
        "import requests",
        "import httpx",
        "import urllib",
        "PayOS",
        "from wallet",
    ):
        assert forbidden not in WORKBOARD


def test_workboard_mutations_match_the_server_contract_and_no_more() -> None:
    actions = _workboard_actions()
    for action in (
        "workboard-refresh",
        "workboard-filter",
        "workboard-filter-clear",
        "workboard-page",
        "workboard-create",
        "workboard-update",
        "workboard-state",
        "workboard-checklist-create",
        "workboard-checklist-update",
        "workboard-restore-version",
    ):
        assert f'action === "{action}"' in actions
        assert action in PORTAL
    for needle in (
        'path: "/workboard/items"',
        'path: "/workboard/items/" + encodeURIComponent(itemId)',
        '"/state"',
        '"/checklist"',
        '"/restore/" + encodeURIComponent(String(targetRevision))',
        "expected_revision: expectedRevision",
        "expected_checklist_revision: expectedChecklistRevision",
        "idempotency_key: submission.key",
        "refreshWorkboardAfterMutation(itemId)",
    ):
        assert needle in actions or needle in INTEGRATION
    assert '"/restore-version"' not in actions
    assert "const { checklist: _checklist, ...itemPayload }" in actions
    for forbidden in ("bridgeAvailable", "PayOS", "/payments", "/jobs", "wallet", "telegram", "provider"):
        assert forbidden.lower() not in actions.lower()


def test_workboard_client_limits_and_responsive_private_pwa_match_api() -> None:
    helpers = _workboard_helpers()
    for needle in (
        'workboardText(fields.title, "Tên công việc", 3, 180, false)',
        'workboardText(fields.description, "Mô tả", 0, 5000, true)',
        'workboardText(value, "Checklist", 2, 360, false)',
        "if (references.length > 8)",
        "if (checklist.length > 40)",
        'workboardText(source.q, "Từ khóa Workboard", 0, 120, false)',
        "limit: String(WORKBOARD_LIST_LIMIT)",
    ):
        assert needle in helpers
    for needle in (
        'minLength: 3, maxLength: 180',
        'maxLength: 5000',
        'minlength="2" maxlength="360"',
        ".portal-workboard-board",
        ".portal-workboard-detail-grid",
        ".portal-workboard-checklist",
        "function workboardFilterFields()",
        ".portal-workboard-filter",
        ".portal-workboard-pagination",
        ".portal-workboard-intro, .portal-workboard-detail-summary, .portal-workboard-editor-layout, .portal-workboard-detail-grid, .portal-workboard-history-grid { grid-template-columns: 1fr; }",
    ):
        assert needle in PORTAL or needle in CSS
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    # Cache generations now come from the worker's validated build query, so
    # a static `v43` assertion would make this private-route contract fail on
    # every legitimate release. Retain the stronger lifecycle invariants.
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in SERVICE_WORKER
    assert "const BUILD_ID = workerBuildId();" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    assert '"/" + "api/v1/workboard"' in SERVICE_WORKER
    assert '"/workboard"' in SERVICE_WORKER
    assert "private `/workboard/*` routes" in SERVICE_WORKER
    assert '"/" + "api/v1/workboard"' not in shell
    assert '"/workboard"' not in shell
    actions = _workboard_actions()
    for forbidden in ("localStorage", "sessionStorage", "Telegram", "PayOS", "/payments", "/jobs"):
        assert forbidden.lower() not in actions.lower()


def test_workboard_schedule_read_failure_locks_only_schedule_controls() -> None:
    """A schedule-list outage must not erase an otherwise verified work item.

    The schedule is an opt-in Inbox capability, not the canonical Workboard
    detail.  Keep the signed item/history readable, surface an honest guarded
    schedule card, and never mistake an unavailable list for an empty list.
    """

    detail_start = INTEGRATION.index("async function hydrateWorkboardItem")
    detail_end = INTEGRATION.index("function stateForWorkboardItem", detail_start)
    detail = INTEGRATION[detail_start:detail_end]
    for contract in (
        "const results = await Promise.allSettled([",
        "const requiredResults = [results[0], results[1], results[2], results[4], results[5]];",
        'requiredResults.some((result) => result.status !== "fulfilled")',
        'const scheduleReadState = scheduleResult.status === "fulfilled" && workboardBoundaryIsSafe(schedulesData)',
        '? "read_only"',
        ': "guarded"',
        'scheduleReadState === "read_only" && Array.isArray(schedulesData.schedule_intents)',
        "scheduleIntentsReadState: scheduleReadState",
    ):
        assert contract in detail

    schedule_start = PORTAL.index("function renderWorkboardSchedule")
    schedule_end = PORTAL.index("function renderWorkboardDetail", schedule_start)
    schedule = PORTAL[schedule_start:schedule_end]
    for contract in (
        'const scheduleReadable = scheduleReadState === "read_only";',
        'scheduleReadable && context.capabilities',
        "const rows = !scheduleReadable",
        "Chưa thể xác minh lịch nhắc",
        "khóa thay vì giả định không có lịch cũ",
        "const scheduleBadge = !scheduleReadable",
    ):
        assert contract in schedule
    assert 'Chưa có lịch nhắc. Khi đến mốc giờ' in schedule


def test_workboard_schedule_uses_the_retained_profile_timezone() -> None:
    """A signed profile preference must win over a browser-only fallback."""

    start = PORTAL.index("function workboardScheduleTimezoneDefault")
    end = PORTAL.index("function renderWorkboardSchedule", start)
    helper = PORTAL[start:end]
    assert "context.profile" in helper
    assert "profile.timezone" in helper
    assert "context.account" not in helper
    assert 'return "Asia/Ho_Chi_Minh";' in helper
