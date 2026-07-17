"""Static Portal/PWA contracts for the request-only Creative Flow route."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


def test_creative_flow_is_a_first_class_private_portal_route() -> None:
    assert 'customerPage("/creative-flow", "Creative Flow Composer"' in PORTAL
    assert 'layout: "creative-flow", type: "creative-flow", fields: [], action: "none"' in PORTAL
    assert "function renderCreativeFlow(page, context)" in PORTAL
    assert 'data-portal-action="creative-flow-compose"' in PORTAL
    assert 'data-portal-route="/creative-flow"' in PORTAL
    assert 'case "creative-flow": return renderCreativeFlow(page, context);' in PORTAL


def test_creative_flow_has_exact_payload_boundary_and_no_bridge_execution() -> None:
    start = INTEGRATION.index("function creativeFlowPayload(fields)")
    end = INTEGRATION.index("function creativeFlowText", start)
    payload = INTEGRATION[start:end]
    assert "return { idea, language };" in payload
    for forbidden in ("provider", "url", "path", "asset", "job", "payment", "idempotency", "publish"):
        assert f"{forbidden}:" not in payload

    normalizer = INTEGRATION[
        INTEGRATION.index("function creativeFlowBoundaryIsSafe"):INTEGRATION.index("// Voice Studio", INTEGRATION.index("function creativeFlowBoundaryIsSafe"))
    ]
    for marker in (
        'data.execution === "web_native_deterministic_creative_flow_only"',
        "data[field] === false",
        'flow.mode === "template_only_manual_review"',
        "CREATIVE_FLOW_WORKFLOWS",
    ):
        assert marker in normalizer

    action = INTEGRATION[
        INTEGRATION.index('if (action === "creative-flow-compose")'):INTEGRATION.index('if (action === "music-prompt-compose")')
    ]
    assert 'api("/media-factory/creative-flow"' in action
    assert "creativeFlowPayload(fields)" in action
    assert "creativeFlowResultIsSafe(data)" in action
    assert "bridge_request" not in action
    assert "CORE_BRIDGE" not in action
    assert "idempotency_key" not in action


def test_creative_flow_receipts_are_never_pwa_cached() -> None:
    assert '"/creative-flow"' in WORKER
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-"' in WORKER
    assert "const BUILD_ID = workerBuildId();" in WORKER
