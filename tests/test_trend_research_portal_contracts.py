"""Static Portal/PWA contracts for the request-only Trend Research page."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_trend_research_is_a_first_class_private_portal_route() -> None:
    assert 'customerPage("/trend-research", "Trend Research Plan"' in PORTAL
    assert 'layout: "trend-research", type: "trend-research", fields: [], action: "none"' in PORTAL
    assert 'function renderTrendResearch(page, context)' in PORTAL
    assert 'data-portal-action="trend-research-plan"' in PORTAL
    assert 'data-portal-route="/trend-research"' in PORTAL
    assert 'data-portal-no-transient' in PORTAL
    assert 'case "trend-research": return renderTrendResearch(page, context);' in PORTAL


def test_trend_research_payload_is_exact_and_result_requires_the_no_execution_boundary() -> None:
    start = INTEGRATION.index("function trendResearchPayload(fields)")
    end = INTEGRATION.index("function trendResearchString", start)
    payload = INTEGRATION[start:end]
    assert "return { topic, language };" in payload
    for forbidden in ("provider", "url", "path", "asset", "job", "payment", "idempotency", "publish"):
        assert f"{forbidden}:" not in payload

    normalizer = INTEGRATION[
        INTEGRATION.index("function trendResearchBoundaryIsSafe"):INTEGRATION.index("// Voice Studio", INTEGRATION.index("function trendResearchBoundaryIsSafe"))
    ]
    for marker in (
        'data.execution === "web_native_deterministic_trend_research_only"',
        'data[field] === false',
        'plan.research_mode === "manual_content_only"',
        'plan.freshness === "not_live_not_verified"',
        'TREND_RESEARCH_WORKFLOWS',
    ):
        assert marker in normalizer

    action = INTEGRATION[
        INTEGRATION.index('if (action === "trend-research-plan")'):INTEGRATION.index('if (action === "music-prompt-compose")')
    ]
    assert 'api("/trend-research/plan"' in action
    assert "trendResearchPayload(fields)" in action
    assert "trendResearchResultIsSafe(data)" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action
    assert "idempotency_key" not in action


def test_trend_research_receipts_are_never_pwa_cached() -> None:
    assert '"/" + "api/v1/trend-research"' in WORKER
    assert '"/trend-research"' in WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in WORKER
    assert "const BUILD_ID = workerBuildId();" in WORKER
