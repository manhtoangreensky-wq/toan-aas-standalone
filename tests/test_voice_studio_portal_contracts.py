"""Static contracts for the private, Web-native Voice Studio surface.

These contracts deliberately stay structural rather than snapshotting copy or
CSS.  They protect the important separation: `/voice-studio` is its own
signed-account authoring workspace, never a route alias that accidentally
calls the existing Bot/Core-Bridge Voice Vault or a cacheable audio surface.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_voice_studio.py").read_text(encoding="utf-8")


def test_voice_studio_is_a_native_private_route_not_the_legacy_voice_alias() -> None:
    assert 'customerPage("/voice-studio"' in PORTAL
    assert 'customerPage("/voice-studio/new"' in PORTAL
    assert 'path: "/voice-studio/:id"' in PORTAL
    assert "function renderVoiceStudio(" in PORTAL
    assert "function renderVoiceStudioDetail(" in PORTAL
    assert 'case "voice-studio": return renderVoiceStudio(page, context);' in PORTAL
    assert 'case "voice-studio-detail": return renderVoiceStudioDetail(page, context);' in PORTAL
    assert "VOICE_STUDIO_PATH" in PAGES
    assert "VOICE_STUDIO_PATH.fullmatch(normalized)" in PAGES
    assert 'botCompanionPage("/voice-studio"' not in PORTAL

    # `/voice` remains the existing Bot/Core-Bridge family.  The hyphenated
    # Web-native route must not be swallowed by a startsWith("/voice") check.
    assert 'path === "/voice" || path.startsWith("/voice/")' in INTEGRATION

    # The globally delegated shell action must forward native Voice Studio
    # IDs/revisions and must not let an unrelated incomplete form block a
    # state action such as archive/restore/version restore.
    for field in (
        'voiceVaultId: source.getAttribute("data-voice-vault-id") || ""',
        'voiceVaultRevision: source.getAttribute("data-voice-vault-revision") || ""',
        'voiceVaultVersion: source.getAttribute("data-voice-vault-version") || ""',
        'voiceScriptId: source.getAttribute("data-voice-script-id") || ""',
        'voiceScriptRevision: source.getAttribute("data-voice-script-revision") || ""',
        'voiceScriptVersion: source.getAttribute("data-voice-script-version") || ""',
    ):
        assert field in PORTAL
    assert '"voice-vault-archive"' in PORTAL
    assert '"voice-script-cue-sheet"' in PORTAL


def test_voice_studio_hydrates_and_mutates_only_via_private_native_api() -> None:
    for helper in (
        "voiceVaultIdFromPath",
        "isNativeVoiceStudioPath",
        "voiceStudioSafetyError",
        "voiceVaultPayload",
        "voiceScriptPayload",
        "voiceStudioFilterPayload",
        "hydrateVoiceStudio",
        "hydrateVoiceVault",
        "hydrateVoiceCueSheet",
        "voiceStudioMutation",
    ):
        assert f"function {helper}" in INTEGRATION or f"async function {helper}" in INTEGRATION

    for endpoint in (
        'api("/voice-studio/summary")',
        'api("/voice-studio/policy")',
        'api("/voice-studio/events?limit=50")',
        'api("/voice-studio/references")',
        'path: "/voice-studio/vaults"',
        'api("/voice-studio/vaults/" + encodeURIComponent(String(vaultId)))',
    ):
        assert endpoint in INTEGRATION

    for capability in (
        '"voice-studio-view": Boolean(account && voiceStudioEnabled)',
        '"voice-vault-create": Boolean(account && me.csrf_token && voiceStudioEnabled)',
        '"voice-script-create": Boolean(account && me.csrf_token && voiceStudioEnabled)',
        '"voice-script-cue-sheet": Boolean(account && voiceStudioEnabled)',
    ):
        assert capability in INTEGRATION

    assert '[route]: "ready"' in INTEGRATION
    assert '[route]: "read_only"' not in INTEGRATION[INTEGRATION.index("async function hydrateVoiceVault"):INTEGRATION.index("async function hydrateVoiceCueSheet")]

    assert "WEB_VOICE_STUDIO_BODY_TOO_LARGE" in APP
    assert "VOICE_STUDIO_BODY_MAX_BYTES = 128 * 1024" in APP
    assert '"voice-studio-write" if voice_studio_write' in APP
    assert '"voice-studio-read" if voice_studio_read' in APP
    assert "WEBAPP_VOICE_STUDIO_ENABLED" in ROUTER

    # Every command remains within the local Voice Studio API.  In particular,
    # a future UI cannot silently expose Bot jobs, payments, or bridge voice
    # profiles by appending actions here.
    start = INTEGRATION.index('if (action === "voice-studio-filter"')
    end = INTEGRATION.index('if (action === "support-cases-filter")')
    actions = INTEGRATION[start:end].lower()
    for forbidden in ("bridgeavailable", "core bridge", "payos", "/payments", "/jobs", "/voice/profiles"):
        assert forbidden not in actions
    for action in (
        "voice-studio-filter",
        "voice-studio-refresh",
        "voice-vault-create",
        "voice-vault-update",
        "voice-vault-archive",
        "voice-vault-restore",
        "voice-vault-duplicate",
        "voice-vault-restore-version",
        "voice-vault-compose",
        "voice-script-create",
        "voice-script-update",
        "voice-script-archive",
        "voice-script-restore",
        "voice-script-duplicate",
        "voice-script-restore-version",
        "voice-script-cue-sheet",
    ):
        assert action in actions
    assert "voicestudiomutation({" in actions
    assert "idempotency_key: submission.key" in INTEGRATION
    assert "local_deterministic_draft_only" in actions
    assert "provider_called !== false" in actions
    assert "audio_created !== false" in actions


def test_voice_studio_cannot_become_provider_or_private_pwa_storage() -> None:
    assert "from copyfast_bridge import" not in ROUTER
    assert "import requests" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "urllib.request" not in ROUTER
    assert '"provider_called": False' in ROUTER
    assert '"audio_created": False' in ROUTER
    assert "local_deterministic_writing_aid" in ROUTER
    assert "local_deterministic_draft_only" in ROUTER

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert "/api/v1/voice-studio" not in shell
    assert '"/voice-studio"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
