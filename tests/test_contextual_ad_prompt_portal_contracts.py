"""Static contracts for the Bot-derived Contextual Ad Prompt Wizard.

The original Bot flow is a short Telegram pending-state wizard. Its Web
conversion must be a signed, CSRF-protected deterministic text receipt only;
it must never become a hidden Meta/provider/Bot call, durable draft, job,
wallet/payment action, media result or publishing action.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_content_studio.py").read_text(encoding="utf-8")
ENGINES = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def test_contextual_ad_prompt_is_a_native_private_portal_feature() -> None:
    assert 'customerPage("/content/contextual-prompt", "Contextual Ad Prompt Wizard"' in PORTAL
    assert 'layout: "contextual-ad-prompt", type: "contextual-ad-prompt"' in PORTAL
    assert "function contextualAdPromptFields()" in PORTAL
    assert "function renderContextualAdPrompt(page, context)" in PORTAL
    assert 'case "contextual-ad-prompt": return renderContextualAdPrompt(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="contextual-ad-prompt-compose"' in PORTAL
    assert '["/content/contextual-prompt", "Contextual Ad Prompt", ICONS.prompt]' in PORTAL
    assert 'WebFeature("contextual_ad_prompt", "Contextual Ad Prompt Wizard", "content", "/content/contextual-prompt"' in REGISTRY
    assert '("contextual_ad_prompt",)' in ENGINES


def test_contextual_ad_prompt_result_requires_all_no_execution_boundaries() -> None:
    assert "function normalizeContextualAdPromptResult(raw)" in PORTAL
    assert "CONTEXTUAL_AD_PROMPT_BOUNDARY_FIELDS" in PORTAL
    assert "source.execution !== \"web_native_deterministic_contextual_ad_prompt_only\"" in PORTAL
    for field in (
        "input_persisted", "provider_called", "bot_called", "job_created", "wallet_mutated", "payment_started",
        "asset_saved", "media_output_created", "publish_action_created", "fact_checked", "rights_verified",
    ):
        assert field in PORTAL
    start = PORTAL.index("function renderContextualAdPromptResult")
    end = PORTAL.index("function renderContextualAdPrompt(page, context)", start)
    result_renderer = PORTAL[start:end]
    assert "safeText" in result_renderer
    assert "output_url" not in result_renderer
    assert "job_id" not in result_renderer
    assert "<video" not in result_renderer


def test_contextual_ad_prompt_uses_only_the_csrf_stateless_api() -> None:
    for helper in ("contextualAdPromptPayload", "contextualAdPromptBoundaryIsSafe", "contextualAdPromptResultIsSafe"):
        assert f"function {helper}" in INTEGRATION
    assert '"contextual-ad-prompt-compose": Boolean(account && me.csrf_token && contextualAdPromptEnabled)' in INTEGRATION
    assert '"/content/contextual-prompt": account && contextualAdPromptEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/content-studio/tools/contextual-ad-prompt", {' in INTEGRATION
    assert "contextualAdPromptResult: data" in INTEGRATION
    assert "contextualAdPromptResult: {}," in INTEGRATION

    start = INTEGRATION.index('if (action === "contextual-ad-prompt-compose")')
    end = INTEGRATION.index('if (action === "trend-research-plan")', start)
    action = INTEGRATION[start:end].lower()
    for forbidden in (
        "bridgeavailable", "core bridge", "/payments", "/jobs", "payos", "idempotency_key", "localstorage", "sessionstorage",
    ):
        assert forbidden not in action
    assert "contextualadpromptpayload(fields)" in action
    assert "contextualadpromptresultissafe(data)" in action


def test_contextual_ad_prompt_backend_is_request_only_and_never_executes() -> None:
    assert "class ContextualAdPromptRequest(BaseModel)" in ROUTER
    assert "class ContextualAdPromptPlan(BaseModel)" in ROUTER
    assert '@router.post("/tools/contextual-ad-prompt")' in ROUTER
    assert "CONTEXTUAL_AD_PROMPT_INDUSTRIES" in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/contextual-ad-prompt")')
    end = ROUTER.index('@router.get("/summary")', start)
    endpoint = ROUTER[start:end]
    assert "_contextual_ad_prompt" in endpoint
    assert '"web_native_deterministic_contextual_ad_prompt_only"' in endpoint
    for boundary in (
        '"input_persisted": False', '"provider_called": False', '"bot_called": False',
        '"job_created": False', '"wallet_mutated": False', '"payment_started": False',
        '"asset_saved": False', '"media_output_created": False', '"publish_action_created": False',
        '"fact_checked": False', '"rights_verified": False',
    ):
        assert boundary in endpoint
    for forbidden_call in ("_idempotent(", "transaction(", "_audit(", "_event("):
        assert forbidden_call not in endpoint


def test_contextual_ad_prompt_private_route_and_api_are_never_pwa_cached() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/content/contextual-prompt"' not in shell
    assert '"/content/contextual-prompt"' in private_paths
    assert '"/" + "api/v1/content-studio"' in private_paths
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER
    assert "const BUILD_ID = workerBuildId();" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    assert ".filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)" in SERVICE_WORKER
