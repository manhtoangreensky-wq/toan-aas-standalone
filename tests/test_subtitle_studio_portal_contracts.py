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
    assert 'intent: subtitleStudioNewProjectIntentFromQuery(page)' in PORTAL
    for forbidden in ("api(", "fetch(", "bridge", "payos", "/payments", "/jobs", "provider"):
        assert forbidden not in new_project.lower()
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
    assert "const writable = projectState === \"draft\";" in PORTAL
    assert "const writable = state === \"draft\";" in PORTAL
    assert "archive toàn bộ cue active" in PORTAL
    assert "Sao chép SRT text" in PORTAL
    assert "Sao chép VTT text" in PORTAL
    assert "không có file, output provider hoặc delivery" in PORTAL

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/subtitle-studio" in SERVICE_WORKER
    assert "/api/v1/subtitle-studio" not in shell
    assert '"/subtitle-studio"' not in shell
    # Cache versions intentionally advance whenever the public shell changes;
    # this contract is about keeping private Subtitle routes out of it, not a
    # stale version literal.
    assert 'const CACHE_NAME = "toan-aas-portal-shell-v' in SERVICE_WORKER

    for selector in (
        ".portal-subtitle-studio-intro",
        ".portal-subtitle-project-grid",
        ".portal-subtitle-cue-card",
        ".portal-subtitle-preview-text",
        ".portal-subtitle-studio-guard-list",
        ".portal-subtitle-project-grid, .portal-subtitle-cue-grid { grid-template-columns: 1fr; }",
    ):
        assert selector in CSS
