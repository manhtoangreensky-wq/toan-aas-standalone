"""Static contracts for the signed Web-native Partner Readiness workspace."""

from pathlib import Path

from copyfast_registry import allowed_paths


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
DATABASE = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_partner_readiness_is_one_signed_customer_route_without_an_admin_or_referral_surface() -> None:
    assert "/partner-readiness" in allowed_paths()
    assert 'WebFeature("partner_readiness", "Partner Readiness", "growth", "/partner-readiness"' in REGISTRY
    assert 'customerPage("/partner-readiness", "Partner Readiness"' in PORTAL
    assert 'layout: "partner-readiness"' in PORTAL
    assert 'case "partner-readiness": return renderPartnerReadiness(page, context);' in PORTAL
    assert 'function renderPartnerReadiness(page, context)' in PORTAL
    assert '"/admin/partner-readiness"' not in PORTAL


def test_partner_readiness_renderer_keeps_the_local_interest_boundary_visible() -> None:
    renderer = _between(PORTAL, "function renderPartnerReadiness", "function renderWorkspaceSetup")
    for requirement in (
        'data-portal-action="partner-readiness-save"',
        'data-portal-action="partner-readiness-request-review"',
        'data-portal-action="partner-readiness-interest"',
        'data-portal-action="partner-readiness-archive"',
        'data-portal-action="partner-readiness-restore"',
        'data-portal-action="partner-readiness-refresh"',
        "data-portal-no-transient",
        'name="confirm_interest"',
        "Đã ghi nhận quan tâm trong Web App; chưa có duyệt, ghép khách, liên hệ, referral, hoa hồng, thanh toán hoặc payout.",
        "aria-live=\"polite\"",
    ):
        assert requirement in renderer
    for forbidden in ("localStorage", "sessionStorage", "telegram_id", "canonical_user_id", 'href="/referrals"', "data-portal-route=\"/admin"):
        assert forbidden not in renderer


def test_partner_readiness_hydration_is_owner_fenced_and_contract_checked() -> None:
    for endpoint in (
        'api("/partner-readiness/policy")',
        'api("/partner-readiness/profile")',
        'api("/partner-readiness/profile/history")',
    ):
        assert endpoint in INTEGRATION
    for requirement in (
        "PARTNER_READINESS_BOUNDARY_FALSE_FIELDS",
        "function partnerReadinessBoundaryIsSafe",
        "function partnerReadinessProfileProjection",
        "function partnerReadinessRequestIsCurrent",
        "partnerReadinessSessionEpoch",
        "partnerReadinessHydrationEpoch",
        '"/partner-readiness"',
        '"partner-readiness-save": Boolean(account && me.csrf_token && partnerReadinessEnabled)',
        '"partner-readiness-interest": Boolean(account && me.csrf_token && partnerReadinessEnabled)',
        'if (action === "partner-readiness-save")',
        'if (action === "partner-readiness-interest")',
        "acquireSubmission(scope, featureFingerprint(payload))",
        "await hydratePartnerReadiness()",
    ):
        assert requirement in INTEGRATION
    partner_slice = _between(INTEGRATION, "const PARTNER_READINESS_BOUNDARY_FALSE_FIELDS", "const STARTER_KIT_KEYS")
    for forbidden in ("localStorage", "sessionStorage", "telegram_id", "canonical_user_id", "partnerCrm"):
        assert forbidden not in partner_slice


def test_partner_readiness_write_completion_is_fenced_to_the_originating_session() -> None:
    helper = _between(
        INTEGRATION,
        "function partnerReadinessWriteSessionIsCurrent",
        "function setPartnerReadinessActionBusy",
    )
    write = _between(
        INTEGRATION,
        "async function submitPartnerReadinessWrite",
        "function isNativeStarterKitsPath",
    )
    for requirement in (
        "sessionEpoch === partnerReadinessSessionEpoch",
        "currentPortalPath() === expectedPath",
        "base().partnerReadinessEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in helper
    assert "const sessionEpoch = partnerReadinessSessionEpoch;" in write
    assert write.count("partnerReadinessWriteSessionIsCurrent(sessionEpoch, route)") >= 6
    assert "if (acknowledged && partnerReadinessWriteSessionIsCurrent(sessionEpoch, route)) await hydratePartnerReadiness();" in write
    assert "if (partnerReadinessWriteSessionIsCurrent(sessionEpoch, route)) setPartnerReadinessActionBusy(action, route, false);" in write


def test_partner_readiness_has_private_cache_and_responsive_boundaries() -> None:
    assert '"/" + "api/v1/partner-readiness"' in WORKER
    assert '"/partner-readiness"' in WORKER
    for selector in (
        ".portal-partner-readiness-layout",
        ".portal-partner-readiness-form-grid",
        ".portal-partner-readiness-state",
        ".portal-partner-readiness-history",
        ".portal-partner-readiness-form .portal-input",
        "@media (max-width: 700px)",
    ):
        assert selector in CSS
    assert "min-height: 44px" in CSS
    for requirement in (
        "WEBAPP_PARTNER_READINESS_ENABLED",
        "PARTNER_READINESS_BODY_MAX_BYTES",
        "partner-readiness-write",
        "partner-readiness-interest",
        "WEB_PARTNER_READINESS_BODY_TOO_LARGE",
    ):
        assert requirement in (DATABASE if requirement == "WEBAPP_PARTNER_READINESS_ENABLED" else APP)


def test_partner_readiness_choice_motion_only_composites_transform() -> None:
    choice_rule = _between(
        CSS,
        ".portal-page.portal-partner-readiness .portal-partner-readiness-choice {",
        ".portal-page.portal-partner-readiness .portal-partner-readiness-choice:is(:hover, :focus-within)",
    )
    assert "transition: transform var(--portal-motion-fast);" in choice_rule
    assert "border-color var(--portal-motion-fast)" not in choice_rule
    assert "background var(--portal-motion-fast)" not in choice_rule
