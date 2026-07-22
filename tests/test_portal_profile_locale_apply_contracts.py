"""Focused browser-contract checks for applying a saved interface locale."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")


def source_between(start: str, end: str) -> str:
    beginning = INTEGRATION.index(start)
    finish = INTEGRATION.index(end, beginning)
    return INTEGRATION[beginning:finish]


def test_profile_locale_payload_is_closed_to_reviewed_interface_catalogs() -> None:
    helpers = source_between("function profileUpdateInterfaceLocale", "const WORKSPACE_SETUP_BOUNDARY_FALSE_FIELDS")

    assert 'const INTERFACE_LOCALES = new Set(["vi", "en", "zh"]);' in INTEGRATION
    assert "if (!INTERFACE_LOCALES.has(locale)) throw new Error" in helpers
    assert "display_name:" in helpers
    assert "locale: profileUpdateInterfaceLocale(source.locale)" in helpers
    assert "timezone:" in helpers
    for forbidden in (
        "source_language",
        "target_language",
        "workflow_language",
        "telegram_id",
        "canonical_user_id",
        "role:",
        "localStorage.",
        "sessionStorage.",
    ):
        assert forbidden not in helpers


def test_profile_locale_applies_only_after_signed_receipt_then_remounts() -> None:
    action = source_between('if (action === "update-profile") {', 'if (action === "upgrade-telegram-account") {')
    receipt = source_between("function confirmedProfileInterfaceLocale", "function applyConfirmedProfileInterfaceLocale")
    apply = source_between("function applyConfirmedProfileInterfaceLocale", "const WORKSPACE_SETUP_BOUNDARY_FALSE_FIELDS")

    assert "const payload = profileUpdatePayload(fields);" in action
    assert "body: JSON.stringify(payload)" in action
    assert "applyConfirmedProfileInterfaceLocale(confirmedProfileInterfaceLocale(result));" in action
    assert action.index("applyConfirmedProfileInterfaceLocale") < action.index("await hydrate();") < action.index("toast(result.message);")
    assert "merge(" not in action
    assert "INTERFACE_LOCALES.has(locale)" in receipt
    for forbidden in ("canonical_user_id", "telegram_id", "role", "source_language", "target_language", "workflow_language"):
        assert forbidden not in receipt
    assert "i18n.setLocale(locale, { emit: false })" in apply
    # The signed receipt may retain its one exact presentation value in
    # in-memory bootstrap so a render before `/auth/me` cannot flash back to
    # the old locale. It must not merge the broader profile/account receipt.
    assert "const current = base();" in apply
    assert "window.__TOAN_AAS_PORTAL__ = { ...current, interfaceLocale: locale };" in apply
    assert "merge(" not in apply
