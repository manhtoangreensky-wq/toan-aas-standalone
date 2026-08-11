"""Locale contracts for the customer membership and billing catalogues.

Only fixed Web presentation copy is translated here. Plan names, package
labels, notes, prices and statuses remain canonical server projections and
must stay escaped at the render boundary.
"""

from __future__ import annotations

from pathlib import Path
import re

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


FIXED_KEYS = frozenset(
    {
        "page.membership.title",
        "page.membership.description",
        "page.packages.title",
        "page.packages.description",
        "page.pricing.title",
        "page.pricing.description",
        "membership.defaultPlanName",
        "membership.defaultPlanStatus",
        "membership.defaultCatalogNote",
        "membership.current.title",
        "membership.current.description",
        "membership.label.currentPlan",
        "membership.label.planStatus",
        "membership.label.webAccount",
        "membership.label.canonicalCredit",
        "membership.empty.title",
        "membership.empty.body",
        "membership.principle.title",
        "membership.principle.body",
        "membership.catalog.title",
        "membership.catalog.description",
        "membership.catalog.emptyTitle",
        "membership.catalog.emptyBody",
        "membership.action.packages",
        "membership.action.pricing",
        "membership.action.topup",
        "catalog.family.imageTier",
        "catalog.family.videoTier",
        "catalog.family.videoCombo",
        "catalog.family.monthly",
        "catalog.family.combo",
        "catalog.priceMissing",
        "catalog.statusCanonical",
        "catalog.statusWaiting",
        "catalog.pricing.kicker",
        "catalog.packages.kicker",
        "catalog.pricing.introTitle",
        "catalog.packages.introTitle",
        "catalog.pricing.introBody",
        "catalog.packages.introBody",
        "catalog.pricing.cardTitle",
        "catalog.packages.cardTitle",
        "catalog.card.subtitle",
        "catalog.pricing.emptyActiveTitle",
        "catalog.packages.emptyActiveTitle",
        "catalog.pricing.emptyWaitingTitle",
        "catalog.packages.emptyWaitingTitle",
        "catalog.pricing.emptyActiveBody",
        "catalog.packages.emptyActiveBody",
        "catalog.pricing.emptyWaitingBody",
        "catalog.packages.emptyWaitingBody",
        "catalog.footer.note",
        "catalog.footer.topupAction",
        "catalog.publicSale.kicker",
        "catalog.publicSale.introTitle",
        "catalog.publicSale.introBody",
        "catalog.publicSale.cardTitle",
        "catalog.publicSale.cardDescription",
        "catalog.publicSale.emptyTitle",
        "catalog.publicSale.emptyBody",
        "catalog.publicSale.priceMissing",
        "catalog.publicSale.statusApproved",
        "catalog.publicSale.family.service",
        "catalog.publicSale.family.video",
        "catalog.publicSale.family.image",
        "catalog.publicSale.family.music",
        "catalog.publicSale.family.audio",
        "catalog.publicSale.footerNote",
    }
)


