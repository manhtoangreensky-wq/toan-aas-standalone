"""Static presentation contracts for the shared portal brand mark."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def _theme_rule(selector: str) -> str:
    rule = re.search(re.escape(selector) + r"\s*\{(?P<declarations>.*?)\n\}", THEME, flags=re.DOTALL)
    assert rule is not None
    return rule.group("declarations")


def test_brand_mark_is_a_closed_decorative_svg_with_three_paths() -> None:
    helper = _section(PORTAL, "function portalBrandMark()", "function portalStatusIcon(status)")

    assert '<svg class="portal-brand-mark-symbol" viewBox="0 0 32 32" aria-hidden="true" focusable="false">' in helper
    assert re.findall(r'<path d="([^"]+)"', helper) == [
        "m16 3 11 6.3v13.4L16 29 5 22.7V9.3z",
        "m9.5 12.9 6.5 3.7 6.5-3.7M16 16.6V24",
        "m9.5 19.1 6.5 3.7 6.5-3.7",
    ]
    assert "</svg>" in helper
    assert "${" not in helper
    assert not any(token in helper for token in ("fetch(", "window.", "document.", "localStorage", "sessionStorage"))


def test_all_existing_brand_mark_sites_use_the_shared_helper() -> None:
    brand_marks = re.findall(
        r'<span class="portal-brand-mark" aria-hidden="true">(?P<content>.*?)</span>',
        PORTAL,
    )

    assert brand_marks == ["${portalBrandMark()}"] * 4
    assert '<span class="portal-brand-mark" aria-hidden="true">TA</span>' not in PORTAL


def test_theme_uses_current_color_outline_geometry_for_the_brand_mark_symbol() -> None:
    mark = _theme_rule(".portal-brand-mark")
    symbol = _theme_rule(".portal-brand-mark-symbol")

    assert "overflow: hidden;" in mark
    for declaration in (
        "display: block;",
        "width: 22px;",
        "height: 22px;",
        "fill: none;",
        "stroke: currentColor;",
        "stroke-linecap: round;",
        "stroke-linejoin: round;",
        "stroke-width: 1.9;",
    ):
        assert declaration in symbol
    assert not any(
        token in symbol.lower()
        for token in ("#", "rgb(", "hsl(", "var(", "gradient", "animation", "transition", "transform")
    )
