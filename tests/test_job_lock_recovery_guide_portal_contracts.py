"""Focused boundaries for the canonical-admin Job-Lock Recovery Safety Guide."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_start = source.find("\n  function ", start + len(marker))
    return source[start:] if next_start < 0 else source[start:next_start]


def test_job_recovery_guide_uses_the_generic_canonical_admin_route_gate() -> None:
    app = _read("app.py")
    registry = _read("copyfast_registry.py")
    navigation = _read("copyfast_admin_erp_navigation.py")

    assert 'WebFeature("admin_job_recovery_guide", "Job-Lock Recovery Safety Guide", "admin", "/admin/job-recovery-guide", "admin"' in registry
    assert '_directory_module("job_recovery_guide", "Job-Lock Recovery Safety Guide", "/admin/job-recovery-guide")' in navigation
    assert '"job_recovery_guide": "Hướng dẫn triage job-lock chỉ đọc' in navigation
    assert 'elif normalized == "/admin" or normalized.startswith("/admin/"):\n        await require_canonical_admin(request)' in app
    assert 'normalized == "/admin/job-recovery-guide"' not in app


def test_job_recovery_renderer_is_static_guidance_without_a_job_or_finance_control_plane() -> None:
    portal = _read("static/portal/portal.js")
    css = _read("static/portal/portal.css")

    for declaration in (
        'adminPage("/admin/job-recovery-guide", "Job-Lock Recovery Safety Guide"',
        'layout: "admin-job-recovery-guide", action: "none", status: "read_only"',
        'case "admin-job-recovery-guide": return renderAdminJobRecoveryGuide(page, context);',
        '"/admin/job-recovery-guide", "/admin/providers"',
    ):
        assert declaration in portal

    renderer = _function_source(portal, "renderAdminJobRecoveryGuide")
    assert 'serverAuthorizesAdminRoute(context, "/admin/jobs")' in renderer
    for forbidden in (
        "fetch(",
        "api(",
        "readAdminPath(",
        "data-portal-action",
        "<form",
        "<button",
        "payloadFor(",
        "FormData",
        "Idempotency-Key",
        "/admin/modules/",
        "adminData",
        "localStorage",
        "sessionStorage",
        "setInterval",
        "data-admin-job-id",
        "jobId",
        "/clear_job_lock",
    ):
        assert forbidden not in renderer
    assert "Không clear, retry hoặc refund" in renderer
    assert "Không điều khiển runtime" in renderer
    assert "Không có financial side effect" in renderer
    assert '${badge("guarded")}' not in renderer
    assert renderer.count('${badge("read_only")}') >= 3

    for selector in (
        ".portal-admin-job-recovery-guide",
        ".portal-job-recovery-intro",
        ".portal-job-recovery-grid",
        ".portal-job-recovery-card",
        ".portal-job-recovery-process",
        ".portal-job-recovery-boundary",
        "font-size: 12px",
        "@media (max-width: 980px)",
        "@media (max-width: 700px)",
    ):
        assert selector in css


def test_job_recovery_is_fenced_off_from_admin_bridge_hydration_and_refresh() -> None:
    integration = _read("static/portal/integration.js")
    api = _read("copyfast_api.py")

    predicate = _function_source(integration, "isNativeAdminJobRecoveryGuidePath")
    assert '=== "/admin/job-recovery-guide"' in predicate
    bridge_target = _function_source(integration, "adminBridgeTargetForPath")
    assert "if (isNativeAdminJobRecoveryGuidePath(normalized))" in bridge_target
    assert 'return { endpoint: "", module: "job-recovery-guide", requestedModule: "job-recovery-guide", recordId: "", supported: false };' in bridge_target
    assert "record_id=job-recovery-guide" not in bridge_target
    assert "return target.supported ? api(target.endpoint) : localAdminCompatibilityGuard(target);" in integration

    current_guard = _function_source(integration, "canonicalAdminDataRequestIsCurrent")
    admin_hydrator = _function_source(integration, "hydrateCanonicalAdminData")
    generic_hydrator = _function_source(integration, "hydrateCanonicalData")
    for source in (current_guard, admin_hydrator, generic_hydrator):
        assert "isNativeAdminJobRecoveryGuidePath" in source
    assert "!isNativeAdminJobRecoveryGuidePath(currentPath)" in integration
    assert '"/admin/job-recovery-guide": account ? "read_only" : "guarded"' in integration

    refresh = integration[integration.index('if (action === "refresh-admin")'):integration.index('if (action === "admin-retry"')]
    assert "isNativeAdminJobRecoveryGuidePath(path)" in refresh
    assert "không có làm mới, clear, retry, refund hay control action trong browser" in refresh

    api_modules = api[api.index("ADMIN_BRIDGE_MODULES"):api.index("ADMIN_BRIDGE_MODULE_ALIASES")]
    assert "job_recovery_guide" not in api_modules
    assert "job-recovery-guide" not in api_modules


def test_job_recovery_audit_contract_is_finite_and_keeps_mutations_out_of_the_browser() -> None:
    audit = _read("scripts/migration/audit_bot_to_web.py")
    contract = _read("docs/migration/JOB_LOCK_RECOVERY_CALLBACK_CONTRACT.md")

    for declaration in (
        "JOB_LOCK_RECOVERY_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS",
        '"JOB_LOCK_RECOVERY_CALLBACK_CONTRACT.md"',
        "reviewed_job_lock_recovery_fresh_web_navigation",
        "NO_BOT_JOB_OR_USER_IDENTIFIER_TRANSFER",
        "NO_JOB_CLEAR_RETRY_REFUND_OR_CHARGE_ACTION",
        "NO_PROVIDER_WORKER_RUNTIME_CONTROL",
        "NO_PAYOS_WALLET_LEDGER_ACTION",
    ):
        assert declaration in audit

    registry = audit[
        audit.index("JOB_LOCK_RECOVERY_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS"):
        audit.index("JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_BASE_DISPOSITIONS")
    ]
    assert '"menu|clear_stale_jobs_help": {' in registry
    for excluded in (
        "menu|admin_confirm_clear_stale_jobs",
        "menu|admin_confirm_ack_clear_stale_jobs",
        "menu|admin_confirm_refund_job",
        "menu|admin_confirm_ack_refund_job",
        "menu|clear_*",
    ):
        assert f'"{excluded}":' not in registry

    source_review = audit[
        audit.index("JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_ACTIONS"):
        audit.index("MENU_ACTION_REGISTRY: dict")
    ]
    for callback in (
        "menu|admin_confirm_clear_stale_jobs",
        "menu|admin_confirm_ack_clear_stale_jobs",
        "menu|admin_confirm_refund_job",
        "menu|admin_confirm_ack_refund_job",
    ):
        assert callback in source_review
    for command in ("clear_job_lock", "refund_job"):
        assert command in source_review

    assert "The one guidance row opens only the exact `/admin/job-recovery-guide` page" in contract
    assert "not a queue console, job read model" in contract
    assert "canonical mutation source-review records" in contract
    assert "The Web must not expose, copy, parse or replay them" in contract
