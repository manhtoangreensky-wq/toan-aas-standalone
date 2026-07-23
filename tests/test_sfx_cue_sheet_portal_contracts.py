"""Static safety contracts for the Web-native SFX Cue Sheet page.

The interface may present a polished editor workflow, but it must remain a
small signed text-receipt surface: one explicit Web preset, one fresh brief,
and exactly three semantic positions.  It must not silently become a Bot
callback adapter, a sound library/player, a fake media timeline, or an
execution/payment/persistence path.
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
    "motion_transition",
    "interface_confirm",
    "reveal_impact",
    "status_signal",
    "caption_emphasis",
}
EXPECTED_PRESET_FAMILIES = {
    "motion_transition": "motion",
    "interface_confirm": "interface",
    "reveal_impact": "impact",
    "status_signal": "signal",
    "caption_emphasis": "emphasis",
}
EXPECTED_PLACEMENT_IDS = ("opening", "transition", "closing")

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
    "source_video_inspected",
    "catalog_searched",
    "sfx_generated",
)


def _function_block(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\n  function ", start + 1)
    return source[start:end if end != -1 else len(source)]


def _action_block() -> str:
    start = INTEGRATION.index('if (action === "sfx-cue-sheet-compose")')
    end = INTEGRATION.index('if (action === "music-prompt-compose")', start)
    return INTEGRATION[start:end]


def _route_block() -> str:
    start = ROUTER.index('@router.post("/tools/sfx-cue-sheet/compose")')
    end = ROUTER.index('@router.post("/tools/music-prompt-composer/save")', start)
    return ROUTER[start:end]


def _sfx_cue_sheet_css() -> str:
    start = CSS.index(".portal-sfx-cue-sheet {")
    end = CSS.index("\n/* Coordination workspaces", start + 1)
    return CSS[start:end if end != -1 else len(CSS)]


def _quoted_ids_from_set(source: str, declaration: str) -> set[str]:
    start = source.index(declaration)
    end = source.index("]);", start)
    return set(re.findall(r'"([a-z_]+)"', source[start:end]))


def test_sfx_cue_sheet_is_a_private_web_route_with_five_opaque_presets_and_three_positions() -> None:
    page_start = PORTAL.index('customerPage("/media-workspace/sfx-cue-sheet", "SFX Cue Sheet"')
    page = PORTAL[page_start:PORTAL.index("  customerPage(", page_start + 1)]
    assert 'layout: "sfx-cue-sheet", type: "sfx-cue-sheet"' in page
    assert 'case "sfx-cue-sheet": return renderSfxCueSheet(page, context);' in PORTAL
    assert 'WebFeature("sfx_cue_sheet", "SFX Cue Sheet Composer", "music", "/media-workspace/sfx-cue-sheet"' in REGISTRY
    assert 'ENGINE_SPECS.update(_many(("sfx_cue_sheet",), mode=ENGINE_MODE_WEB_NATIVE' in ENGINES
    assert "isNativeSfxCueSheetPath(normalized)" in INTEGRATION

    assert _quoted_ids_from_set(PORTAL, "const SFX_CUE_SHEET_PRESET_IDS = new Set([") == EXPECTED_PRESET_IDS
    assert _quoted_ids_from_set(INTEGRATION, "const SFX_CUE_SHEET_PRESET_IDS = new Set([") == EXPECTED_PRESET_IDS
    assert 'const SFX_CUE_SHEET_PLACEMENT_IDS = new Set(["opening", "transition", "closing"])' in PORTAL
    assert 'const SFX_CUE_SHEET_PLACEMENT_IDS = Object.freeze(["opening", "transition", "closing"])' in INTEGRATION

    map_start = ROUTER.index("SFX_CUE_SHEET_PRESET_MAP")
    map_end = ROUTER.index("SFX_CUE_SHEET_PRESET_IDS", map_start)
    assert set(re.findall(r'^    "([a-z_]+)": \{', ROUTER[map_start:map_end], flags=re.MULTILINE)) == EXPECTED_PRESET_IDS
    for preset_id, family in EXPECTED_PRESET_FAMILIES.items():
        # Both browser maps may quote object keys; pin the semantic mapping
        # without making quote style itself a product contract.
        pattern = rf"[\"']?{re.escape(preset_id)}[\"']?\s*:\s*\"{re.escape(family)}\""
        assert re.search(pattern, PORTAL)
        assert re.search(pattern, INTEGRATION)

    preset_start = PORTAL.index("const SFX_CUE_SHEET_PRESETS = Object.freeze([")
    preset_end = PORTAL.index("]);", preset_start)
    assert set(re.findall(r'id: "([a-z_]+)"', PORTAL[preset_start:preset_end])) == EXPECTED_PRESET_IDS
    assert "sfx_quick|" not in PORTAL[preset_start:preset_end]
    assert "whoosh" not in PORTAL[preset_start:preset_end]
    assert "click" not in PORTAL[preset_start:preset_end]


def test_sfx_cue_sheet_uses_native_radio_selection_without_auto_submit_navigation_or_fake_timing() -> None:
    renderer = _function_block(PORTAL, "renderSfxCueSheet")
    assert 'data-portal-action="sfx-cue-sheet-compose"' in renderer
    assert 'data-portal-route="/media-workspace/sfx-cue-sheet"' in renderer
    assert 'type="radio" name="web_sfx_preset_id"' in renderer
    assert "data-sfx-cue-sheet-preset-card" in renderer
    assert "data-sfx-cue-sheet-submit" in renderer
    assert 'type="hidden" name="web_sfx_preset_id"' not in renderer
    assert "Không có timeline số" in renderer

    sync = _function_block(PORTAL, "synchronizeSfxCueSheetForm")
    edit = _function_block(PORTAL, "markSfxCueSheetDraftEdited")
    assert 'input[name="web_sfx_preset_id"]:checked' in sync
    assert "submit.disabled = !(enabled && presetId)" in sync
    assert 'window.dispatchEvent(new CustomEvent("toanaas:sfx-cue-sheet-draft-edited"))' in edit
    for local_only in (sync, edit):
        for forbidden in ("api(", "fetch(", "location", "history", ".submit(", ".reset(", "localStorage", "sessionStorage"):
            assert forbidden not in local_only

    result_renderer = _function_block(PORTAL, "renderSfxCueSheetResult")
    for forbidden in (
        "output_url", "job_id", "audio_url", "preview_url", "asset_url", "payment_url", "collection_id",
        "telegram_message_id", "<audio", "new Audio(", "start_ms", "end_ms", "duration_seconds", "waveform",
    ):
        assert forbidden not in result_renderer


def test_sfx_cue_sheet_requires_signed_capability_csrf_and_exact_receipt_matching() -> None:
    assert '"sfx-cue-sheet-compose": Boolean(account && me.csrf_token && sfxCueSheetEnabled)' in INTEGRATION
    assert '"/media-workspace/sfx-cue-sheet": account && sfxCueSheetEnabled ? "ready" : "guarded"' in INTEGRATION
    assert "function sfxCueSheetPayload(" in INTEGRATION
    assert "function sfxCueSheetBoundaryIsSafe(" in INTEGRATION
    payload = _function_block(INTEGRATION, "sfxCueSheetPayload")
    assert 'const allowed = ["description", "language", "web_sfx_preset_id"]' in payload
    assert "SFX_CUE_SHEET_RAW_BOT_INPUT_PATTERN.test(description)" in payload
    assert "SFX_CUE_SHEET_PRESET_IDS.has(presetId)" in payload
    for source in (INTEGRATION, PORTAL):
        assert "SFX_CUE_SHEET_RAW_BOT_INPUT_PATTERN" in source
        assert "sfx_quick" in source
        assert "/sfx_library" in source

    boundary = _function_block(INTEGRATION, "sfxCueSheetBoundaryIsSafe")
    assert 'value.execution === "web_native_deterministic_sfx_cue_sheet_only"' in boundary
    for field in BOUNDARY_FIELDS:
        assert f"value.{field} === false" in boundary

    normalizer = _function_block(PORTAL, "normalizeSfxCueSheetState")
    assert 'const expected = ["source", "receipt"]' in normalizer
    assert "normalizeSfxCueSheetReceipt(state.receipt)" in normalizer
    assert "cueSheet.description !== source.description || cueSheet.language !== source.language" in normalizer
    assert "cueSheet.web_sfx_preset_id !== source.web_sfx_preset_id" in normalizer
    receipt_normalizer = _function_block(PORTAL, "normalizeSfxCueSheetReceipt")
    assert "SFX_CUE_SHEET_RESULT_KEYS" in receipt_normalizer
    assert "sfxCueSheetBoundaryIsSafe(boundary)" in receipt_normalizer
    assert "cueFamily !== expectedFamily" in receipt_normalizer
    assert "cues.length !== placementIds.length" in receipt_normalizer

    action = _action_block()
    for required in (
        "sfxCueSheetPayload(fields)",
        'api("/media-workspace/tools/sfx-cue-sheet/compose", {',
        'method: "POST"',
        "sfxCueSheetBoundaryIsSafe(data)",
        "sfxCueSheetResult: { source: payload, receipt: data }",
        "sfxCueSheetDraft: payload",
    ):
        assert required in action
    assert "route !== expectedPath || currentPortalPath() !== expectedPath" in action
    assert 'capabilities["sfx-cue-sheet-compose"] !== true' in action

    endpoint = _route_block()
    for required in (
        "SfxCueSheetRequest",
        "Depends(require_csrf)",
        "_require_enabled()",
        "_sfx_cue_sheet_guard",
        "_compose_sfx_cue_sheet(payload)",
        "_sfx_cue_sheet_boundary()",
        'status_name="draft"',
    ):
        assert required in endpoint


def test_sfx_cue_sheet_fences_stale_requests_and_has_no_execution_or_persistence_side_effect_path() -> None:
    action = _action_block().lower()
    assert "++sfxcuesheetcomposerequestepoch" in action
    assert "requestepoch !== sfxcuesheetcomposerequestepoch" in action
    assert "currentportalpath() !== expectedpath" in action
    assert "sfxcuesheetcomposependingrequestepoch" in action
    for forbidden in (
        "/save", "/payments", "/jobs", "payos", "idempotency", "localstorage", "sessionstorage",
        "provider", "bridge", "telegram", "new audio(", "<audio", "timeline", "duration_seconds", "start_ms",
    ):
        assert forbidden not in action

    listener_start = INTEGRATION.index('window.addEventListener("toanaas:sfx-cue-sheet-draft-edited"')
    listener_end = INTEGRATION.index('window.addEventListener("toanaas:portal-action"', listener_start)
    listener = INTEGRATION[listener_start:listener_end]
    assert "++sfxCueSheetComposeRequestEpoch" in listener
    assert 'setActionBusy("sfx-cue-sheet-compose", "/media-workspace/sfx-cue-sheet", false)' in listener
    for forbidden in ("api(", "fetch(", "location", "history", "localStorage", "sessionStorage"):
        assert forbidden not in listener

    endpoint = _route_block()
    for forbidden_call in (
        "_idempotent(", "transaction(", "_record_audit(", "_event(", "web_memory_",
        "_insert_collection(", "_write_collection_update(",
    ):
        assert forbidden_call not in endpoint
    assert 'data={"cue_sheet": cue_sheet, **_sfx_cue_sheet_boundary()}' in endpoint


def test_sfx_cue_sheet_is_accessible_responsive_and_private_from_pwa_shell_cache() -> None:
    sfx_css = _sfx_cue_sheet_css()
    for selector in (
        ".portal-sfx-cue-sheet",
        ".portal-sfx-cue-sheet-form",
        ".portal-sfx-cue-sheet-preset-grid",
        ".portal-sfx-cue-sheet-preset-card[data-selected=\"true\"]",
        ".portal-sfx-cue-sheet-radio:focus-visible",
        ".portal-sfx-cue-sheet-result",
    ):
        assert selector in sfx_css
    assert "@media (max-width: 700px)" in sfx_css
    assert "grid-template-columns: 1fr" in sfx_css
    assert 'grid-template-areas: "form boundary" "result result"' in sfx_css
    assert 'grid-template-areas: "form" "result" "boundary"' in sfx_css
    assert ".portal-sfx-cue-sheet-form .portal-select, .portal-sfx-cue-sheet-form .portal-button { min-height: 44px; }" in sfx_css
    assert ".portal-sfx-cue-sheet-preset-cue" in sfx_css and "font-size: 11px" in sfx_css
    assert ".portal-sfx-cue-sheet-guard-list em" in sfx_css and ".portal-sfx-cue-sheet-list-head em" in sfx_css

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/media-workspace/sfx-cue-sheet"' not in shell
    assert '"/media-workspace/sfx-cue-sheet"' in private_paths
    assert '\"/\" + "api/v1/media-workspace"' in private_paths
    assert '"/api/v1/media-workspace"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER


def test_sfx_cue_sheet_keeps_unsent_edits_stale_across_remount_without_storage_or_auto_navigation() -> None:
    values = _function_block(PORTAL, "sfxCueSheetFormValues")
    remember = _function_block(PORTAL, "rememberSfxCueSheetTransientDraft")
    edit = _function_block(PORTAL, "markSfxCueSheetDraftEdited")
    result = _function_block(PORTAL, "renderSfxCueSheetResult")
    placement = _function_block(PORTAL, "placeSfxCueSheetReceipt")
    action = _action_block()

    assert "transientFormDrafts.has(SFX_CUE_SHEET_ROUTE)" in values
    assert "sfxCueSheetTransientFormValues(transientFormValues(SFX_CUE_SHEET_ROUTE))" in values
    assert "transientFormDrafts.set(SFX_CUE_SHEET_ROUTE" in remember
    assert "rememberSfxCueSheetTransientDraft(form);" in edit
    assert "receiptIsStale" in result
    assert 'data-sfx-cue-sheet-receipt' in result
    assert 'portal-sfx-cue-sheet-result" aria-live="polite"' not in result
    assert 'tabindex="-1" data-sfx-cue-sheet-result-heading' in result
    assert "layout.insertBefore(receipt, boundary);" in placement
    assert 'status.setAttribute("role", "status")' in placement
    assert 'setSfxCueSheetSubmissionStatus("Đã lập 3 cue semantic. Kết quả ở bên dưới.")' in action

    assert "function clearSessionScopedTransientDrafts()" in INTEGRATION
    assert "clearTransientFormDraft(SFX_CUE_SHEET_ROUTE)" in INTEGRATION
    for source in (values, remember, edit, result, placement):
        for forbidden in ("localStorage", "sessionStorage", "location", "history", "api(", "fetch("):
            assert forbidden not in source


def test_sfx_cue_sheet_has_a_clear_audio_workspace_entry_and_readable_review_copy() -> None:
    """Keep this bounded tool discoverable without disguising it as a library.

    The parent workspace and side navigation are the two customer-facing entry
    points.  The second assertion protects task-critical cue/review text from
    being reduced back to decorative metadata sizes on the dark app surface.
    """

    navigation_start = PORTAL.index('label: "AI Labs & Media"')
    navigation_end = PORTAL.index('label: "Tạo mới"', navigation_start)
    navigation = PORTAL[navigation_start:navigation_end]
    assert '["/media-workspace/sfx-cue-sheet", "SFX Cue Sheet", ICONS.music]' in navigation

    workspace = _function_block(PORTAL, "renderMediaWorkspace")
    assert "Công cụ biên tập nhanh" in workspace
    assert "Lập SFX theo ngữ cảnh trước khi chọn nguồn âm thanh" in workspace
    assert 'href="/media-workspace/sfx-cue-sheet"' in workspace

    assert "task-critical text" in CSS
    assert ".portal-sfx-cue-sheet .portal-form-note" in CSS
    assert ".portal-sfx-cue-sheet-result[data-stale=\"true\"]::after { font-size: 13px; }" in CSS
    assert ".portal-sfx-cue-sheet-index { font-size: 11px; }" in CSS