def _section(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def _catalogue_keys(locale: str) -> set[str]:
    match = re.search(
        rf"Object\.assign\(BILLING_CATALOG_MESSAGES\.{re.escape(locale)}, \{{(?P<body>.*?)\n  \}}\);",
        I18N,
        flags=re.DOTALL,
    )
    assert match, f"Missing billing catalogue for {locale}"
    return set(
        re.findall(
            r'^\s*"billingCatalog\.([^"]+)"\s*:',
            match.group("body"),
            flags=re.MULTILINE,
        )
    )


def test_billing_catalogue_has_equal_reviewed_vi_en_zh_keys() -> None:
    assert "const BILLING_CATALOG_MESSAGES = { vi: {}, en: {}, zh: {} };" in I18N
    catalogues = {locale: _catalogue_keys(locale) for locale in ("vi", "en", "zh")}
    assert catalogues["vi"] == catalogues["en"] == catalogues["zh"]
    assert FIXED_KEYS <= catalogues["vi"]
    assert "BILLING_CATALOG_MESSAGES[locale]" in I18N
    for key in FIXED_KEYS:
        assert I18N.count(f'"billingCatalog.{key}"') == 3


def test_membership_and_catalog_renderers_localize_fixed_copy_and_escape_canonical_data() -> None:
    membership = _section(PORTAL, "function membershipCatalogEntries(context)", "function renderServiceStatus")
    catalog = _section(PORTAL, "function renderCatalog(page, context)", "const JOB_FILTERS")
    rendered = membership + catalog

    assert "function billingCatalogText(" in PORTAL
    for key in FIXED_KEYS:
        # Page metadata is consumed by the route-aware title/description
        # helpers; all other keys are renderer-owned fixed copy.
        if key.startswith("page."):
            continue
        assert f'billingCatalogText("{key}"' in rendered, key

    for path, key in (
        ("/membership", "page.membership.title"),
        ("/packages", "page.packages.title"),
        ("/pricing", "page.pricing.title"),
    ):
        assert f'if (path === "{path}") return billingCatalogText("{key}"' in PORTAL
    for path, key in (
        ("/membership", "page.membership.description"),
        ("/packages", "page.packages.description"),
        ("/pricing", "page.pricing.description"),
    ):
        assert f'if (path === "{path}") return billingCatalogText("{key}"' in PORTAL

    # Canonical package/price values are still escaped data, not translated
    # browser copy.  The catalog renderers remain read-only projections.
    for token in (
        "safeText(planName)",
        "safeText(planStatus)",
        "safeText(item.label)",
        "safeText(item.note)",
        "safeText(item.priceLabel",
        "safeText(item.family)",
        "canonicalPricingCatalog(context.pricingCatalog)",
        "canonicalPackageCatalog(context.packageCatalog)",
    ):
        assert token in rendered
    assert "billingCatalogText(item.label" not in rendered
    assert "billingCatalogText(item.note" not in rendered
    for forbidden in ("data-portal-action", "<form", "api(", "fetch(", "payment-create"):
        assert forbidden not in rendered


def test_billing_catalog_first_paint_is_route_and_locale_specific() -> None:
    expected = {
        "vi": {
            "/membership": (
                "Gói thành viên · TOAN AAS",
                "Xem quyền lợi và trạng thái gói do nguồn canonical xác minh; Web không tự cấp tier hoặc thay đổi Xu.",
            ),
            "/packages": (
                "Gói dịch vụ · TOAN AAS",
                "Duyệt danh mục gói do nguồn canonical công bố; Web không tạo mua hàng, checkout hoặc thay đổi Xu.",
            ),
            "/pricing": (
                "Bảng giá · TOAN AAS",
                "Xem bảng giá bán công khai do Core Bridge phát hành; Web không suy đoán tỷ lệ, ưu đãi hoặc hạn mức Xu.",
            ),
        },
        "en": {
            "/membership": (
                "Membership · TOAN AAS",
                "Review membership benefits and plan status verified by the canonical source; the Web does not grant tiers or change credits.",
            ),
            "/packages": (
                "Service packages · TOAN AAS",
                "Browse packages published by the canonical source; the Web does not create a purchase, checkout, or credit change.",
            ),
            "/pricing": (
                "Pricing · TOAN AAS",
                "Review public sale prices published by Core Bridge; the Web does not infer rates, promotions, or credit limits.",
            ),
        },
        "zh": {
            "/membership": (
                "会员方案 · TOAN AAS",
                "查看由 canonical 来源验证的会员权益和套餐状态；Web 不会授予等级或更改积分。",
            ),
            "/packages": (
                "服务套餐 · TOAN AAS",
                "浏览 canonical 来源发布的服务套餐；Web 不会创建购买、结账或积分变更。",
            ),
            "/pricing": (
                "价格 · TOAN AAS",
                "查看由 Core Bridge 发布的公开销售价格；Web 不会推测费率、优惠或积分限额。",
            ),
        },
    }

    assert '"/packages": {' in PAGES
    assert '"/pricing": {' in PAGES
    for locale, routes in expected.items():
        for route, (title, description) in routes.items():
            response = render_portal(route, interface_locale=locale)
            assert response.status_code == 200
            assert f"<title>{title}</title>".encode("utf-8") in response.body
            assert f'<meta name="description" content="{description}">'.encode("utf-8") in response.body
