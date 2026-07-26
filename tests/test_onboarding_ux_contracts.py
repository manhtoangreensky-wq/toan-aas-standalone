"""Focused contracts for the optional, signed Telegram onboarding experience."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_onboarding_keeps_workspace_independent_and_never_offers_a_dead_link_action() -> None:
    onboarding = _section(
        PORTAL,
        "function renderOnboarding(page, context)",
        "function authProviderMark(provider)",
    )

    assert "const connectionReady = telegramConnectionReady(context);" in onboarding
    assert "const linkActionEnabled = enabled && connectionReady;" in onboarding
    assert "const linkActionDisabled = linkActionEnabled" in onboarding
    assert "telegramConnectionBlockReason(context)" in onboarding
    assert 'data-portal-action="start-telegram-link" data-portal-route="/onboarding"${linkActionDisabled}>${safeText(linkActionLabel)}' in onboarding
    assert "Web hoạt động độc lập" in onboarding
    assert "Vào Workspace" in onboarding
    choice = onboarding[onboarding.index("const independentWorkspaceChoice"):onboarding.index("const linkChallengePaused")]
    assert "const skipRoute = workspaceRoute;" in onboarding
    assert 'const skipLabel = continuation ? "Mở lại workflow" : "Vào Workspace";' in onboarding
    assert 'href="${safeText(skipRoute)}"' in choice
    assert ">${safeText(skipLabel)}</a>" in choice
    assert 'renderEmpty("Chưa có mã liên kết"' in onboarding


def test_telegram_link_state_changes_hide_actions_that_the_server_would_reject() -> None:
    hero = _section(PORTAL, "function renderHero(page, context)", "const FEATURE_CATALOG_GROUPS")
    assert 'const telegramLinkAlreadyComplete = page.action === "start-telegram-link" && telegramIdentityLinked(context);' in hero
    assert "&& !telegramLinkAlreadyComplete" in hero

    onboarding = _section(
        PORTAL,
        "function renderOnboarding(page, context)",
        "function authProviderMark(provider)",
    )
    assert "const linkChallengePaused = (Boolean(code) || recovered) && !connectionReady;" in onboarding
    assert "? renderPausedTelegramLinkChallenge({ workspaceRoute: skipRoute, workspaceLabel: skipLabel })" in onboarding

    paused = _section(
        PORTAL,
        "function renderPausedTelegramLinkChallenge(",
        "function renderOnboarding(page, context)",
    )
    assert "Liên kết Telegram đang tạm dừng" in paused
    assert 'data-portal-action="refresh-link-status"' in paused
    assert "Mở Telegram" not in paused
    assert "copy-telegram-link-command" not in paused
    assert 'data-portal-action="start-telegram-link"' not in paused


def test_onboarding_exposes_clear_step_state_and_uses_closed_svg_icons() -> None:
    onboarding = _section(
        PORTAL,
        "function renderOnboarding(page, context)",
        "function authProviderMark(provider)",
    )

    assert 'class="portal-onboarding-steps" aria-label="Tiến trình liên kết Telegram"' in onboarding
    assert 'aria-current="step"' in onboarding
    assert "portalIcon(ICONS.check)" in onboarding
    assert "portalIcon(ICONS.link)" in onboarding
    assert "portalIcon(ICONS.shield)" in onboarding
    assert "data-portal-link-status aria-live" in onboarding
    assert "⌁" not in onboarding
    assert "↗" not in onboarding
    assert "✓" not in onboarding


def test_telegram_connection_notices_and_onboarding_layout_have_app_grade_affordances() -> None:
    notice = _section(
        PORTAL,
        "function renderTelegramConnectionNotice(context)",
        "function safeOnboardingContinuation(value)",
    )

    assert "portalIcon(ICONS.check)" in notice
    assert "portalIcon(ICONS.link)" in notice
    assert "portalIcon(ICONS.info)" in notice
    assert "Telegram ID không đi qua browser" in notice
    assert ".portal-onboarding-choice {" in CSS
    assert ".portal-onboarding-choice-icon .portal-icon" in CSS
    assert ".portal-onboarding-steps li[data-state=\"current\"]" in CSS
    assert ".portal-onboarding-steps small { color: #aab8c7; font-size: 12px;" in CSS
    assert ".portal-notice-icon .portal-icon { width: 17px; height: 17px; }" in CSS


def test_onboarding_prioritizes_the_independent_workspace_path_without_changing_link_actions() -> None:
    hero = _section(PORTAL, "function renderHero(page, context)", "const FEATURE_CATALOG_GROUPS")
    onboarding = _section(
        PORTAL,
        "function renderOnboarding(page, context)",
        "function authProviderMark(provider)",
    )

    assert "const showHeroAction = hasAction && !hasFields;" in hero
    assert 'const onboardingHeroPage = { ...page, action: "none" };' in onboarding
    assert "renderHero(onboardingHeroPage, context)" in onboarding
    assert '<div class="portal-onboarding-layout">' in onboarding
    assert '<div class="portal-onboarding-action">' in onboarding
    assert '<aside class="portal-onboarding-progress">' in onboarding

    choice = onboarding[onboarding.index("const independentWorkspaceChoice"):onboarding.index("const linkChallengePaused")]
    assert 'class="portal-button portal-button--primary" href="${safeText(skipRoute)}"' in choice
    assert 'class="portal-button portal-button--quiet" type="button" data-portal-action="start-telegram-link"' in onboarding


def test_onboarding_keeps_the_workspace_exit_available_when_the_optional_bridge_is_pending_or_paused() -> None:
    onboarding = _section(
        PORTAL,
        "function renderOnboarding(page, context)",
        "function authProviderMark(provider)",
    )
    paused = _section(
        PORTAL,
        "function renderPausedTelegramLinkChallenge(",
        "function starterKitCatalogItem(context, key)",
    )
    recovered = _section(
        PORTAL,
        "function renderRecoveredTelegramLinkChallenge(",
        "function renderPausedTelegramLinkChallenge(",
    )

    assert "renderPausedTelegramLinkChallenge({ workspaceRoute: skipRoute, workspaceLabel: skipLabel })" in onboarding
    assert "workspaceRoute: skipRoute, workspaceLabel: skipLabel" in onboarding
    assert 'class="portal-button portal-button--quiet" href="${safeText(skipRoute)}">${safeText(skipLabel)}</a>' in onboarding
    assert "workspaceRoute, workspaceLabel" in paused
    assert 'class="portal-button portal-button--primary" href="${safeText(workspaceRoute)}">${safeText(workspaceLabel)}</a>' in paused
    assert "workspaceRoute, workspaceLabel" in recovered
    assert 'portal-button--primary" href="' in recovered
    assert "safeText(workspaceRoute) + '\">' + safeText(workspaceLabel)" in recovered


def test_onboarding_final_scope_uses_a_compact_progress_rail_and_mobile_safe_action_order() -> None:
    scope = CSS[CSS.rindex("/* App-first optional Telegram onboarding."):]

    assert ".portal-onboarding-layout {\n  display: grid;\n  grid-template-columns: minmax(228px, .42fr) minmax(0, 1fr);" in scope
    assert ".portal-onboarding-progress {\n  grid-area: progress;" in scope
    assert ".portal-onboarding-action {\n  grid-area: action;" in scope
    assert "@media (max-width: 820px)" in scope
    assert "grid-template-areas:\n      \"action\"\n      \"progress\";" in scope
    assert "min-height: 44px;" in scope
