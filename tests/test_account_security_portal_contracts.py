"""Static portal contracts for the Web-native Account Security Center.

These checks deliberately cover browser wiring only.  The endpoint ownership,
CSRF checks, password policy and factor/session mutation contracts remain in
``test_account_security_center.py`` and are not duplicated here.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_account_security_has_a_signed_portal_route_and_safe_forms() -> None:
    assert 'customerPage("/account/security", "Bảo mật tài khoản"' in PORTAL
    assert 'layout: "account-security"' in PORTAL
    assert 'href="/account/security">Bảo mật tài khoản →</a>' in PORTAL
    assert 'case "account-security": return renderAccountSecurity(page, context);' in PORTAL

    view = _between(PORTAL, "function renderAccountSecurity", "function accountActivityStatus")
    assert 'const validSessionRef = (value) => /^[a-f0-9]{64}$/i' in view
    assert '<input type="hidden" name="session_ref"' in view
    assert 'data-security-session-ref' not in view
    assert 'data-session-ref' not in view
    assert '<strong>${safeText(sessionRef)}</strong>' not in view
    assert "localStorage.getItem" not in view
    assert "localStorage.setItem" not in view
    assert "sessionStorage.getItem" not in view
    assert "sessionStorage.setItem" not in view

    for action in (
        "account-security-revoke-session",
        "account-security-revoke-others",
        "account-security-password-change",
        "account-security-email-verification-start",
        "account-security-oauth-unlink",
    ):
        assert f'data-portal-action="{action}"' in view
    assert view.count("data-portal-no-transient") >= 5
    assert 'data-account-security-secret type="password" name="current_password"' in view
    assert 'autocomplete="current-password"' in view
    assert 'autocomplete="new-password"' in view
    assert 'data-portal-confirm="Đổi mật khẩu và thu hồi các phiên khác?' in view
    assert 'provider === "telegram" && canonicalTelegram' in view
    assert "Không có nút gỡ liên kết Telegram trên Web App." in view
    assert "Portal không hiển thị luồng khôi phục giả." in view


def test_account_security_hydration_is_route_session_fenced_and_redacted() -> None:
    for epoch in ("accountSecuritySessionEpoch", "accountSecurityHydrationEpoch"):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    helper = _between(
        INTEGRATION,
        "function accountSecurityRequestIsCurrent",
        "function workspaceDraftRequestIsCurrent",
    )
    for requirement in (
        "requestEpoch === accountSecurityHydrationEpoch",
        "sessionEpoch === accountSecuritySessionEpoch",
        "currentPortalPath() === expectedPath",
        'expectedPath === "/account/security"',
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper
    assert "localStorage." not in helper
    assert "sessionStorage." not in helper
    assert "session_id" not in helper
    assert "toan_aas_session" not in helper

    hydrator = _between(INTEGRATION, "async function hydrateAccountSecurity", "function workspaceDraftRequestIsCurrent")
    assert 'api("/auth/security/sessions")' in hydrator
    assert 'api("/auth/security/login-methods")' in hydrator
    assert "Promise.all([" in hydrator
    assert "accountSecuritySessionProjection" in hydrator
    assert "accountSecurityLoginMethodProjection" in hydrator
    assert 'accountSecurity: { sessions: [], loginMethods: {}, mfa: accountSecurityMfaProjection({}), readState: "guarded" }' in hydrator
    assert 'if (account && currentPath === "/account/security") await hydrateAccountSecurity();' in INTEGRATION
    assert 'accountSecurity: { sessions: [], loginMethods: {}, mfa: accountSecurityMfaProjection({}), readState: account ? "loading" : "guarded" }' in INTEGRATION


def test_account_security_contact_assurance_is_allowlisted_and_never_keeps_contact_email() -> None:
    projection = _between(
        INTEGRATION,
        "function accountSecurityLoginMethodProjection",
        "function accountSecurityRequestIsCurrent",
    )
    for requirement in (
        'ACCOUNT_SECURITY_CONTACT_PROVIDERS = new Set(["google", "github", "apple"])',
        '"verified_email_link"',
        'contactState === "verified_oauth"',
        'contactState === "verified_email_link"',
        'contactProvider === "email_link"',
        'ACCOUNT_SECURITY_CONTACT_PROVIDERS.has(contactProvider)',
        'rawContact.verified === true',
        'rawEmailVerification.available === true',
        '{ state: "unavailable", provider: "", verified: false }',
    ):
        assert requirement in INTEGRATION or requirement in projection
    assert "contact_email" not in projection
    assert "rawContact.email" not in projection

    view = _between(PORTAL, "function renderAccountSecurity", "function accountActivityStatus")
    assert "Email & quyền sở hữu" in view
    assert "Email chưa có bằng chứng xác minh độc lập" in view
    assert "Email đã được xác minh qua liên kết bảo mật" in view
    assert 'data-portal-action="account-security-email-verification-start"' in view
    assert "Web không lưu token OAuth hoặc giả lập gửi thư xác minh." in view
    assert 'href="/account">Mở phương thức đăng nhập</a>' in view


def test_account_security_writes_reuse_csrf_api_and_refresh_rotated_session() -> None:
    actions = _between(INTEGRATION, 'if (action === "account-security-refresh")', 'if (action === "copy-payment-command")')
    for requirement in (
        'api("/auth/security/sessions/revoke"',
        'api("/auth/security/sessions/revoke-others"',
        'api("/auth/security/password"',
        'api("/auth/security/email-verification/start"',
        'api(`/auth/security/oauth/${encodeURIComponent(provider)}/unlink`',
        "headers: { \"Content-Type\": \"application/json\" }",
        "clearAccountSecurityPasswordInputs()",
        "applyAccountSecuritySessionRotation(result.data || {});",
        "await hydrate();",
        "await hydrateAccountSecurity();",
        "ACCOUNT_SECURITY_OAUTH_PROVIDERS.has(provider)",
        'provider === "telegram" && canonicalTelegram',
    ):
        assert requirement in actions

    rotation = _between(INTEGRATION, "function applyAccountSecuritySessionRotation", "async function hydrateAccountSecurity")
    assert "csrfToken" in rotation
    assert "sessionStorage." not in rotation
    assert "localStorage." not in rotation

    cancellation = _between(PORTAL, "function dispatchAction", "function sidebarFocusables")
    assert 'action === "account-security-password-change"' in cancellation
    assert 'querySelectorAll("[data-account-security-secret]")' in cancellation


def test_account_security_survives_the_portal_bootstrap_projection() -> None:
    """Strict account-security metadata must remain available after remount."""

    projection = _between(PORTAL, "function normalizeAccountSecurityBootstrap", "function normalizeBootstrap")
    for requirement in (
        "ACCOUNT_SECURITY_BOOTSTRAP_READ_STATES",
        "ACCOUNT_SECURITY_BOOTSTRAP_OAUTH_PROVIDERS",
        "ACCOUNT_SECURITY_BOOTSTRAP_CONTACT_PROVIDERS",
        "ACCOUNT_SECURITY_BOOTSTRAP_CONTACT_STATES",
        "/^[a-f0-9]{64}$/.test(sessionRef)",
        "source.sessions.slice(0, 20)",
        "rawMethods.oauth.slice(0, 4)",
        "rawContact.verified === true",
        "usable_factor_count",
        "readState: \"read_only\"",
    ):
        assert requirement in projection

    # Session action references are opaque HMAC handles. No raw browser
    # session, contact email, OAuth token/subject, or persistent store can
    # cross the presentation boundary.
    for private_field in (
        "session_id",
        "contact_email",
        "rawContact.email",
        "access_token",
        "refresh_token",
        "oauth_subject",
        "localStorage.",
        "sessionStorage.",
    ):
        assert private_field not in projection

    bootstrap = _between(PORTAL, "function normalizeBootstrap", "function getBootstrap")
    assert "accountSecurity: normalizeAccountSecurityBootstrap(source.accountSecurity)" in bootstrap
