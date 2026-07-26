"""Static UI contracts for the route-only Delivery workspace navigator."""

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")

APPROVED_DELIVERY_PATHS = ("/jobs", "/assets", "/asset-vault")
ACTIVE_PATH_CONDITION = 'item.path === activePath ? \' aria-current="page"\' : ""'
FORBIDDEN_NAV_TOKENS = (
    "button",
    "form",
    "input",
    "textarea",
    "data-portal-action",
    "fetch(",
    "api(",
    "payment",
    "payos",
    "provider",
    "wallet",
    "telegram",
    "download",
    "upload",
    "retry",
    "refund",
    "ledger",
)


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _delivery_nav(source: str = PORTAL) -> str:
    return _section(source, "function renderDeliveryWorkspaceNav(currentPath)", "function renderJobOutputAssets")


def _delivery_renderer(name: str, end: str) -> str:
    return _section(PORTAL, f"function {name}(page, context)", end)


def _delivery_nav_css(source: str = CSS) -> str:
    return _section(source, "/* Delivery workspace navigation.", "/* Music & SFX Library")


def _assert_delivery_nav_contract(nav: str) -> None:
    items_match = re.search(r"const items = \[(?P<items>.*?)\];", nav, re.DOTALL)
    assert items_match, "Delivery nav must declare its route items locally."
    items_source = items_match.group("items")
    paths = re.findall(r'path:\s*"([^"]+)"', items_source)
    assert paths == list(APPROVED_DELIVERY_PATHS)
    assert len(paths) == len(set(paths)) == len(APPROVED_DELIVERY_PATHS)
    expected_items = '''
      { path: "/jobs", label: uiText("nav.jobs", "Job Center") },
      { path: "/assets", label: uiText("nav.assets", "Tài sản") },
      { path: "/asset-vault", label: "Asset Vault" }
    '''
    assert re.sub(r"\s+", "", items_source) == re.sub(r"\s+", "", expected_items)

    assert '${items.map((item) => `<a href="${safeText(item.path)}"' in nav
    assert nav.count("items.map((item) =>") == 1
    assert len(re.findall(r"<a(?:\s|>)", nav)) == 1
    assert nav.count('aria-current="page"') == 1
    assert nav.count(ACTIVE_PATH_CONDITION) == 1
    assert nav.count("activePath") == 2
    assert "active" not in nav.replace("activePath", "").casefold()
    for extra_active_marker in ("aria-selected", "data-active", "is-active", "active-class"):
        assert extra_active_marker not in nav.casefold()

    nav_lower = nav.casefold()
    for forbidden in FORBIDDEN_NAV_TOKENS:
        assert forbidden not in nav_lower


def _assert_delivery_nav_css_contract(scope: str) -> None:
    nav_block = re.search(r"\.portal-delivery-nav\s*\{(?P<body>.*?)\}", scope, re.DOTALL)
    assert nav_block, "Delivery nav must retain its own containment block."
    body = nav_block.group("body")
    for token in ("width: 100%;", "max-width: 100%;", "overflow-x: auto;", "scroll-snap-type: x mandatory;"):
        assert token in body
    assert re.search(r"var\(--portal-[a-z0-9-]+\)", body)
    assert re.search(r"var\(--portal-[a-z0-9-]+\)", scope)


def test_delivery_navigation_has_only_the_three_approved_routes() -> None:
    nav = _delivery_nav()

    for path, key, fallback in (
        ("/jobs", "nav.jobs", "Job Center"),
        ("/assets", "nav.assets", "Tài sản"),
    ):
        assert f'{{ path: "{path}", label: uiText("{key}", "{fallback}") }}' in nav
    assert '{ path: "/asset-vault", label: "Asset Vault" }' in nav
    _assert_delivery_nav_contract(nav)


def test_delivery_navigation_keeps_job_details_in_job_center() -> None:
    nav = _delivery_nav()

    assert 'const normalized = normalizePath(currentPath || "/jobs");' in nav
    assert 'const activePath = normalized.startsWith("/jobs/") ? "/jobs" : normalized;' in nav
    assert 'aria-current="page"' in nav
    _assert_delivery_nav_contract(nav)


def test_delivery_navigation_is_inserted_after_each_delivery_hero() -> None:
    renderers = (
        ("renderJobs", "function renderJobDetail(page, context)"),
        ("renderJobDetail", "function renderAssets(page, context)"),
        ("renderAssets", "function validVaultAssetId(value)"),
        ("renderAssetVault", "function renderTickets(page, context)"),
    )
    for name, end in renderers:
        source = _delivery_renderer(name, end)
        assert 'const deliveryNav = renderDeliveryWorkspaceNav(page.path);' in source
        assert "${renderHero(page, context)}${deliveryNav}" in source


def test_delivery_navigation_stays_route_only_and_uses_tokenized_mobile_safe_css() -> None:
    nav = _delivery_nav()
    scope = _delivery_nav_css()

    _assert_delivery_nav_contract(nav)
    _assert_delivery_nav_css_contract(scope)
    for token in (
        ".portal-delivery-nav a",
        "min-height: 44px;",
        "scroll-snap-align: start;",
        "white-space: nowrap;",
        ".portal-delivery-nav a:focus-visible",
        "@media (max-width: 700px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert token in scope
    assert "linear-gradient" not in scope


def test_delivery_navigation_contract_rejects_route_active_action_and_containment_mutations() -> None:
    nav = _delivery_nav()
    css = _delivery_nav_css()

    with pytest.raises(AssertionError):
        _assert_delivery_nav_contract(nav.replace('{ path: "/asset-vault"', '{ path: "/assets"', 1))
    with pytest.raises(AssertionError):
        _assert_delivery_nav_contract(
            nav.replace(
                "    ];",
                '      { path: "/other", label: uiText("nav.other", "Other") }\n    ];',
                1,
            )
        )
    with pytest.raises(AssertionError):
        _assert_delivery_nav_contract(nav.replace(ACTIVE_PATH_CONDITION, "true", 1))
    with pytest.raises(AssertionError):
        _assert_delivery_nav_contract(nav.replace("</nav>`;", '<button type="button">Unsafe</button></nav>`;', 1))
    with pytest.raises(AssertionError):
        _assert_delivery_nav_css_contract(css.replace("max-width: 100%;", "max-width: none;", 1))
