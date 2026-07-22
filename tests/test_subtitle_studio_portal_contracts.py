"""Static contracts for the Web-native Subtitle & Transcript Workspace.

The route family is deliberately independent from the legacy Bot-facing
subtitle/translate/dubbing/ASR screens.  These checks keep all text authoring
private, revisioned and honest about its lack of media/provider execution.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "SUBTITLE_TRANSCRIPT_WORKSPACE_CONTRACT.md").read_text(encoding="utf-8")
SERVER = (ROOT / "copyfast_subtitle_workspace.py").read_text(encoding="utf-8")


def test_subtitle_studio_is_native_and_does_not_alias_legacy_routes() -> None:
    assert 'customerPage("/subtitle-studio"' in PORTAL
    assert 'customerPage("/subtitle-studio/new"' in PORTAL
    assert 'path: "/subtitle-studio/:id"' in PORTAL
    assert "function renderSubtitleStudio(" in PORTAL
    assert "function renderSubtitleStudioDetail(" in PORTAL
    assert 'case "subtitle-studio": return renderSubtitleStudio(page, context);' in PORTAL
    assert 'case "subtitle-studio-detail": return renderSubtitleStudioDetail(page, context);' in PORTAL
    assert "SUBTITLE_STUDIO_PATH" in PAGES
    assert "SUBTITLE_STUDIO_PATH.fullmatch(normalized)" in PAGES
    assert 'if (linkPath === "/subtitle-studio") return matchesRouteFamily(path, "/subtitle-studio");' in PORTAL
    assert 'if (linkPath === "/subtitle") return matchesRouteFamily(path, "/subtitle") || ["/translate", "/dubbing", "/asr"].includes(path);' in PORTAL
    assert "function isNativeSubtitleStudioPath(" in INTEGRATION
    assert "isNativeSubtitleStudioPath(path)" in INTEGRATION
    assert "isNativeSubtitleStudioPath(currentPath)" in INTEGRATION
    assert 'botCompanionPage("/subtitle-studio"' not in PORTAL


def test_legacy_subtitle_routes_offer_only_a_plain_text_editor_navigation_link() -> None:
    start = PORTAL.index("const SUBTITLE_STUDIO_COMPANION_INTENTS")
    end = PORTAL.index("function renderWorkspace", start)
    companion = PORTAL[start:end]
    expected_intents = {
        "/subtitle": "subtitle",
        "/subtitle/create": "subtitle",
        "/translate": "translation",
        "/dubbing": "dubbing_direction",
        "/asr": "asr_review",
    }
    for route, intent in expected_intents.items():
        assert f'"{route}": "{intent}"' in companion
    assert "function renderSubtitleStudioCompanionLink(page)" in companion
    assert 'const href = `/subtitle-studio/new?intent=${encodeURIComponent(intent)}`;' in companion
    assert "Biên tập transcript/cue thủ công" in companion
    assert "không chuyển prompt, upload, media hoặc trạng thái" in companion
    assert "không chạy ASR, dịch máy, TTS hoặc dubbing" in companion
    for forbidden in ("data-portal-action", "data-portal-form", "data-portal-route", "api(", "fetch(", "window.location"):
        assert forbidden not in companion

    workspace_start = PORTAL.index("function renderWorkspace(page, context)")
    workspace_end = PORTAL.index("function renderVoiceVault", workspace_start)
    workspace = PORTAL[workspace_start:workspace_end]
    assert "renderSubtitleStudioCompanionLink(page)" in workspace
    assert "${subtitleStudioCompanion}" in workspace

    # The compatibility flows stay intact; the link is deliberately not a
    # redirect/alias and does not remove their bridge mapping or intake rules.
    feature_start = INTEGRATION.index("const FEATURE_BY_PATH")
    feature_end = INTEGRATION.index("  };", feature_start) + len("  };")
    feature_map = INTEGRATION[feature_start:feature_end]
    for route in ("/subtitle", "/subtitle/create", "/translate", "/dubbing", "/asr"):
        assert f'"{route}"' in feature_map


def test_subtitle_studio_new_project_query_is_allowlisted_and_form_only() -> None:
    start = PORTAL.index("const SUBTITLE_STUDIO_INTENTS")
    end = PORTAL.index("function subtitleStudioCueFields", start)
    new_project = PORTAL[start:end]
    assert "const SUBTITLE_STUDIO_INTENT_KEYS = new Set" in new_project
    assert "function subtitleStudioNewProjectIntentFromQuery(page)" in new_project
    assert 'if (route !== "/subtitle-studio/new") return "subtitle";' in new_project
    assert 'new URLSearchParams(window.location.search).get("intent")' in new_project
    assert 'SUBTITLE_STUDIO_INTENT_KEYS.has(candidate) ? candidate : "subtitle"' in new_project
    assert 'intent: draft.intent || subtitleStudioNewProjectIntentFromQuery(page)' in PORTAL
    query_start = PORTAL.index("function subtitleStudioNewProjectIntentFromQuery(page)")
    query_end = PORTAL.index("function subtitleStudioCueFields", query_start)
    query_helper = PORTAL[query_start:query_end].lower()
    for forbidden in ("api(", "fetch(", "bridge", "payos", "/payments", "/jobs", "provider"):
        assert forbidden not in query_helper
    for mapping in (
        "`/subtitle`, `/subtitle/create` | `?intent=subtitle`",
        "`/translate` | `?intent=translation`",
        "`/asr` | `?intent=asr_review`",
        "`/dubbing` | `?intent=dubbing_direction`",
    ):
        assert mapping in CONTRACT
    assert "không mang theo" in CONTRACT
    assert "không phải redirect\nhay alias" in CONTRACT


def test_subtitle_studio_uses_private_text_only_api_and_server_revision_controls() -> None:
    for helper in (
        "subtitleProjectIdFromPath",
        "subtitleStudioMetadataSafetyError",
        "subtitleProjectPayload",
        "subtitleCuePayload",
        "subtitleTextImportPayload",
        "subtitleStudioBoundaryIsSafe",
        "hydrateSubtitleStudio",
        "hydrateSubtitleProject",
        "subtitleStudioMutation",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    for endpoint in (
        'api("/subtitle-studio/summary")',
        'api(subtitleStudioProjectsPath(requested))',
        'api("/subtitle-studio/events?limit=50")',
        'api("/subtitle-studio/references")',
        'api("/subtitle-studio/projects/" + encodeURIComponent(String(projectId)))',
        '"/subtitle-studio/projects/" + encodeURIComponent(String(projectId)) + "/estimate"',
        'path: "/subtitle-studio/projects"',
        '/subtitle-studio/projects/${encodeURIComponent(projectId)}/import',
        '/subtitle-studio/projects/${encodeURIComponent(projectId)}/export?format=${encodeURIComponent(format)}',
    ):
        assert endpoint in INTEGRATION

    for capability in (
        '"subtitle-studio-view": Boolean(account && subtitleStudioEnabled)',
        '"subtitle-project-create": Boolean(account && me.csrf_token && subtitleStudioEnabled)',
        '"subtitle-cue-import": Boolean(account && me.csrf_token && subtitleStudioEnabled)',
        '"subtitle-text-export": Boolean(account && subtitleStudioEnabled)',
        '"subtitle-cue-reorder": Boolean(account && me.csrf_token && subtitleStudioEnabled)',
    ):
        assert capability in INTEGRATION

    # Browser payload and server DTO agree exactly: form field remains `text`
    # but the contract key is `content`, preventing an extra=forbid 422.
    assert "return { format, content: text };" in INTEGRATION
    assert 'intent, caption_format: captionFormat' in INTEGRATION
    assert '"subtitle", "translation", "asr_review", "dubbing_direction"' in INTEGRATION
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "expected_revision: expectedRevision" in INTEGRATION
    assert "cue_ids: cueIds" in INTEGRATION

    start = INTEGRATION.index('if (action === "subtitle-studio-refresh")')
    end = INTEGRATION.index('if (action === "voice-studio-filter"')
    actions = INTEGRATION[start:end].lower()
    for forbidden in ("bridgeavailable", "core bridge", "payos", "/payments", "/jobs", "provider call"):
        assert forbidden not in actions
    for action in (
        "subtitle-studio-refresh",
        "subtitle-project-create",
        "subtitle-project-update",
        "subtitle-project-state",
        "subtitle-project-restore-version",
        "subtitle-cue-create",
        "subtitle-cue-import",
        "subtitle-text-export",
        "subtitle-cue-update",
        "subtitle-cue-archive",
        "subtitle-cue-restore",
        "subtitle-cue-restore-version",
        "subtitle-cue-reorder",
    ):
        assert action in actions


def test_subtitle_studio_stays_text_only_and_draft_editable() -> None:
    # The safe boundary explicitly rejects successful provider/media claims.
    for flag in (
        'boundary.execution === "authoring_only"',
        "boundary.provider_called === false",
        "boundary.output_created === false",
        "boundary.asr_called === false",
        "boundary.tts_called === false",
        "boundary.dubbing_called === false",
        "boundary.translation_called === false",
    ):
        assert flag in INTEGRATION

    # URLs can be part of spoken/displayed caption text and must remain plain
    # escaped text; project metadata and notes use the strict safety helper.
    assert "const cueSafety = subtitleStudioSecretSafetyError(sourceText, translatedText);" in INTEGRATION
    assert "const metadataSafety = subtitleStudioMetadataSafetyError(speaker, notes);" in INTEGRATION
    assert '<pre class="portal-subtitle-preview-text">${safeText(preview)}</pre>' in PORTAL
    assert 'const writable = projectState === "draft" && subtitleStudioSourceContractWritable(project);' in PORTAL
    assert "const writable = state === \"draft\";" in PORTAL
    assert "archive toàn bộ cue active" in PORTAL
    assert "Sao chép SRT text" in PORTAL
    assert "Sao chép VTT text" in PORTAL
    assert "không có file, output provider hoặc delivery" in PORTAL

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/subtitle-studio" in SERVICE_WORKER
    assert "/api/v1/subtitle-studio" not in shell
    assert '"/subtitle-studio"' not in shell
    # The build-scoped cache must retire only obsolete portal shell generations;
    # private Subtitle routes remain outside it.
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER
    assert "const BUILD_ID = workerBuildId();" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    assert ".filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)" in SERVICE_WORKER

    for selector in (
        ".portal-subtitle-studio-intro",
        ".portal-subtitle-project-grid",
        ".portal-subtitle-cue-card",
        ".portal-subtitle-preview-text",
        ".portal-subtitle-studio-guard-list",
        ".portal-subtitle-project-grid, .portal-subtitle-cue-grid { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS


def test_language_source_intake_is_new_project_only_and_metadata_only() -> None:
    source_start = PORTAL.index("const SUBTITLE_LANGUAGE_SOURCE_MODE_KEYS")
    source_end = PORTAL.index("function subtitleStudioNewProjectIntentFromQuery", source_start)
    source_ui = PORTAL[source_start:source_end]
    for pair in (
        ".mp4|video/mp4",
        ".mov|video/quicktime",
        ".webm|video/webm",
        ".mp3|audio/mpeg",
        ".wav|audio/wav",
        ".m4a|audio/mp4",
        ".ogg|audio/ogg",
        ".txt|text/plain",
        ".srt|application/x-subrip",
        ".vtt|text/vtt",
    ):
        assert pair in source_ui
    for field in ("source_mode", "source_asset_id", "source_rights_confirmed"):
        assert f'name: "{field}"' in source_ui
    # The source UI passes an opaque Vault UUID only.  It cannot grow a
    # browser upload, Blob preview/download or a direct provider/bridge call.
    for forbidden in (
        'type: "file"',
        "<input type=\"file\"",
        "FileReader",
        "createObjectURL",
        "new FormData",
        ".blob(",
        "fetch(",
        "api(",
        "XMLHttpRequest",
        "data-portal-upload",
        "original_filename",
        "storage_key",
        "sha256",
    ):
        assert forbidden not in source_ui
    assert "safeText(facts)" in source_ui
    assert "asset_available" in source_ui
    assert "Không có preview, upload, download, ASR hoặc dịch máy" in source_ui

    create_start = PORTAL.index("function renderSubtitleStudio(")
    create_end = PORTAL.index("function renderSubtitleStudioDetail(", create_start)
    create_view = PORTAL[create_start:create_end]
    detail_end = PORTAL.index("function renderSubtitleStudioCompanionLink", create_end)
    detail_view = PORTAL[create_end:detail_end]
    assert "subtitleStudioProjectFields(context, true)" in create_view
    assert "subtitleStudioProjectFields(context)" in detail_view
    assert "subtitleStudioProjectFields(context, true)" not in detail_view
    assert "renderSubtitleStudioLanguageSource(project)" in detail_view


def test_language_source_frontend_contract_is_signed_private_and_has_no_execution_path() -> None:
    payload_start = INTEGRATION.index("function subtitleProjectPayload")
    payload_end = INTEGRATION.index("function subtitleCuePayload", payload_start)
    payload = INTEGRATION[payload_start:payload_end]
    assert "const sourceIntake = Boolean(options && options.sourceIntake === true);" in payload
    assert 'source_mode: "manual", source_asset_id: null, source_rights_confirmed: false' in payload
    assert 'source_mode: "asset_reference", source_asset_id: sourceAssetId, source_rights_confirmed: true' in payload
    for forbidden in ("fetch(", "api(", "FileReader", "createObjectURL", "new FormData", ".blob(", "/jobs", "/payments"):
        assert forbidden not in payload

    hydration_start = INTEGRATION.index("async function hydrateSubtitleStudio")
    hydration_end = INTEGRATION.index("async function hydrateSubtitleProject", hydration_start)
    hydration = INTEGRATION[hydration_start:hydration_end]
    assert "api(subtitleLanguageSourcePagePath(0), { cache: \"no-store\" })" in hydration
    assert "subtitleLanguageSourcesStateFromPage({}, languageSources, false)" in hydration
    assert "rawProjects.every(subtitleStudioProjectIsSafe)" in hydration
    assert "subtitleLanguageSources: languageSourceState" in hydration
    assert "subtitleLanguageSources: {}" in hydration
    for flag in (
        "boundary.source_bytes_read === false",
        "boundary.provider_called === false",
        "boundary.bot_called === false",
        "boundary.bridge_called === false",
        "boundary.job_created === false",
        "boundary.download_created === false",
        "boundary.payment_started === false",
        "boundary.wallet_mutated === false",
    ):
        assert flag in INTEGRATION

    create_action_start = INTEGRATION.index('if (action === "subtitle-project-create")')
    create_action_end = INTEGRATION.index('if (action === "subtitle-project-update")', create_action_start)
    create_action = INTEGRATION[create_action_start:create_action_end]
    update_action_end = INTEGRATION.index('if (action === "subtitle-project-state")', create_action_end)
    update_action = INTEGRATION[create_action_end:update_action_end]
    assert "subtitleProjectPayload(fields, { sourceIntake: true })" in create_action
    assert "subtitleProjectPayload(fields)" in update_action
    assert "sourceIntake: true" not in update_action

    # A private workspace route/API may never become a shell or offline page;
    # the worker only caches its finite public asset allow-list.
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/subtitle-studio" not in shell
    assert '"/subtitle-studio"' not in shell
    public_paths = SERVICE_WORKER.split("const PUBLIC_NAVIGATION_PATHS = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/subtitle-studio"' not in public_paths


def test_language_source_project_contract_fails_closed_and_paginates_metadata_only() -> None:
    integration_start = INTEGRATION.index("function subtitleLanguageSourceAssetIsSafe")
    integration_end = INTEGRATION.index("async function downloadPromptLibraryExport", integration_start)
    source_contract = INTEGRATION[integration_start:integration_end]
    for required in (
        "function subtitleProjectLanguageSourceIsSafe",
        "function subtitleStudioProjectIsSafe",
        "function subtitleStudioProjectCreateReceiptIsSafe",
        "function subtitleLanguageSourceAttestationIsSafe",
        "source.mode === \"manual\"",
        "source.mode === \"guarded\"",
        "source.mode !== \"asset_reference\"",
        "source.rights_confirmed !== true",
        "source.asset_available === true && subtitleLanguageSourceAssetIsSafe(source.asset)",
        "String(item.state || \"\") === \"active\"",
        "Number.isInteger(revision) && revision >= 1",
        "SUBTITLE_LANGUAGE_SOURCE_ASSET_PAIRS.has(`${extension}|${contentType}`)",
        "SUBTITLE_LANGUAGE_SOURCE_PAGE_LIMIT = 30",
        "SUBTITLE_LANGUAGE_SOURCE_MAX_RENDERED = 90",
        "function subtitleLanguageSourcesStateFromPage",
        "is_render_capped: isRenderCapped",
    ):
        assert required in source_contract
    # MIME parameters must not be normalized into an allowlisted pair.
    assert '.split(";", 1)' not in source_contract

    hydration_start = INTEGRATION.index("async function hydrateSubtitleLanguageSources")
    hydration_end = INTEGRATION.index("async function hydrateSubtitleProject", hydration_start)
    pager_hydration = INTEGRATION[hydration_start:hydration_end]
    assert 'api(subtitleLanguageSourcePagePath(requestedOffset), { cache: "no-store" })' in pager_hydration
    assert "requestedOffset !== expectedOffset" in pager_hydration
    assert "merge({ subtitleLanguageSources: state })" in pager_hydration
    for forbidden in ("FileReader", "createObjectURL", "new FormData", ".blob(", "/jobs", "/payments"):
        assert forbidden not in pager_hydration

    action_start = INTEGRATION.index('if (action === "subtitle-language-source-more")')
    action_end = INTEGRATION.index('if (action === "subtitle-asset-operation-refresh")', action_start)
    pager_action = INTEGRATION[action_start:action_end]
    assert 'base().capabilities["subtitle-language-source-more"] === true' in pager_action
    assert "fields.__subtitleLanguageSourceOffset" in pager_action
    assert "hydrateSubtitleLanguageSources(offset)" in pager_action

    studio_hydration_start = INTEGRATION.index("async function hydrateSubtitleStudio(overrides)")
    studio_hydration_end = INTEGRATION.index("async function hydrateSubtitleLanguageSources", studio_hydration_start)
    studio_hydration = INTEGRATION[studio_hydration_start:studio_hydration_end]
    assert "++subtitleLanguageSourceHydrationEpoch;" in studio_hydration

    create_start = INTEGRATION.index('if (action === "subtitle-project-create")')
    create_end = INTEGRATION.index('if (action === "subtitle-project-update")', create_start)
    create_action = INTEGRATION[create_start:create_end]
    assert "subtitleStudioProjectCreateReceiptIsSafe(receipt)" in create_action
    assert "subtitleStudioProjectIsSafe(receipt)" not in create_action

    portal_start = PORTAL.index("function subtitleLanguageSourceAttestationIsSafe")
    portal_end = PORTAL.index("function subtitleStudioNewProjectIntentFromQuery", portal_start)
    portal_source = PORTAL[portal_start:portal_end]
    assert 'if (!source) return { mode: "guarded", asset: null, available: false, rights: false };' in portal_source
    assert 'String(source.mode || "manual")' not in portal_source
    assert "function renderSubtitleLanguageSourcePager" in portal_source
    assert "function subtitleStudioSourceContractWritable" in portal_source
    assert 'data-portal-action="subtitle-language-source-more"' in portal_source
    assert "data-subtitle-language-source-offset" in portal_source
    assert 'data-subtitle-language-source-dependent="asset"' in portal_source
    assert "SUBTITLE_LANGUAGE_SOURCE_MAX_RENDERED = 90" in PORTAL
    assert '.split(";", 1)' not in portal_source
    for forbidden in ("FileReader", "createObjectURL", "new FormData", ".blob(", "fetch(", "api(", "storage_key", "original_filename"):
        assert forbidden not in portal_source

    dispatch_start = PORTAL.index("function dispatchAction")
    dispatch_end = PORTAL.index("function bindInteractions", dispatch_start)
    dispatch = PORTAL[dispatch_start:dispatch_end]
    assert "const subtitleLanguageSourcePickerAction" in dispatch
    assert "__subtitleLanguageSourceOffset" in dispatch
    assert 'source.getAttribute("data-subtitle-language-source-offset")' in dispatch

    detail_start = PORTAL.index("function renderSubtitleCueCard")
    detail_end = PORTAL.index("function renderStudioDocumentEditor", detail_start)
    detail_ui = PORTAL[detail_start:detail_end]
    assert 'projectState === "draft" && subtitleStudioSourceContractWritable(project)' in detail_ui
    assert 'state === "draft" && sourceContractWritable' in detail_ui
    assert 'Boolean(sourceContractWritable && context.capabilities && context.capabilities["subtitle-project-lifecycle"] === true)' in detail_ui


def test_language_source_server_has_no_asset_stream_provider_or_bridge_import() -> None:
    # The only database read is a narrow owner-scoped metadata projection;
    # this module has no ability to open the referenced file or execute it.
    assert "@router.get(\"/references/language-sources\")" in SERVER
    assert "FROM web_asset_files WHERE id=? AND account_id=?" in SERVER
    assert "SELECT id, display_name, extension, content_type, byte_size, state, lifecycle_revision, updated_at" in SERVER
    for forbidden in (
        "from copyfast_assets import",
        "import copyfast_assets",
        "from copyfast_bridge import",
        "import copyfast_bridge",
        "open_verified_private_asset_stream",
        "FileResponse",
        "StreamingResponse",
        "httpx.",
        "requests.",
        "@router.post(\"/uploads\")",
    ):
        assert forbidden not in SERVER
