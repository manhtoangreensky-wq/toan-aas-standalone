"""Regression contracts for the public login/register responsive shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")


def _auth_renderer() -> str:
    start = PORTAL.index("function renderAuth(page, context)")
    return PORTAL[start:PORTAL.index("const RESULT_LABELS", start)]


def _final_auth_mobile_layer() -> str:
    semantic = THEME.index("/* Teal–Sky Product Redesign -- final semantic layer. */")
    start = THEME.index("@media (max-width: 1080px) {", semantic)
    end = THEME.index("@media (max-width: 390px) {", start)
    return THEME[start:end]


def test_email_form_does_not_end_with_a_second_email_divider() -> None:
    auth = _auth_renderer()

    assert "portal-auth-divider" not in auth
    assert "HOẶC TIẾP TỤC VỚI EMAIL" not in auth
    assert "Workspace" not in auth


def test_mobile_and_tablet_show_compact_intro_before_the_auth_card() -> None:
    mobile = _final_auth_mobile_layer()

    assert 'grid-template-areas: "intro" "card";' in mobile
    assert 'grid-template-areas: "card" "intro";' not in mobile
    assert ".portal-auth-page--access .portal-auth-intro .portal-description" in mobile
    assert "display: none;" in mobile
    assert ".portal-auth-page--access .portal-auth-intro .portal-title" in mobile
    assert "font-size: 28px;" in mobile


def test_tablet_header_keeps_brand_and_back_copy_from_wrapping() -> None:
    mobile = _final_auth_mobile_layer()

    assert ".portal-auth-page--access .portal-auth-brand strong" in mobile
    assert "white-space: nowrap;" in mobile
    assert ".portal-auth-page--access .portal-auth-brand small," in mobile
    assert ".portal-auth-page--access .portal-auth-back-label" in mobile
    assert (
        ".portal-auth-page--access .portal-auth-locale-link {\n"
        "    white-space: nowrap;\n"
        "  }"
    ) in mobile


def test_auth_header_uses_three_normal_flow_rows_at_nine_hundred() -> None:
    marker = "/* A09 Admin Vertical Shell */"
    assert marker in THEME
    layer = THEME[THEME.index(marker):]
    start = layer.index("@media (max-width: 900px) {")
    mobile = layer[start:]

    assert "grid-template-areas:" in mobile
    assert '"brand"' in mobile
    assert '"locale"' in mobile
    assert '"actions"' in mobile
    assert '"brand actions"' not in mobile
    assert "grid-template-columns: minmax(0, 1fr);" in mobile
    assert "position: absolute" not in mobile
    assert "position: fixed" not in mobile
    assert "transform: scale" not in mobile
    assert "zoom:" not in mobile
    assert "white-space: nowrap;" in mobile
    assert (
        ".portal-auth-page--access {\n"
        "    width: 100%;\n"
        "    row-gap: 8px;"
    ) in mobile
    assert ".portal-auth-page--access .portal-auth-intro" not in mobile


def test_narrow_header_keeps_the_toan_aas_name_visible() -> None:
    semantic = THEME.index("/* Teal–Sky Product Redesign -- final semantic layer. */")
    start = THEME.index("@media (max-width: 380px) {", semantic)
    narrow = THEME[start:THEME.index("@media (max-width: 1180px) and (min-width: 701px) {", start)]

    assert "clip: rect(0, 0, 0, 0);" not in narrow
    assert "position: absolute;" not in narrow


def test_mobile_auth_fields_use_an_ios_safe_font_size() -> None:
    start = THEME.index("@media (max-width: 600px) {")
    mobile = THEME[start:THEME.index("@media (max-width: 700px) {", start)]

    assert (
        ".portal-auth-page--access :is(.portal-input, .portal-select, .portal-textarea) {\n"
        "    font-size: 16px;\n"
        "  }"
    ) in mobile


def test_mobile_auth_shell_does_not_keep_the_hidden_intro_row() -> None:
    semantic = THEME.index("/* Teal–Sky Product Redesign -- final semantic layer. */")
    responsive = THEME.index("@media (max-width: 1080px) {", semantic)
    mobile = THEME[responsive:THEME.index("@media (max-width: 390px) {", responsive)]

    assert "@media (max-width: 600px) {" in mobile
    assert (
        '.portal-auth-page--access .portal-auth-shell {\n'
        '    grid-template-areas: "card";\n'
        "    row-gap: 0;\n"
        "  }"
    ) in mobile


def test_vietnamese_auth_copy_uses_khong_gian_lam_viec_consistently() -> None:
    vi = I18N[I18N.index("    vi: {"):I18N.index("    en: {")]

    assert '"access.heading.register": "Tạo không gian làm việc của bạn"' in vi
    assert '"access.intro.login": "Đăng nhập để tiếp tục vào không gian làm việc."' in vi
    assert '"access.context.label": "Lợi ích của không gian làm việc"' in vi
    assert '"access.context.kicker": "Không gian làm việc"' in vi
    assert '"access.brand.subtitle": "Không gian AI"' in vi
    assert "Workspace" not in "\n".join(
        line for line in vi.splitlines() if '"access.' in line
    )
