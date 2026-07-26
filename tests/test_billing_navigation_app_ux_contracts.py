"""UI contracts for the signed Billing workspace navigator."""

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")

APPROVED_BILLING_PATHS = (
    "/wallet",
    "/wallet/topup",
    "/packages",
    "/pricing",
)
ACTIVE_PATH_CONDITION = 'activePath === item.path ? \' aria-current="page"\' : ""'
DYNAMIC_BILLING_ANCHOR = (
    '${items.map((item) => `<a href="${safeText(item.path)}"'
    '${activePath === item.path ? \' aria-current="page"\' : ""}'
    '>${safeText(item.label)}</a>`).join("")}'
)
ITEM_LITERAL = re.compile(
    r'''\{\s*
        path:\s*"(?P<path>[^"]+)"\s*,\s*
        label:\s*uiText\("[^"]+",\s*"[^"]+"\)\s*
    \}''',
    re.DOTALL | re.VERBOSE,
)
FORBIDDEN_NAV_TOKENS = (
    "button",
    "form",
    "input",
    "textarea",
    "data-portal-action",
    "fetch(",
    "api(",
    "payment-create",
    "payos",
    "provider",
    "ledger",
    "telegram",
    "bot",
    "txid",
    "otp",
    "qr",
    "proof",
)


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _billing_nav(source: str = PORTAL) -> str:
    return _section(source, "function renderBillingWorkspaceNav(currentPath)", "function renderPaymentEntryPoints")


def _assert_billing_nav_contract(nav: str) -> None:
    items_match = re.search(r"const items = \[(?P<items>.*?)\];", nav, re.DOTALL)
    assert items_match, "Billing nav must declare its route items locally."
    items_source = items_match.group("items")
    paths = ITEM_LITERAL.findall(items_source)
    assert paths == list(APPROVED_BILLING_PATHS)
    assert len(paths) == len(set(paths)) == len(APPROVED_BILLING_PATHS)
    assert re.sub(r"[\s,]", "", ITEM_LITERAL.sub("", items_source)) == ""

    assert DYNAMIC_BILLING_ANCHOR in nav
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


def _billing_nav_css(source: str = CSS) -> str:
    return _section(source, "/* Billing workspace navigation.", "/* Music & SFX Library")


def _assert_billing_nav_css_contract(scope: str) -> None:
    nav_block = re.search(r"\.portal-billing-nav\s*\{(?P<body>.*?)\}", scope, re.DOTALL)
    assert nav_block, "Billing nav must retain its own containment block."
    assert "max-width: 100%;" in nav_block.group("body")
    assert re.search(r"var\(--portal-[a-z0-9-]+\)", nav_block.group("body"))
    assert re.search(r"var\(--portal-[a-z0-9-]+\)", scope)


def test_billing_workspace_nav_covers_the_four_existing_routes_without_actions() -> None:
    nav = _billing_nav()

    assert "const activePath = normalizePath(currentPath || \"/wallet\");" in nav
    for path, key, fallback in (
        ("/wallet", "nav.wallet", "Ví Xu"),
        ("/wallet/topup", "shellNav.topupCredit", "Nạp Xu"),
        ("/packages", "workspaceMenu.card.packages.title", "Gói dịch vụ"),
        ("/pricing", "nav.pricing", "Bảng giá"),
    ):
        assert f'{{ path: "{path}", label: uiText("{key}", "{fallback}") }}' in nav
    assert 'uiText("shellNav.billing", "Ví & gói")' in nav
    assert 'aria-current="page"' in nav
    _assert_billing_nav_contract(nav)


def test_wallet_and_catalog_renderers_place_the_shared_nav_after_the_hero() -> None:
    wallet = _section(PORTAL, "function renderWallet(page, context)", "function renderCatalog(page, context)")
    catalog = _section(PORTAL, "function renderCatalog(page, context)", "const JOB_FILTERS")

    assert 'const billingNav = renderBillingWorkspaceNav(page.path);' in wallet
    assert 'const billingNav = renderBillingWorkspaceNav(page.path);' in catalog
    assert wallet.index("${renderHero(page, context)}${billingNav}") < wallet.index("portal-wallet-command")
    assert catalog.index("${renderHero(page, context)}${billingNav}") < catalog.index("portal-billing-catalog-intro")


def test_billing_nav_uses_mobile_safe_tokenized_app_chrome() -> None:
    scope = _billing_nav_css()

    for token in (
        ".portal-billing-nav",
        "overflow-x: auto;",
        "scroll-snap-type: x mandatory;",
        ".portal-billing-nav a",
        "min-height: 44px;",
        "scroll-snap-align: start;",
        "white-space: nowrap;",
        ".portal-billing-nav a:focus-visible",
        "@media (max-width: 700px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert token in scope
    _assert_billing_nav_css_contract(scope)
    assert "linear-gradient" not in scope


def test_billing_nav_contract_rejects_route_active_authority_and_containment_mutations() -> None:
    nav = _billing_nav()
    css = _billing_nav_css()

    with pytest.raises(AssertionError):
        _assert_billing_nav_contract(nav.replace('{ path: "/pricing"', '{ path: "/wallet"', 1))
    with pytest.raises(AssertionError):
        _assert_billing_nav_contract(
            nav.replace(
                '    ];',
                '      { path: "/other", label: uiText("other", "Other") }\n    ];',
                1,
            )
        )
    with pytest.raises(AssertionError):
        _assert_billing_nav_contract(nav.replace(ACTIVE_PATH_CONDITION, "true", 1))
    with pytest.raises(AssertionError):
        _assert_billing_nav_contract(nav.replace('<a href=', '<a class="active" href=', 1))
    with pytest.raises(AssertionError):
        _assert_billing_nav_contract(nav.replace("</nav>`;", '<button type="button">Unsafe</button></nav>`;', 1))
    with pytest.raises(AssertionError):
        _assert_billing_nav_css_contract(css.replace("max-width: 100%;", "max-width: none;", 1))
