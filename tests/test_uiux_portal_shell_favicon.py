"""Regression contract for a branded icon on rendered Portal shells."""

from pathlib import Path

import copyfast_pages


ROOT = Path(__file__).resolve().parents[1]
ICON_HREF = "/static/portal/app-icon.svg"
ICON_LINK = f'<link rel="icon" type="image/svg+xml" href="{ICON_HREF}">'


def test_rendered_portal_shell_points_to_the_existing_brand_icon() -> None:
    for route in ("/welcome", "/dashboard", "/admin/login"):
        html = copyfast_pages.render_portal(route).body.decode("utf-8")
        assert ICON_LINK in html, route

    assert (ROOT / ICON_HREF.lstrip("/")).is_file()


def test_fallback_portal_shell_also_declares_the_brand_icon() -> None:
    assert ICON_LINK in copyfast_pages._fallback_template()
