"""Contracts for the bounded login brand and low-height viewport hotfix."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "webapp-quality.yml").read_text(encoding="utf-8")
MARKER = "/* AUTH-LOGIN-BRAND-VIEWPORT-001 */"


def test_auth_brand_and_card_keep_measured_geometry_without_touching_behavior() -> None:
    assert THEME.count(MARKER) == 1
    hotfix = THEME[THEME.index(MARKER) :]

    for token in (
        ".portal-shell--auth .portal-main",
        "width: min(100%, 660px);",
        "max-width: 660px;",
        ".portal-auth-page--access .portal-auth-header",
        "width: min(calc(100vw - 32px), 620px);",
        "justify-self: center;",
        ".portal-auth-page--access .portal-auth-brand",
        "flex: 0 0 auto;",
        ".portal-auth-page--access .portal-auth-brand .portal-brand-mark",
        "flex: 0 0 36px;",
        "min-width: 36px;",
        ".portal-auth-page--access .portal-auth-brand .portal-brand-mark-image",
        "object-fit: contain;",
        "transform: none;",
        "@media (max-height: 680px) and (min-width: 601px)",
        "padding: 12px 0 20px;",
        "row-gap: 10px;",
        "padding: 18px;",
        "min-height: 44px;",
        "@media (max-width: 600px)",
        "width: 100%;",
    ):
        assert token in hotfix

    for forbidden in (
        "display: none",
        "visibility: hidden",
        "position: absolute",
        "transform: scale",
        "zoom:",
        "overflow: hidden",
        "input[type",
        "data-portal-action",
    ):
        assert forbidden not in hotfix

    assert (
        ".portal-auth-page--access .portal-auth-brand .portal-brand-mark-image {\n"
        "  width: 100%;\n"
        "  height: 100%;"
    ) in hotfix
    assert (
        ".portal-auth-page--access .portal-auth-card button,\n"
        ".portal-auth-page--access .portal-auth-switch,\n"
        ".portal-auth-page--access .portal-auth-switch a {\n"
        "  min-height: 44px;"
    ) in hotfix


def test_pull_request_quality_gate_executes_the_hotfix_contract() -> None:
    assert "tests/test_auth_login_brand_viewport_001_contracts.py" in WORKFLOW
