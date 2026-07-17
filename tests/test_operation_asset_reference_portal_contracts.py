"""Static contracts for typed Asset Vault pickers in native operations.

These contracts intentionally cover the client boundary rather than merely
asserting that a select has options.  A signed account with hundreds of
private files must be able to search and page PDF/image references without
losing a selection when it leaves the current page.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")


def test_document_and_image_operation_pickers_keep_independent_typed_reference_state() -> None:
    # Do not reuse the general Asset Vault's 50-item page.  Document has two
    # independent typed lists because image-to-PDF needs image references,
    # while PDF operations need documents.  Resize/edit have their own image
    # state so a document search cannot reset an image form.
    for token in (
        "OPERATION_ASSET_REFERENCE_LIST_LIMIT",
        "OPERATION_ASSET_REFERENCE_MAX_LIST_OFFSET",
        "documentAssetReferences",
        "imageOperationAssetReferences",
        "pinned_pdf",
        "pinned_image",
        "reference_kind",
        "hydrateDocumentAssetReferences(kind, filterValue, offsetValue, selectedIds)",
        "hydrateImageOperationAssetReferences(filterValue, offsetValue, selectedIds)",
    ):
        assert token in INTEGRATION

    # A server-selected reference type remains part of the signed API query;
    # the browser must not download an arbitrary library page and infer MIME.
    assert '"pdf"' in INTEGRATION
    assert '"image"' in INTEGRATION


def test_operation_picker_filter_page_actions_preserve_selected_metadata_across_pages() -> None:
    combined = INTEGRATION + "\n" + PORTAL
    action_tokens = (
        "document-asset-reference-filter",
        "document-asset-reference-filter-clear",
        "document-asset-reference-page",
        "image-operation-asset-reference-filter",
        "image-operation-asset-reference-filter-clear",
        "image-operation-asset-reference-page",
    )
    for token in action_tokens:
        # The signed dispatcher must know the concrete action string.
        assert token in INTEGRATION
    # The renderer constructs the concrete strings from these two scoped
    # prefixes, which avoids duplicating operation-action vocabulary.
    for token in ("document-asset-reference", "image-operation-asset-reference", '"-filter"', '"-filter-clear"', '"-page"'):
        assert token in PORTAL
    for token in (
        "__documentAssetReferenceOffset",
        "__imageOperationAssetReferenceOffset",
        "__documentAssetReferenceSelections",
        "__imageOperationAssetReferenceSelections",
    ):
        assert token in combined

    for token in ("documentAssetReferences", "imageOperationAssetReferences", "__documentAssetReferenceSelections", "__imageOperationAssetReferenceSelections"):
        assert token in PORTAL

    def function_block(signature: str) -> str:
        start = INTEGRATION.index(signature)
        next_start = INTEGRATION.find("\n  async function ", start + len(signature))
        return INTEGRATION[start:] if next_start < 0 else INTEGRATION[start:next_start]

    document_hydrator = function_block("async function hydrateDocumentAssetReferences(")
    image_hydrator = function_block("async function hydrateImageOperationAssetReferences(")
    # Pins are server-returned safe metadata.  They make a multi-source merge
    # or a chosen image remain visible after searching or paging, without
    # persisting private IDs to localStorage or inventing a browser path.
    for source in (document_hydrator, image_hydrator):
        assert "selectedIds" in source
        assert "localStorage" not in source
    assert "pinned_pdf" in INTEGRATION
    assert "pinned_image" in INTEGRATION
    assert "pinned" in INTEGRATION


def test_asset_vault_and_typed_pickers_ignore_stale_private_responses() -> None:
    """A late file list must not cross a signed session or operation route."""

    for epoch in ("assetVaultSessionEpoch", "assetVaultListHydrationEpoch", "imageOperationAssetReferenceHydrationEpoch"):
        assert f"++{epoch}" in INTEGRATION
    assert "documentAssetReferenceHydrationEpoch.pdf += 1;" in INTEGRATION
    assert "documentAssetReferenceHydrationEpoch.image += 1;" in INTEGRATION

    for helper, requirements in (
        (
            "assetVaultRequestIsCurrent",
            ("sessionEpoch === assetVaultSessionEpoch", "currentPortalPath() === expectedPath", "isAssetVaultReadPath(expectedPath)", "base().assetVaultEnabled === true"),
        ),
        (
            "documentAssetReferenceRequestIsCurrent",
            ("sessionEpoch === assetVaultSessionEpoch", "documentAssetReferenceKindForPath(expectedPath) === kind", "base().assetVaultEnabled === true"),
        ),
        (
            "imageOperationAssetReferenceRequestIsCurrent",
            ("sessionEpoch === assetVaultSessionEpoch", "IMAGE_OPERATION_ASSET_REFERENCE_ROUTES.has(expectedPath)", "base().assetVaultEnabled === true"),
        ),
    ):
        start = INTEGRATION.index(f"function {helper}")
        end = INTEGRATION.index("\n  function ", start + 1)
        source = INTEGRATION[start:end]
        for requirement in requirements:
            assert requirement in source

    asset_start = INTEGRATION.index("async function hydrateAssetVault(")
    document_start = INTEGRATION.index("async function hydrateDocumentAssetReferences(")
    image_start = INTEGRATION.index("async function hydrateImageOperationAssetReferences(")
    asset = INTEGRATION[asset_start:document_start]
    document = INTEGRATION[document_start:image_start]
    image = INTEGRATION[image_start:INTEGRATION.index("async function hydrateCurrentOperationAssetReferences(", image_start)]
    assert "const requestEpoch = ++assetVaultListHydrationEpoch;" in asset
    assert "if (!assetVaultRequestIsCurrent(requestEpoch, sessionEpoch, expectedPath)) return [];" in asset
    assert "documentAssetReferenceRequestIsCurrent(selectedKind, epoch, sessionEpoch, expectedPath)" in document
    assert "imageOperationAssetReferenceRequestIsCurrent(epoch, sessionEpoch, expectedPath)" in image
