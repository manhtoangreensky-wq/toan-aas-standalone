"""Static privacy and contract checks for Music Prompt Composer.

The signed private page may display three deterministic, Bot-inspired music
directions.  It must never turn a text receipt into a browser player, music
provider/Suno request, audio job, collection save, payment, delivery or cached
private record.
"""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_music_media.py").read_text(encoding="utf-8")
ENGINES = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _function_block(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\n  function ", start + 1)
    return source[start:end if end != -1 else len(source)]


def _integration_action() -> str:
    start = INTEGRATION.index('if (action === "music-prompt-compose")')
    next_action = re.search(r"\n\s*if \(action ===", INTEGRATION[start + 1:])
    end = start + 1 + next_action.start() if next_action else len(INTEGRATION)
    return INTEGRATION[start:end]


def _integration_save_action() -> str:
    start = INTEGRATION.index('if (action === "music-prompt-composer-save-memory")')
    next_action = re.search(r"\n\s*if \(action ===", INTEGRATION[start + 1:])
    end = start + 1 + next_action.start() if next_action else len(INTEGRATION)
    return INTEGRATION[start:end]


def test_music_prompt_composer_is_a_native_private_music_route_and_catalog_feature() -> None:
    assert 'customerPage("/media-workspace/music-prompt-composer", "Music Prompt Composer"' in PORTAL
    assert 'layout: "music-prompt-composer", type: "music-prompt-composer"' in PORTAL
    assert "function renderMusicPromptComposerResult" in PORTAL
    assert "function renderMusicPromptComposer(page, context)" in PORTAL
    assert 'case "music-prompt-composer": return renderMusicPromptComposer(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="music-prompt-compose"' in PORTAL
    assert 'botCompanionPage("/media-workspace/music-prompt-composer"' not in PORTAL
    assert '"music_prompt_composer"' in ENGINES
    assert 'WebFeature("music_prompt_composer", "Music Prompt Composer", "music", "/media-workspace/music-prompt-composer"' in REGISTRY


def test_music_prompt_composer_normalizer_and_validator_require_exact_flat_boundary() -> None:
    normalizer = _function_block(PORTAL, "normalizeMusicPromptComposerResult")
    validator = _function_block(INTEGRATION, "musicPromptComposerResultIsSafe")
    boundary_validator = _function_block(INTEGRATION, "musicPromptComposerBoundaryIsSafe")
    assert "function normalizeMusicPromptComposerResult(raw)" in PORTAL
    assert "function musicPromptComposerResultIsSafe(value)" in INTEGRATION
    assert "function musicPromptComposerBoundaryIsSafe(value)" in INTEGRATION

    for field in (
        "input_persisted",
        "source_audio_inspected",
        "provider_called",
        "ai_music_called",
        "lyrics_generated",
        "audio_created",
        "preview_created",
        "output_created",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "asset_saved",
        "collection_saved",
        "publish_action_created",
        "telegram_called",
        "rights_verified",
    ):
        assert f"source.{field} === false" in normalizer
        assert f"value.{field} === false" in boundary_validator
    assert 'source.execution === "web_native_deterministic_music_prompt_only"' in normalizer
    assert 'value.execution === "web_native_deterministic_music_prompt_only"' in boundary_validator
    assert "musicPromptComposerBoundaryIsSafe(data)" in validator

    for source in (normalizer, validator):
        for key in (
            "description",
            "mode",
            "language",
            "suggestion_set",
            "selected_suggestion",
            "suggestions",
            "selected_direction",
            "usage_notes",
            "cautions",
            "review_before_use",
        ):
            assert key in source
    # Usage note keys live in a single exact-key constant shared by the
    # normalizer and validator.  Keeping that declaration outside both
    # functions avoids loose browser objects while still binding every field.
    for key in ("voice_mix_notes", "edit_notes", "rights_notes", "delivery_notes"):
        assert f'"{key}"' in PORTAL
        assert f'"{key}"' in INTEGRATION
    # Suggestions are normalized through dedicated helpers, so the nested
    # lyric field is intentionally declared in their exact-key constants
    # rather than repeated verbatim inside the receipt normalizer.
    assert '"lyric_direction"' in PORTAL
    assert '"lyric_direction"' in INTEGRATION
    for state_field in (
        "musicPromptComposerEnabled: source.musicPromptComposerEnabled === true",
        "musicPromptComposerResult: normalizeMusicPromptComposerResult(source.musicPromptComposerResult)",
        "musicPromptComposerSaveSource: normalizeMusicPromptComposerSaveSource(source.musicPromptComposerSaveSource)",
        "musicPromptComposerSaveReceipt: normalizeMusicPromptComposerSaveReceipt(source.musicPromptComposerSaveReceipt)",
    ):
        assert state_field in PORTAL

    renderer = _function_block(PORTAL, "renderMusicPromptComposerResult")
    assert "safeText" in renderer
    assert "usage_notes" in renderer
    for forbidden in (
        "output_url",
        "job_id",
        "audio_url",
        "preview_url",
        "asset_url",
        "payment_url",
        "collection_id",
        "telegram_message_id",
    ):
        assert forbidden not in renderer


def test_music_prompt_composer_uses_only_signed_csrf_native_api_without_browser_persistence() -> None:
    for helper in (
        "musicPromptComposerPayload",
        "musicPromptComposerResultIsSafe",
        "musicPromptComposerMemorySaveSource",
        "musicPromptComposerMemorySaveSourceMatchesResult",
        "musicPromptComposerMemorySaveReceipt",
    ):
        assert f"function {helper}" in INTEGRATION
    assert '"music-prompt-compose": Boolean(account && me.csrf_token && musicPromptComposerEnabled)' in INTEGRATION
    assert '"music-prompt-composer-save-memory": Boolean(account && me.csrf_token && musicPromptComposerEnabled && memoryCenterEnabled)' in INTEGRATION
    assert '"/media-workspace/music-prompt-composer": account && musicPromptComposerEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/media-workspace/tools/music-prompt-composer", {' in INTEGRATION
    assert "musicPromptComposerResult: data" in INTEGRATION
    assert "musicPromptComposerResult: {}," in INTEGRATION

    action = _integration_action().lower()
    for forbidden in (
        "bridgeavailable",
        "core bridge",
        "/payments",
        "/jobs",
        "payos",
        "idempotency_key",
        "localstorage",
        "sessionstorage",
        "provider",
        "suno",
        "new audio(",
        "<audio",
        "collection",
        "telegram",
    ):
        assert forbidden not in action
    assert "musicpromptcomposerpayload(fields)" in action
    assert "musicpromptcomposerresultissafe(data)" in action
    assert "musicpromptcomposermemorysavesource(payload)" in action
    assert "musicpromptcomposermemorysavesourcematchesresult(savesource, data)" in action


def test_music_prompt_composer_memory_save_is_explicit_confirmed_and_content_free() -> None:
    for token in (
        "function normalizeMusicPromptComposerSaveSource(raw)",
        "function normalizeMusicPromptComposerSaveReceipt(raw)",
        'data-portal-action="music-prompt-composer-save-memory"',
        "data-portal-confirm=",
        "renderMusicPromptComposerSaveReceipt(context.musicPromptComposerSaveReceipt)",
        'href="/notes"',
    ):
        assert token in PORTAL

    save_action = _integration_save_action()
    for token in (
        "musicPromptComposerMemorySaveSource(base().musicPromptComposerSaveSource)",
        "musicPromptComposerMemorySaveSourceMatchesResult(source, currentResult)",
        'destination: "memory_note"',
        "acquireSubmission(scope, JSON.stringify(payload))",
        'api("/media-workspace/tools/music-prompt-composer/save", {',
        "idempotency_key: submission.key",
        "musicPromptComposerMemorySaveReceipt(result.data)",
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
        '"source_audio_inspected"',
        '"provider_called"',
        '"ai_music_called"',
        '"lyrics_generated"',
        '"audio_created"',
        '"preview_created"',
        '"output_created"',
        '"job_created"',
        '"wallet_mutated"',
        '"payment_started"',
        '"asset_saved"',
        '"collection_saved"',
        '"publish_action_created"',
        '"delivery_created"',
        '"fact_checked"',
        '"rights_verified"',
        '"web_native_memory_note_server_recomputed"',
    ):
        assert boundary in INTEGRATION
        assert boundary in PORTAL


def test_music_prompt_composer_backend_stays_request_only_and_never_claims_audio_delivery() -> None:
    assert "class MusicPromptComposerRequest(BaseModel)" in ROUTER
    assert "class MusicPromptComposerResult(BaseModel)" in ROUTER
    assert '@router.post("/tools/music-prompt-composer")' in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/music-prompt-composer")')
    # The request-only route is intentionally positioned immediately before
    # the existing durable Media Workspace endpoints.  Limit the static scan
    # to its own route body, otherwise calls in the unrelated collection API
    # would produce a false persistence failure.
    end = ROUTER.index('@router.post("/tools/music-prompt-composer/save")', start)
    endpoint = ROUTER[start:end]
    assert "_require_enabled" in endpoint
    assert "web_native_deterministic_music_prompt_only" in ROUTER
    for field in (
        '"input_persisted": False',
        '"source_audio_inspected": False',
        '"provider_called": False',
        '"ai_music_called": False',
        '"lyrics_generated": False',
        '"audio_created": False',
        '"preview_created": False',
        '"output_created": False',
        '"job_created": False',
        '"wallet_mutated": False',
        '"payment_started": False',
        '"asset_saved": False',
        '"collection_saved": False',
        '"publish_action_created": False',
        '"telegram_called": False',
        '"rights_verified": False',
    ):
        assert field in ROUTER
    for forbidden_call in (
        "_idempotent(",
        "transaction(",
        "_record_audit(",
        "_event(",
        "_insert_collection(",
        "_write_collection_update(",
    ):
        assert forbidden_call not in endpoint


def test_music_prompt_composer_memory_save_is_a_separate_server_recomputed_handoff() -> None:
    start = ROUTER.index('@router.post("/tools/music-prompt-composer/save")')
    end = ROUTER.index('@router.get("/summary")', start)
    endpoint = ROUTER[start:end]
    for token in (
        "MusicPromptComposerMemorySaveRequest",
        "Depends(require_csrf)",
        "_require_memory_handoff_enabled()",
        "_compose_music_prompt(payload)",
        "web_memory_notes",
        "_idempotent(",
        "web.media_workspace.music_prompt_composer.save_memory",
        '"destination": "memory_note"',
    ):
        assert token in endpoint
    for forbidden in ("copyfast_bridge", "httpx", "requests", "payos", "provider_client"):
        assert forbidden not in endpoint.lower()
    boundary_start = ROUTER.index("def _music_prompt_composer_memory_boundaries(")
    boundary_end = ROUTER.index('@router.post("/tools/music-prompt-composer")', boundary_start)
    boundary = ROUTER[boundary_start:boundary_end]
    for token in ('"draft_recomputed_on_server"', '"web_note_persisted"', '"provider_called": False', '"audio_created": False'):
        assert token in boundary


def test_music_prompt_composer_is_responsive_and_never_pwa_cached() -> None:
    for selector in (
        ".portal-music-prompt-composer",
        ".portal-music-prompt-composer-intro",
        ".portal-music-prompt-composer-layout",
        ".portal-music-prompt-composer-form",
        ".portal-music-prompt-composer-boundary",
        ".portal-music-prompt-composer-result",
        ".portal-music-prompt-composer-suggestions",
        ".portal-music-prompt-composer-usage",
        ".portal-music-prompt-composer-review",
    ):
        assert selector in CSS
    assert "@media" in CSS

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/media-workspace/music-prompt-composer"' not in shell
    assert '"/media-workspace/music-prompt-composer"' in private_paths
    assert '\"/\" + \"api/v1/media-workspace\"' in private_paths
    assert '"/api/v1/media-workspace"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
