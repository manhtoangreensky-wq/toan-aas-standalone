"""Static contracts for the private Web-native Music Directions page.

The page intentionally upgrades a narrow Bot suggestion concept without
accepting a Bot callback or keyword.  A customer chooses one reviewed Web
preset locally, writes a brief, and explicitly requests a signed transient
text receipt.  These checks keep that small workflow from silently becoming a
player, provider/job/payment path, Memory write, or cached private page.
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


EXPECTED_PRESET_IDS = {
    "commercial_bright",
    "cinematic_brand",
    "warm_story",
    "technology_future",
    "short_viral",
}

EXPECTED_PRESET_COMPOSER_SELECTIONS = {
    "commercial_bright": ("background", "primary", 1),
    "cinematic_brand": ("background", "primary", 2),
    "warm_story": ("background", "primary", 3),
    "technology_future": ("background", "alternate", 1),
    "short_viral": ("background", "alternate", 2),
}

BOUNDARY_FIELDS = (
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
)


def _function_block(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\n  function ", start + 1)
    return source[start:end if end != -1 else len(source)]


def _action_block() -> str:
    start = INTEGRATION.index('if (action === "music-direction-preset-compose")')
    end = INTEGRATION.index('if (action === "music-prompt-compose")', start)
    return INTEGRATION[start:end]


def _route_block() -> str:
    start = ROUTER.index('@router.post("/tools/music-directions/compose")')
    end = ROUTER.index('@router.post("/tools/music-prompt-composer/save")', start)
    return ROUTER[start:end]


def _music_direction_css() -> str:
    start = CSS.index(".portal-music-directions {")
    end = CSS.index("\n/*", start + 1)
    return CSS[start:end if end != -1 else len(CSS)]


def _quoted_ids_from_set(source: str, declaration: str) -> set[str]:
    start = source.index(declaration)
    end = source.index("]);", start)
    return set(re.findall(r'"([a-z_]+)"', source[start:end]))


def test_music_directions_is_a_private_web_route_with_exactly_five_opaque_presets() -> None:
    page_start = PORTAL.index('customerPage("/media-workspace/music-directions", "Music Directions"')
    page = PORTAL[page_start:PORTAL.index("  customerPage(", page_start + 1)]
    assert 'layout: "music-direction-presets", type: "music-direction-presets"' in page
    assert 'case "music-direction-presets": return renderMusicDirectionPresets(page, context);' in PORTAL
    assert 'WebFeature("music_direction_presets", "Music Directions", "music", "/media-workspace/music-directions"' in REGISTRY
    assert 'ENGINE_SPECS.update(_many(("music_direction_presets",), mode=ENGINE_MODE_WEB_NATIVE' in ENGINES
    assert "isNativeMusicDirectionPresetPath(normalized)" in INTEGRATION

    assert _quoted_ids_from_set(INTEGRATION, "const MUSIC_DIRECTION_PRESET_IDS = new Set([") == EXPECTED_PRESET_IDS
    map_start = ROUTER.index("MUSIC_DIRECTION_PRESET_MAP")
    map_end = ROUTER.index("MUSIC_DIRECTION_PRESET_IDS", map_start)
    assert set(re.findall(r'"([a-z_]+)"\s*:', ROUTER[map_start:map_end])) == EXPECTED_PRESET_IDS
    preset_start = PORTAL.index("const MUSIC_DIRECTION_PRESETS = Object.freeze([")
    preset_end = PORTAL.index("]);", preset_start)
    assert set(re.findall(r'id: "([a-z_]+)"', PORTAL[preset_start:preset_end])) == EXPECTED_PRESET_IDS
    assert "suggest_music|" not in PORTAL[preset_start:preset_end]

    for source in (INTEGRATION, PORTAL):
        selection_start = source.index("const MUSIC_DIRECTION_PRESET_COMPOSER_SELECTIONS = Object.freeze({")
        selection_end = source.index("  });", selection_start) + len("  });")
        selection = source[selection_start:selection_end]
        for preset_id, (mode, suggestion_set, selected_suggestion) in EXPECTED_PRESET_COMPOSER_SELECTIONS.items():
            assert f'{preset_id}: Object.freeze({{ mode: "{mode}", suggestion_set: "{suggestion_set}", selected_suggestion: {selected_suggestion} }})' in selection


def test_music_directions_uses_native_radio_selection_without_auto_submit_or_navigation() -> None:
    renderer = _function_block(PORTAL, "renderMusicDirectionPresets")
    assert 'data-portal-action="music-direction-preset-compose"' in renderer
    assert 'data-portal-route="/media-workspace/music-directions"' in renderer
    assert 'type="radio" name="web_preset_id"' in renderer
    assert "data-music-direction-preset-card" in renderer
    assert "data-music-direction-submit" in renderer
    assert 'type="hidden" name="web_preset_id"' not in renderer

    sync = _function_block(PORTAL, "synchronizeMusicDirectionPresetForm")
    edit = _function_block(PORTAL, "markMusicDirectionPresetDraftEdited")
    assert 'input[name="web_preset_id"]:checked' in sync
    assert "submit.disabled = !(enabled && presetId)" in sync
    assert 'window.dispatchEvent(new CustomEvent("toanaas:music-direction-preset-draft-edited"))' in edit
    for local_only in (sync, edit):
        for forbidden in ("api(", "fetch(", "location", "history", ".submit(", ".reset(", "localStorage", "sessionStorage"):
            assert forbidden not in local_only


def test_music_directions_requires_signed_capability_csrf_and_validates_matching_receipts() -> None:
    assert '"music-direction-preset-compose": Boolean(account && me.csrf_token && musicDirectionPresetsEnabled)' in INTEGRATION
    assert '"/media-workspace/music-directions": account && musicDirectionPresetsEnabled ? "ready" : "guarded"' in INTEGRATION
    assert "function musicDirectionPresetPayload(fields)" in INTEGRATION
    assert "function musicDirectionPresetBoundaryIsSafe(value)" in INTEGRATION
    assert "function musicDirectionPresetResultIsSafe(value)" in INTEGRATION
    assert "function musicDirectionPresetResultMatchesSource(source, result)" in INTEGRATION
    assert "function musicDirectionPresetComposerMatchesPreset(presetId, composer)" in INTEGRATION

    payload = _function_block(INTEGRATION, "musicDirectionPresetPayload")
    assert 'const allowed = ["description", "language", "web_preset_id"]' in payload
    assert "MUSIC_DIRECTION_PRESET_RAW_BOT_INPUT_PATTERN.test(description)" in payload
    assert "MUSIC_DIRECTION_PRESET_IDS.has(webPresetId)" in payload
    for source in (INTEGRATION, PORTAL):
        assert "suggest_music\\|.*" in source
        assert "\\/music_library(?:\\s.*)?" in source

    boundary = _function_block(INTEGRATION, "musicDirectionPresetBoundaryIsSafe")
    assert 'value.execution === "web_native_deterministic_music_direction_only"' in boundary
    for field in BOUNDARY_FIELDS:
        assert f"value.{field} === false" in boundary

    normalizer = _function_block(PORTAL, "normalizeMusicDirectionPresetState")
    assert 'const expected = ["source", "receipt"]' in normalizer
    assert "normalizeMusicDirectionPresetReceipt(state.receipt)" in normalizer
    assert "composer.description !== source.description || composer.language !== source.language" in normalizer
    assert "musicDirectionPresetComposerMatchesPreset(source.web_preset_id, composer)" in normalizer

    matcher = _function_block(INTEGRATION, "musicDirectionPresetResultMatchesSource")
    assert "musicDirectionPresetComposerMatchesPreset(payload.web_preset_id, composer)" in matcher

    receipt_matcher = _function_block(INTEGRATION, "musicDirectionPresetComposerMatchesPreset")
    for required in (
        "composer.mode === expected.mode",
        "composer.suggestion_set === expected.suggestion_set",
        "composer.selected_suggestion === expected.selected_suggestion",
    ):
        assert required in receipt_matcher

    action = _action_block()
    for required in (
        "musicDirectionPresetPayload(fields)",
        'api("/media-workspace/tools/music-directions/compose", {',
        'method: "POST"',
        "musicDirectionPresetResultMatchesSource(payload, data)",
        "musicDirectionPresetBoundaryIsSafe(data)",
        "musicDirectionPresetResult: { source: payload, receipt: data }",
        "musicDirectionPresetDraft: payload",
    ):
        assert required in action
    assert 'route !== expectedPath || currentPortalPath() !== expectedPath' in action
    assert 'capabilities["music-direction-preset-compose"] !== true' in action

    endpoint = _route_block()
    for required in (
        "MusicDirectionPresetRequest",
        "Depends(require_csrf)",
        "_require_enabled()",
        "_music_direction_preset_guard",
        "_music_direction_preset_composer_payload(payload)",
        "_music_direction_preset_boundary()",
        'status_name="draft"',
    ):
        assert required in endpoint


def test_music_directions_fences_stale_requests_and_has_no_memory_or_runtime_side_effect_path() -> None:
    action = _action_block().lower()
    assert "++musicdirectionpresetcomposerequestepoch" in action
    assert "requestepoch !== musicdirectionpresetcomposerequestepoch" in action
    assert "currentportalpath() !== expectedpath" in action
    assert "musicdirectionpresetcomposependingrequestepoch" in action
    for forbidden in (
        "music-prompt-composer-save-memory",
        "/save",
        "/payments",
        "/jobs",
        "payos",
        "idempotency",
        "localstorage",
        "sessionstorage",
        "provider",
        "bridge",
        "telegram",
        "new audio(",
        "<audio",
    ):
        assert forbidden not in action

    listener_start = INTEGRATION.index('window.addEventListener("toanaas:music-direction-preset-draft-edited"')
    listener_end = INTEGRATION.index('window.addEventListener("toanaas:portal-action"', listener_start)
    listener = INTEGRATION[listener_start:listener_end]
    assert "++musicDirectionPresetComposeRequestEpoch" in listener
    assert "setActionBusy(\"music-direction-preset-compose\", \"/media-workspace/music-directions\", false)" in listener
    for forbidden in ("api(", "fetch(", "location", "history", "localStorage", "sessionStorage"):
        assert forbidden not in listener

    endpoint = _route_block()
    for forbidden_call in (
        "_idempotent(",
        "transaction(",
        "_record_audit(",
        "_event(",
        "web_memory_",
        "_insert_collection(",
        "_write_collection_update(",
    ):
        assert forbidden_call not in endpoint
    assert "data={\"composer\": composer, **_music_direction_preset_boundary()}" in endpoint

    result_renderer = _function_block(PORTAL, "renderMusicDirectionPresetResult")
    for forbidden in (
        "music-prompt-composer-save-memory",
        "output_url",
        "job_id",
        "audio_url",
        "preview_url",
        "asset_url",
        "payment_url",
        "collection_id",
        "telegram_message_id",
        "<audio",
        "new Audio(",
    ):
        assert forbidden not in result_renderer

    values = _function_block(PORTAL, "musicDirectionPresetFormValues")
    assert "musicDirectionPresetDraft" in values
    assert "draft.description ? draft" in values

    collector = _function_block(PORTAL, "collectFormFields")
    assert 'if (input.type === "radio")' in collector
    assert 'if (input.checked) fields[input.name] = input.value;' in collector

    locale_payload = _function_block(INTEGRATION, "interfaceLocaleUpdatePayload")
    assert 'Object.prototype.hasOwnProperty.call(source, "locale")' in locale_payload
    assert "Hãy chọn một ngôn ngữ giao diện trước khi lưu." in locale_payload


def test_music_directions_is_accessible_responsive_and_private_from_pwa_shell_cache() -> None:
    music_css = _music_direction_css()
    for selector in (
        ".portal-music-directions",
        ".portal-music-directions-form",
        ".portal-music-directions-preset-grid",
        ".portal-music-directions-preset-card[data-selected=\"true\"]",
        ".portal-music-directions-radio:focus-visible",
        ".portal-music-directions-result",
    ):
        assert selector in music_css
    assert "@media (max-width: 700px)" in music_css
    assert "grid-template-columns: 1fr" in music_css

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/media-workspace/music-directions"' not in shell
    assert '"/media-workspace/music-directions"' in private_paths
    assert '\"/\" + \"api/v1/media-workspace\"' in private_paths
    assert '"/api/v1/media-workspace"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
