from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
BASE_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
MARKER = "/* ADMIN-LOGIN-RESPONSIVE-001 */"
ADMIN_MAIN = '.portal-shell--auth[data-portal-app-kind="admin"] .portal-main'
ADMIN_PAGE = ".portal-auth-page--access.portal-auth-page--admin"
DESKTOP_BREAKPOINT = 841
STACKED_BREAKPOINT = 840
DESKTOP_INLINE_PADDING = 16


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _brace_body(source: str, token: str) -> str:
    pattern = re.compile(re.escape(token) + r"\s*\{")
    match = pattern.search(source)
    assert match is not None, f"Missing exact CSS block: {token}"
    depth = 1
    cursor = match.end()
    for index in range(cursor, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[cursor:index]
    raise AssertionError(f"Unclosed CSS block: {token}")


def _brace_bodies(source: str, token: str) -> list[str]:
    bodies: list[str] = []
    offset = 0
    while token in source[offset:]:
        start = source.index(token, offset)
        bodies.append(_brace_body(source[start:], token))
        offset = start + len(token)
    return bodies


def _takeover_block() -> str:
    assert THEME.count(MARKER) == 1, "Takeover marker must exist exactly once"
    return THEME.split(MARKER, 1)[1]


def _assert_declarations(body: str, *declarations: str) -> None:
    compact = _compact(body)
    for declaration in declarations:
        assert _compact(declaration) in compact, f"Missing declaration: {declaration}"


def _assert_every_rule_is_admin_scoped(block: str) -> None:
    without_comments = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
    for match in re.finditer(r"([^{}]+)\{", without_comments):
        header = match.group(1).strip()
        if header.startswith("@media"):
            continue
        for selector in header.split(","):
            normalized = selector.strip()
            assert (
                ".portal-auth-page--admin" in normalized
                or '.portal-shell--auth[data-portal-app-kind="admin"]' in normalized
            ), f"Selector escaped Admin login scope: {normalized}"


def test_admin_login_route_marker_reaches_the_main_ancestor() -> None:
    shell_index = SHELL.index('<div class="portal-shell" id="portal-shell" data-portal-shell>')
    main_index = SHELL.index('<main class="portal-main" id="portal-main"')
    assert shell_index < main_index
    assert "function isAdminPortalSurface(page)" in PORTAL
    assert 'path === "/admin" || path.startsWith("/admin/")' in PORTAL
    assert "shell.dataset.portalAppKind = appKind;" in PORTAL
    assert 'shell.classList.toggle("portal-shell--auth", isAuth);' in PORTAL
    assert "main.innerHTML = renderPage(page, context);" in PORTAL
    assert f"{ADMIN_PAGE} .portal-main" not in THEME


def test_admin_login_desktop_contract_uses_reachable_exact_rule_bodies() -> None:
    block = _takeover_block()
    _assert_every_rule_is_admin_scoped(block)
    _assert_declarations(
        _brace_body(block, ADMIN_MAIN),
        "width: min(1200px, calc(100vw - 48px));",
        "max-width: 1200px;",
    )

    desktop = _brace_body(block, f"@media (min-width: {DESKTOP_BREAKPOINT}px)")
    _assert_declarations(
        _brace_body(desktop, ADMIN_MAIN),
        f"padding-inline: {DESKTOP_INLINE_PADDING}px;",
    )
    _assert_declarations(
        _brace_body(desktop, ADMIN_PAGE),
        "width: 100%;",
        "grid-template-columns: minmax(0, 1fr);",
        'grid-template-areas: "header" "shell";',
    )
    _assert_declarations(
        _brace_body(desktop, f"{ADMIN_PAGE} .portal-auth-header"),
        "grid-area: header;",
        "width: 100%;",
    )
    _assert_declarations(
        _brace_body(desktop, f"{ADMIN_PAGE} .portal-auth-shell"),
        "grid-area: shell;",
        "display: grid;",
        "grid-template-columns: minmax(280px, .9fr) minmax(420px, 1.1fr);",
        'grid-template-areas: "intro card";',
        "gap: clamp(24px, 3vw, 48px);",
    )
    _assert_declarations(
        _brace_body(desktop, f"{ADMIN_PAGE} .portal-auth-intro"),
        "grid-area: intro;",
        "min-width: 0;",
        "width: 100%;",
        "max-width: none;",
        "justify-items: start;",
        "text-align: left;",
    )
    _assert_declarations(
        _brace_body(desktop, f"{ADMIN_PAGE} .portal-auth-card"),
        "grid-area: card;",
        "min-width: 0;",
        "width: 100%;",
        "max-width: none;",
    )


def test_admin_login_tablet_and_mobile_contracts_remain_route_scoped() -> None:
    block = _takeover_block()
    _assert_every_rule_is_admin_scoped(block)
    for forbidden in (
        ".portal-auth-page--admin .portal-main",
        ".portal-auth-form",
        ".portal-auth-input",
        ".portal-interactive-target",
        "position: fixed",
        "transform: scale",
        "zoom:",
        "overflow: hidden",
        "overflow-x: hidden",
    ):
        assert forbidden not in block

    tablet = _brace_body(block, f"@media (max-width: {STACKED_BREAKPOINT}px)")
    _assert_declarations(
        _brace_body(tablet, ADMIN_MAIN),
        "width: min(100%, calc(100vw - 32px));",
        "max-width: 680px;",
    )
    _assert_declarations(
        _brace_body(tablet, ADMIN_PAGE),
        "width: 100%;",
        "grid-template-columns: minmax(0, 1fr);",
        'grid-template-areas: "header" "shell";',
    )
    _assert_declarations(
        _brace_body(tablet, f"{ADMIN_PAGE} .portal-auth-shell"),
        "grid-area: shell;",
        "display: grid;",
        "grid-template-columns: minmax(0, 1fr);",
        'grid-template-areas: "intro" "card";',
    )
    for selector, area in (
        (f"{ADMIN_PAGE} .portal-auth-intro", "intro"),
        (f"{ADMIN_PAGE} .portal-auth-card", "card"),
    ):
        _assert_declarations(
            _brace_body(tablet, selector),
            f"grid-area: {area};",
            "min-width: 0;",
            "width: 100%;",
            "max-width: 100%;",
            "white-space: normal;",
            "word-break: normal;",
            "overflow-wrap: normal;",
        )

    mobile = _brace_body(block, "@media (max-width: 600px)")
    _assert_every_rule_is_admin_scoped(mobile)
    _assert_declarations(
        _brace_body(mobile, f"{ADMIN_PAGE} .portal-form"),
        "min-width: 0;",
        "max-width: 100%;",
    )
    _assert_declarations(
        _brace_body(mobile, f"{ADMIN_PAGE} .portal-input"),
        "min-width: 0;",
        "max-width: 100%;",
        "font-size: 16px;",
    )
    _assert_declarations(
        _brace_body(mobile, f"{ADMIN_PAGE} button"),
        "min-width: 44px;",
        "min-height: 44px;",
        "max-width: 100%;",
    )
    _assert_declarations(
        _brace_body(mobile, f"{ADMIN_PAGE} .portal-auth-card a"),
        "display: inline-flex;",
        "min-width: 44px;",
        "min-height: 44px;",
        "max-width: 100%;",
        "align-items: center;",
    )


def test_admin_login_layout_is_independent_of_motion_preference() -> None:
    block = _takeover_block()
    compact = _compact(block).lower()
    for declaration in ("animation:", "transition:", "transform:", "opacity:"):
        assert declaration not in compact

    reduced_blocks = _brace_bodies(THEME, "@media (prefers-reduced-motion: reduce)")
    admin_reduced = next(
        (
            body
            for body in reduced_blocks
            if '.portal-shell[data-portal-app-kind="admin"] .portal-main' in body
        ),
        None,
    )
    assert admin_reduced is not None
    _assert_declarations(
        admin_reduced,
        "opacity: 1;",
        "transform: none;",
        "animation: none;",
    )


def test_admin_login_desktop_breakpoint_can_contain_both_minimum_columns() -> None:
    assert "* { box-sizing: border-box; }" in BASE_CSS
    viewport = DESKTOP_BREAKPOINT
    main_border_box = min(1200, viewport - 48)
    effective_inline_padding = DESKTOP_INLINE_PADDING * 2
    available_content = main_border_box - effective_inline_padding
    minimum_gap = max(24, min(viewport * 0.03, 48))
    minimum_grid = 280 + 420 + minimum_gap
    assert available_content >= minimum_grid
    assert STACKED_BREAKPOINT + 1 == DESKTOP_BREAKPOINT
