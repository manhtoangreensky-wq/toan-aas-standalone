"""Static safety contracts for the Web-native Publish Review Pack.

The Bot Free Hub formatter once used a Telegram-only pending result.  The Web
conversion must instead accept explicit copy in a signed, CSRF-protected,
short-lived request and return a review receipt only.  It must never create a
social connection, scheduler entry, provider/Bot call, job, payment, asset,
delivery or a publish action.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
SERVICE_WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
ROUTER = (ROOT / "copyfast_content_studio.py").read_text(encoding="utf-8")
ENGINES = (ROOT / "copyfast_web_engine.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def test_publish_review_pack_is_a_native_private_portal_feature() -> None:
    assert 'customerPage("/content/publish-review", "Gói review trước khi đăng"' in PORTAL
    assert 'layout: "publish-review-pack", type: "publish-review-pack"' in PORTAL
    assert "function publishReviewPackFields()" in PORTAL
    assert "function renderPublishReviewPack(page, context)" in PORTAL
    assert 'case "publish-review-pack": return renderPublishReviewPack(page, context);' in PORTAL
    assert 'data-portal-no-transient data-portal-action="publish-review-pack-compose"' in PORTAL
    assert '["/content/publish-review", "Gói review trước khi đăng", ICONS.prompt]' in PORTAL
    assert '"publish-review-pack"' in PORTAL
    assert 'WebFeature("publish_review_pack", "Gói review trước khi đăng", "content", "/content/publish-review"' in REGISTRY
    assert '("publish_review_pack",)' in ENGINES


def test_publish_review_pack_result_is_strictly_bounded_and_escaped() -> None:
    assert "const PUBLISH_REVIEW_PACK_BOUNDARY_FIELDS" in PORTAL
    assert "function normalizePublishReviewPackResult(raw)" in PORTAL
    assert 'source.execution !== "web_native_publish_review_text_only"' in PORTAL
    assert "source[field] === false" in PORTAL
    for field in (
        "input_persisted", "provider_called", "bot_called", "job_created", "wallet_mutated", "payment_started",
        "asset_saved", "media_output_created", "publish_action_created", "delivery_created", "fact_checked", "rights_verified",
    ):
        assert field in PORTAL
    for state_field in (
        "publishReviewPackEnabled: source.publishReviewPackEnabled === true",
        "publishReviewPackResult: normalizePublishReviewPackResult(source.publishReviewPackResult)",
    ):
        assert state_field in PORTAL

    start = PORTAL.index("function renderPublishReviewPackResult")
    end = PORTAL.index("function renderPublishReviewPack(page, context)", start)
    result_renderer = PORTAL[start:end]
    assert "safeText" in result_renderer
    assert 'badge("read_only")' in result_renderer
    assert "output_url" not in result_renderer
    assert "job_id" not in result_renderer
    assert "<video" not in result_renderer


def test_publish_review_pack_uses_only_the_csrf_web_native_api() -> None:
    for helper in (
        "publishReviewPackHashtags",
        "publishReviewPackPayload",
        "publishReviewPackBoundaryIsSafe",
        "publishReviewPackResultIsSafe",
    ):
        assert f"function {helper}" in INTEGRATION
    assert '"publish-review-pack-compose": Boolean(account && me.csrf_token && publishReviewPackEnabled)' in INTEGRATION
    assert '"/content/publish-review": account && publishReviewPackEnabled ? "ready" : "guarded"' in INTEGRATION
    assert 'api("/content-studio/tools/publish-review-pack", {' in INTEGRATION
    assert "publishReviewPackResult: data" in INTEGRATION
    assert "publishReviewPackResult: {}," in INTEGRATION

    start = INTEGRATION.index('if (action === "publish-review-pack-compose")')
    end = INTEGRATION.index('if (action === "contextual-ad-prompt-compose")', start)
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
    assert "publishreviewpackpayload(fields)" in action
    assert "publishreviewpackresultissafe(data)" in action


def test_publish_review_pack_backend_is_request_only_and_never_executes() -> None:
    assert "class PublishReviewPackRequest(BaseModel)" in ROUTER
    assert "class PublishReviewPack(BaseModel)" in ROUTER
    assert '@router.post("/tools/publish-review-pack")' in ROUTER
    assert "from copyfast_bridge import" not in ROUTER
    assert "import httpx" not in ROUTER
    assert "import requests" not in ROUTER

    start = ROUTER.index('@router.post("/tools/publish-review-pack")')
    end = ROUTER.index('@router.get("/summary")', start)
    endpoint = ROUTER[start:end]
    assert "PublishReviewPackRequest" in endpoint
    assert "marker = _marker(" in endpoint
    assert "WEB_PUBLISH_REVIEW_ORIGINALITY_GUARD" in endpoint
    assert "_publish_review_pack" in endpoint
    assert '"web_native_publish_review_text_only"' in endpoint
    for boundary in (
        '"input_persisted": False',
        '"provider_called": False',
        '"bot_called": False',
        '"job_created": False',
        '"wallet_mutated": False',
        '"payment_started": False',
        '"asset_saved": False',
        '"media_output_created": False',
        '"publish_action_created": False',
        '"delivery_created": False',
        '"fact_checked": False',
        '"rights_verified": False',
    ):
        assert boundary in endpoint
    for forbidden_call in ("_idempotent(", "transaction(", "_audit(", "_event("):
        assert forbidden_call not in endpoint


def test_publish_review_pack_private_ui_and_api_are_never_pwa_cached() -> None:
    shell = SERVICE_WORKER.split("const SHELL = Object.freeze([", 1)[1].split("]);", 1)[0]
    private_paths = SERVICE_WORKER.split("const PRIVATE_PATH_PREFIXES = Object.freeze([", 1)[1].split("]);", 1)[0]
    assert '"/content/publish-review"' not in shell
    assert '"/content/publish-review"' in private_paths
    assert '"/" + "api/v1/content-studio"' in private_paths
    assert "SHELL_PATHS.has(url.pathname)" in SERVICE_WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER
    assert "const BUILD_ID = workerBuildId();" in SERVICE_WORKER
    assert "const CACHE_NAME = `${CACHE_PREFIX}${BUILD_ID}`;" in SERVICE_WORKER
    assert ".filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)" in SERVICE_WORKER
