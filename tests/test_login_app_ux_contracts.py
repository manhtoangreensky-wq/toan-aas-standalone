"""Static contracts for the compact, application-first access screen."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def test_access_screen_uses_one_compact_app_entry_without_repeating_the_brand() -> None:
    auth = _section(PORTAL, "function renderAuth(page, context)", "const RESULT_LABELS")

    assert 'class="portal-auth-header"' in auth
    assert 'class="portal-auth-shell"' in auth
    assert 'class="portal-auth-brand"' in auth
    assert '<a class="portal-auth-brand"' not in auth
    assert 'const authHeading = isLogin ? accessText("heading.login", "Chào mừng trở lại")' in auth
    assert "TOAN AAS · secure access" not in auth
    assert "portal-auth-journey" not in auth


def test_access_screen_keeps_sensitive_auth_actions_but_stacks_fields_for_readability() -> None:
    auth = _section(PORTAL, "function renderAuth(page, context)", "const RESULT_LABELS")
    access_theme = _section(
        THEME,
        "/* Access remains email-first and server-owned.",
        "/* The public companion shares the brand palette",
    )

    assert 'data-portal-action="${safeText(page.action)}"' in auth
    assert 'data-portal-route="${safeText(page.path)}"' in auth
    assert 'class="portal-auth-alternatives"' in auth
    assert 'class="portal-auth-assurance"' in auth
    assert ".portal-auth-page--access .portal-auth-primary .portal-fields {\n  grid-template-columns: minmax(0, 1fr);" in access_theme
    assert ".portal-auth-page--access .portal-auth-card {\n  grid-area: card;" in access_theme
    assert "border-color: var(--portal-border);" in access_theme
    assert ".portal-auth-back {\n  display: inline-flex;\n  min-height: 44px;" in access_theme
    assert "var(--portal-context)" in access_theme


def test_access_screen_uses_a_balanced_desktop_rail_and_single_column_mobile_fallback() -> None:
    """The redesign makes desktop access proportional without changing auth ownership."""

    marker = "/* Teal–Sky Product Redesign -- final semantic layer. */"
    redesign = THEME[THEME.index(marker):]

    assert "/* Compact application access screen." not in CSS
    assert ".portal-body--auth,\n.portal-shell--auth { background: #0a0f17; }" not in CSS
    assert "grid-template-columns: minmax(0, .82fr) minmax(440px, 480px);" not in CSS
    assert '@media (min-width: 981px)' in redesign
    assert "width: min(100%, 1180px);" in redesign
    assert 'grid-template-areas: "intro card";' in redesign
    assert "minmax(420px, 480px)" in redesign
    assert 'class="portal-auth-context"' in PORTAL
    assert '@media (max-width: 980px)' in redesign
    assert 'grid-template-areas: "intro" "card";' in redesign
    assert ".portal-auth-context { display: none; }" in redesign


def test_access_screen_compacts_mobile_rhythm_without_shrinking_controls() -> None:
    mobile = THEME.split("@media (max-width: 600px) {", 1)[1]

    assert "padding-top: 16px;" in mobile
    assert ".portal-auth-page--access .portal-auth-card { padding: 16px; }" in mobile
    assert ".portal-auth-page--access .portal-auth-switch," in mobile
    assert "min-height: 44px;" in mobile


def test_access_intro_uses_a_balanced_heading_measure_without_a_single_word_wrap() -> None:
    title = _section(
        THEME,
        ".portal-auth-page--access .portal-auth-intro .portal-title {",
        "\n}\n\n.portal-auth-page--access .portal-auth-intro .portal-description",
    )

    assert "max-width: 18ch;" in title
    assert "max-width: 11ch;" not in title
    assert "font-size: clamp(38px, 3.7vw, 48px);" in title
    assert "text-wrap: balance;" in title


def test_public_access_uses_reviewed_locale_links_and_translated_field_copy() -> None:
    auth = _section(PORTAL, "function renderAuth(page, context)", "const RESULT_LABELS")
    fields = _section(PORTAL, "const FIELD_SETS = Object.freeze({", "// Public account and portal routes.")

    assert "portal-auth-locale-nav" in auth
    assert "portal-auth-back-label" in auth
    assert 'accessText("locale.label", "Ngôn ngữ giao diện")' in auth
    assert 'accessText("alternatives.loginTitle", "Dùng Telegram hoặc OAuth")' in auth
    assert 'accessText("assurance.summary", "Vì sao Workspace này an toàn?")' in auth
    assert 'accessText("help.summary", "Thông tin bảo mật và tích hợp")' in auth
    assert 'accessText("primary.unavailable", "Đang kiểm tra phiên bảo mật trước khi cho phép thao tác.")' in auth
    assert "access.field.email" in fields
    assert "access.placeholder.password" in fields
    assert "field.placeholderKey ? uiText(field.placeholderKey, field.placeholder)" in PORTAL
    assert "def _public_access_interface_locale(request: Request) -> str:" in APP
    assert "render_portal(page_path, interface_locale=_public_access_interface_locale(request))" in APP
    for key in (
        "access.locale.label",
        "access.nav.backWelcome",
        "access.heading.login",
        "access.heading.register",
        "access.field.email",
        "access.field.password",
        "access.placeholder.password",
        "access.action.signIn",
        "access.action.register",
        "access.alternatives.loginTitle",
        "access.alternatives.registerTitle",
        "access.assurance.summary",
        "access.help.summary",
        "access.primary.unavailable",
    ):
        assert I18N.count(f'"{key}"') == 3

    locale_link = _section(
        THEME,
        ".portal-auth-page--access .portal-auth-locale-link {",
        "\n}\n\n.portal-auth-page--access .portal-auth-locale-link:hover",
    )
    assert "min-width: 44px;" in locale_link
    assert "min-height: 44px;" in locale_link
    mobile_theme = THEME.split("@media (max-width: 600px) {", 1)[1]
    assert ".portal-auth-page--access .portal-auth-brand strong {\n    white-space: nowrap;\n  }" in mobile_theme
    assert ".portal-auth-page--access .portal-auth-back-label {\n    display: none;\n  }" in mobile_theme


def test_document_title_strips_an_existing_product_suffix_before_adding_it_once() -> None:
    assert "function documentTitle(page, context)" in PORTAL
    assert 'replace(/\\s*[·—–-]\\s*TOAN AAS\\s*$/i, "")' in PORTAL
    assert "document.title = documentTitle(page, context);" in PORTAL
