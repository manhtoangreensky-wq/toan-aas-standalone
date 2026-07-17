"""Static safety contracts for the Web-native Content Prompt Pack.

The five prompt recipes originate from deterministic Bot text helpers.  The
compose endpoint stays a short-lived signed-session text planning tool; a
separate explicit, confirmed Memory Center handoff may persist only a
server-recomputed Web-owned note.  Neither route is a hidden Bot handoff,
provider execution, job, payment, publish action, or PWA-cached private
result.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_content_studio.py").read_text(encoding="utf-8")
ENGINES = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def test_content_prompt_pack_is_a_native_portal_route_and_catalog_feature() -> None:
    assert 'customerPage("/content/prompt-pack", "Content Prompt Pack"' in PORTAL
    assert 'layout: "content-prompt-pack", type: "content-prompt-pack"' in PORTAL
    assert "function renderContentPromptPack(page, context)" in PORTAL
    assert 'case "content-prompt-pack": return renderContentPromptPack(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="content-prompt-pack-compose"' in PORTAL
    assert '["/content/prompt-pack", "Content Prompt Pack", ICONS.prompt]' in PORTAL
    assert 'botCompanionPage("/content/prompt-pack"' not in PORTAL
    assert '"content_prompt_pack"' in ENGINES
    assert 'WebFeature("content_prompt_pack", "Content Prompt Pack", "content", "/content/prompt-pack"' in REGISTRY


def test_content_prompt_pack_result_is_strictly_bounded_and_escaped() -> None:
    assert "const CONTENT_PROMPT_PACK_KINDS" in PORTAL
    assert '"hook_script"' in PORTAL
    assert '["hook_script", "Hook & kịch bản"]' in PORTAL
    assert "function normalizeContentPromptPackResult(raw)" in PORTAL
    for boundary in (
        'source.execution !== "local_deterministic_text_only"',
        "source.input_persisted !== false",
        "source.provider_called !== false",
        "source.job_created !== false",
        "source.payment_started !== false",
        "source.publish_action_created !== false",
        "source.fact_checked !== false",
        "source.rights_verified !== false",
    ):
        assert boundary in PORTAL
    for state_field in (
        "contentPromptPackEnabled: source.contentPromptPackEnabled === true",
        "contentPromptPackResult: normalizeContentPromptPackResult(source.contentPromptPackResult)",
    ):
        assert state_field in PORTAL

    start = PORTAL.index("function renderContentPromptPackResult")
    end = PORTAL.index("function renderContentPromptPack(page, context)", start)
    result_renderer = PORTAL[start:end]
    assert "safeText" in result_renderer
    assert "verify_before_publish" in result_renderer
    assert "output_url" not in result_renderer
    assert "job_id" not in result_renderer


def test_content_prompt_pack_suggestion_chips_are_static_dom_only_helpers() -> None:
    # The examples are a deliberately small static subset of Bot source.  The
    # page must not import/run the Bot or turn a suggestion into a hidden job.
    assert "const CONTENT_PROMPT_PACK_SUGGESTIONS" in PORTAL
    assert "FREE_HUB_SUGGESTION_BANK" in PORTAL
    assert '"hook_script"' in PORTAL
    assert "function contentPromptPackSuggestionItems(kind)" in PORTAL
    assert "function renderContentPromptPackSuggestions(selectedKind, enabled)" in PORTAL
    assert "data-content-prompt-suggestion-group" in PORTAL
    assert "data-content-prompt-suggestion" in PORTAL
    assert "group.hidden = !visible" in PORTAL
    assert "synchronizeContentPromptPackSuggestions(form)" in PORTAL
    assert 'event.target.name === "kind"' in PORTAL
    assert "${renderContentPromptPackSuggestions(values.kind, canCompose)}" in PORTAL

    start = PORTAL.index("function applyContentPromptPackSuggestion(chip)")
    end = PORTAL.index("function renderContentPromptPackResult", start)
    chip_handler = PORTAL[start:end]
    assert "topic.value = suggestion" in chip_handler
    assert "topic.focus" in chip_handler
    assert "data-content-prompt-suggestion-kind" in chip_handler
    for forbidden in (
        "dispatchAction(",
        "window.TOANAASPortal",
        ".mount(",
        "requestSubmit(",
        "api(",
        "fetch(",
        "localStorage",
        "sessionStorage",
        "rememberTransientFormDraft",
    ):
        assert forbidden not in chip_handler

    click_start = PORTAL.index('const contentPromptSuggestion = event.target.closest("[data-content-prompt-suggestion]")')
    click_end = PORTAL.index("const action = event.target.closest", click_start)
    click_handler = PORTAL[click_start:click_end]
    assert "applyContentPromptPackSuggestion(contentPromptSuggestion)" in click_handler
    assert "dispatchAction(" not in click_handler


def test_content_prompt_pack_uses_only_the_csrf_web_native_api() -> None:
    for helper in ("contentPromptPackPayload", "contentPromptPackResultIsSafe"):
        assert f"function {helper}" in INTEGRATION
    assert '"content-prompt-pack-compose": Boolean(account && me.csrf_token && contentPromptPackEnabled)' in INTEGRATION
    assert '"hook_script"' in INTEGRATION
    assert '"/content/prompt-pack": account && contentPromptPackEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/content-studio/tools/prompt-pack", {' in INTEGRATION
    assert "contentPromptPackResult: data" in INTEGRATION
    assert "contentPromptPackResult: {}," in INTEGRATION

    start = INTEGRATION.index('if (action === "content-prompt-pack-compose")')
    # Keep the stateless composer isolated from the immediately following
    # unrelated review composer. The explicit server-recomputed Memory handoff
    # is farther down in this dispatcher and intentionally has its own
    # idempotency boundary.
    end = INTEGRATION.index('if (action === "publish-review-pack-compose")', start)
    action = INTEGRATION[start:end].lower()
    for forbidden in (
        "bridgeavailable",
        "core bridge",
        "/payments",
        "/jobs",
        "payos",
        "idempotency_key",
        "localstorage",
        "sessionstorage",
    ):
        assert forbidden not in action
    assert "contentpromptpackpayload(fields)" in action
    assert "contentpromptpackresultissafe(data)" in action


def test_content_prompt_pack_memory_save_is_explicit_and_receipt_is_content_free() -> None:
    for helper in (
        "normalizeContentPromptPackSaveSource",
        "normalizeContentPromptPackSaveReceipt",
        "renderContentPromptPackSaveReceipt",
    ):
        assert f"function {helper}" in PORTAL
    assert 'data-portal-action="content-prompt-pack-save-memory"' in PORTAL
    assert "data-portal-confirm=" in PORTAL
    assert 'href="/notes"' in PORTAL
    assert "contentPromptPackSaveSource: normalizeContentPromptPackSaveSource(source.contentPromptPackSaveSource)" in PORTAL
    assert "contentPromptPackSaveReceipt: normalizeContentPromptPackSaveReceipt(source.contentPromptPackSaveReceipt)" in PORTAL

    for helper in (
        "contentPromptPackMemorySaveSource",
        "contentPromptPackMemorySaveSourceMatchesResult",
        "contentPromptPackMemorySaveReceipt",
    ):
        assert f"function {helper}" in INTEGRATION
    assert '"content-prompt-pack-save-memory": Boolean(account && me.csrf_token && contentPromptPackEnabled && memoryCenterEnabled)' in INTEGRATION
    assert 'api("/content-studio/tools/prompt-pack/save", {' in INTEGRATION
    assert 'const payload = { ...source, destination: "memory_note" };' in INTEGRATION
    assert "contentPromptPackMemorySaveSourceMatchesResult(source, currentResult)" in INTEGRATION
    assert "contentPromptPackMemorySaveReceipt(result.data)" in INTEGRATION
    assert "contentPromptPackSaveSource: {}," in INTEGRATION
    assert "contentPromptPackSaveReceipt: {}," in INTEGRATION

    start = INTEGRATION.index('if (action === "content-prompt-pack-save-memory")')
    end = INTEGRATION.index('if (action === "content-studio-refresh")', start)
    action = INTEGRATION[start:end].lower()
    for forbidden in ("localstorage", "sessionstorage", "prompt text", "bridgeavailable", "/payments", "/jobs", "payos"):
        assert forbidden not in action
    assert "destination: \"memory_note\"" in action
    assert "idempotency_key: submission.key" in action

    receipt_start = INTEGRATION.index("function contentPromptPackMemorySaveReceipt")
    receipt_end = INTEGRATION.index("// The Bot assembled", receipt_start)
    receipt = INTEGRATION[receipt_start:receipt_end]
    assert "CONTENT_PROMPT_PACK_MEMORY_SAVE_FALSE_BOUNDARY_FIELDS.every" in receipt
    assert 'data.execution !== "web_native_memory_note_server_recomputed"' in receipt
    assert "draft_recomputed_on_server !== true || data.web_note_persisted !== true" in receipt
    assert '"title"' not in receipt
    assert '"content"' not in receipt
    for boundary in (
        "browser_result_persisted", "pending_bot_save_created", "telegram_state_changed", "bot_called", "bridge_called",
        "provider_called", "job_created", "wallet_mutated", "payment_started", "asset_saved", "publish_action_created",
        "delivery_created", "fact_checked", "rights_verified",
    ):
        assert f'"{boundary}"' in INTEGRATION


def test_content_prompt_pack_backend_stays_request_only_without_durable_mutation() -> None:
    assert "class ContentPromptPackRequest(BaseModel)" in ROUTER
    assert '@router.post("/tools/prompt-pack")' in ROUTER
    assert "PROMPT_PACK_KINDS" in ROUTER
    assert 'elif kind == "hook_script":' in ROUTER
    assert "free_tools_hub.hook_script_pack" in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/prompt-pack")')
    # `/tools/prompt-pack/save` is intentionally a separate confirmed write.
    # Keep the original compose endpoint's no-mutation contract isolated from
    # that explicit Memory Center handoff.
    end = ROUTER.index('@router.post("/tools/prompt-pack/save")', start)
    endpoint = ROUTER[start:end]
    assert "_policy_guard" in endpoint
    assert "_content_prompt_pack" in endpoint
    assert '"local_deterministic_text_only"' in endpoint
    for boundary in (
        '"input_persisted": False',
        '"provider_called": False',
        '"job_created": False',
        '"payment_started": False',
        '"publish_action_created": False',
        '"fact_checked": False',
        '"rights_verified": False',
    ):
        assert boundary in endpoint
    for forbidden_call in ("_idempotent(", "transaction(", "_audit(", "_event("):
        assert forbidden_call not in endpoint


def test_content_prompt_pack_private_ui_is_responsive_and_never_pwa_cached() -> None:
    for selector in (
        ".portal-content-prompt-pack",
        ".portal-content-prompt-pack-intro",
        ".portal-content-prompt-pack-layout",
        ".portal-content-prompt-pack-form",
        ".portal-content-prompt-pack-boundary",
        ".portal-content-prompt-pack-result",
        ".portal-content-prompt-pack-section",
    ):
        assert selector in CSS

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/content/prompt-pack"' not in shell
    assert '"/content/prompt-pack"' in private_paths
    assert '"/api/v1/content-studio"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
