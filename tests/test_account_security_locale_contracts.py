"""Presentation-only locale contracts for the signed Account Security Center.

The Security Center may translate only its reviewed, fixed Web chrome.  It
must not reinterpret a server-projected factor, session timestamp, provider
label, opaque session reference, credential, or API result.
"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


SECURITY_RENDERER_KEYS = (
    "contactLoadingTitle",
    "contactLoadingBody",
    "contactGuardedTitle",
    "contactGuardedBody",
    "emailLinkVerifiedTitle",
    "emailLinkPendingTitle",
    "emailLinkPendingBody",
    "emailVerificationRefresh",
    "emailUnverifiedTitle",
    "emailVerificationConfirm",
    "emailVerificationAction",
    "providerEmailVerifiedTitle",
    "noContactProofTitle",
    "openLoginMethods",
    "noContactEmailTitle",
    "openAccount",
    "sessionCreated",
    "sessionLastSeen",
    "sessionExpires",
    "currentSessionTitle",
    "otherSessionTitle",
    "currentSessionNote",
    "revokeSessionConfirm",
    "revokeSessionAction",
    "sessionLoadingTitle",
    "sessionGuardedTitle",
    "revokeOthersConfirm",
    "revokeOthersAction",
    "noOtherSessions",
    "passwordLoadingTitle",
    "passwordGuardedTitle",
    "passwordChangeConfirm",
    "currentPasswordLabel",
    "newPasswordLabel",
    "confirmNewPasswordLabel",
    "passwordChangeAction",
    "oauthOnlyTitle",
    "telegramFirstAccountTitle",
    "passwordUnavailableTitle",
    "oauthLoadingTitle",
    "oauthGuardedTitle",
    "oauthNotLinked",
    "telegramFirstMethodTitle",
    "oauthUnlinkConfirm",
    "oauthUnlinkAction",
    "oauthProtectedNote",
    "oauthLinkedVerified",
    "noLinkedOAuthTitle",
    "mfaStartConfirm",
    "mfaStartAction",
    "mfaRecoveryTitle",
    "mfaRecoveryClearAction",
    "mfaDisabledTitle",
    "mfaGuardedTitle",
    "mfaLoadingTitle",
    "mfaUnavailableTitle",
    "mfaEnabledTitle",
    "mfaDisableAction",
    "mfaEnrollmentTitle",
    "mfaConfirmAction",
    "mfaRestartTitle",
    "mfaTitle",
    "mfaPasswordRequiredTitle",
    "postureAria",
    "postureTitle",
    "postureRefresh",
    "sessionSectionTitle",
    "passwordSectionTitle",
    "oauthSectionTitle",
    "contactSectionTitle",
    "securityBoundaryTitle",
)

SECURITY_ACTION_KEYS = (
    "actionRefreshRouteError",
    "actionRefreshCapabilityError",
    "actionRefreshSuccess",
    "actionRevokeSessionRouteError",
    "actionRevokeSessionCapabilityError",
    "actionSessionInvalidError",
    "actionRevokeSessionSuccess",
    "actionRevokeSessionUnavailable",
    "actionRevokeOthersRouteError",
    "actionRevokeOthersCapabilityError",
    "actionRevokeOthersSuccess",
    "actionNoOtherSessions",
    "actionPasswordRouteError",
    "actionPasswordCapabilityError",
    "actionPasswordMissingError",
    "actionPasswordMismatchError",
    "actionPasswordSuccess",
    "actionEmailRouteError",
    "actionEmailCapabilityError",
    "actionEmailUnavailableError",
    "actionEmailSuccess",
    "actionMfaStartRouteError",
    "actionMfaStartCapabilityError",
    "actionMfaStartPasswordError",
    "actionMfaStartPayloadError",
    "actionMfaStartSuccess",
    "actionMfaConfirmRouteError",
    "actionMfaConfirmCapabilityError",
    "actionMfaConfirmInvalidError",
    "actionMfaRecoveryUnavailableError",
    "actionMfaConfirmSuccess",
    "actionMfaDisableRouteError",
    "actionMfaDisableCapabilityError",
    "actionMfaDisableInputError",
    "actionMfaDisableSuccess",
    "actionMfaClearRouteError",
    "actionMfaClearSuccess",
    "actionOauthRouteError",
    "actionOauthCapabilityError",
    "actionOauthInvalidError",
    "actionTelegramCanonicalError",
    "actionOauthUnlinkSuccess",
    "actionOauthUnavailable",
)

SECURITY_ASSURANCE_KEYS = (
    "assuranceReadOnlyTitle",
    "assuranceReadOnlyBody",
    "assuranceGuardedTitle",
    "assuranceGuardedBody",
    "assuranceBridgeConnected",
    "assuranceBridgeOptional",
    "assuranceSignedSessionPresent",
    "assuranceSignedSessionPending",
    "assuranceNoProviderPayment",
    "assuranceFlowTitle",
    "assuranceFlowBody",
    "assuranceWebWorkspace",
    "assuranceWebIndependent",
    "assuranceLoginRequired",
    "assuranceBotCompanion",
    "assuranceConnected",
    "assuranceOptional",
    "assuranceSignedSession",
    "assuranceVerified",
    "assurancePending",
    "assuranceCsrf",
    "assuranceReady",
    "assuranceNotIssued",
    "assuranceApiBase",
    "assuranceApiConfigured",
    "assuranceApiNotPublished",
)


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def test_account_security_uses_a_reviewed_vi_en_zh_fixed_copy_catalogue() -> None:
    security = _between(PORTAL, "function renderAccountSecurity", "function accountActivityStatus")

    assert 'const copy = (key, fallback, params) => accountCenterText(`security.${key}`, fallback, params);' in security
    assert "const providerLabels = { telegram: \"Telegram Login\", google: \"Google\", github: \"GitHub\", apple: \"Sign in with Apple\" };" in security
    rendered_keys = set(re.findall(r'\bcopy\("([^"]+)"', security))
    for key in SECURITY_RENDERER_KEYS:
        assert key in rendered_keys
    for key in rendered_keys:
        assert I18N.count(f'"accountCenter.security.{key}"') == 3

    # Account/identity values and opaque server data remain escaped display
    # values.  Translation keys are restricted to fixed UI copy above.
    for requirement in (
        "safeText(sessionRef)",
        "safeText(label)",
        "safeText(String(mfaEnrollment.manual_key || \"\"))",
        "localStorage.getItem",
        "sessionStorage.getItem",
    ):
        if requirement.startswith("safeText"):
            assert requirement in security
        else:
            assert requirement not in security
    # The remaining-code count may be interpolated into fixed reviewed copy,
    # but it is still rendered through the outer safeText boundary.
    assert 'copy("mfaRecoveryRemainingBody"' in security
    assert "mfa.recoveryCodesRemaining" in security


def test_account_security_does_not_render_unlocalized_global_assurance_cards() -> None:
    security = _between(PORTAL, "function renderAccountSecurity", "function accountActivityStatus")

    assert "${renderStatusCard(page, context)}" not in security
    assert "${renderSummary(page, context)}" not in security
    assurance_keys = set(re.findall(r'\bcopy\("([^"]+)"', security))
    for key in SECURITY_ASSURANCE_KEYS:
        assert key in assurance_keys
        assert I18N.count(f'"accountCenter.security.{key}"') == 3


def test_account_security_actions_localize_browser_messages_without_changing_requests() -> None:
    actions = _between(
        INTEGRATION,
        'if (action === "account-security-refresh")',
        'if (action === "copy-payment-command")',
    )

    assert "function accountSecurityText(key, fallback, params)" in INTEGRATION
    action_keys = set(re.findall(r'\baccountSecurityText\("([^"]+)"', actions))
    for key in SECURITY_ACTION_KEYS:
        assert key in action_keys
    for key in action_keys:
        assert I18N.count(f'"accountCenter.security.{key}"') == 3

    for request in (
        'api("/auth/security/sessions/revoke"',
        'api("/auth/security/sessions/revoke-others"',
        'api("/auth/security/password"',
        'api("/auth/security/email-verification/start"',
        'api("/auth/mfa/enrollment/start"',
        'api("/auth/mfa/enrollment/confirm"',
        'api("/auth/mfa/disable"',
        'api(`/auth/security/oauth/${encodeURIComponent(provider)}/unlink`',
    ):
        assert request in actions


def test_account_security_has_localized_document_metadata_and_signed_first_paint() -> None:
    title = _between(PORTAL, "function localizedPageTitle", "function documentTitle")
    description = _between(PORTAL, "function localizedPageDescription", "function initials")
    navigation = _between(PORTAL, "const NAVIGATION_I18N_KEYS", "function localizedNavigationLabel")

    for key in ("page.accountSecurity.title", "page.accountSecurity.description"):
        assert I18N.count(f'"{key}"') == 3
    assert 'if (path === "/account/security") return uiText("page.accountSecurity.title", fallback);' in title
    assert 'if (path === "/account/security") return uiText("page.accountSecurity.description", fallback);' in description
    assert '"Bảo mật tài khoản": "page.accountSecurity.title"' in navigation
    assert '"/account/security": {"vi": "Bảo mật tài khoản · TOAN AAS", "en": "Account security · TOAN AAS", "zh": "账户安全 · TOAN AAS"},' in PAGES


def test_account_security_session_timestamps_are_escaped_once_at_the_render_boundary() -> None:
    security = _between(PORTAL, "function renderAccountSecurity", "function accountActivityStatus")

    assert 'return text ? text.slice(0, 80) : "—";' in security
    assert 'return text ? safeText(text.slice(0, 80)) : "—";' not in security
    assert '].map((item) => safeText(item)).join(" · ");' in security
