"""Focused contracts for the signed Web Interface Locale Navigator.

The screen deliberately reuses the existing CSRF-protected Web profile save;
it is not a Bot callback replay, bridge surface or workflow-language control.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
STYLES = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
REGISTRY = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    beginning = source.index(start)
    finish = source.index(end, beginning)
    return source[beginning:finish]


def test_interface_locale_navigator_is_a_dedicated_signed_account_surface() -> None:
    assert 'WebFeature("interface_locale_navigator", "Ngôn ngữ giao diện", "account", "/account/interface-language"' in REGISTRY
    assert 'customerPage("/account/interface-language", "Ngôn ngữ giao diện"' in PORTAL
    assert 'layout: "interface-locale-navigator"' in PORTAL
    assert 'case "interface-locale-navigator": return renderInterfaceLocaleNavigator(page, context);' in PORTAL
    assert 'if (path === "/account/interface-language") return uiText("page.interfaceLocale.title", fallback);' in PORTAL
    assert 'if (path === "/account/interface-language") return uiText("page.interfaceLocale.description", fallback);' in PORTAL


def test_interface_locale_navigator_has_only_three_selectable_web_catalogues() -> None:
    options = _between(PORTAL, "const INTERFACE_LOCALE_OPTIONS = Object.freeze([", "]);\n\n  const FIELD_SETS")
    view = _between(PORTAL, "function renderInterfaceLocaleNavigator", "function renderAccountSecurity")

    assert options.count('value: "') == 3
    for locale in ("vi", "en", "zh"):
        assert f'value: "{locale}"' in options
    for unreviewed in ("ja", "ko", "th", "ar", "zh_cn", "auto"):
        assert f'value: "{unreviewed}"' not in options

    assert 'type="radio" name="locale"' in view
    assert "INTERFACE_LOCALE_OPTIONS.map" in view
    assert '<input type="hidden" name="display_name"' in view
    assert '<input type="hidden" name="timezone"' in view
    assert 'data-portal-action="update-profile"' in view
    assert 'data-portal-route="/account/interface-language"' in view
    assert "lang_more" not in view
    assert "back_lang" not in view
    for display_only in ('code: "ja"', 'code: "ko"', 'code: "th"', 'code: "ar"'):
        assert display_only in view
    for forbidden in (
        "fetch(",
        "api(",
        "context.bridge",
        "bridgeAvailable",
        "/internal/v1",
        "canonical_user_id",
        "telegram_id",
        "localStorage",
        "sessionStorage",
    ):
        assert forbidden not in view


def test_interface_locale_navigator_fences_generic_canonical_hydration() -> None:
    helper = _between(
        INTEGRATION,
        "function isNativeInterfaceLocaleNavigatorPath",
        "function isNativeAdminSystemStewardshipPath",
    )
    hydrator = _between(INTEGRATION, "async function hydrateCanonicalData()", "async function payloadFor")

    assert '=== "/account/interface-language"' in helper
    assert "localStorage" not in helper
    assert "sessionStorage" not in helper
    assert "!isNativeInterfaceLocaleNavigatorPath(currentPath)" in INTEGRATION
    assert "if (isNativeInterfaceLocaleNavigatorPath(path)" in hydrator
    assert "api(" not in hydrator.split("if (isNativeInterfaceLocaleNavigatorPath(path)", 1)[0]


def test_interface_locale_navigator_has_clear_navigation_and_mobile_accessibility() -> None:
    settings = _between(PORTAL, "function renderAccountSettingsNav", "function renderAccount(page, context)")
    assert 'path: "/account/interface-language"' in settings
    assert 'aria-current="page"' in settings
    assert 'if (linkPath === "/account/interface-language") return path === "/account/interface-language";' in PORTAL
    assert '"/account/interface-language", "/account/activity"' in PORTAL

    for selector in (
        ".portal-interface-locale-navigator",
        ".portal-interface-locale-choice:focus-within .portal-interface-locale-choice-body",
        ".portal-interface-locale-input:checked + .portal-interface-locale-choice-body",
        ".portal-interface-locale-choice:has(.portal-interface-locale-input:disabled)",
        ".portal-interface-locale-support ul",
        "@media (max-width: 980px)",
        "@media (max-width: 700px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert selector in STYLES
    assert "min-height: 174px" in STYLES


def test_interface_locale_navigator_i18n_copy_is_complete_for_reviewed_catalogues() -> None:
    for key in (
        "interfaceLocale.nav",
        "interfaceLocale.formLegend",
        "interfaceLocale.noBotState",
        "interfaceLocale.noWorkflow",
        "interfaceLocale.noPayments",
        "interfaceLocale.supportHeading",
        "interfaceLocale.unsupportedHelp",
        "page.interfaceLocale.title",
        "page.interfaceLocale.description",
    ):
        assert I18N.count(f'"{key}"') == 3
