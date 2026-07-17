"""Static contracts for the Web-native Image Prompt Composer.

It reuses safe, deterministic planning semantics from the Bot's prompt helper
but deliberately remains separate from Telegram, a provider, Image Operations,
Asset Vault writes, jobs, payments, publishing, and PWA persistence.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_image_studio.py").read_text(encoding="utf-8")
ENGINES = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def test_image_prompt_composer_is_a_native_image_route_and_catalog_feature() -> None:
    assert 'customerPage("/image/prompt-composer", "Image Prompt Composer"' in PORTAL
    assert 'layout: "image-prompt-composer", type: "image-prompt-composer"' in PORTAL
    assert "function renderImagePromptComposer(page, context)" in PORTAL
    assert 'case "image-prompt-composer": return renderImagePromptComposer(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="image-prompt-compose"' in PORTAL
    assert 'botCompanionPage("/image/prompt-composer"' not in PORTAL
    assert '"image_prompt_composer"' in ENGINES
    assert 'WebFeature("image_prompt_composer", "Image Prompt Composer", "image", "/image/prompt-composer"' in REGISTRY


def test_image_prompt_composer_result_is_bounded_escaped_and_honest() -> None:
    assert "const IMAGE_PROMPT_COMPOSER_GOAL_CODES" in PORTAL
    assert "function normalizeImagePromptComposerResult(raw)" in PORTAL
    for boundary in (
        'source.execution !== "web_native_deterministic_prompt_only"',
        "source.input_persisted !== false",
        "source.source_image_inspected !== false",
        "source.provider_called !== false",
        "source.image_created !== false",
        "source.output_created !== false",
        "source.job_created !== false",
        "source.payment_started !== false",
        "source.wallet_mutated !== false",
        "source.asset_saved !== false",
        "source.publish_action_created !== false",
        "source.fact_checked !== false",
        "source.rights_verified !== false",
    ):
        assert boundary in PORTAL
    for state_field in (
        "imagePromptComposerEnabled: source.imagePromptComposerEnabled === true",
        "imagePromptComposerResult: normalizeImagePromptComposerResult(source.imagePromptComposerResult)",
        "imagePromptComposerSaveSource: normalizeImagePromptComposerSaveSource(source.imagePromptComposerSaveSource)",
        "imagePromptComposerSaveReceipt: normalizeImagePromptComposerSaveReceipt(source.imagePromptComposerSaveReceipt)",
    ):
        assert state_field in PORTAL

    start = PORTAL.index("function renderImagePromptComposerResult")
    end = PORTAL.index("function renderImagePromptComposer(page, context)", start)
    result_renderer = PORTAL[start:end]
    assert "safeText" in result_renderer
    assert "review_before_use" in result_renderer
    assert "output_url" not in result_renderer
    assert "job_id" not in result_renderer


def test_image_prompt_composer_uses_only_the_signed_csrf_web_native_api() -> None:
    for helper in (
        "imagePromptComposerPayload",
        "imagePromptComposerResultIsSafe",
        "imagePromptComposerMemorySaveSource",
        "imagePromptComposerMemorySaveSourceMatchesResult",
        "imagePromptComposerMemorySaveReceipt",
    ):
        assert f"function {helper}" in INTEGRATION
    assert '"image-prompt-compose": Boolean(account && me.csrf_token && imagePromptComposerEnabled)' in INTEGRATION
    assert '"image-prompt-composer-save-memory": Boolean(account && me.csrf_token && imagePromptComposerEnabled && memoryCenterEnabled)' in INTEGRATION
    assert '"/image/prompt-composer": account && imagePromptComposerEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/image-studio/tools/prompt-composer", {' in INTEGRATION
    assert 'api("/image-studio/tools/prompt-composer/save", {' in INTEGRATION
    assert "imagePromptComposerResult: data" in INTEGRATION
    assert "imagePromptComposerResult: {}," in INTEGRATION
    assert "imagePromptComposerSaveSource: {}," in INTEGRATION
    assert "imagePromptComposerSaveReceipt: {}," in INTEGRATION

    result_start = INTEGRATION.index("function imagePromptComposerResultIsSafe(value)")
    result_end = INTEGRATION.index("// AI Chat Workspace", result_start)
    result_validator = INTEGRATION[result_start:result_end]
    # The Router and Portal normalizer deliberately expose the Bot-derived
    # variants as three plain prompt strings.  A browser-only object schema
    # would reject every otherwise-valid server response before rendering it.
    assert 'typeof entry === "string"' in result_validator
    assert "entry.key" not in result_validator
    assert 'imageStudioLine(fields.subject, "Mô tả chủ thể", 2, 260, false)' in INTEGRATION

    start = INTEGRATION.index('if (action === "image-prompt-compose")')
    end = INTEGRATION.index('if (action === "image-prompt-composer-save-memory")', start)
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
    assert "imagepromptcomposerpayload(fields)" in action
    assert "imagepromptcomposerresultissafe(data)" in action
    assert "imagepromptcomposermemorysavesource(payload)" in action
    assert "imagepromptcomposermemorysavesourcematchesresult(savesource, data)" in action


def test_image_prompt_composer_memory_save_is_explicit_confirmed_and_content_free() -> None:
    for token in (
        "function normalizeImagePromptComposerSaveSource(raw)",
        "function normalizeImagePromptComposerSaveReceipt(raw)",
        'data-portal-action="image-prompt-composer-save-memory"',
        "data-portal-confirm=",
        "renderImagePromptComposerSaveReceipt(context.imagePromptComposerSaveReceipt)",
        'href="/notes"',
    ):
        assert token in PORTAL

    save_start = INTEGRATION.index('if (action === "image-prompt-composer-save-memory")')
    save_end = INTEGRATION.index('if (action === "image-studio-refresh")', save_start)
    save_action = INTEGRATION[save_start:save_end]
    for token in (
        "imagePromptComposerMemorySaveSource(base().imagePromptComposerSaveSource)",
        "imagePromptComposerMemorySaveSourceMatchesResult(source, currentResult)",
        'destination: "memory_note"',
        "acquireSubmission(scope, JSON.stringify(payload))",
        'api("/image-studio/tools/prompt-composer/save", {',
        "idempotency_key: submission.key",
        "imagePromptComposerMemorySaveReceipt(result.data)",
    ):
        assert token in save_action
    for forbidden in ("localStorage", "sessionStorage", "bridgeAvailable", "/payments", "/jobs", "PayOS"):
        assert forbidden not in save_action

    for boundary in (
        '"browser_result_persisted"',
        '"pending_bot_save_created"',
        '"telegram_state_changed"',
        '"bot_called"',
        '"bridge_called"',
        '"source_image_inspected"',
        '"provider_called"',
        '"image_created"',
        '"output_created"',
        '"job_created"',
        '"wallet_mutated"',
        '"payment_started"',
        '"asset_saved"',
        '"publish_action_created"',
        '"delivery_created"',
        '"fact_checked"',
        '"rights_verified"',
        '"web_native_memory_note_server_recomputed"',
    ):
        assert boundary in INTEGRATION
        assert boundary in PORTAL


def test_image_prompt_composer_backend_remains_request_only_without_durable_mutation() -> None:
    assert '@router.post("/tools/prompt-composer")' in ROUTER
    assert "PROMPT_COMPOSER_GOAL_CODES" in ROUTER
    assert "PROMPT_COMPOSER_RATIO_ALIASES" in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/prompt-composer")')
    end = ROUTER.index('@router.post("/tools/prompt-composer/save")', start)
    endpoint = ROUTER[start:end]
    assert "_require_enabled" in endpoint
    assert "_prompt_composer_boundary" in endpoint
    boundary_start = ROUTER.index("def _prompt_composer_boundary()")
    boundary_end = ROUTER.index("def _prompt_composer_guard", boundary_start)
    boundary_source = ROUTER[boundary_start:boundary_end]
    assert '"web_native_deterministic_prompt_only"' in boundary_source
    for field in (
        '"input_persisted": False',
        '"source_image_inspected": False',
        '"provider_called": False',
        '"image_created": False',
        '"output_created": False',
        '"job_created": False',
        '"payment_started": False',
        '"wallet_mutated": False',
        '"asset_saved": False',
        '"publish_action_created": False',
        '"fact_checked": False',
        '"rights_verified": False',
    ):
        assert field in boundary_source
    for forbidden_call in ("_idempotent(", "transaction(", "_record_audit(", "_event("):
        assert forbidden_call not in endpoint


def test_image_prompt_composer_memory_save_is_a_separate_server_recomputed_handoff() -> None:
    start = ROUTER.index('@router.post("/tools/prompt-composer/save")')
    end = ROUTER.index('@router.get("/summary")', start)
    endpoint = ROUTER[start:end]
    for token in (
        "ImagePromptComposerMemorySaveRequest",
        "Depends(require_csrf)",
        "_require_memory_handoff_enabled()",
        "_compose_image_prompt(payload)",
        "web_memory_notes",
        "_idempotent(",
        "web.image_studio.prompt_composer.save_memory",
        '"destination": "memory_note"',
    ):
        assert token in endpoint
    for forbidden in ("copyfast_bridge", "httpx", "requests", "payos", "provider_client"):
        assert forbidden not in endpoint.lower()
    boundary_start = ROUTER.index("def _image_prompt_composer_memory_boundaries(")
    boundary_end = ROUTER.index("def _boundary(", boundary_start)
    boundary = ROUTER[boundary_start:boundary_end]
    for token in ('"draft_recomputed_on_server"', '"web_note_persisted"', '"provider_called": False', '"image_created": False'):
        assert token in boundary


def test_image_prompt_composer_private_ui_is_responsive_and_never_pwa_cached() -> None:
    for selector in (
        ".portal-image-prompt-composer",
        ".portal-image-prompt-composer-intro",
        ".portal-image-prompt-composer-layout",
        ".portal-image-prompt-composer-form",
        ".portal-image-prompt-composer-boundary",
        ".portal-image-prompt-composer-result",
        ".portal-image-prompt-composer-prompt",
        ".portal-image-prompt-composer-variants",
        ".portal-image-prompt-composer-review",
    ):
        assert selector in CSS

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/image/prompt-composer"' not in shell
    assert '"/image/prompt-composer"' in private_paths
    assert '"/api/v1/image-studio"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
