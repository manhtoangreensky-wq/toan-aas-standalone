"""Static browser contracts for Web-native TOTP MFA.

The backend cryptography, anti-replay and session rules are covered separately
by test_copyfast_mfa.py. These assertions keep the Portal wiring narrow:
no secret or recovery code may be persisted, and all mutations remain server
API calls behind the signed-session/CSRF boundary.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_mfa_login_is_a_short_lived_password_first_second_step() -> None:
    login_view = _between(PORTAL, "function renderAuth", "const RESULT_LABELS")
    assert 'data-portal-action="auth-mfa-login"' in login_view
    assert 'data-portal-action="auth-mfa-login-cancel"' in login_view
    assert "mfaLoginPending" in login_view
    assert "challenge_token" in login_view
    assert "Mã xác thực hoặc mã khôi phục" in login_view
    assert "data-portal-no-transient" in login_view

    login_actions = _between(INTEGRATION, 'if (action === "auth-login")', 'if (action === "start-telegram-login")')
    for requirement in (
        'accountSecurityMfaLoginChallengeProjection(result.data)',
        'merge({ mfaLoginFlow: mfaFlow })',
        'api("/auth/login/mfa"',
        "challenge_id: flow.challenge_id",
        "challenge_token: flow.challenge_token",
        "clearAccountSecurityMfaInputs()",
        'merge({ mfaLoginFlow: {} })',
        'if (action === "auth-mfa-login-cancel")',
    ):
        assert requirement in login_actions

    for source in (login_view, login_actions):
        assert "localStorage.getItem" not in source
        assert "localStorage.setItem" not in source
        assert "sessionStorage.getItem" not in source
        assert "sessionStorage.setItem" not in source


def test_account_security_mfa_is_gated_and_never_uses_browser_persistence() -> None:
    view = _between(PORTAL, "function renderAccountSecurity", "function accountActivityStatus")
    for action in (
        "account-security-mfa-start",
        "account-security-mfa-confirm",
        "account-security-mfa-disable",
        "account-security-mfa-clear-recovery-codes",
    ):
        assert f'data-portal-action="{action}"' in view
    for requirement in (
        "totpMfaEnabled",
        "mfaEnrollment",
        "mfaRecoveryCodes",
        "Manual setup key",
        "Lưu 8 mã khôi phục",
        "data-account-security-mfa-secret",
        "Server chống replay",
    ):
        assert requirement in view
    assert view.count("data-portal-no-transient") >= 9
    assert "localStorage.getItem" not in view
    assert "localStorage.setItem" not in view
    assert "sessionStorage.getItem" not in view
    assert "sessionStorage.setItem" not in view

    action_block = _between(
        INTEGRATION,
        'if (action === "account-security-refresh")',
        'if (action === "account-security-oauth-unlink")',
    )
    for requirement in (
        'api("/auth/mfa/enrollment/start"',
        'api("/auth/mfa/enrollment/confirm"',
        'api("/auth/mfa/disable"',
        "accountSecurityMfaEnrollmentProjection",
        "accountSecurityMfaCode",
        "applyAccountSecuritySessionRotation(result.data || {});",
        "mfaRecoveryCodes: recoveryCodes",
        "mfaEnrollment: {}",
    ):
        assert requirement in action_block
    assert "localStorage." not in action_block
    assert "sessionStorage." not in action_block


def test_mfa_survives_only_the_strict_live_portal_projection() -> None:
    normalizers = _between(
        PORTAL,
        "function normalizeAccountSecurityMfaBootstrap",
        "function normalizeOperationsAdminQueueStates",
    )
    for requirement in (
        "normalizeAccountSecurityMfaBootstrap",
        "normalizeMfaEnrollmentBootstrap",
        "normalizeMfaLoginFlowBootstrap",
        "normalizeMfaRecoveryCodesBootstrap",
        "enrollment_token",
        "challenge_token",
        "manual_key",
        "The setup key and opaque enrollment token are intentionally retained",
        "never enter persistent",
    ):
        assert requirement in normalizers
    assert "localStorage." not in normalizers
    assert "sessionStorage." not in normalizers

    bootstrap = _between(PORTAL, "function normalizeBootstrap", "function getBootstrap")
    for requirement in (
        "totpMfaEnabled: source.totpMfaEnabled === true",
        "mfaEnrollment: normalizeMfaEnrollmentBootstrap(source.mfaEnrollment)",
        "mfaRecoveryCodes: normalizeMfaRecoveryCodesBootstrap(source.mfaRecoveryCodes)",
        "mfaLoginFlow: normalizeMfaLoginFlowBootstrap(source.mfaLoginFlow)",
        "accountSecurity: normalizeAccountSecurityBootstrap(source.accountSecurity)",
    ):
        assert requirement in bootstrap

    assert '"auth-mfa-login": true' in INTEGRATION
    assert '"account-security-mfa-start": Boolean(account && me.csrf_token && totpMfaEnabled)' in INTEGRATION
    assert 'api("/auth/mfa/status")' in INTEGRATION
    public_navigation = _between(SERVICE_WORKER, "const PUBLIC_NAVIGATION_PATHS", "const PRIVATE_PATH_PREFIXES")
    assert "/account/security" not in public_navigation
    assert "/login/mfa" not in public_navigation
