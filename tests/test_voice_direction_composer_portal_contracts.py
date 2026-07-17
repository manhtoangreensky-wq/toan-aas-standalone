"""Static privacy and contract checks for Voice Direction Composer.

The private route turns the Bot's fixed voice-style ideas into a signed,
transient writing receipt.  It must never turn that receipt into a browser
voice engine, clone/preview player, provider call, job/payment action or
cached private record.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_voice_studio.py").read_text(encoding="utf-8")
ENGINES = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _portal_normalizer() -> str:
    start = PORTAL.index("function normalizeVoiceDirectionComposerResult(raw)")
    end = PORTAL.index("function normalize", start + 12)
    return PORTAL[start:end]


def _integration_result_validator() -> str:
    start = INTEGRATION.index("function voiceDirectionComposerResultIsSafe(value)")
    end = INTEGRATION.index('if (action === "voice-studio-filter" ||', start)
    return INTEGRATION[start:end]


def _integration_action() -> str:
    start = INTEGRATION.index('if (action === "voice-direction-compose")')
    end = INTEGRATION.index('if (action === "voice-studio-filter" ||', start)
    return INTEGRATION[start:end]


def test_voice_direction_composer_is_a_native_private_voice_route_and_catalog_feature() -> None:
    assert 'customerPage("/voice-studio/direction-composer", "Voice Direction Composer"' in PORTAL
    assert 'layout: "voice-direction-composer", type: "voice-direction-composer"' in PORTAL
    assert "function renderVoiceDirectionComposerResult" in PORTAL
    assert "function renderVoiceDirectionComposer(page, context)" in PORTAL
    assert 'case "voice-direction-composer": return renderVoiceDirectionComposer(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="voice-direction-compose"' in PORTAL
    assert 'botCompanionPage("/voice-studio/direction-composer"' not in PORTAL
    assert '"voice_direction_composer"' in ENGINES
    assert 'WebFeature("voice_direction_composer", "Voice Direction Composer", "voice", "/voice-studio/direction-composer"' in REGISTRY


def test_voice_direction_composer_normalizer_and_validator_require_exact_flat_boundary() -> None:
    normalizer = _portal_normalizer()
    validator = _integration_result_validator()
    assert "function normalizeVoiceDirectionComposerResult(raw)" in PORTAL
    assert "function voiceDirectionComposerResultIsSafe(value)" in INTEGRATION

    for field in (
        "input_persisted",
        "raw_audio_stored",
        "consent_attestation_recorded",
        "provider_called",
        "provider_voice_id_stored",
        "tts_called",
        "voice_clone_called",
        "preview_created",
        "audio_created",
        "job_created",
        "wallet_mutated",
        "payment_started",
        "asset_saved",
        "output_created",
        "telegram_called",
    ):
        assert f"source.{field} !== false" in normalizer
        # The normalizer uses `source`; the integration validator names its
        # receipt object `data`.  Both must require the explicit false value.
        assert f"data.{field} === false" in validator
    assert 'source.execution !== "web_native_deterministic_voice_direction_only"' in normalizer
    assert 'data.execution === "web_native_deterministic_voice_direction_only"' in validator

    for source in (normalizer, validator):
        for key in (
            "text",
            "language",
            "suggestion_set",
            "selected_suggestion",
            "reading_speed",
            "suggestions",
            "selected_direction",
            "delivery_notes",
            "cautions",
            "review_before_use",
        ):
            assert key in source
    # Both layers bind the four delivery-note fields through a named exact-key
    # set, rather than treating the nested object as arbitrary free-form data.
    for key in ("pace_adjustment", "pause_notes", "emphasis_notes", "cta_notes"):
        assert f'"{key}"' in PORTAL
        assert f'"{key}"' in INTEGRATION
    for state_field in (
        "voiceDirectionComposerEnabled: source.voiceDirectionComposerEnabled === true",
        "voiceDirectionComposerResult: normalizeVoiceDirectionComposerResult(source.voiceDirectionComposerResult)",
    ):
        assert state_field in PORTAL

    renderer_start = PORTAL.index("function renderVoiceDirectionComposerResult")
    renderer_end = PORTAL.index("function renderVoiceDirectionComposer(page, context)", renderer_start)
    renderer = PORTAL[renderer_start:renderer_end]
    assert "safeText" in renderer
    assert "delivery_notes" in renderer
    for forbidden in (
        "output_url",
        "job_id",
        "audio_url",
        "preview_url",
        "asset_url",
        "payment_url",
        "provider_voice_id",
    ):
        assert forbidden not in renderer


def test_voice_direction_composer_uses_only_signed_csrf_native_api_without_browser_persistence() -> None:
    for helper in ("voiceDirectionComposerPayload", "voiceDirectionComposerResultIsSafe"):
        assert f"function {helper}" in INTEGRATION
    assert '"voice-direction-compose": Boolean(account && me.csrf_token && voiceDirectionComposerEnabled)' in INTEGRATION
    assert '"/voice-studio/direction-composer": account && voiceDirectionComposerEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/voice-studio/tools/direction-composer", {' in INTEGRATION
    assert "voiceDirectionComposerResult: data" in INTEGRATION
    assert "voiceDirectionComposerResult: {}," in INTEGRATION

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
        "tts",
        "clone",
    ):
        assert forbidden not in action
    assert "voicedirectioncomposerpayload(fields)" in action
    assert "voicedirectioncomposerresultissafe(data)" in action


def test_voice_direction_composer_backend_stays_request_only_and_never_claims_audio_delivery() -> None:
    assert "class VoiceDirectionComposerRequest(BaseModel)" in ROUTER
    assert "class VoiceDirectionComposerResult(BaseModel)" in ROUTER
    assert '@router.post("/tools/direction-composer")' in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/direction-composer")')
    # The stateless route is intentionally appended after the durable Voice
    # Studio endpoints; route order is not part of the public contract.
    endpoint = ROUTER[start:]
    assert "_require_enabled" in endpoint
    assert "web_native_deterministic_voice_direction_only" in ROUTER
    for field in (
        '"input_persisted": False',
        '"raw_audio_stored": False',
        '"consent_attestation_recorded": False',
        '"provider_called": False',
        '"provider_voice_id_stored": False',
        '"tts_called": False',
        '"voice_clone_called": False',
        '"preview_created": False',
        '"audio_created": False',
        '"job_created": False',
        '"wallet_mutated": False',
        '"payment_started": False',
        '"asset_saved": False',
        '"output_created": False',
        '"telegram_called": False',
    ):
        assert field in ROUTER
    for forbidden_call in ("_idempotent(", "transaction(", "_record_audit(", "_event("):
        assert forbidden_call not in endpoint


def test_voice_direction_composer_is_responsive_and_never_pwa_cached() -> None:
    for selector in (
        ".portal-voice-direction-composer",
        ".portal-voice-direction-composer-intro",
        ".portal-voice-direction-composer-layout",
        ".portal-voice-direction-composer-form",
        ".portal-voice-direction-composer-boundary",
        ".portal-voice-direction-composer-result",
        ".portal-voice-direction-composer-suggestions",
        ".portal-voice-direction-composer-delivery",
        ".portal-voice-direction-composer-review",
    ):
        assert selector in CSS
    assert "@media" in CSS

    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/voice-studio/direction-composer"' not in shell
    assert '"/voice-studio/direction-composer"' in private_paths
    assert '"/" + "api/v1/voice-studio"' in private_paths
    assert '"/api/v1/voice-studio"' not in shell
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
