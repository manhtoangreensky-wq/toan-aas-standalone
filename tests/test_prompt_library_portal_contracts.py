"""Static contracts for the private, Web-native Prompt Library Portal."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_prompt_library_pages_are_real_native_workspace_routes() -> None:
    assert 'customerPage("/prompt-library", "Prompt Library"' in PORTAL
    assert 'customerPage("/prompt-library/new", "Template Prompt mới"' in PORTAL
    assert 'layout: "prompt-library", type: "prompt-library"' in PORTAL
    assert 'path: "/prompt-library/:id"' in PORTAL
    assert "function renderPromptLibrary(page, context)" in PORTAL
    assert "function renderPromptLibraryDetail(page, context)" in PORTAL
    assert 'case "prompt-library": return renderPromptLibrary(page, context);' in PORTAL
    assert 'case "prompt-library-detail": return renderPromptLibraryDetail(page, context);' in PORTAL
    assert "PROMPT_LIBRARY_PATH" in PAGES
    assert "PROMPT_LIBRARY_PATH.fullmatch(normalized)" in PAGES
    assert 'botCompanionPage("/prompt-library"' not in PORTAL


def test_prompt_library_hydration_and_actions_use_owner_scoped_web_api_only() -> None:
    for helper in (
        "validPromptTemplateId",
        "promptTemplateIdFromPath",
        "promptLibraryFilterPayload",
        "promptLibraryListPath",
        "promptTemplatePayload",
        "promptLibraryImportPayload",
        "hydratePromptLibrary",
        "hydratePromptTemplate",
        "downloadPromptLibraryExport",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    assert '"prompt-library-view": Boolean(account && promptLibraryEnabled)' in INTEGRATION
    assert '"prompt-library-purge": Boolean(account && me.csrf_token && promptLibraryEnabled)' in INTEGRATION
    assert 'api("/prompt-library/summary")' in INTEGRATION
    assert 'api("/prompt-library/events?limit=50")' in INTEGRATION
    assert 'api(`/prompt-library/templates/${encodeURIComponent(String(templateId))}`)' in INTEGRATION
    assert 'method: "POST", credentials: "same-origin", headers' in INTEGRATION
    assert 'fetch(`${API}/prompt-library/export`' in INTEGRATION
    assert 'promptLibrarySummary: {}, promptTemplates: [], promptTemplateDetail: {}, promptTemplatePreview: {}, promptLibraryEvents: []' in INTEGRATION

    start = INTEGRATION.index('if (action === "prompt-library-filter"')
    end = INTEGRATION.index('if (action === "support-cases-filter")')
    actions = INTEGRATION[start:end].lower()
    for forbidden in (
        "bridgeavailable",
        "payos",
        "wallet",
        "telegram",
        "provider",
        "create-ticket",
        "/support/tickets",
    ):
        assert forbidden not in actions
    for action in (
        "prompt-template-create",
        "prompt-template-update",
        "prompt-template-archive",
        "prompt-template-purge",
        "prompt-template-preview",
        "prompt-library-import",
        "prompt-library-export",
    ):
        assert action in actions


def test_prompt_library_dispatch_carries_owner_checked_template_metadata() -> None:
    assert 'promptTemplateId: source.getAttribute("data-prompt-template-id") || ""' in PORTAL
    assert 'promptTemplateRevision: source.getAttribute("data-prompt-template-revision") || ""' in PORTAL
    assert 'promptTemplateVersion: source.getAttribute("data-prompt-template-version") || ""' in PORTAL
    assert 'data-portal-action="prompt-template-purge"' in PORTAL
    assert 'data-portal-confirm="Xóa vĩnh viễn template đã archive' in PORTAL
    assert 'prompt-template-purge' in PORTAL


def test_prompt_library_privacy_controls_and_pwa_boundary_are_staticly_enforced() -> None:
    assert "PROMPT_FORBIDDEN_VARIABLE_NAMES" in INTEGRATION
    assert "PROMPT_PRIVATE_KEY_PATTERN" in INTEGRATION
    assert "PROMPT_UNSAFE_CONTROL_PATTERN" in INTEGRATION
    assert "PROMPT_LIBRARY_IMPORT_MAX_CHARS = 1400000" in INTEGRATION
    assert 'maxlength="1400000"' in PORTAL
    assert "Object.create(null)" in INTEGRATION
    assert "URL.revokeObjectURL(objectUrl)" in INTEGRATION
    assert "/api/v1/prompt-library" not in SERVICE_WORKER
    assert '"/prompt-library"' not in SERVICE_WORKER
    assert "toan-aas-portal-shell-v6" in SERVICE_WORKER
    assert "private_prompt_export" in APP
    assert '"prompt-library-write" if prompt_library_write' in APP
    assert '"prompt-library-read" if prompt_library_read' in APP
    assert "_prune_rate_windows(now)" in APP
    assert "PromptLibraryBodyLimitMiddleware" in APP
    assert "PROMPT_LIBRARY_IMPORT_BODY_MAX_BYTES" in APP
    assert ".portal-prompt-library-intro" in CSS
    assert ".portal-prompt-library-filter" in CSS
    assert ".portal-prompt-library-preview-result" in CSS
    assert ".portal-prompt-library-detail-grid" in CSS
    assert ".portal-prompt-library-grid { grid-template-columns: 1fr; }" in CSS


def test_prompt_library_archives_disable_preview_and_clipboard_actions() -> None:
    assert 'const canPreview = Boolean(context.capabilities && context.capabilities["prompt-library-preview"] === true && state === "active");' in PORTAL
    assert 'const canCopy = state === "active";' in PORTAL
    assert 'data-portal-action="prompt-template-copy"' in PORTAL
    assert 'String(template.state || "") !== "active"' in INTEGRATION
