"""Presentation contracts for the narrow Admin ERP mobile table harmony pass."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


ADMIN_MOBILE_DATA_HARMONY_MARKER = "/* Admin ERP mobile data surface harmony"


def admin_mobile_data_harmony_css() -> str:
    marker = THEME.find(ADMIN_MOBILE_DATA_HARMONY_MARKER)
    assert marker >= 0, "Admin ERP mobile table harmony must remain a reviewable final theme layer."
    # Customer Shell Harmony remains a separately reviewable final layer after
    # this narrow Admin patch. Do not let its customer-only words masquerade as
    # an Admin scope regression in this slice.
    next_layer = THEME.find("/* Customer Shell Harmony", marker)
    return THEME[marker:] if next_layer < 0 else THEME[marker:next_layer]


def test_admin_mobile_data_harmony_is_presentation_only_and_scoped_to_signed_admin_shell() -> None:
    harmony = admin_mobile_data_harmony_css()

    for selector in (
        '.portal-shell[data-portal-app-kind="admin"] .portal-page .portal-admin-data-surface .portal-data-table-scroll-hint',
        '.portal-shell[data-portal-app-kind="admin"] .portal-page .portal-admin-data-surface .portal-data-table th:first-child',
        '.portal-shell[data-portal-app-kind="admin"] .portal-page .portal-admin-data-surface .portal-data-table tbody tr:hover > td:first-child:not(.portal-empty-cell)',
    ):
        assert selector in harmony

    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "/api/",
        "data-portal-action",
        "wallet",
        "payos",
        "provider",
        "telegram",
        'data-portal-app-kind="customer"',
    ):
        assert forbidden.lower() not in harmony.lower()


def test_admin_mobile_data_harmony_overrides_legacy_dark_table_affordances_with_theme_tokens() -> None:
    harmony = admin_mobile_data_harmony_css()

    assert "@media (max-width: 700px)" in harmony
    for token in (
        "var(--portal-border)",
        "var(--portal-surface-soft)",
        "var(--portal-surface-light)",
        "var(--portal-light-hover-surface)",
        "var(--portal-muted)",
        "var(--portal-ink)",
    ):
        assert token in harmony

    assert "#" not in harmony
    assert "background: #172638;" not in harmony
    assert "color-mix(in srgb, var(--portal-ink) 60%, transparent)" in harmony
