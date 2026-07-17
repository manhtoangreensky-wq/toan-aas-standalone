"""Focused static contracts for the signed Web Free Prompt Gallery UI.

The Gallery snapshot stays read-only. This browser layer may filter, page,
show detail, copy a returned seed, and explicitly save the selected seed into
the signed owner's Memory Center. It must never turn the catalog into Bot,
provider, job, wallet/payment, asset, publish, delivery or browser-persisted
state.
"""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_free_prompt_gallery_has_a_signed_compact_portal_route() -> None:
    assert 'customerPage("/free-prompt-gallery", "Prompt Gallery miễn phí"' in PORTAL
    assert 'layout: "free-prompt-gallery", type: "free-prompt-gallery"' in PORTAL
    assert "function renderFreePromptGallery(page, context)" in PORTAL
    assert 'case "free-prompt-gallery": return renderFreePromptGallery(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="free-prompt-gallery-filter"' in PORTAL
    assert '["/free-prompt-gallery", "Prompt Gallery miễn phí", ICONS.prompt]' in PORTAL
    assert '"free-prompt-gallery"' in PORTAL


def test_gallery_presentation_requires_a_narrow_snapshot_contract_and_escapes_text() -> None:
    for helper in (
        "normalizeFreePromptGalleryCatalog",
        "normalizeFreePromptGalleryListing",
        "normalizeFreePromptGalleryDetail",
        "normalizeFreePromptGallerySaveResult",
        "normalizeFreePromptGalleryItem",
        "renderFreePromptGalleryCards",
        "renderFreePromptGalleryDetail",
        "renderFreePromptGallerySaveResult",
    ):
        assert f"function {helper}" in PORTAL
    for boundary in (
        'source.execution === "web_native_static_prompt_gallery"',
        "source.snapshot_read_only === true",
        "gallery_request_persisted",
        "provider_called",
        "bot_called",
        "bridge_called",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "asset_saved",
        "publish_action_created",
        "delivery_created",
    ):
        assert boundary in PORTAL
    start = PORTAL.index("function renderFreePromptGalleryCards")
    end = PORTAL.index("function renderFreePromptGallery(page, context)", start)
    renderer = PORTAL[start:end]
    assert "safeText" in renderer
    for forbidden in ("output_url", "job_id", "payment_id", "<video", "<audio"):
        assert forbidden not in renderer


def test_gallery_client_only_reads_current_private_route_and_keeps_state_in_memory() -> None:
    for helper in (
        "freePromptGalleryFilterPayload",
        "freePromptGalleryItemsPath",
        "freePromptGalleryCatalogIsSafe",
        "freePromptGalleryListingIsSafe",
        "freePromptGalleryDetailIsSafe",
        "hydrateFreePromptGallery",
        "hydrateFreePromptGalleryDetail",
    ):
        assert f"function {helper}" in INTEGRATION
    assert '"free-prompt-gallery-view": Boolean(account && freePromptGalleryEnabled)' in INTEGRATION
    assert '"/free-prompt-gallery": account && freePromptGalleryEnabled ? "processing" : "guarded"' in INTEGRATION
    assert 'api("/free-prompt-gallery/catalog")' in INTEGRATION
    assert 'api(`/free-prompt-gallery/items/${encodeURIComponent(id)}`)' in INTEGRATION
    assert "if (currentPath === \"/free-prompt-gallery\")" in INTEGRATION
    assert "await hydrateFreePromptGallery();" in INTEGRATION

    start = INTEGRATION.index('if (action === "free-prompt-gallery-filter")')
    end = INTEGRATION.index('if (action === "free-prompt-gallery-save")', start)
    actions = INTEGRATION[start:end].lower()
    for forbidden in (
        "bridgeavailable",
        "core bridge",
        "/payments",
        "/jobs",
        "payos",
        "localstorage",
        "sessionstorage",
        "document.execcommand",
    ):
        assert forbidden not in actions
    assert "navigator.clipboard.writetext(prompt)" in actions
    assert "freepromptgalleryfilterpayload(fields" in actions
    assert "hydratefreepromptgallerydetail(promptid)" in actions


def test_gallery_save_is_explicit_owner_scoped_and_receipt_only() -> None:
    for helper in (
        "freePromptGallerySaveBoundariesAreSafe",
        "freePromptGallerySaveReceipt",
        "freePromptGallerySaveResultIsSafe",
    ):
        assert f"function {helper}" in INTEGRATION
    assert 'FREE_PROMPT_GALLERY_MEMORY_NOTE_FIELDS = Object.freeze(["id", "category", "priority", "state", "revision"])' in INTEGRATION
    assert 'data.execution === "web_native_memory_gallery_save"' in INTEGRATION
    assert 'data.source_snapshot_read_only === true && data.memory_note_persisted === true' in INTEGRATION
    assert 'const keys = ["note", "gallery", "boundaries"];' in INTEGRATION
    assert "FREE_PROMPT_GALLERY_MEMORY_NOTE_ID" in PORTAL
    assert 'const expected = ["note", "gallery"];' in PORTAL
    assert '"free-prompt-gallery-save": Boolean(account && me.csrf_token && freePromptGalleryEnabled && memoryCenterEnabled)' in INTEGRATION
    assert 'data-portal-action="free-prompt-gallery-save"' in PORTAL
    assert 'data-portal-confirm="Lưu seed Gallery này thành ghi chú riêng trong Memory Center?' in PORTAL
    assert "Lưu vào Memory Center" in PORTAL
    assert "Mở ghi chú riêng" in PORTAL
    assert 'href="/notes/${encodeURIComponent(String(receipt.note.id || ""))}"' in PORTAL
    assert "freePromptGallerySaveResult" in PORTAL

    start = INTEGRATION.index('if (action === "free-prompt-gallery-save")')
    end = INTEGRATION.index('if (action === "workboard-refresh")', start)
    action = INTEGRATION[start:end]
    assert 'api(`/memory/gallery-items/${encodeURIComponent(promptId)}/save`, {' in action
    assert 'body: JSON.stringify({ idempotency_key: submission.key })' in action
    assert "acquireSubmission(scope, promptId)" in action
    assert "releaseSubmission(submission)" in action
    assert "discardSubmission(scope, submission)" in action
    assert "freePromptGallerySaveReceipt(result.data, promptId)" in action
    assert "freePromptGallerySaveResult: receipt" in action
    assert "selected.item.prompt" not in action
    for forbidden in (
        "/internal/",
        "/payments",
        "/jobs",
        "payos",
        "localstorage",
        "sessionstorage",
        "document.execcommand",
        "prompt_text",
        "prompt-library",
        "webhook",
    ):
        assert forbidden not in action.lower()


def test_gallery_route_and_api_are_private_and_not_part_of_shell_cache() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/free-prompt-gallery"' not in shell
    assert '"/free-prompt-gallery"' in private_paths
    assert '"/" + "api/v1/free-prompt-gallery"' in private_paths
    # The shell cache must remain versioned so a deploy can invalidate only
    # public assets; its exact revision legitimately changes as new private
    # no-cache boundaries are added.
    assert re.search(r'const CACHE_NAME = "toan-aas-portal-shell-v\d+";', SERVICE_WORKER)
