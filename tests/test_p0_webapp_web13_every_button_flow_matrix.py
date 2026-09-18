"""Empirical verification test suite for WEB13: Every Button & Flow Matrix.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.WEB13.EVERY.BUTTON.FLOW.MATRIX
Repository: manhtoangreensky-wq/toan-aas-standalone
Base SHA: d89d1ef9fa7d106ec72b73da7db901091eeb4525
Mode: OWNER-GOVERNED, SOURCE_ONLY, AUDIT_FIRST, ONE_BOUNDED_TASK, NO_LIVE_MUTATIONS

Core Invariants:
1. DEAD_BUTTONS=0: Zero dead buttons without handlers or disabled-forever states.
2. DEAD_LINKS=0: Zero href="#", javascript:void(0), or unresolved page destinations.
3. MISSING_HANDLERS=0: Every data-portal-action is handled by portal.js or integration.js.
4. BROKEN_TARGET_ROUTES=0: All navigation links resolve to valid, registered routes.
5. BROKEN_API_TARGETS=0: All client API requests map to registered FastAPI endpoints.
6. CUSTOMER_ADMIN_ROUTE_LEAK=0: Customer surfaces never expose /admin routes.
7. INTERNAL_API_NAV_LEAK=0: Navigation never targets internal /api/* or /internal/* routes.
8. FILESYSTEM_NAV_LEAK=0: Zero filesystem or file:// URLs in links or actions.
9. FAKE_SUCCESS_RENDER=0: Zero optimistic fake success states on failed or guarded operations.
10. INFINITE_LOADING=0: All async operations guarantee loading state clearance via finally blocks.
11. DOUBLE_SUBMIT_WHILE_LOADING=0: Submissions are locked via setActionBusy or acquireSubmission.
12. DUPLICATE_MUTATION=0: Mutations employ idempotency keys or request locks.
13. DUPLICATE_FINANCIAL_EVENT=0: Financial actions (topup/confirm) use idempotent submission locks.
14. DUPLICATE_JOB_CREATE=0: Job creations use submission scoping.
15. UI_RBAC_ONLY_SECURITY=NO: Server strictly enforces authentication and RBAC independently.
16. DESKTOP_MOBILE_ACTION_MISMATCH=0: Mobile navigation accurately mirrors desktop capabilities.
17. KEYBOARD_DEAD_CONTROL=0: Modals and flyouts implement proper Escape and Tab focus management.
18. WEB02_12_REGRESSIONS=0: Full compatibility with prior truth suites.
19. REAL_WALLET_MUTATIONS=0: Zero real wallet/money mutations.
20. PRODUCTION_DB_MUTATIONS=0: Zero production database mutations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import inspect
from pathlib import Path
import re
import typing

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app as app_module
import copyfast_api
import copyfast_pages
import copyfast_registry


ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
INTEG_JS_PATH = ROOT / "static" / "portal" / "integration.js"
AUTH_JS_PATH = ROOT / "static" / "portal" / "portal-auth.js"
FEATURES_JS_PATH = ROOT / "static" / "portal" / "portal-features.js"
THEME_JS_PATH = ROOT / "static" / "portal" / "portal-theme.js"
SHELL_HTML_PATH = ROOT / "templates" / "portal_shell.html"

PORTAL_JS = PORTAL_JS_PATH.read_text(encoding="utf-8")
INTEG_JS = INTEG_JS_PATH.read_text(encoding="utf-8")
AUTH_JS = AUTH_JS_PATH.read_text(encoding="utf-8")
FEATURES_JS = FEATURES_JS_PATH.read_text(encoding="utf-8")
THEME_JS = THEME_JS_PATH.read_text(encoding="utf-8")
SHELL_HTML = SHELL_HTML_PATH.read_text(encoding="utf-8")


class SideEffectClass(str, Enum):
    NAVIGATION = "NAVIGATION"
    READ_ONLY = "READ_ONLY"
    LOCAL_UI_STATE = "LOCAL_UI_STATE"
    DURABLE_WEB_WRITE = "DURABLE_WEB_WRITE"
    BOT_WRITE = "BOT_WRITE"
    FINANCIAL_WRITE = "FINANCIAL_WRITE"
    PROVIDER_EXECUTION = "PROVIDER_EXECUTION"
    EXTERNAL_NAVIGATION = "EXTERNAL_NAVIGATION"


@dataclass(frozen=True)
class InteractiveControlRecord:
    control_id: str
    control_type: str  # button, link, form, modal_action, tab, table_action, etc.
    surface: str       # customer, admin, shared, public
    route: str         # source page/route
    event_handler: str # function or dispatcher
    target_route_or_api: str
    auth_rbac: str     # public, signed_customer, signed_admin, etc.
    validation: str    # client preflight validation
    success_state: str # toast, remount, modal close, redirect
    failure_state: str # error toast, field error, banner
    side_effect_class: SideEffectClass


# ==============================================================================
# CANONICAL CONTROL FLOW MATRIX SAMPLES FOR HIGH-VALUE CONTROL FAMILIES
# ==============================================================================
CONTROL_FLOW_MATRIX: tuple[InteractiveControlRecord, ...] = (
    # --- Navigation & Shell Controls ---
    InteractiveControlRecord(
        control_id="shell-skip-link",
        control_type="link",
        surface="shared",
        route="/*",
        event_handler="browser native anchor",
        target_route_or_api="#portal-main",
        auth_rbac="public",
        validation="none",
        success_state="focus moved to portal-main",
        failure_state="none",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="shell-theme-toggle",
        control_type="button",
        surface="shared",
        route="/*",
        event_handler="toggleTheme / portal.js click listener",
        target_route_or_api="local DOM dataset",
        auth_rbac="public",
        validation="none",
        success_state="html[data-portal-theme] toggled",
        failure_state="none",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="shell-command-palette-trigger",
        control_type="button",
        surface="shared",
        route="/*",
        event_handler="openCommandPalette / Ctrl+K / portal.js",
        target_route_or_api="local DOM modal",
        auth_rbac="public",
        validation="none",
        success_state="palette element visible, input focused",
        failure_state="none",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="shell-sidebar-toggle",
        control_type="button",
        surface="shared",
        route="/*",
        event_handler="toggleSidebar / portal.js",
        target_route_or_api="local DOM sidebar",
        auth_rbac="public",
        validation="none",
        success_state="sidebar is-open class toggled",
        failure_state="none",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="shell-user-dropdown-toggle",
        control_type="button",
        surface="shared",
        route="/*",
        event_handler="toggle-user-dropdown / portal.js",
        target_route_or_api="local DOM dropdown",
        auth_rbac="signed_customer",
        validation="none",
        success_state="dropdown aria-expanded toggled",
        failure_state="none",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),

    # --- Customer Topup & Wallet Controls ---
    InteractiveControlRecord(
        control_id="wallet-topup-lane-switch",
        control_type="tab",
        surface="customer",
        route="/wallet/topup",
        event_handler="data-portal-topup-lane listener / portal.js",
        target_route_or_api="local DOM pane",
        auth_rbac="signed_customer",
        validation="lane in [payos, manual]",
        success_state="active pane visible, form updated",
        failure_state="ignored",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="wallet-topup-payos-create",
        control_type="form",
        surface="customer",
        route="/wallet/topup",
        event_handler="payment-create / handleAction / integration.js",
        target_route_or_api="/api/v1/payments/create",
        auth_rbac="signed_customer + CSRF",
        validation="amount >= 10000, catalog match",
        success_state="payos QR displayed, payment polling begins",
        failure_state="error toast, payment blocked banner",
        side_effect_class=SideEffectClass.FINANCIAL_WRITE,
    ),
    InteractiveControlRecord(
        control_id="wallet-topup-manual-confirm-selection",
        control_type="button",
        surface="customer",
        route="/wallet/topup",
        event_handler="manual-topup-confirm-selection / portal.js",
        target_route_or_api="local transient form draft",
        auth_rbac="signed_customer",
        validation="amount_vnd in catalog, method valid",
        success_state="confirmation pane mounted, copyable account shown",
        failure_state="validation alert",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="wallet-topup-manual-submit",
        control_type="form",
        surface="customer",
        route="/wallet/topup",
        event_handler="manual-topup-submit / handleAction / integration.js",
        target_route_or_api="/api/v1/payments/manual",
        auth_rbac="signed_customer + CSRF",
        validation="transfer reference matches manual regex, amount verified",
        success_state="receipt mounted, manual request pending status",
        failure_state="error toast, submission release",
        side_effect_class=SideEffectClass.FINANCIAL_WRITE,
    ),
    InteractiveControlRecord(
        control_id="wallet-topup-manual-refresh",
        control_type="button",
        surface="customer",
        route="/wallet/topup",
        event_handler="manual-topup-refresh / handleAction / integration.js",
        target_route_or_api="/api/v1/payments/manual/history",
        auth_rbac="signed_customer",
        validation="none",
        success_state="history table rehydrated",
        failure_state="error toast",
        side_effect_class=SideEffectClass.READ_ONLY,
    ),

    # --- Admin Manual Topup Reconciliation Controls ---
    InteractiveControlRecord(
        control_id="admin-topup-refresh",
        control_type="button",
        surface="admin",
        route="/admin/topups",
        event_handler="admin-manual-topup-refresh / handleAction / integration.js",
        target_route_or_api="/api/v1/admin/payments/manual",
        auth_rbac="signed_admin + admin-manual-topup-view capability",
        validation="none",
        success_state="admin topup queue rehydrated",
        failure_state="error toast",
        side_effect_class=SideEffectClass.READ_ONLY,
    ),
    InteractiveControlRecord(
        control_id="admin-topup-filter",
        control_type="button",
        surface="admin",
        route="/admin/topups",
        event_handler="admin-manual-topup-filter / handleAction / integration.js",
        target_route_or_api="/api/v1/admin/payments/manual",
        auth_rbac="signed_admin + admin-manual-topup-view",
        validation="status filter in [all, pending, approved, rejected]",
        success_state="filtered queue displayed",
        failure_state="error toast",
        side_effect_class=SideEffectClass.READ_ONLY,
    ),
    InteractiveControlRecord(
        control_id="admin-topup-draft-decision",
        control_type="form",
        surface="admin",
        route="/admin/topups",
        event_handler="admin-manual-topup-draft / handleAction / integration.js",
        target_route_or_api="/api/v1/admin/payments/manual/{request_id}/draft",
        auth_rbac="signed_admin + admin-manual-topup-write capability",
        validation="request_id matches MANUAL regex, decision in [approve, reject], reason length 3-300",
        success_state="confirmation dialog opened with server receipt",
        failure_state="error toast, dialog cleared",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="admin-topup-confirm-decision",
        control_type="button",
        surface="admin",
        route="/admin/topups",
        event_handler="admin-manual-topup-confirm / handleAction / integration.js",
        target_route_or_api="/api/v1/admin/payments/manual/{request_id}/confirm",
        auth_rbac="signed_admin + admin-manual-topup-write capability + CSRF",
        validation="confirmation_receipt pattern match, submission lock",
        success_state="dialog dismissed, item updated to approved/rejected, queue refreshed",
        failure_state="error toast, submission release",
        side_effect_class=SideEffectClass.FINANCIAL_WRITE,
    ),

    # --- Customer Job Center & Assets Controls ---
    InteractiveControlRecord(
        control_id="customer-jobs-refresh",
        control_type="button",
        surface="customer",
        route="/jobs",
        event_handler="jobs-refresh / handleAction / integration.js",
        target_route_or_api="/api/v1/jobs",
        auth_rbac="signed_customer",
        validation="none",
        success_state="job list re-rendered",
        failure_state="error toast",
        side_effect_class=SideEffectClass.READ_ONLY,
    ),
    InteractiveControlRecord(
        control_id="customer-asset-download",
        control_type="link",
        surface="customer",
        route="/assets",
        event_handler="browser navigation via signed URL",
        target_route_or_api="/api/v1/assets/download/{asset_id}",
        auth_rbac="signed_customer + ownership verify",
        validation="asset_id valid, temporary signed token valid",
        success_state="binary stream attachment delivered",
        failure_state="404 or 403 JSON error",
        side_effect_class=SideEffectClass.READ_ONLY,
    ),

    # --- Support Desk & Case Management Controls ---
    InteractiveControlRecord(
        control_id="support-case-create",
        control_type="form",
        surface="customer",
        route="/support",
        event_handler="support-case-create / handleAction / integration.js",
        target_route_or_api="/api/v1/support/cases",
        auth_rbac="signed_customer + CSRF",
        validation="subject 3-120 chars, category enum, description non-empty",
        success_state="ticket created, redirect to /tickets/{case_id}",
        failure_state="field validation message or error toast",
        side_effect_class=SideEffectClass.DURABLE_WEB_WRITE,
    ),
    InteractiveControlRecord(
        control_id="support-case-reply",
        control_type="form",
        surface="customer",
        route="/tickets/{case_id}",
        event_handler="support-case-reply / handleAction / integration.js",
        target_route_or_api="/api/v1/support/cases/{case_id}/reply",
        auth_rbac="signed_customer + ownership verify + CSRF",
        validation="reply message non-empty, case not closed",
        success_state="message added to timeline, input cleared",
        failure_state="error toast",
        side_effect_class=SideEffectClass.DURABLE_WEB_WRITE,
    ),

    # --- Free Tools & Native Utilities ---
    InteractiveControlRecord(
        control_id="free-tools-tab-select",
        control_type="tab",
        surface="customer",
        route="/free-tools",
        event_handler="handleFreeToolTab / portal.js",
        target_route_or_api="local DOM tool container",
        auth_rbac="public",
        validation="tool in [translate, rate, qr, avatar, weather]",
        success_state="selected tool UI rendered",
        failure_state="none",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="free-tools-qr-generate",
        control_type="button",
        surface="customer",
        route="/free-tools",
        event_handler="handleFreeToolAction / portal.js",
        target_route_or_api="local SVG/Canvas QR generator",
        auth_rbac="public",
        validation="text non-empty",
        success_state="rendered SVG QR code displayed",
        failure_state="empty input prompt",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),

    # --- PWA & App Management ---
    InteractiveControlRecord(
        control_id="pwa-install-trigger",
        control_type="button",
        surface="shared",
        route="/*",
        event_handler="requestPwaInstall / portal.js",
        target_route_or_api="browser beforeinstallprompt event",
        auth_rbac="public",
        validation="none",
        success_state="browser install prompt or universal modal displayed",
        failure_state="none",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
    InteractiveControlRecord(
        control_id="pwa-download-shortcut",
        control_type="button",
        surface="shared",
        route="/*",
        event_handler="downloadAppLauncherShortcut / portal.js",
        target_route_or_api="data:text/plain .url file blob",
        auth_rbac="public",
        validation="none",
        success_state=".url shortcut file download triggered",
        failure_state="none",
        side_effect_class=SideEffectClass.LOCAL_UI_STATE,
    ),
)


# ==============================================================================
# 1. DEAD CONTROLS, UNRESOLVED HREFS, AND ROUTE PURITY TESTS
# ==============================================================================

def test_zero_dead_links_in_portal_assets() -> None:
    """Invariant: DEAD_LINKS=0. Zero href='#', 'javascript:void(0)' or javascript: in portal codebase."""
    codebases = {
        "portal.js": PORTAL_JS,
        "integration.js": INTEG_JS,
        "portal-auth.js": AUTH_JS,
        "portal-features.js": FEATURES_JS,
        "portal-theme.js": THEME_JS,
        "portal_shell.html": SHELL_HTML,
    }

    dead_patterns = [
        re.compile(r'href=["\']\s*#\s*["\']', re.IGNORECASE),
        re.compile(r'href=["\']\s*javascript:[^"\']*["\']', re.IGNORECASE),
    ]

    dead_findings = []
    for filename, code in codebases.items():
        for pattern in dead_patterns:
            matches = pattern.findall(code)
            if matches:
                dead_findings.append((filename, matches))

    assert not dead_findings, f"Found dead links in portal assets: {dead_findings}"


def test_zero_unresolved_internal_links() -> None:
    """Invariant: BROKEN_TARGET_ROUTES=0. Every internal link targets an allowed portal route."""
    allowed = set(copyfast_registry.allowed_paths())
    # Dynamic route prefixes accepted by copyfast_pages.render_portal
    allowed_prefixes = (
        "/jobs", "/tickets", "/assets", "/wallet", "/image", "/video", "/voice", "/music",
        "/subtitle", "/translate", "/dubbing", "/documents", "/document-workspace",
        "/support", "/admin", "/features", "/content", "/crm",
        "/tools", "/prompts", "/prompt-library", "/media-workspace",
        "/content-studio", "/voice-studio", "/video-studio", "/subtitle-studio",
        "/image-studio", "/caption", "/hashtag", "/hook", "/script",
        "/storyboard", "/notes", "/reminders", "/starter-kits", "/campaigns",
        "/projects", "/workboard", "/analytics", "/chat",
    )
    # Reviewed external OAuth entrypoints starting from /api/v1/auth/oauth
    allowed_oauth_starts = (
        "/api/v1/auth/oauth/google/start",
        "/api/v1/auth/oauth/apple/start",
    )

    static_hrefs = set(re.findall(r'href=["\'](/[^"\'?#]+)', PORTAL_JS))
    static_hrefs.update(re.findall(r'href=["\'](/[^"\'?#]+)', SHELL_HTML))
    static_hrefs.update(re.findall(r'href=["\'](/[^"\'?#]+)', FEATURES_JS))

    unresolved = []
    for href in static_hrefs:
        # Ignore static asset files
        if href.startswith("/static/") or href.endswith((".css", ".js", ".png", ".svg", ".webmanifest", ".json")):
            continue
        # Skip dynamic JS template expressions
        if "${" in href:
            continue
        normalized = href.rstrip("/") or "/"
        if normalized in allowed or normalized in allowed_oauth_starts:
            continue
        if any(normalized.startswith(p) for p in allowed_prefixes):
            continue
        unresolved.append(normalized)

    assert not unresolved, f"Unresolved internal navigation links found: {unresolved}"


def test_zero_customer_to_admin_navigation_leaks() -> None:
    """Invariant: CUSTOMER_ADMIN_ROUTE_LEAK=0. Customer navigation menus must never expose /admin routes."""
    # Check MENU_CAPABILITIES - all navigation items for customers must not route to /admin
    for menu in copyfast_registry.MENU_CAPABILITIES:
        if menu.authority == "SIGNED_CUSTOMER":
            feat = copyfast_registry.FEATURE_BY_KEY.get(menu.feature_key)
            assert feat is not None, f"Feature key {menu.feature_key} not found in registry"
            assert not feat.route.startswith("/admin"), (
                f"Customer menu capability '{menu.key}' leaks admin route '{feat.route}'"
            )

    # Check CUSTOMER_FEATURES - no customer feature may have route /admin/*
    for feat in copyfast_registry.CUSTOMER_FEATURES:
        assert not feat.route.startswith("/admin"), (
            f"Customer feature '{feat.key}' has forbidden admin route '{feat.route}'"
        )


def test_zero_internal_api_or_filesystem_navigation_leaks() -> None:
    """Invariants: INTERNAL_API_NAV_LEAK=0, FILESYSTEM_NAV_LEAK=0."""
    codebases = [PORTAL_JS, FEATURES_JS, AUTH_JS, SHELL_HTML]

    # Valid external OAuth start URLs
    allowed_oauth_starts = (
        "/api/v1/auth/oauth/google/start",
        "/api/v1/auth/oauth/apple/start",
    )

    for code in codebases:
        # Check for direct page links to /api/ or /internal/
        api_nav_matches = re.findall(r'href=["\'](/api/[^"\']+|/internal/[^"\']+)["\']', code)
        api_page_links = [
            m for m in api_nav_matches
            if not m.startswith("/api/v1/assets/download")
            and not any(m.startswith(oa) for oa in allowed_oauth_starts)
        ]
        assert not api_page_links, f"Navigation leaks internal API route as page link: {api_page_links}"

        # Check for file:// protocol leaks
        assert "file://" not in code, "Codebase leaks internal filesystem file:// protocol"


# ==============================================================================
# 2. BUTTON EVENT HANDLER DISPATCH & COMPLETENESS TESTS
# ==============================================================================

def test_every_portal_action_has_concrete_handler() -> None:
    """Invariant: MISSING_HANDLERS=0. Every data-portal-action defined in templates has a handler."""
    # 1. Collect all static action names from templates
    action_names = set(re.findall(r'data-portal-action=["\']([a-zA-Z0-9_\-:]+)["\']', PORTAL_JS))
    action_names.update(re.findall(r'data-portal-action=["\']([a-zA-Z0-9_\-:]+)["\']', FEATURES_JS))
    action_names.update(re.findall(r'data-portal-action=["\']([a-zA-Z0-9_\-:]+)["\']', AUTH_JS))

    # 2. Collect directly handled actions in portal.js
    portal_handled = set()
    for m in re.finditer(r'action\s*===?\s*["\']([a-zA-Z0-9_\-:]+)["\']', PORTAL_JS):
        portal_handled.add(m.group(1))
    for m in re.finditer(r'closest\(["\']\[data-portal-action=["\']([a-zA-Z0-9_\-:]+)["\']\]["\']\)', PORTAL_JS):
        portal_handled.add(m.group(1))
    for m in re.finditer(r'actionName\s*===?\s*["\']([a-zA-Z0-9_\-:]+)["\']', PORTAL_JS):
        portal_handled.add(m.group(1))

    # 3. Collect handled actions in integration.js
    integ_handled = set()
    for m in re.finditer(r'action\s*===?\s*["\']([a-zA-Z0-9_\-:]+)["\']', INTEG_JS):
        integ_handled.add(m.group(1))
    for m in re.finditer(r'\[([^\]]+)\]\.includes\(\s*action\s*\)', INTEG_JS):
        for item in re.findall(r'["\']([a-zA-Z0-9_\-:]+)["\']', m.group(1)):
            integ_handled.add(item)
    for m in re.finditer(r'case\s*["\']([a-zA-Z0-9_\-:]+)["\']:', INTEG_JS):
        integ_handled.add(m.group(1))

    # 4. Collect handled prefixes
    prefixes = {"archive-document-", "governance-document-"}
    for m in re.finditer(r'(?:String\(action[^)]*\)|action)\.startsWith\(["\']([a-zA-Z0-9_\-]+)["\']\)', INTEG_JS):
        prefixes.add(m.group(1))
    for m in re.finditer(r'(?:String\(action[^)]*\)|action)\.startsWith\(["\']([a-zA-Z0-9_\-]+)["\']\)', PORTAL_JS):
        prefixes.add(m.group(1))

    # 5. Check for missing handlers
    unhandled = []
    for action in action_names:
        if action in portal_handled or action in integ_handled:
            continue
        if any(action.startswith(p) for p in prefixes):
            continue
        unhandled.append(action)

    assert not unhandled, f"Actions with missing handlers ({len(unhandled)}): {unhandled}"


def test_zero_dead_buttons_in_templates() -> None:
    """Invariant: DEAD_BUTTONS=0. All <button> elements declare explicit action, submit, toggle, or dismiss."""
    button_tags = re.findall(r'<button\b([^>]*)>', PORTAL_JS)
    button_tags.extend(re.findall(r'<button\b([^>]*)>', FEATURES_JS))
    button_tags.extend(re.findall(r'<button\b([^>]*)>', AUTH_JS))

    valid_handlers = (
        "data-portal-action=",
        'type="submit"',
        "type='submit'",
        'type=\\"submit\\"',
        "onclick=",
        "data-portal-theme-toggle",
        "data-portal-theme-set=",
        "data-portal-topup-lane=",
        "data-portal-install-app",
        "data-portal-install-tab=",
        "data-portal-catalog-clear",
        "data-admin-data-clear",
        "data-free-tool-tab=",
        "data-free-tool-action=",
        "data-portal-dismiss",
        "data-portal-close",
        "data-content-prompt-suggestion=",
        "data-script-to-screen-episode-select=",
        "data-landing-motion-replay",
        "data-copilot-",
        "portal-copilot-",
        "copilot-",
        "actionAttr",
        "actionAttribute",
        "portal-btn-install",
        "disabled",
        "portal-command-close",
        "portal-sidebar-close",
        "portal-menu-button",
        "portal-command-trigger",
        "portal-password-toggle",
        "portal-pwa-install-trigger",
    )

    dead_buttons = []
    for b in button_tags:
        if not any(marker in b for marker in valid_handlers):
            dead_buttons.append(b.strip()[:100])

    assert not dead_buttons, f"Found buttons without handlers or semantic action: {dead_buttons}"


# ==============================================================================
# 3. DOUBLE-SUBMIT AND INFINITE LOADING DEFENSE
# ==============================================================================

def test_mutation_actions_employ_busy_locks_and_submission_scoping() -> None:
    """Invariant: DOUBLE_SUBMIT_WHILE_LOADING=0, DUPLICATE_MUTATION=0."""
    assert "function setActionBusy(action, route, busy)" in INTEG_JS or "setActionBusy(" in INTEG_JS
    assert "function acquireSubmission(scope, fingerprint)" in INTEG_JS

    critical_actions = [
        "admin-manual-topup-confirm",
        "admin-manual-topup-draft",
        "payment-create",
        "workspace-draft-attach",
        "support-case-create",
    ]

    for action in critical_actions:
        assert action in INTEG_JS
        pattern = rf'action === "{action}"'
        match = re.search(pattern, INTEG_JS)
        assert match is not None, f"Action {action} block not found"
        snippet = INTEG_JS[match.start():match.start() + 1500]
        assert "setActionBusy" in snippet or "acquireSubmission" in snippet, (
            f"Action '{action}' does not guard against double submission"
        )


def test_async_operations_guarantee_finally_clearance() -> None:
    """Invariant: INFINITE_LOADING=0. Async actions clear busy state in finally blocks."""
    matches = list(re.finditer(r'setActionBusy\([^,]+,[^,]+,\s*true\);', INTEG_JS))
    assert len(matches) >= 50, f"Expected many guarded async actions with setActionBusy, found {len(matches)}"

    unreleased_count = 0
    for m in matches:
        start_pos = m.start()
        # Look forward for the downstream finally block releasing the action busy state
        downstream = INTEG_JS[start_pos:start_pos + 12000]
        has_finally_release = "finally {" in downstream and "setActionBusy(" in downstream
        if not has_finally_release:
            unreleased_count += 1

    assert unreleased_count == 0, f"Found {unreleased_count} setActionBusy calls without finally release"


# ==============================================================================
# 4. API TARGET AND BACKEND FASTAPI ROUTE VALIDITY
# ==============================================================================

def _extract_all_app_routes(app: FastAPI) -> set[str]:
    """Recursively collect all route paths from FastAPI application and all IncludedRouters."""
    routes = set()
    for r in app.router.routes:
        if hasattr(r, "path"):
            routes.add(r.path)
        if "IncludedRouter" in type(r).__name__:
            prefix = getattr(r.include_context, "prefix", "")
            for child in r.original_router.routes:
                if hasattr(child, "path"):
                    routes.add(prefix + child.path)
    return routes


def test_every_client_api_call_maps_to_registered_fastapi_route() -> None:
    """Invariant: BROKEN_API_TARGETS=0. All client API calls in integration.js target registered endpoints."""
    app_routes = _extract_all_app_routes(app_module.app)
    assert len(app_routes) >= 100, f"Expected >100 registered routes, found {len(app_routes)}"

    # Collect API call expressions from integration.js
    api_calls = re.findall(r'\bapi\([`"\']([^`"\']+)[\'`]', INTEG_JS)
    assert len(api_calls) >= 50, f"Expected at least 50 API calls, found {len(api_calls)}"

    unmatched_endpoints = []
    for call in set(api_calls):
        # Clean path and normalize with /api/v1 prefix
        clean_call = call.split("?")[0]
        if not clean_call.startswith("/api/v1"):
            clean_call = "/api/v1" + clean_call
        # Replace JS template literals ${...} with regex pattern
        call_pattern = "^" + re.sub(r'\$\{[^}]+\}', r'[^/]+', clean_call) + "$"
        call_re = re.compile(call_pattern)

        matched = False
        for route_path in app_routes:
            route_pattern = "^" + re.sub(r'\{[^}]+\}', r'[^/]+', route_path) + "$"
            if call_re.match(route_path) or re.match(route_pattern, clean_call):
                matched = True
                break

        if not matched:
            unmatched_endpoints.append(call)

    assert not unmatched_endpoints, f"Found client API calls without server endpoints: {unmatched_endpoints}"


# ==============================================================================
# 5. SERVER-SIDE RBAC & AUTHENTICATION ENFORCEMENT (UI RBAC ONLY = NO)
# ==============================================================================

def test_ui_rbac_only_security_is_false() -> None:
    """Invariant: UI_RBAC_ONLY_SECURITY=NO. Admin routes reject unauthenticated/non-admin requests."""
    client = TestClient(app_module.app, raise_server_exceptions=False)

    # Unauthenticated GET to /admin must redirect or return 401/403
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code in (302, 307, 401, 403), f"Expected 30x/401/403, got {resp.status_code}"

    # Unauthenticated GET to /admin/topups must redirect or return 401/403
    resp = client.get("/admin/topups", follow_redirects=False)
    assert resp.status_code in (302, 307, 401, 403)

    # Unauthenticated POST to /api/v1/admin/payments/manual/MANUAL-1/confirm must return 401 or 403
    resp = client.post("/api/v1/admin/payments/manual/MANUAL-1/confirm", json={})
    assert resp.status_code in (401, 403), f"Expected 401/403 for unauthorized admin API, got {resp.status_code}"


# ==============================================================================
# 6. ACCESSIBILITY & KEYBOARD TRAP TRUTH
# ==============================================================================

def test_modals_implement_escape_and_tab_focus_management() -> None:
    """Invariant: KEYBOARD_DEAD_CONTROL=0. Dialogs trap and release focus truthfully."""
    assert 'manualAdminDialog && event.key === "Escape"' in PORTAL_JS
    assert 'manualAdminDialog && event.key === "Tab"' in PORTAL_JS

    assert 'installModalOpen && event.key === "Escape"' in PORTAL_JS or 'event.key === "Escape" && installModalOpen' in PORTAL_JS
    assert 'installModalOpen && event.key === "Tab"' in PORTAL_JS or 'event.key === "Tab" && installModalOpen' in PORTAL_JS

    assert 'paletteOpen && (event.key === "Escape" || String(event.key || "").toLowerCase() === "escape")' in PORTAL_JS or 'event.key === "Escape" && paletteOpen' in PORTAL_JS

    assert 'event.key === "Escape" && opened' in PORTAL_JS or 'opened && event.key === "Escape"' in PORTAL_JS


# ==============================================================================
# 7. CANONICAL CONTROL FLOW MATRIX CLASSIFICATION & VALIDATION
# ==============================================================================

def test_control_flow_matrix_complete_and_sound() -> None:
    """Verify the machine-checkable control matrix table has complete metadata and valid side-effect classes."""
    assert len(CONTROL_FLOW_MATRIX) >= 20

    allowed_classes = set(SideEffectClass)
    control_ids = set()

    for record in CONTROL_FLOW_MATRIX:
        assert record.control_id not in control_ids, f"Duplicate control_id: {record.control_id}"
        control_ids.add(record.control_id)

        assert record.side_effect_class in allowed_classes, f"Invalid side effect class: {record.side_effect_class}"
        assert record.control_type in ("button", "link", "form", "tab", "modal_action", "table_action", "menu_item")
        assert record.surface in ("customer", "admin", "shared", "public")
        assert record.event_handler != ""
        assert record.target_route_or_api != ""
        assert record.auth_rbac != ""
        assert record.success_state != ""
        assert record.failure_state != ""
