"""Focused contracts for the canonical /documents operations board."""

from pathlib import Path
from functools import lru_cache
import subprocess


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "DOCUMENT_OPERATIONS_BOARD_CONTRACT.md").read_text(encoding="utf-8")
NAVIGATION = (ROOT / "docs" / "migration" / "DOCUMENT_COMMAND_NAVIGATION_CONTRACT.md").read_text(encoding="utf-8")


def board_surface() -> str:
    return PORTAL[
        PORTAL.index("function renderDocumentHub(page, context)"):
        PORTAL.index("function renderPdfSplit(page, context)")
    ]


def test_documents_remains_the_canonical_board_without_a_duplicate_document_hub() -> None:
    assert 'customerPage("/documents", "Document Studio"' in PORTAL
    assert 'layout: "document-hub", type: "document-hub", action: "none"' in PORTAL
    assert 'case "document-hub": return renderDocumentHub(page, context);' in PORTAL
    assert 'customerPage("/document-hub"' not in PORTAL
    assert "/doc_tools" in NAVIGATION
    assert "/documents" in NAVIGATION
    assert "NAVIGATION_ONLY" in NAVIGATION


def test_document_board_uses_the_existing_combined_owner_scoped_reader_only() -> None:
    surface = board_surface()
    for token in (
        'const readState = String(context.documentOperationsReadState || "guarded");',
        'documentOperationItems(context, "")',
        "documentOperationHistoryListing(context)",
        "renderDocumentOperationCards(operations",
        "renderDocumentOperationHistoryPagination(context, canView, activePath)",
        'data-portal-action="document-operation-refresh"',
        'href="/asset-vault"',
        'href="/document-workspace"',
    ):
        assert token in surface
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "URLSearchParams", "source_asset_id", "provider_request"):
        assert forbidden not in surface


@lru_cache(maxsize=1)
def _rendered_board_checks() -> None:
    result = subprocess.run(
        ["node", "--test", "--test-name-pattern", "Documents presents vertical", str(ROOT / "tests/documents-product-controls.test.mjs")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_document_board_keeps_truthful_loading_failure_guard_and_download_boundaries() -> None:
    surface = board_surface()
    for token in (
        'if (!canView)',
        'if (readState === "loading")',
        'if (readState !== "ready")',
        'uiText("documentAccessUiHeading"',
        'uiText("documentAccessUiBody"',
        "Không cache private",
        "Không có URL công khai",
    ):
        assert token in surface
    assert "bridge_request" not in surface
    assert "CORE_BRIDGE" not in surface
    assert "download_ready === true" in PORTAL
    assert "document-operation-page" in PORTAL
    _rendered_board_checks()


def test_document_board_groups_workflows_and_keeps_guarded_navigation_explanatory() -> None:
    surface = board_surface()
    for token in (
        'data-document-tool-state="${state}"',
        "<h3>${safeText(item.title)}</h3>",
        'aria-labelledby="document-workflow-${safeText(group.key)}"',
    ):
        assert token in surface
    assert "aria-disabled" not in surface
    _rendered_board_checks()


def test_document_board_hydration_is_existing_signed_api_with_root_state_reset() -> None:
    for token in (
        '"/documents": account && assetVaultEnabled && documentOperationsEnabled ? "processing" : "guarded"',
        '"/documents/pdf": account && assetVaultEnabled && documentOperationsEnabled ? "processing" : "guarded"',
        'documentOperationsReadState: account && assetVaultEnabled && documentOperationsEnabled ? "loading" : "guarded"',
        'const documentOperationsBoardRoute = currentPath === "/documents" || currentPath === "/documents/pdf";',
        "if (documentOperationsBoardRoute) await hydrateDocumentOperations();",
        'documentOperationsReadState: "ready"',
        'documentOperationsReadState: "failed"',
        '"/documents": "ready"',
        '"/documents": "guarded"',
        "function documentOperationHistoryPath(kind, offset)",
        'return "/document-operations?" + query.toString();',
    ):
        assert token in INTEGRATION
    hydration = INTEGRATION[
        INTEGRATION.index("async function hydrateDocumentOperations(offsetValue)"):
        INTEGRATION.index("async function hydrateImageOperations(offsetValue)")
    ]
    assert "bridge_request" not in hydration
    assert "CORE_BRIDGE" not in hydration
    assert "localStorage" not in hydration


def test_document_board_refresh_and_pagination_are_route_scoped_and_do_not_need_vault_on_board() -> None:
    actions = INTEGRATION[
        INTEGRATION.index('if (action === "document-operation-refresh")'):
        INTEGRATION.index('if (action === "project-package-export")')
    ]
    for token in (
        "const isDocumentBoard = documentPath === \"/documents\" || documentPath === \"/documents/pdf\";",
        "route !== documentPath",
        '"document-operation-refresh"',
        'if (action === "document-operation-page")',
    ):
        assert token in actions
    assert "api(\"/document-operations" not in actions
    # Execute the real action/hydrators: root refresh must not read the vault,
    # child refresh must, failed reads cannot report success, stale reads quiet.
    result = subprocess.run(
        ["node", "--test", str(ROOT / "tests/document-refresh-feedback.test.mjs")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_document_board_is_explicitly_private_in_pwa_and_app_first_responsive() -> None:
    assert '"/documents",' in SERVICE_WORKER
    assert '"/" + "api/v1/document-operations"' in SERVICE_WORKER
    for token in (
        ".portal-document-hub .portal-document-operation-intro",
        ".portal-document-board-action-grid",
        ".portal-document-board-workflow-group",
        ".portal-document-hub .portal-module-card[data-document-tool-state=\"guarded\"]",
        ".portal-document-hub .portal-module-heading h3",
        "min-height: 44px",
        "@media (prefers-reduced-motion: reduce)",
        ".portal-document-board-action:focus-visible",
        ".portal-document-hub .portal-module-card:focus-visible",
    ):
        assert token in CSS
    assert "linear-gradient" not in CSS[CSS.index("/* Document Operations Board"):]


def test_document_board_contract_records_existing_authority_and_non_goals() -> None:
    for token in (
        "`/documents`",
        "`/documents/pdf`",
        "GET /api/v1/document-operations?limit=50&offset=…",
        "kind` is omitted",
        "owner-scoped",
        "Asset Vault",
        "Document Workspace",
        "Telegram-only",
        "PayOS",
        "No source PDF/image bytes",
        "service-worker private-path policy",
        "44px mobile controls",
    ):
        assert token in CONTRACT
