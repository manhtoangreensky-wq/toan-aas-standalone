"""Focused browser contracts for the private Asset Vault lifecycle panel.

The endpoint implementation and migration safety live in
``test_asset_vault_lifecycle.py``.  These checks keep the Portal side honest:
one signed owner can inspect a redacted lifecycle and make archive/restore
requests with a freshly read revision, never with browser-held authority.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    finish = source.index(end, begin)
    return source[begin:finish]


def test_asset_vault_lifecycle_panel_is_selected_redacted_and_honest() -> None:
    panel = _between(PORTAL, "function assetVaultLifecyclePanel", "function assetVaultFormFields")

    for action in ("asset-vault-lifecycle-restore", "asset-vault-lifecycle-close"):
        assert f'data-portal-action="{action}"' in panel

    assert 'state === "archived" && lifecycle.restore_available === true' in panel
    assert "Number.isInteger(revision) && revision >= 1" in panel
    assert 'data-portal-confirm="Khôi phục tệp này vào Asset Vault đang hoạt động?' in panel
    assert "Server sẽ kiểm tra integrity trước khi cho phép tải lại." in panel
    assert "reference_summary" in panel
    assert "support_evidence_retention" in panel
    assert "Không hiển thị path, hash, storage key, case hay operation ID." in panel
    assert "không tạo download/khôi phục giả" in panel

    # The selected panel must receive only a deliberately redacted projection,
    # never blob location/hash or cross-domain identifiers.
    for private_field in ("storage_key", "sha256", "case_id", "operation_id", "localStorage.", "sessionStorage."):
        assert private_field not in panel


def test_asset_vault_cards_expose_inspection_for_active_and_archived_items() -> None:
    view = _between(PORTAL, "function renderAssetVault", "const SUPPORT_CASE_STATES")
    assert 'const canInspectLifecycle = Boolean(context.capabilities && context.capabilities["asset-vault-lifecycle-view"] === true);' in view
    assert "const lifecyclePanel = assetVaultLifecyclePanel(context, items, canRestore);" in view
    assert 'data-portal-action="asset-vault-lifecycle-open"' in view
    assert 'Tệp đã lưu trữ; tải về đang khóa.</span>${inspect}' in view
    assert "${cards}${lifecyclePanel}${renderAssetVaultPagination(listing)}" in view


def test_asset_vault_lifecycle_read_is_route_session_and_selection_fenced() -> None:
    for epoch in ("assetVaultSessionEpoch", "assetVaultLifecycleHydrationEpoch"):
        assert f"let {epoch} = 0;" in INTEGRATION
        assert f"++{epoch};" in INTEGRATION

    fence = _between(INTEGRATION, "function assetVaultLifecycleRequestIsCurrent", "function clearAssetVaultLifecycle")
    for requirement in (
        "requestEpoch === assetVaultLifecycleHydrationEpoch",
        "sessionEpoch === assetVaultSessionEpoch",
        "currentPortalPath() === expectedPath",
        'expectedPath === "/asset-vault"',
        "assetVaultLifecycleSelectionId() === assetId",
        "base().assetVaultEnabled === true",
        "base().session && base().session.authenticated === true",
    ):
        assert requirement in fence

    hydrator = _between(INTEGRATION, "async function hydrateAssetVaultLifecycle", "async function hydrateDocumentAssetReferences")
    assert 'api(`/asset-vault/${encodeURIComponent(selectedAssetId)}/lifecycle`)' in hydrator
    assert "assetVaultLifecycleProjection(result.data && result.data.lifecycle)" in hydrator
    assert 'readState: "loading"' in hydrator
    assert 'readState: "ready"' in hydrator
    assert 'readState: "guarded"' in hydrator
    assert "No asset ID or" in hydrator
    assert "browser storage or cache" in hydrator
    assert "localStorage." not in hydrator
    assert "sessionStorage." not in hydrator
    assert 'assetVaultLifecycle: emptyAssetVaultLifecycle(account && assetVaultEnabled ? "idle" : "guarded")' in INTEGRATION


def test_asset_vault_archive_restore_use_fresh_revisions_and_owner_refresh() -> None:
    actions = _between(
        INTEGRATION,
        'if (action === "asset-vault-archive")',
        'if (["document-asset-reference-filter",',
    )

    for requirement in (
        'api(`/asset-vault/${encodeURIComponent(assetId)}/archive`',
        'headers: { "Content-Type": "application/json", "Idempotency-Key": submission.key }',
        "body: JSON.stringify({ expected_revision: expectedRevision })",
        'api(`/asset-vault/${encodeURIComponent(assetId)}/restore`',
        'body: JSON.stringify({ expected_revision: expectedRevision, idempotency_key: submission.key })',
        "const lifecycle = await hydrateAssetVaultLifecycle(assetId);",
        "Number.isInteger(expectedRevision) || expectedRevision < 1",
        "Promise.all([hydrateAssetVault(), hydrateAssetVaultLifecycle(assetId)])",
        "discardSubmission(`asset-vault:${assetId}:archive`, submission)",
        "discardSubmission(`asset-vault:${assetId}:restore`, submission)",
        "clearAssetVaultLifecycle();",
    ):
        assert requirement in actions

    assert 'action === "asset-vault-lifecycle-open"' in actions
    assert 'action === "asset-vault-lifecycle-close"' in actions
    assert 'action === "asset-vault-lifecycle-restore"' in actions


def test_asset_vault_lifecycle_survives_the_portal_bootstrap_projection() -> None:
    """A successful owner-scoped lifecycle read must not disappear on remount."""

    projection = _between(PORTAL, "function normalizeAssetVaultLifecycle", "function normalizeAccountSecurityBootstrap")
    for requirement in (
        "validVaultAssetId(source.asset_id)",
        "ASSET_VAULT_LIFECYCLE_STATES",
        "ASSET_VAULT_LIFECYCLE_REASONS",
        "ASSET_VAULT_LIFECYCLE_REFERENCE_REASONS",
        "lifecycle_revision",
        "restore_available: state === \"archived\"",
        "reference_summary",
        "readState: \"guarded\"",
    ):
        assert requirement in projection

    # The presentation boundary may retain only the redacted lifecycle panel;
    # never a private storage location, integrity hash, support case, or an
    # operation/database identifier.
    for private_field in ("storage_key", "sha256", "case_id", "operation_id", "session_id", "localStorage.", "sessionStorage."):
        assert private_field not in projection

    bootstrap = _between(PORTAL, "function normalizeBootstrap", "function getBootstrap")
    assert "assetVaultLifecycle: normalizeAssetVaultLifecycle(source.assetVaultLifecycle)" in bootstrap
    assert "assetVaultEnabled: source.assetVaultEnabled === true" in bootstrap
