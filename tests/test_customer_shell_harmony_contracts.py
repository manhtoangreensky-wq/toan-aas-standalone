"""Presentation contracts for the customer Workspace shell harmony pass.

The visual layer must make the signed customer app easier to scan without
turning it into a second authority, data source, or action flow.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")


CUSTOMER_SHELL_HARMONY_MARKER = "/* Customer Shell Harmony ----------------------------------------------"
CUSTOMER_SHELL_HARMONY_END_MARKER = "/* Final responsive app dock harmony */"


def customer_shell_harmony_css() -> str:
    marker = THEME.find(CUSTOMER_SHELL_HARMONY_MARKER)
    assert marker >= 0, "Customer shell harmony must be a final, reviewable theme layer."
    end = THEME.find(CUSTOMER_SHELL_HARMONY_END_MARKER, marker)
    assert end >= 0, "The harmony slice must end before later dock-only CSS."
    return THEME[marker:end]


def test_customer_shell_harmony_is_scoped_to_the_existing_signed_customer_shell() -> None:
    harmony = customer_shell_harmony_css()

    for selector in (
        '.portal-shell[data-portal-app-kind="customer"] .portal-sidebar',
        '.portal-shell[data-portal-app-kind="customer"] .portal-header',
        '.portal-shell[data-portal-app-kind="customer"] .portal-nav-group',
        '.portal-shell[data-portal-app-kind="customer"] .portal-command-palette .portal-command-dialog',
    ):
        assert selector in harmony
    assert 'data-portal-command-palette' in SHELL
    assert SHELL.index('data-portal-command-palette') < SHELL.index('</div>\n  <div class="portal-toast-region"')
    assert '~ .portal-command-palette' not in harmony

    # The existing server-owned marker is only consumed as a visual scope;
    # no new browser source of identity, authority, or feature readiness is
    # allowed in this polish layer.
    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "/api/",
        "localStorage",
        "sessionStorage",
        "data-portal-action",
        "wallet",
        "payos",
        "provider",
        "telegram",
    ):
        assert forbidden.lower() not in harmony.lower()


def test_customer_shell_harmony_uses_semantic_tokens_and_keeps_the_operational_canvas_clean() -> None:
    harmony = customer_shell_harmony_css()

    for token in (
        "var(--portal-rail)",
        "var(--portal-surface-light)",
        "var(--portal-surface-soft)",
        "var(--portal-border)",
        "var(--portal-ink)",
        "var(--portal-muted)",
        "var(--portal-context)",
    ):
        assert token in harmony

    assert "linear-gradient" not in harmony
    assert "#" not in harmony
    assert "min-height: 44px;" in harmony
    assert "@media (max-width: 620px)" in harmony
    assert ".portal-session-copy" in harmony
    assert "width: 44px;" in harmony
    assert ".portal-nav-group--current" in harmony
    assert "border-bottom-color: var(--portal-border-strong);" in harmony
    assert ".portal-command-hint kbd" in harmony
    assert (
        '.portal-shell[data-portal-app-kind="customer"] '
        ".portal-command-palette .portal-command-search-icon"
    ) in harmony


def test_customer_shell_harmony_has_bounded_motion_and_a_complete_reduced_motion_path() -> None:
    harmony = customer_shell_harmony_css()

    for keyframe in (
        "@keyframes portal-customer-shell-enter",
        "@keyframes portal-customer-command-enter",
    ):
        assert keyframe in harmony

    assert "@media (prefers-reduced-motion: no-preference)" in harmony
    assert "@media (prefers-reduced-motion: reduce)" in harmony
    assert "@media (min-width: 981px) and (prefers-reduced-motion: no-preference)" in harmony
    assert '.portal-shell[data-portal-app-kind="customer"]:not(.portal-shell--focus) .portal-sidebar' in harmony
    assert "transform: translateY(" in harmony
    assert "transform: translateX(" in harmony
    assert "animation: none !important;" in harmony
    assert "transition: none !important;" in harmony
    assert "transform: none !important;" in harmony
    assert '.portal-shell[data-portal-app-kind="customer"] .portal-command-palette:not([hidden]) .portal-command-dialog' in harmony
    assert "outline: 3px solid var(--portal-focus);" in harmony
    assert "background: var(--portal-surface-soft);" in harmony
