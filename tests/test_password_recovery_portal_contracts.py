"""Static browser contracts for the public, Web-native password recovery flow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_password_recovery_is_a_public_non_transient_portal_route() -> None:
    assert 'path: "/password-recovery"' in PORTAL
    assert 'action: "auth-password-recovery-start"' in PORTAL
    assert "fields: copyFields(FIELD_SETS.passwordRecovery)" in PORTAL
    assert "Phản hồi luôn giống nhau để không tiết lộ tài khoản có tồn tại hay không." in PORTAL
    assert 'href="/password-recovery">Quên mật khẩu?</a>' in PORTAL

    view = _between(PORTAL, "function renderAuth", "const RESULT_LABELS")
    assert 'page.path === "/password-recovery" ? " data-portal-no-transient" : ""' in view
    assert 'page.path === "/register" ? renderOAuthRegistrationMethods(context) : ""' in view
    assert "localStorage.getItem" not in view
    assert "localStorage.setItem" not in view
    assert "sessionStorage.getItem" not in view
    assert "sessionStorage.setItem" not in view


def test_password_recovery_browser_wiring_never_receives_or_persists_a_proof() -> None:
    assert '"auth-password-recovery-start": true' in INTEGRATION
    action = _between(INTEGRATION, 'if (action === "auth-register")', 'if (action === "auth-login")')
    assert 'if (action === "auth-password-recovery-start")' in action
    assert 'api("/auth/password-recovery/start"' in action
    assert 'data-portal-action="auth-password-recovery-start"' in action
    assert "recoveryForm.reset()" in action
    assert "token" not in action
    assert "localStorage." not in action
    assert "sessionStorage." not in action

    for source in (PORTAL, INTEGRATION):
        assert '"/password-recovery", "/onboarding"' in source

    public_navigation = _between(SERVICE_WORKER, "const PUBLIC_NAVIGATION_PATHS", "const PRIVATE_PATH_PREFIXES")
    assert '"/password-recovery"' not in public_navigation
