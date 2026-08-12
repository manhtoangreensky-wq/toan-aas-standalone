"""Contracts for the deferred, non-authorizing route-engine Portal surface.

The route engine remains a server-side, fail-closed selector.  Until an
owner-approved catalog is attached, the browser may only receive a fixed
informational descriptor.  It must never receive internal route/pricing data
or turn the descriptor into an execution, payment, or capability grant.
"""

from __future__ import annotations

from pathlib import Path

from copyfast_api import _project_surface_data


ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
DEFERRED_DOCUMENT = ROOT / "docs" / "migration" / "ROUTE_ENGINE_PRICING_DEFERRED.md"


def _section(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def _function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    end = source.find("\n  function ", start + 1)
    return source[start:] if end == -1 else source[start:end]


def _python_function(source: str, name: str) -> str:
    start = source.index(f"def {name}(")
    boundaries = [
        source.find("\n\ndef ", start + 1),
        source.find("\n\n@", start + 1),
    ]
    end = min((boundary for boundary in boundaries if boundary != -1), default=-1)
    return source[start:] if end == -1 else source[start:end]


def test_route_engine_deferred_descriptor_is_closed_and_price_free() -> None:
    from copyfast_api import _route_engine_deferred_descriptor

    assert _route_engine_deferred_descriptor() == {
        "state": "deferred",
        "catalog_version": "unconfigured",
        "catalog_approval": "unconfigured",
        "price_display": False,
    }


def test_catalog_publishes_only_the_deferred_route_engine_descriptor() -> None:
    catalog_route = _section(API, '@router.get("/catalog")', '@router.get("/core/status")')
    assert '"route_engine": _route_engine_deferred_descriptor()' in catalog_route

    descriptor = _python_function(API, "_route_engine_deferred_descriptor")
    for forbidden in (
        "resolve_route",
        "provider",
        "adapter",
        "model",
        "fallback",
        "cost",
        "retail_price_minor",
        "currency",
        "payment",
        "wallet",
        "job",
        "output",
        "capability",
    ):
        assert forbidden not in descriptor


def test_generic_pricing_projection_carries_metadata_but_no_legacy_price_fields() -> None:
    projection = _section(API, 'if surface == "pricing":', 'if surface == "packages":')
    for forbidden in (
        '"cost_xu"',
        '"price_vnd"',
        '"display_price"',
        '"trend_workflow_content_total_cost_xu"',
    ):
        assert forbidden not in projection

    projected = _project_surface_data(
        {
            "available": True,
            "billing_mode": "canonical",
            "price_table_source": "bridge",
            "trend_workflow_content_total_cost_xu": 999,
            "image_tiers": [
                {
                    "code": "image_standard",
                    "label": "Ảnh tiêu chuẩn",
                    "cost_xu": 42,
                    "note": "Metadata tier",
                    "retry_warranty_count": 1,
                }
            ],
            "video_combos": [
                {
                    "code": "video_combo",
                    "label": "Video",
                    "price_vnd": 100_000,
                    "display_price": "100.000đ",
                    "summary": "Metadata combo",
                }
            ],
        },
        "pricing",
    )

    assert projected == {
        "available": True,
        "billing_mode": "canonical",
        "price_table_source": "bridge",
        "image_tiers": [
            {
                "code": "image_standard",
                "label": "Ảnh tiêu chuẩn",
                "note": "Metadata tier",
                "retry_warranty_count": 1,
            }
        ],
        "video_tiers": [],
        "video_combos": [
            {
                "code": "video_combo",
                "label": "Video",
                "summary": "Metadata combo",
            }
        ],
    }


def test_catalog_hydration_replaces_route_engine_state_without_browser_storage() -> None:
    assert "const routeEngine = catalogData.route_engine" in INTEGRATION
    assert "routeEngine," in INTEGRATION
    route_engine_read = _section(INTEGRATION, "const routeEngine = catalogData.route_engine", "const webWorkspaceDraftFeatures")
    assert "localStorage" not in route_engine_read


def test_portal_route_engine_notice_is_closed_localized_and_non_authorizing() -> None:
    normalizer = _function(PORTAL, "normalizeRouteEngineDescriptor")
    assert 'return { state: "loading" }' in normalizer
    assert 'source.state !== "deferred"' in normalizer
    assert 'source.catalog_version !== "unconfigured"' in normalizer
    assert 'source.catalog_approval !== "unconfigured"' in normalizer
    assert "source.price_display !== false" in normalizer
    assert 'return { state: "guarded" }' in normalizer

    notice = _function(PORTAL, "renderRouteEngineBoundary")
    assert 'role="status"' in notice
    assert "data-portal-action" not in notice
    for forbidden in ("provider", "model", "fallback", "cost", "price", "payment", "wallet", "job", "canAct"):
        assert forbidden not in notice

    for render_name in ("renderFeatureCatalog", "renderFeatureFamily"):
        assert "renderRouteEngineBoundary(context)" in _function(PORTAL, render_name)

    for key in (
        '"routeEngine.notice.deferred.title"',
        '"routeEngine.notice.deferred.body"',
        '"routeEngine.notice.loading.title"',
        '"routeEngine.notice.guarded.title"',
    ):
        assert I18N.count(key) == 3


def test_portal_never_renders_legacy_tier_or_package_prices() -> None:
    assert "tier.cost_xu" not in PORTAL
    assert "item.price_vnd" not in PORTAL
    pricing_normalizer = _function(PORTAL, "canonicalPricingCatalog")
    for forbidden in ("cost_xu", "price_vnd", "display_price", "priceLabel"):
        assert forbidden not in pricing_normalizer


def test_pricing_return_gate_is_documented_before_route_engine_can_be_enabled() -> None:
    document = DEFERRED_DOCUMENT.read_text(encoding="utf-8")
    for required in (
        "owner-approved",
        "provider",
        "adapter",
        "capability",
        "model",
        "billable unit",
        "currency",
        "Core Bridge",
        "public sale",
        "cost",
        "contract test",
    ):
        assert required.casefold() in document.casefold()
