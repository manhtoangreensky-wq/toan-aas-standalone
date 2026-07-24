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
    assert "? renderPausedTelegramLinkChallenge()" in onboarding

    paused = _section(
        PORTAL,
        "function renderPausedTelegramLinkChallenge()",
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
