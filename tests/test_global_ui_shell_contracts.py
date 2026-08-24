"""Static presentation contracts for the shared portal brand mark."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def test_brand_mark_uses_the_official_decorative_image() -> None:
    helper = _section(PORTAL, "function portalBrandMark()", "function portalStatusIcon(status)")

    assert 'class="portal-brand-mark-image"' in helper
    assert 'src="/static/logo_ch%C3%ADnh_th%E1%BB%A9c.png"' in helper
    assert 'alt=""' in helper
    assert 'width="56"' in helper
    assert 'height="56"' in helper
    assert 'decoding="async"' in helper
    assert "portal-brand-mark-symbol" not in helper
    assert "${" not in helper
    assert not any(token in helper for token in ("fetch(", "window.", "document.", "localStorage", "sessionStorage"))


def test_all_existing_brand_mark_sites_use_the_shared_helper() -> None:
    brand_marks = re.findall(
        r'<span class="portal-brand-mark" aria-hidden="true">(?P<content>.*?)</span>',
        PORTAL,
    )

    assert brand_marks == ["${portalBrandMark()}"] * 4
    assert '<span class="portal-brand-mark" aria-hidden="true">TA</span>' not in PORTAL


def test_shell_crops_the_official_brand_image_without_animation() -> None:
    image = re.search(
        r"\.portal-brand-mark-image\s*\{(?P<declarations>.*?)\n\}",
        CSS,
        flags=re.DOTALL,
    )

    assert image is not None
    declarations = image.group("declarations")
    assert "display: block;" in declarations
    assert "width: 56px;" in declarations
    assert "height: 56px;" in declarations
    assert "transform: translate(-8px, -4px);" in declarations
    assert "animation" not in declarations
