"""Static safety contracts for the Web-native Admin Security & Access views."""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end() :])
    return source[match.start() : match.end() + following.start() if following else len(source)]


def test_security_and_access_are_native_admin_routes_not_bridge_modules() -> None:
    assert 'adminPage("/admin/security", "Security Posture"' in PORTAL
    assert 'adminPage("/admin/access", "Access Posture"' in PORTAL
    assert 'layout: "admin-security-access-posture", action: "none", status: "read_only"' in PORTAL
    # definePage intentionally uses last-write-wins manifest registration.  Keep
    # each route registered once so a later legacy adminPage cannot overwrite
    # the native read-only layout at portal boot.
    assert PORTAL.count('adminPage("/admin/security",') == 1
    assert PORTAL.count('adminPage("/admin/access",') == 1
    security_registration = PORTAL.split('adminPage("/admin/security",', 1)[1].split('adminPage("/admin/access",', 1)[0]
    access_registration = PORTAL.split('adminPage("/admin/access",', 1)[1].split('adminPage("/admin/reliability",', 1)[0]
    assert 'layout: "admin-security-access-posture"' in security_registration
    assert 'layout: "admin-security-access-posture"' in access_registration
    assert 'case "admin-security-access-posture": return renderAdminSecurityAccessPosture(page, context);' in PORTAL
    native = _function_source(INTEGRATION, "isNativeAdminSecurityAccessPosturePath")
    assert 'normalized === "/admin/security" || normalized === "/admin/access"' in native

    canonical_modules = INTEGRATION[
        INTEGRATION.index("const ADMIN_CANONICAL_READ_MODULES") : INTEGRATION.index("const ADMIN_MODULE_NAME_PATTERN")
    ]
    assert '"security"' not in canonical_modules
    assert '"access"' not in canonical_modules

    bridge_gate = INTEGRATION[INTEGRATION.index("if (bridgeAvailable &&") :]
    bridge_gate = bridge_gate[:1_700]
    assert "!isNativeAdminSecurityAccessPosturePath(currentPath)" in bridge_gate
    canonical = _function_source(INTEGRATION, "hydrateCanonicalAdminData")
    assert "isNativeAdminSecurityAccessPosturePath(expectedPath)" in canonical
    assert '|| isNativeAdminSecurityAccessPosturePath(expectedPath)) return null;' in canonical


def test_native_hydration_is_closed_read_only_and_fenced_against_stale_responses() -> None:
    for declaration in (
        "let adminSecurityAccessPostureSessionEpoch = 0;",
        "let adminSecurityAccessPostureHydrationEpoch = 0;",
        "++adminSecurityAccessPostureSessionEpoch;",
        "++adminSecurityAccessPostureHydrationEpoch;",
        "adminSecurityAccessPosture: {}",
        'adminSecurityAccessPostureReadState: account && adminSecurityAccessPostureEnabled ? "loading" : "guarded"',
        "function adminSecurityAccessPostureRequestIsCurrent",
        "function hydrateAdminSecurityAccessPosture",
        "base().adminSecurityAccessPostureEnabled === true",
        "currentPortalPath() === expectedPath",
        "isNativeAdminSecurityAccessPosturePath(currentPath)",
    ):
        assert declaration in INTEGRATION

    hydrator = _function_source(INTEGRATION, "hydrateAdminSecurityAccessPosture")
    for required in (
        'api("/admin/security-posture/summary", { cache: "no-store" })',
        "adminSecurityAccessPostureProjection",
        "adminSecurityAccessPostureRequestIsCurrent",
        'adminSecurityAccessPostureReadState: "loading"',
        'adminSecurityAccessPostureReadState: "failed"',
        'adminSecurityAccessPostureStatus: "guarded"',
    ):
        assert required in hydrator
    assert hydrator.index('adminSecurityAccessPostureReadState: "loading"') < hydrator.index('api("/admin/security-posture/summary"')
    for forbidden in ("bridgeAvailable", "readAdminPath", "fetch(", "method: \"POST\"", "localStorage", "sessionStorage", "setInterval"):
        assert forbidden not in hydrator


def test_projection_rejects_expanded_or_partial_sensitive_models() -> None:
    projection = _function_source(INTEGRATION, "adminSecurityAccessPostureProjection")
    for required in (
        'const ADMIN_SECURITY_ACCESS_POSTURE_POLICY = "web_security_access_posture_v1";',
        'source.source !== ADMIN_SECURITY_ACCESS_POSTURE_POLICY',
        'source.policy_version !== ADMIN_SECURITY_ACCESS_POSTURE_POLICY',
        "source.read_only !== true",
        "source.integrity_guarded",
        "adminSecurityAccessPostureObjectHasOnly",
        "ADMIN_SECURITY_ACCESS_POSTURE_BOUNDARIES",
        "adminSecurityAccessPostureCountGroup",
        "adminSecurityAccessPostureActivityProjection",
    ):
        assert required in INTEGRATION
    assert '"active_accounts", "inactive_accounts", "privileged_accounts", "admin_accounts"' in INTEGRATION
    assert '"login_active_buckets", "register_active_buckets", "password_change_active_buckets"' in INTEGRATION
    assert '"window_hours", "sign_in_completed", "sign_in_guarded"' in INTEGRATION
    assert "count !== null" in _function_source(INTEGRATION, "adminSecurityAccessPostureCountGroup")
    assert "windowHours !== 24" in _function_source(INTEGRATION, "adminSecurityAccessPostureActivityProjection")
    assert "adminSecurityAccessPostureProjection" in projection

    normalizer = _function_source(PORTAL, "normalizeAdminSecurityAccessPostureBootstrap")
    assert "ADMIN_SECURITY_ACCESS_POSTURE_BOUNDARIES" in normalizer
    assert "normalizeAdminSecurityAccessPostureCountGroup" in normalizer
    assert "access.privileged_accounts" in normalizer
    # Raw action/reason fields can no longer take the old generic Security
    # renderer path. Audit stays separately redacted by its own API contract.
    generic = _function_source(PORTAL, "renderAdminDataTable")
    assert '["audit", "security"]' not in generic
    assert 'if (module === "audit")' in generic


def test_renderer_has_no_controls_or_unredacted_fallback_and_private_pwa_scope() -> None:
    renderer = _function_source(PORTAL, "renderAdminSecurityAccessPosture")
    for required in (
        "serverAuthorizesAdminRoute(context, route)",
        "integrityGuarded && hasClosedProjection",
        "Portal không hiển thị số 0, số liệu một phần",
        "Không có control action",
        "Ranh giới dữ liệu",
    ):
        assert required in renderer
    for forbidden in (
        "data-portal-action",
        "<button",
        "localStorage",
        "sessionStorage",
        "fetch(",
        "/internal/",
        "idempotency",
        "csrf",
    ):
        assert forbidden.lower() not in renderer.lower()

    assert '"/" + "api/v1/admin"' in SERVICE_WORKER
    assert '"/admin"' in SERVICE_WORKER
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/admin/security"' not in shell
    assert '"/admin/access"' not in shell
