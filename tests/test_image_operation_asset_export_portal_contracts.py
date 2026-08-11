"""Static Portal and API contracts for Image Operation Asset Vault export."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
API = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
OPERATIONS = (ROOT / "copyfast_image_operations.py").read_text(encoding="utf-8")


ACTION = 'image-operation-export-to-asset-vault'
CONTINUATION_ACTION = 'image-operation-export-to-content-handoff'
ROUTE_SUFFIX = "/export-to-asset-vault"


def _action_source() -> str:
    return _export_actions_source()


def _export_actions_source() -> str:
    marker = f'if (["{ACTION}", "{CONTINUATION_ACTION}"].includes(action))'
    assert marker in INTEGRATION
    start = INTEGRATION.index(marker)
    following = re.search(r"\n\s*if \(action === ", INTEGRATION[start + len(marker):])
    end = len(INTEGRATION) if following is None else start + len(marker) + following.start()
    return INTEGRATION[start:end]


def _route_source() -> str:
    marker = '@router.post("/{operation_id}/export-to-asset-vault")'
    assert marker in OPERATIONS
    start = OPERATIONS.index(marker)
    next_route = OPERATIONS.find("\n@router.", start + len(marker))
    return OPERATIONS[start:] if next_route < 0 else OPERATIONS[start:next_route]


def test_portal_exposes_one_explicit_confirmed_export_action_only_for_verified_completed_pngs() -> None:
    attribute = f'data-portal-action="{ACTION}"'
    assert attribute in PORTAL
    position = PORTAL.index(attribute)
    action_markup = PORTAL[max(0, position - 2400):position + 2400]
    assert "data-portal-confirm=" in action_markup
    assert "download_ready" in PORTAL
    assert '"completed"' in PORTAL
    assert "image_operation_export_enabled" in API
    assert (
        '"image-operation-export-to-asset-vault": Boolean(account && me.csrf_token && assetVaultEnabled '
        "&& imageOperationsEnabled && imageOperationExportEnabled)"
    ) in INTEGRATION


def test_portal_offers_a_separate_gated_image_export_to_content_handoff_action() -> None:
    marker = "function imageOperationAssetExportControl(item, context)"
    assert marker in PORTAL
    start = PORTAL.index(marker)
    control = PORTAL[start:PORTAL.index("function storyboardGridDownloadPath", start)]
    assert f'data-portal-action="{ACTION}"' in control
    assert f'data-portal-action="{CONTINUATION_ACTION}"' in control
    assert 'context.capabilities["content-handoff-create"] === true' in control
    assert "Lưu & chuẩn bị bàn giao" in control
    assert "imageOperationState(item) === \"completed\"" in control
    assert "item.download_ready === true" in control


def test_image_export_handoff_reuses_the_fence_and_navigates_only_from_active_receipt() -> None:
    action = _export_actions_source()
    assert "const preparingContentHandoff = action === \"image-operation-export-to-content-handoff\"" in action
    assert '"content-handoff-create"' in action
    assert "/image-operations/${encodeURIComponent(operationId)}/export-to-asset-vault" in action
    assert 'assetState !== "active"' in action
    assert "contentHandoffDraftPath(asset.id)" in action
    assert "window.location.assign(handoffPath)" in action
    assert "/content-handoffs/records" not in action
    for forbidden in ("provider", "bridge", "telegram", "bot", "wallet", "payment", "payos"):
        assert forbidden not in action.lower()


def test_portal_event_extraction_accepts_both_image_export_actions() -> None:
    marker = f'if (["{ACTION}", "{CONTINUATION_ACTION}"].includes(action))'
    assert marker in PORTAL
    start = PORTAL.index(marker)
    source = PORTAL[start:PORTAL.index('if (String(action || "").startsWith("image-enhance-operation-"))', start)]
    assert "__imageOperationId" in source
    assert "data-image-operation-id" in source


def test_portal_export_handler_has_only_an_opaque_same_origin_csrf_idempotent_request() -> None:
    action = _action_source()
    assert "validImageOperationId(operationId)" in action
    assert "encodeURIComponent(operationId)" in action
    assert ROUTE_SUFFIX in action
    assert "api(" in action
    assert '"Idempotency-Key": submission.key' in action
    assert "hydrateAssetVault" in action
    # The API reads a fresh lifecycle receipt after finalization. A concurrent
    # integrity transition is truthful `unavailable`, not an invalid browser
    # receipt or a reason to fabricate a second copy.
    assert '"unavailable"' in action
    for forbidden in (
        "fetch(",
        "blob",
        "arraybuffer",
        "filereader",
        "formdata",
        "provider",
        "bridge",
        "telegram",
        "bot",
        "wallet",
        "payment",
        "payos",
        "storage_key",
        "sha256",
        "source_asset_id",
    ):
        assert forbidden not in action.lower()


def test_export_endpoint_requires_csrf_and_a_server_published_capability() -> None:
    route = _route_source()
    assert "Depends(require_csrf)" in route
    assert '"Idempotency-Key"' in route
    assert "WEBAPP_IMAGE_OPERATION_EXPORT_ENABLED" in API
    assert "export-to-asset-vault" not in (ROOT / "copyfast_bridge.py").read_text(encoding="utf-8")


def test_export_route_has_a_narrow_post_rate_limit_before_private_work() -> None:
    assert "image_operation_asset_export" in APP
    start = APP.index("image_operation_asset_export")
    predicate = APP[start:start + 1500]
    assert 'request.method == "POST"' in predicate
    assert '"/api/v1/image-operations/"' in predicate
    assert '"/export-to-asset-vault"' in predicate
    assert "if image_operation_asset_export:" in APP
    assert 'else "image-operation-asset-export" if image_operation_asset_export' in APP


def test_pwa_never_caches_private_image_operation_export_requests_or_outputs() -> None:
    shell_start = SERVICE_WORKER.index("const SHELL =")
    shell_end = SERVICE_WORKER.index("const SHELL_PATHS", shell_start)
    shell = SERVICE_WORKER[shell_start:shell_end]
    assert "/api/v1/image-operations" not in shell
    assert "SHELL_PATHS" in SERVICE_WORKER
    assert "PRIVATE_PATH_PREFIXES" in SERVICE_WORKER
    assert 'request.method !== "GET"' in SERVICE_WORKER
    assert "url.origin !== self.location.origin" in SERVICE_WORKER
