"""Focused presentation contracts for the private Admin Document Archive.

The archive API owns the authoritative signed-admin, CSRF, owner, revision,
idempotency and binary-integrity checks.  These checks ensure that the Portal
does not accidentally reduce that design to a browser-owned ERP mock, a Bot
adapter, or an unsafe file link while rendering the Web-native workspace.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_admin_document_archive_routes_render_private_list_and_detail_workspaces() -> None:
    portal = _read("static/portal/portal.js")

    for requirement in (
        'adminPage("/admin/internal-documents", "Kho hồ sơ nội bộ"',
        'layout: "admin-document-archive"',
        'path: "/admin/internal-documents/documents/:id"',
        'layout: "admin-document-archive-detail"',
        'case "admin-document-archive": return renderAdminDocumentArchive(page, context);',
        'case "admin-document-archive-detail": return renderAdminDocumentArchiveDetail(page, context);',
        'if (linkPath === "/admin/internal-documents") return matchesRouteFamily(path, "/admin/internal-documents");',
    ):
        assert requirement in portal

    list_view = _between(
        portal,
        "function renderAdminDocumentArchive(page, context)",
        "function renderAdminDocumentArchiveDetail(page, context)",
    )
    for action in (
        "archive-documents-filter",
        "archive-documents-filter-clear",
        "archive-documents-refresh",
        "archive-documents-page",
        "archive-document-create-upload",
    ):
        assert f'data-portal-action="{action}"' in list_view or f'data-portal-action="{action}"' in portal
    assert list_view.count("data-portal-no-transient") >= 1
    assert "PDF, DOCX hoặc TXT" in list_view or "PDF/DOCX/TXT" in list_view
    assert "Bot internal_documents" in portal
    assert "localStorage." not in list_view
    assert "sessionStorage." not in list_view

    detail_view = _between(portal, "function renderAdminDocumentArchiveDetail(page, context)", "function renderLegal")
    for action in (
        "archive-document-update",
        "archive-document-version-upload",
        "archive-document-download-current",
        "archive-document-download-version",
    ):
        assert f'data-portal-action="{action}"' in detail_view or f'data-portal-action="{action}"' in portal
    assert "adminArchiveLifecycleForm(document, 'archive'" in detail_view
    assert "adminArchiveLifecycleForm(document, 'restore'" in detail_view
    assert detail_view.count("data-portal-no-transient") >= 1
    assert "data-portal-confirm" in detail_view


def test_admin_document_archive_bootstrap_is_a_strict_safe_projection() -> None:
    portal = _read("static/portal/portal.js")
    projection = _between(
        portal,
        "const ADMIN_ARCHIVE_BOOTSTRAP_READ_STATES",
        "function normalizeAssetVaultLifecycle",
    )

    for requirement in (
        "function normalizeAdminArchiveBootstrap",
        "function normalizeAdminArchiveBootstrapDocument",
        "function normalizeAdminArchiveBootstrapVersion",
        "adminDocumentArchiveEnabled: adminArchive.enabled",
        "adminDocumentArchiveAdminSessionHint",
    ):
        assert requirement in portal
    # Do not let a server response turn the Portal into a holder of archive
    # storage internals or historical Telegram attachment identifiers.
    for forbidden in (
        "storageKey",
        "storage_key",
        "sha256",
        "objectKey",
        "object_key",
        "telegramFileId",
        "telegram_file_id",
        "chatId",
        "chat_id",
    ):
        assert forbidden not in projection


def test_admin_document_archive_hydration_and_mutation_contract_stay_web_native() -> None:
    integration = _read("static/portal/integration.js")
    archive = _between(
        integration,
        "const ADMIN_ARCHIVE_DOCUMENT_STATES",
        "function dataControlsRequestIsCurrent",
    )

    for requirement in (
        "adminArchiveDocumentIdFromPath",
        "isNativeAdminArchivePath",
        "adminArchiveBoundaryIsSafe",
        'execution === "web_native_admin_internal_document_archive_only"',
        'data_origin === "web_admin_archive_tables_and_private_volume_only"',
        'external_effects === "none"',
        'legacy_bot_scope === "TELEGRAM_ONLY"',
        'api("/admin/internal-documents/policy")',
        'api("/admin/internal-documents/summary")',
        "/admin/internal-documents/documents/",
        "adminArchiveDocumentProjection",
        "adminArchiveVersionProjection",
        "adminArchiveEventProjection",
        'clearAdminArchiveProjection("guarded")',
        "adminDocumentArchiveEnabled",
        "adminDocumentArchiveAdminSessionHint",
    ):
        assert requirement in integration or requirement in archive

    # Uploads and lifecycle writes must use the server's CSRF/idempotency and
    # compare-and-set contracts; an admin-looking browser state is never enough.
    for requirement in (
        "new FormData()",
        '"Idempotency-Key"',
        "expected_revision",
        "acknowledgement",
        "confirm: true",
        "ARCHIVE INTERNAL DOCUMENT",
        "RESTORE INTERNAL DOCUMENT",
        "hydrateAdminArchiveDocumentDetail",
    ):
        assert requirement in integration

    # The archive is not a Core Bridge, wallet/payment/job surface and cannot
    # persist an upload draft in browser storage.
    for forbidden in (
        "/internal/v1/",
        'api("/wallet',
        'api("/payments',
        'api("/jobs',
        "localStorage.",
        "sessionStorage.",
    ):
        assert forbidden not in archive


def test_admin_document_archive_download_is_private_and_browser_fail_closed() -> None:
    integration = _read("static/portal/integration.js")
    archive = _between(
        integration,
        "const ADMIN_ARCHIVE_DOCUMENT_STATES",
        "function dataControlsRequestIsCurrent",
    )

    # The Portal may create a local object URL only after the response proves
    # it is the private, no-store attachment expected by the archive contract.
    normalized = archive.lower()
    for requirement in (
        "content-disposition",
        "attachment",
        "cache-control",
        "no-store",
        "response.blob()",
        "url.createobjecturl",
        "url.revokeobjecturl",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ):
        assert requirement in normalized
    assert "window.open(" not in archive

    app = _read("app.py")
    worker = _read("static/portal/service-worker.js")
    navigation = _read("copyfast_admin_erp_navigation.py")
    backend = _read("copyfast_admin_document_archive.py")

    for requirement in (
        "import copyfast_admin_document_archive",
        "app.include_router(copyfast_admin_document_archive.router)",
        'normalized == "/admin/internal-documents" or normalized.startswith("/admin/internal-documents/")',
        "copyfast_auth.require_admin(request)",
    ):
        assert requirement in app
    assert '"/" + "api/v1/admin/internal-documents"' in worker
    assert '"/admin/internal-documents"' in worker
    assert "internal_document_archive" in navigation
    assert '"/admin/internal-documents"' in navigation
    assert "WEBAPP_ADMIN_DOCUMENT_ARCHIVE_ENABLED" in navigation
    assert "Depends(require_admin_csrf)" in backend
    assert "expected_revision" in backend
    assert "ACKNOWLEDGEMENTS" in backend
    assert "Cache-Control" in backend
    assert "no-store" in backend
