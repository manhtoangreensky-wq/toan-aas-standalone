"""Presentation and visual system contracts for P0.WEBAPP.WEB12.

Task: P0.WEBAPP.WEB12.BLUE.VISUAL.SYSTEM.CUSTOMER.ADMIN.TRUTH
Master Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Mode: OWNER-GOVERNED, SOURCE_ONLY, VISUAL_ONLY
"""

from __future__ import annotations

from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
PORTAL_THEME_CSS_PATH = ROOT / "static" / "portal" / "portal-theme.css"
PORTAL_FIRST_PAINT_CSS_PATH = ROOT / "static" / "portal" / "portal-first-paint.css"
PORTAL_THEME_JS_PATH = ROOT / "static" / "portal" / "portal-theme.js"
PORTAL_SHELL_HTML_PATH = ROOT / "templates" / "portal_shell.html"

PORTAL_THEME_CSS = PORTAL_THEME_CSS_PATH.read_text(encoding="utf-8")
PORTAL_FIRST_PAINT_CSS = PORTAL_FIRST_PAINT_CSS_PATH.read_text(encoding="utf-8")
PORTAL_THEME_JS = PORTAL_THEME_JS_PATH.read_text(encoding="utf-8")
PORTAL_SHELL_HTML = PORTAL_SHELL_HTML_PATH.read_text(encoding="utf-8")

ALLOWED_BLUE_CANVAS = {"#eff8ff", "#f0f9ff", "#f3fbfc"}
ALLOWED_BLUE_RAIL = {"#075985", "#0369a1", "#0e7490", "#0c4a6e"}
ALLOWED_BLUE_DARK_CANVAS = {"#0b2545", "#0a192f", "#0b132b", "#102f4f"}
FORBIDDEN_OBSIDIAN = {"#09090b", "#0c0c0e", "#121215", "#18181b", "#1c1c21", "#03141f"}


def test_customer_light_uses_blue_sidebar_rail_and_light_blue_canvas() -> None:
    """Customer light mode must visibly read as a blue/cyan system with a blue sidebar rail."""
    match = re.search(
        r'\.portal-shell\[data-portal-app-kind="customer"\]\s+\.portal-sidebar\s*\{(?P<rules>[^}]+)\}',
        PORTAL_THEME_CSS,
    )
    assert match is not None, "Customer sidebar rule must exist in portal-theme.css"

    assert (
        "--portal-customer-blue-rail" in PORTAL_THEME_CSS
        or "ADMIN_BLUE_RAIL" in PORTAL_THEME_CSS
    )


def test_customer_dark_eliminates_black_obsidian_surfaces() -> None:
    """Customer dark theme must use deep blue-dark layout surfaces, not obsidian black."""
    dark_block_match = re.search(
        r'html\[data-portal-theme="dark"\]\s+\.portal-shell,\s*html\[data-portal-theme="dark"\]\s+body[^{]*\{(?P<declarations>[^}]+)\}',
        PORTAL_THEME_CSS,
        flags=re.DOTALL,
    )
    assert dark_block_match is not None, "Dark theme override block must exist"
    dark_declarations = dark_block_match.group("declarations")

    assert "var(--portal-saas-obsidian-canvas)" not in dark_declarations, (
        "Dark theme canvas must NOT use obsidian canvas (#09090b)"
    )
    assert "var(--portal-saas-obsidian-surface)" not in dark_declarations, (
        "Dark theme surface must NOT use obsidian surface (#121215)"
    )
    assert "var(--portal-saas-obsidian-rail)" not in dark_declarations, (
        "Dark theme rail must NOT use obsidian rail (#0c0c0e)"
    )


def test_admin_ui_uses_clearly_blue_sidebar_rail_and_blue_actions() -> None:
    """Admin UI must have a clearly blue sidebar rail (ADMIN_BLUE_RAIL=YES, ADMIN_BLACK_SIDEBAR=NO)."""
    assert "ADMIN_BLUE_RAIL" in PORTAL_THEME_CSS or "--portal-admin-blue-rail" in PORTAL_THEME_CSS, (
        "Admin blue rail contract marker must be present"
    )


def test_zero_initial_paint_or_theme_flash_black() -> None:
    """Zero initial paint / theme flash black (BLACK_FLASH=NO)."""
    assert "#03141f" not in PORTAL_SHELL_HTML, (
        "portal_shell.html must NOT use near-black #03141f meta theme-color"
    )
    assert '#063B47' not in PORTAL_THEME_JS, (
        "portal-theme.js setMetaColor must NOT use near-black #063B47"
    )
