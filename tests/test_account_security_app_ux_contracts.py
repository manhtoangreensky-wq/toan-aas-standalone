"""Presentation contracts for the signed Account and Security workspace."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def test_account_family_keeps_one_settings_navigator_with_the_correct_active_route() -> None:
    account = _section(PORTAL, "function renderAccount(page, context)", "function renderInterfaceLocaleNavigator")
    security = _section(PORTAL, "function renderAccountSecurity(page, context)", "function accountActivityStatus")
    activity = _section(PORTAL, "function renderAccountActivity(page, context)", "function renderAccountDataControls")
    data_controls = _section(PORTAL, "function renderAccountDataControls(page, context)", "function renderAdmin")

    assert 'renderAccountSettingsNav("/account")' in account
    assert 'renderAccountSettingsNav("/account/security")' in security
    assert 'renderAccountSettingsNav("/account/activity")' in activity
    assert 'renderAccountSettingsNav("/account/data-controls")' in data_controls
    assert '${settingsNav}' in account
    assert '${settingsNav}' in security
    assert '${settingsNav}' in activity
    assert '${settingsNav}' in data_controls


def test_account_has_one_contextual_primary_and_keeps_optional_telegram_as_secondary_navigation() -> None:
    account = _section(PORTAL, "function renderAccount(page, context)", "function renderInterfaceLocaleNavigator")

    assert 'const accountNextAction = linked' in account
    assert 'const accountPrimaryAction = { href: "/account/security"' in account
    assert 'href: "/account/security"' in account
    assert 'href: "/onboarding"' in account
    assert 'class="portal-button portal-button--primary" href="${safeText(accountPrimaryAction.href)}"' in account
    assert 'class="portal-button portal-button--quiet" href="${safeText(accountNextAction.href)}">${safeText(accountNextAction.label)}</a>' in account
    assert 'class="portal-button portal-button--primary" href="/onboarding">Liên kết Telegram</a>' not in account
    assert 'data-portal-action="auth-logout" data-portal-confirm="Bạn có chắc muốn đăng xuất khỏi phiên này?"' in account


def test_security_frontloads_sanitized_posture_and_keeps_generic_assurance_after_actions() -> None:
    security = _section(PORTAL, "function renderAccountSecurity(page, context)", "function accountActivityStatus")

    assert 'const settingsNav = renderAccountSettingsNav("/account/security");' in security
    assert 'const securityPosture = `<section class="portal-security-posture"' in security
    assert 'class="portal-security-posture-facts"' in security
    assert 'data-portal-action="account-security-refresh"' in security
    assert 'const accountAssurance = `<details class="portal-account-assurance portal-security-assurance"' in security
    assert security.index("${settingsNav}${securityPosture}") < security.index("Phiên đang đăng nhập")
    assert security.index("Phiên đang đăng nhập") < security.index("${accountAssurance}")
    for forbidden in ("data-security-session-ref", "data-session-ref", "localStorage.setItem", "sessionStorage.setItem"):
        assert forbidden not in security


def test_security_posture_never_overstates_a_password_or_mfa_action_without_its_capability() -> None:
    security = _section(PORTAL, "function renderAccountSecurity(page, context)", "function accountActivityStatus")
    posture = security[security.index("const mfaPosture"):security.index("const contactPosture")]
    facts = security[security.index("const postureFacts"):security.index("const securityPosture")]

    assert 'mfa.runtimeAvailable && passwordAvailable && mfaStartEnabled' in posture
    assert 'state: passwordEnabled ? "ready" : (passwordAvailable ? "guarded" : "read_only")' in facts
    assert 'title: passwordEnabled ? "Sẵn sàng" : (passwordAvailable ? "Đang bảo vệ" : "Chưa khả dụng")' in facts


def test_security_posture_uses_clear_vietnamese_guarded_copy() -> None:
    security = _section(PORTAL, "function renderAccountSecurity(page, context)", "function accountActivityStatus")

    assert 'title: "Đang được bảo vệ"' in security
    assert 'title: "Đang guarded"' not in security


def test_account_security_final_scope_uses_tokenized_mobile_safe_app_chrome() -> None:
    scope = CSS[CSS.rindex("/* Account & Security workspace UX."):]

    for token in (
        ".portal-account-page .portal-settings-nav",
        "scroll-snap-type: x mandatory;",
        "scroll-snap-align: start;",
        ".portal-security-posture",
        ".portal-security-posture-facts",
        ".portal-account-page [data-portal-action=\"auth-logout\"]",
        "font-size: 12px;",
        "min-height: 44px;",
        "@media (max-width: 700px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert token in scope
    assert "linear-gradient" not in scope


def test_shared_account_settings_nav_has_the_same_scope_on_the_language_page() -> None:
    scope = CSS[CSS.rindex("/* Account & Security workspace UX."):]

    assert ".portal-interface-locale-navigator .portal-settings-nav" in scope
    assert ".portal-interface-locale-navigator .portal-settings-nav a" in scope


def test_security_route_keeps_its_resolved_title_when_the_server_shell_is_generic() -> None:
    title_resolver = _section(PORTAL, "function displayPageTitle(page, context)", "const NAVIGATION_I18N_KEYS")

    assert 'const genericServerTitles = new Set(["TOAN AAS", "TOAN AAS Workspace"]);' in title_resolver
    assert "!genericServerTitles.has(serverTitle)" in title_resolver
