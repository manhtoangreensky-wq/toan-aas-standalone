"""Static contracts for the private, Web-native Notification Center UI.

The current explicit allow-list materializes only owner-scoped *in-app
records* for an overdue Web reminder or an owner-confirmed Workboard/Campaign
schedule intent. It is deliberately not a Telegram, email, SMS, web-push,
Bot, provider, wallet, payment, job or deployment channel. These checks keep
the Portal honest when a user returns after being away: it can show durable
signed-account records, but must never claim an external delivery or obtain
data through the generic Bot bridge.
"""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
NOTIFICATIONS = (ROOT / "copyfast_notification_center.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    """Return a stable source slice and fail clearly when its contract moves."""
    begin = source.index(start)
    finish = source.index(end, begin + len(start))
    return source[begin:finish]


def _function_source(source: str, name: str) -> str:
    """Read one normal portal helper without coupling the test to its offset."""
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end():])
    end = match.end() + following.start() if following else len(source)
    return source[match.start():end]


def test_notification_customer_routes_are_native_private_portal_surfaces() -> None:
    inbox = _between(
        PORTAL,
        'customerPage("/inbox", "Inbox"',
        'customerPage("/automation", "Automation Center"',
    )
    automation = _between(
        PORTAL,
        'customerPage("/automation", "Automation Center"',
        'customerPage("/legal"',
    )

    assert 'layout: "notification-inbox", action: "none"' in inbox
    assert 'layout: "notification-automation", action: "none"' in automation
    for layout, renderer in (
        ("notification-inbox", "renderInbox"),
        ("notification-automation", "renderNotificationAutomation"),
    ):
        assert f"function {renderer}(page, context)" in PORTAL
        assert f'case "{layout}": return {renderer}(page, context);' in PORTAL

    # A persistent record is not evidence that anything was delivered to a
    # third party. The customer-facing copy must keep that distinction visible.
    for prohibited_claim in ("Telegram", "email", "SMS", "web push"):
        assert prohibited_claim in inbox or prohibited_claim in automation
    assert 'botCompanionPage("/inbox"' not in PORTAL
    assert 'botCompanionPage("/automation"' not in PORTAL


def test_notification_native_hydration_is_not_a_generic_bridge_projection() -> None:
    for helper in (
        "isNativeNotificationPath",
        "notificationBoundaryIsSafe",
        "hydrateInbox",
        "hydrateNotificationAutomation",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    native_path = _function_source(INTEGRATION, "isNativeNotificationPath")
    for path in ('"/inbox"', '"/automation"'):
        assert path in native_path

    # The native signed API is the only source for both private pages.  No
    # browser scheduler/polling is needed to materialize a record.
    for request in (
        'api("/inbox/summary")',
        'api(inboxItemsPath(filter, offset))',
        'api("/inbox/policy")',
    ):
        assert request in INTEGRATION
    assert 'currentPath === "/inbox") await hydrateInbox()' in INTEGRATION
    assert 'currentPath === "/automation") await hydrateNotificationAutomation()' in INTEGRATION
    assert "else if (isNativeNotificationPath(currentPath))" in INTEGRATION

    # A linked Telegram account must not cause the generic bridge hydrator to
    # overwrite owner-scoped Inbox records.
    canonical_gate = INTEGRATION[INTEGRATION.index("if (bridgeAvailable &&") :]
    canonical_gate = canonical_gate[:1_200]
    assert "!isNativeNotificationPath(currentPath)" in canonical_gate


def test_notification_inbox_list_is_paginated_and_state_only() -> None:
    # Inbox deliberately has no title/body/payload search surface. Its only
    # customer filter is a state that the API rechecks inside signed owner
    # scope, while old in-app records remain reachable through pagination.
    for helper in (
        "inboxFilterPayload",
        "inboxListOffset",
        "inboxItemsPath",
        "inboxListingProjection",
    ):
        assert f"function {helper}" in INTEGRATION
    for contract in (
        'const INBOX_LIST_LIMIT = 50',
        'const INBOX_MAX_LIST_OFFSET = 10000',
        'const INBOX_FILTER_STATES = new Set(["all", "unread", "read", "dismissed"])',
        'state: inboxFilterPayload(filter).state',
        'limit: String(INBOX_LIST_LIMIT)',
        'offset: String(inboxListOffset(offset))',
        '"inbox-page": Boolean(account && notificationCenterEnabled)',
        'notificationInboxListing: inboxListingProjection({ state: "all" }, 0, {}, 0)',
        'if (action === "inbox-filter" || action === "inbox-filter-clear")',
        'if (action === "inbox-page")',
    ):
        assert contract in INTEGRATION
    assert "notificationInboxListing" in PORTAL
    assert "data-portal-action=\"inbox-filter\"" in PORTAL
    assert "data-portal-no-transient" in _function_source(PORTAL, "renderNotificationItems")
    assert 'renderMemoryPagination(listing, "bản ghi Inbox", "inbox-page"' in PORTAL
    assert 'data-inbox-offset' in PORTAL

    # The listing must stay inside the native signed Web boundary. No old
    # Inbox page/filter is stored locally or repurposed as Bot/finance data.
    listing = _function_source(INTEGRATION, "hydrateInbox")
    for forbidden in ("localStorage", "sessionStorage", "bridgeAvailable", "PayOS", "/payments", "/jobs", "wallet", "telegram", "provider"):
        assert forbidden.lower() not in listing.lower()


def test_notification_boundary_validator_fails_closed_for_every_external_effect() -> None:
    verifier = _function_source(INTEGRATION, "notificationBoundaryIsSafe")
    for predicate in (
        'boundary.execution === "web_native_in_app_record_materialization_and_urgency_maintenance_only"',
        'boundary.data_origin === "signed_web_records_and_authenticated_notification_scheduler_only"',
        "boundary.notification_center_enabled === true",
        'typeof boundary.notification_automation_enabled === "boolean"',
        'typeof boundary.in_app_record_created === "boolean"',
        'typeof boundary.in_app_urgency_maintained === "boolean"',
        "Number.isInteger(boundary.urgency_escalation_count)",
        "boundary.bot_called === false",
        "boundary.provider_called === false",
        "boundary.wallet_mutated === false",
        "boundary.payment_mutated === false",
        "boundary.payment_processed === false",
        "boundary.customer_reply_sent === false",
        "boundary.external_notification_sent === false",
        "boundary.telegram_sent === false",
        "boundary.email_sent === false",
        "boundary.sms_sent === false",
        "boundary.web_push_sent === false",
        "boundary.job_retried === false",
        "boundary.asset_delivery_changed === false",
        "boundary.role_changed === false",
        "boundary.secret_changed === false",
        "boundary.deployment_changed === false",
        "boundary.self_modifying_code === false",
        "boundary.dangerous_action_executed === false",
    ):
        assert predicate in verifier

    # Hydration must reject a malformed or unsafe response rather than render
    # it as a successful Inbox update.
    assert ".every(notificationBoundaryIsSafe)" in INTEGRATION
    assert "notificationBoundaryIsSafe(result.data)" in INTEGRATION

    # Keep the frontend validator coupled to the server's explicit boundary,
    # but do not allow it to infer delivery from a record existing.
    for predicate in (
        '"execution": "web_native_in_app_record_materialization_and_urgency_maintenance_only"',
        '"data_origin": "signed_web_records_and_authenticated_notification_scheduler_only"',
        '"in_app_urgency_maintained": False',
        '"urgency_escalation_count": 0',
        '"external_notification_sent": False',
        '"telegram_sent": False',
        '"email_sent": False',
        '"sms_sent": False',
        '"web_push_sent": False',
    ):
        assert predicate in NOTIFICATIONS


def test_inbox_mutations_are_owner_scoped_records_not_delivery_actions() -> None:
    for action in ("inbox-item-read", "inbox-item-dismiss"):
        assert action in PORTAL
        assert f'action === "{action}"' in INTEGRATION

    action_start = INTEGRATION.index('if (action === "inbox-item-read" ||')
    action_end = INTEGRATION.index("if (action === \"asset-vault-upload\")", action_start)
    actions = INTEGRATION[action_start:action_end]
    for requirement in (
        '"/inbox/items/"',
        '"/read"',
        '"/dismiss"',
        "expected_revision",
        "confirm: true",
        "idempotency_key",
    ):
        assert requirement in actions
    for forbidden in ("bridgeAvailable", "PayOS", "/payments", "/jobs", "wallet", "telegram", "provider", "showNotification"):
        assert forbidden.lower() not in actions.lower()

    # Public item records intentionally contain no reminder content. The card
    # can point back to the signed reminder surface but must not invent a
    # payload, title, body or external delivery receipt.
    inbox_renderer = _function_source(PORTAL, "renderInbox")
    for forbidden in ("item.title", "item.body", "item.payload", "showNotification", "localStorage", "sessionStorage"):
        assert forbidden not in inbox_renderer
    assert "in_app_record_only" in inbox_renderer


def test_service_worker_never_caches_notification_records_or_tick_routes() -> None:
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in SERVICE_WORKER
    assert "const BUILD_ID = workerBuildId();" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    for private_prefix in (
        '"/" + "api/v1/inbox"',
        '"/" + "internal/v1/notifications"',
        '"/inbox"',
        '"/automation"',
        '"/" + "api/v1/campaigns"',
        '"/campaigns"',
        '"/calendar"',
        '"/approvals"',
    ):
        assert private_prefix in SERVICE_WORKER
        assert private_prefix not in shell
    assert "private `/inbox/*` and private `/automation/*` routes" in SERVICE_WORKER
    assert "isPrivatePath" in SERVICE_WORKER
    assert "showNotification(" not in SERVICE_WORKER


def test_notification_hydration_rejects_stale_session_route_list_and_automation_responses() -> None:
    """The Inbox list and Automation summary are private signed reads.

    These routes have no separate detail endpoint: Inbox obtains a bounded
    list plus summary/policy, while Automation obtains summary/policy only.
    Both must therefore reject a response after logout, account switch,
    navigation or a newer read of the same route.
    """

    for declaration in (
        "let notificationSessionEpoch = 0;",
        "let notificationInboxHydrationEpoch = 0;",
        "let notificationAutomationHydrationEpoch = 0;",
    ):
        assert declaration in INTEGRATION

    bootstrap = _between(INTEGRATION, "const currentAdminErpNavigationEpoch", "    merge({")
    for invalidation in (
        "++notificationSessionEpoch;",
        "++notificationInboxHydrationEpoch;",
        "++notificationAutomationHydrationEpoch;",
    ):
        assert invalidation in bootstrap

    guard = _function_source(INTEGRATION, "notificationRequestIsCurrent")
    for invariant in (
        "requestEpoch === currentEpoch",
        "sessionEpoch === notificationSessionEpoch",
        "currentPortalPath() === expectedPath",
        "base().session && base().session.authenticated === true",
    ):
        assert invariant in guard

    inbox = _function_source(INTEGRATION, "hydrateInbox")
    assert "const requestEpoch = ++notificationInboxHydrationEpoch;" in inbox
    assert "const sessionEpoch = notificationSessionEpoch;" in inbox
    assert "const expectedPath = currentPortalPath();" in inbox
    assert 'if (expectedPath !== "/inbox") return { stale: true };' in inbox
    # Check success and failure paths: an old rejected request must not clear
    # the freshly loaded account's Inbox either.
    assert inbox.count("notificationRequestIsCurrent(") >= 2

    automation = _function_source(INTEGRATION, "hydrateNotificationAutomation")
    assert "const requestEpoch = ++notificationAutomationHydrationEpoch;" in automation
    assert "const sessionEpoch = notificationSessionEpoch;" in automation
    assert "const expectedPath = currentPortalPath();" in automation
    assert 'if (expectedPath !== "/automation") return { stale: true };' in automation
    assert automation.count("notificationRequestIsCurrent(") >= 2


def test_notification_bootstrap_projection_keeps_signed_inbox_state_without_widening_data() -> None:
    """A later Portal render must not discard an already validated Inbox read.

    Integration owns the signed API/boundary validation.  The presentation
    normalizer is a second, narrow allow-list: it must retain enough opaque
    metadata for owner-scoped navigation and record mutations, but never turn
    Inbox into a reminder-content cache or an external delivery surface.
    """

    projection = _between(PORTAL, "const NOTIFICATION_BOOTSTRAP_ITEM_STATES", "function normalizeBootstrap")
    for contract in (
        'const NOTIFICATION_BOOTSTRAP_ITEM_STATES = new Set(["unread", "read", "dismissed"])',
        'const NOTIFICATION_BOOTSTRAP_SEVERITIES = new Set(["warning", "urgent"])',
        'const NOTIFICATION_BOOTSTRAP_FILTER_STATES = new Set(["all", "unread", "read", "dismissed"])',
        'const NOTIFICATION_BOOTSTRAP_LIMIT = 50',
        'const NOTIFICATION_BOOTSTRAP_MAX_OFFSET = 10000',
        'reminder_due: "memory_reminder"',
        'workboard_schedule_due: "workboard_schedule_intent"',
        'campaign_schedule_due: "campaign_schedule_intent"',
        'source.delivery !== "in_app_record_only"',
        "function normalizeNotificationSummary",
        "function normalizeNotificationPolicy",
        "function normalizeNotificationItems",
        "function normalizeNotificationInboxFilter",
        "function normalizeNotificationInboxListing",
        "returned: Math.min(safeLimit, Array.isArray(items) ? items.length : 0)",
        "previous_offset: safeOffset >= safeLimit ? safeOffset - safeLimit : null",
    ):
        assert contract in projection

    items = _function_source(PORTAL, "normalizeNotificationItems")
    for allowed_field in (
        "id,",
        "kind,",
        "source_kind: sourceKind",
        "source_id: sourceId",
        "occurrence_at: occurrenceAt",
        "severity,",
        "state,",
        "revision,",
        'delivery: "in_app_record_only"',
    ):
        assert allowed_field in items
    # No source content, opaque scheduler receipt, arbitrary link or account
    # identity is allowed through the second browser-side boundary.
    for forbidden_field in ("title:", "body:", "payload:", "target_route:", "external_url:", "account_id:", "updated_at:", "read_at:", "dismissed_at:"):
        assert forbidden_field not in items

    bootstrap = _function_source(PORTAL, "normalizeBootstrap")
    for field in (
        "notificationSummary,",
        "notificationPolicy,",
        "notificationItems,",
        "notificationInboxFilter,",
        "notificationInboxListing,",
        "notificationReadState: NOTIFICATION_BOOTSTRAP_READ_STATES.has",
    ):
        assert field in bootstrap
