"""Contracts for the signed public-sale pricing projection.

The Web App may display only sale prices that arrive from the canonical bridge
with an approved versioned SKU catalogue.  It must not infer a catalogue from
legacy tier costs or expose internal pricing fields.
"""

from pathlib import Path

from copyfast_api import _project_surface_data

ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def test_pricing_projection_has_a_strict_public_sale_catalog_allow_list() -> None:
    pricing_projection = _section(
        API,
        'if surface == "pricing":',
        'if surface == "packages":',
    )

    for token in (
        '"public_sale_catalog"',
        '"catalog_version"',
        '"approval_status"',
        '"sale_price_xu"',
        '"family"',
        '"status"',
    ):
        assert token in pricing_projection

    public_projection = pricing_projection[
        pricing_projection.index('"public_sale_catalog"') :
    ]
    for forbidden in (
        '"provider"',
        '"model"',
        '"cost"',
        '"cost_xu"',
        '"price_usd"',
        '"fx"',
        '"markup"',
        '"fallback"',
        '"payment"',
        '"wallet"',
    ):
        assert forbidden not in public_projection


def test_public_sale_projection_redacts_all_internal_pricing_fields() -> None:
    projected = _project_surface_data(
        {
            "available": True,
            "public_sale_catalog": {
                "available": True,
                "catalog_version": "owner-approved-2026-08-11",
                "approval_status": "owner_approved",
                "provider": "private-provider",
                "price_usd": 22.5,
                "items": [
                    {
                        "code": "video_cinematic_multiscene",
                        "family": "video",
                        "label": "Điện ảnh nhiều cảnh",
                        "sale_price_xu": 2360,
                        "status": "ready",
                        "model": "private-model",
                        "cost_xu": 2030,
                        "fallback": "private-fallback",
                    }
                ],
            },
        },
        "pricing",
    )

    assert projected["public_sale_catalog"] == {
        "available": True,
        "catalog_version": "owner-approved-2026-08-11",
        "approval_status": "owner_approved",
        "items": [
            {
                "code": "video_cinematic_multiscene",
                "family": "video",
                "label": "Điện ảnh nhiều cảnh",
                "sale_price_xu": 2360,
                "status": "ready",
            }
        ],
    }


def test_pricing_read_is_private_and_uncacheable() -> None:
    route = _section(API, '@router.get("/pricing")', '@router.get("/packages")')
    assert "response: Response" in route
    assert 'response.headers["Cache-Control"] = "no-store, private"' in route


def test_pricing_page_renders_only_a_validated_public_sale_catalog() -> None:
    validator = _section(
        PORTAL,
        "function canonicalPublicSalePricingCatalog(value)",
        "function canonicalPackageCatalog(value)",
    )
    for token in (
        'source.available !== true',
        'source.approval_status !== "owner_approved"',
        "const version = canonicalCatalogCode(source.catalog_version);",
        "!Array.isArray(source.items) || source.items.length > 100",
        "canonicalCatalogCode(item.code)",
        "canonicalNonnegativeInteger(item.sale_price_xu)",
        "salePrice <= 0",
        'priceLabel: `${salePrice} Xu`',
    ):
        assert token in validator
    for forbidden in (
        "cost_xu",
        "provider",
        "model",
        "USD",
        "FX",
        "fallback",
    ):
        assert forbidden not in validator

    catalog = _section(PORTAL, "function renderCatalog(page, context)", "const JOB_FILTERS")
    for token in (
        "const pricing = canonicalPricingCatalog(context.pricingCatalog);",
        "const publicSalePricing = pricing ? canonicalPublicSalePricingCatalog(context.pricingCatalog) : null;",
        "publicSaleCatalogEntries(publicSalePricing, publicSaleFamilyLabels)",
        "Chờ catalog giá bán được phát hành",
    ):
        assert token in catalog
    assert "pricing.image_tiers.map" not in catalog
    assert "pricing.video_tiers.map" not in catalog
    assert "pricing.video_combos.map" not in catalog


def test_public_sale_catalogue_copy_has_vi_en_zh_coverage() -> None:
    for locale in ("vi", "en", "zh"):
        start = f"Object.assign(BILLING_CATALOG_MESSAGES.{locale}, {{"
        locale_block = _section(I18N, start, "  });")
        for key in (
            '"billingCatalog.catalog.publicSale.kicker"',
            '"billingCatalog.catalog.publicSale.introTitle"',
            '"billingCatalog.catalog.publicSale.introBody"',
            '"billingCatalog.catalog.publicSale.cardTitle"',
            '"billingCatalog.catalog.publicSale.emptyTitle"',
            '"billingCatalog.catalog.publicSale.emptyBody"',
            '"billingCatalog.catalog.publicSale.statusApproved"',
            '"billingCatalog.catalog.publicSale.family.service"',
        ):
            assert key in locale_block


def test_legacy_tier_costs_stay_outside_the_public_price_page() -> None:
    catalog = _section(PORTAL, "function renderCatalog(page, context)", "const JOB_FILTERS")
    assert "function canonicalPricingCatalog(value)" in PORTAL
    assert "optionsFrom: \"imageTiers\"" in PORTAL
    assert "optionsFrom: \"videoTiers\"" in PORTAL
    assert "cost_xu" not in catalog
    assert "feature-estimate" not in catalog
    assert "feature-confirm" not in catalog
    assert "payment-create" not in catalog
