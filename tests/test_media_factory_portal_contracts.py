"""Static Portal/PWA contracts for the request-only Media Factory blueprint."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_media_factory_is_a_first_class_private_portal_route() -> None:
    assert 'customerPage("/media-factory", "Media Factory Blueprint"' in PORTAL
    assert 'layout: "media-factory", type: "media-factory", fields: [], action: "none"' in PORTAL
    assert "function renderMediaFactory(page, context)" in PORTAL
    assert 'data-portal-action="media-factory-blueprint"' in PORTAL
    assert 'data-portal-route="/media-factory"' in PORTAL
    assert 'case "media-factory": return renderMediaFactory(page, context);' in PORTAL


def test_media_factory_payload_and_result_are_exact_and_non_executing() -> None:
    start = INTEGRATION.index("function mediaFactoryPayload(fields)")
    end = INTEGRATION.index("function mediaFactoryText", start)
    payload = INTEGRATION[start:end]
    assert "return { topic, language };" in payload
    for forbidden in ("provider", "url", "path", "asset", "job", "payment", "idempotency", "publish"):
        assert f"{forbidden}:" not in payload

    normalizer = INTEGRATION[
        INTEGRATION.index("function mediaFactoryBoundaryIsSafe"):INTEGRATION.index("// Voice Studio", INTEGRATION.index("function mediaFactoryBoundaryIsSafe"))
    ]
    for marker in (
        'data.execution === "web_native_deterministic_media_factory_blueprint_only"',
        "data[field] === false",
        'blueprint.mode === "content_only_manual_review"',
        "MEDIA_FACTORY_WORKFLOWS",
        "MEDIA_FACTORY_VIDEO_KEYS",
    ):
        assert marker in normalizer

    action = INTEGRATION[
        INTEGRATION.index('if (action === "media-factory-blueprint")'):INTEGRATION.index('if (action === "music-prompt-compose")')
    ]
    assert 'api("/media-factory/blueprint"' in action
    assert "mediaFactoryPayload(fields)" in action
    assert "mediaFactoryResultIsSafe(data)" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action
    assert "idempotency_key" not in action


def test_media_factory_receipts_are_never_pwa_cached() -> None:
    assert '"/" + "api/v1/media-factory"' in WORKER
    assert '"/media-factory"' in WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in WORKER
    assert "const BUILD_ID = workerBuildId();" in WORKER
