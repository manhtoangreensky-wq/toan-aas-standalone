"""Portal contracts for the redacted Admin Audit Explorer."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_admin_audit_uses_the_redacted_web_native_endpoint() -> None:
    integration = _read("static/portal/integration.js")
    portal = _read("static/portal/portal.js")
    app = _read("app.py")

    assert "import copyfast_admin_audit" in app
    assert "app.include_router(copyfast_admin_audit.router)" in app
    assert 'return "/admin/audit-events?" + query.toString();' in integration
    assert "api(adminAuditListPath(filter, offset))" in integration
    assert "function normalizedAdminAudit(data)" in integration
    assert "path === \"/admin/audit\"" in integration
    assert "await hydrateAdminAudit();" in integration
    assert "function renderAdminAuditExplorer(context)" in portal
    assert "Không có account ID, Telegram ID, request ID, target, detail, token" in portal


def test_admin_audit_portal_never_binds_raw_audit_identity_or_detail_fields() -> None:
    integration = _read("static/portal/integration.js")
    backend = _read("copyfast_admin_audit.py")

    assert "account_id" not in integration[integration.index("function normalizedAdminAudit(data)"):integration.index("async function hydrateLinkStatus")]
    assert "canonical_user_id" not in integration[integration.index("function normalizedAdminAudit(data)"):integration.index("async function hydrateLinkStatus")]
    assert "request_id" not in integration[integration.index("function normalizedAdminAudit(data)"):integration.index("async function hydrateLinkStatus")]
    assert "SELECT action, outcome, created_at" in backend
    assert "account_id, canonical_user_id" not in backend[backend.index("SELECT action, outcome, created_at"):]
    assert "@router.post" not in backend


def test_admin_audit_filter_and_page_controls_keep_an_isolated_safe_receipt() -> None:
    """Audit paging is a redacted read receipt, never generic admin state."""

    integration = _read("static/portal/integration.js")
    portal = _read("static/portal/portal.js")
    backend = _read("copyfast_admin_audit.py")

    for fragment in (
        "const ADMIN_AUDIT_LIST_LIMIT = 50;",
        "const ADMIN_AUDIT_MAX_LIST_OFFSET = 10000;",
        "function adminAuditFilterPayload(value)",
        "function adminAuditListOffset(value)",
        "function adminAuditListPath(filter, offset)",
        "function adminAuditListingProjection(filter, offset, source, returned)",
        "adminAuditListing:",
        'if (action === "admin-audit-filter" || action === "admin-audit-filter-clear" || action === "admin-audit-page")',
        "__adminAuditOffset",
        "data.has_more === true",
        "next_offset",
        "previous_offset",
        "adminAuditSessionEpoch",
        "adminAuditHydrationEpoch",
    ):
        assert fragment in integration

    for fragment in (
        "function normalizeAdminAuditProjection(raw)",
        "function normalizeAdminAuditListing(raw)",
        "function adminAuditListing(context)",
        "function renderAdminAuditPagination(listing, enabled)",
        'data-portal-action="admin-audit-filter"',
        "admin-audit-filter-clear",
        'data-portal-action="admin-audit-page"',
        "data-admin-audit-offset",
        "data-portal-no-transient",
        "renderAdminAuditPagination(listing, canRequest)",
    ):
        assert fragment in portal

    assert "offset: int = Query(0, ge=0, le=10000)" in backend
    assert "LIMIT ? OFFSET ?" in backend
    assert "int(limit) + 1" in backend
    assert '"has_more": has_more' in backend
    assert '"next_offset": int(offset) + int(limit) if has_more else None' in backend

    normalizer_start = portal.index("function normalizeAdminAuditProjection(raw)")
    normalizer_end = portal.index("function normalizeAdminAuditListing(raw)", normalizer_start)
    projection = portal[normalizer_start:normalizer_end]
    for private_field in ("account_id", "canonical_user_id", "telegram_id", "request_id", "target", "detail", "provider", "payment"):
        assert f"item.{private_field}" not in projection
        assert f'item["{private_field}"]' not in projection
        assert f"source.{private_field}" not in projection

    listing_start = portal.index("function normalizeAdminAuditListing(raw)")
    listing_end = portal.index("function normalizeBootstrap(raw)", listing_start)
    listing = portal[listing_start:listing_end]
    assert "ADMIN_AUDIT_CATEGORY_KEYS.has(category)" in listing
    assert "nextOffset !== null" in listing
