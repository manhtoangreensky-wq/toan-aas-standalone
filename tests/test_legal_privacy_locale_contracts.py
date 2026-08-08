"""Locale contracts for the public legal and privacy shells."""

from __future__ import annotations

from pathlib import Path
import re

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


FIXED_KEYS = frozenset(
    {
        "page.legal.title",
        "page.legal.description",
        "page.privacy.title",
        "page.privacy.description",
        "notice.title",
        "notice.legalBody",
        "notice.privacyBody",
        "row.legalFirstTitle",
        "row.privacyFirstTitle",
        "row.legalFirstBody",
        "row.privacyFirstBody",
        "row.legalSecondTitle",
        "row.privacySecondTitle",
        "row.legalSecondBody",
        "row.privacySecondBody",
        "row.thirdTitle",
        "row.thirdBody",
    }
)


def _section(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def _catalogue_keys(locale: str) -> set[str]:
    match = re.search(
        rf"Object\.assign\(LEGAL_PRIVACY_MESSAGES\.{re.escape(locale)}, \{{(?P<body>.*?)\n  \}}\);",
        I18N,
        flags=re.DOTALL,
    )
    assert match, f"Missing legal/privacy catalogue for {locale}"
    return set(re.findall(r'^\s*"legalPrivacy\.([^"]+)"\s*:', match.group("body"), flags=re.MULTILINE))


def test_legal_privacy_catalogue_has_equal_reviewed_vi_en_zh_keys() -> None:
    assert "const LEGAL_PRIVACY_MESSAGES = { vi: {}, en: {}, zh: {} };" in I18N
    catalogues = {locale: _catalogue_keys(locale) for locale in ("vi", "en", "zh")}
    assert catalogues["vi"] == catalogues["en"] == catalogues["zh"]
    assert FIXED_KEYS <= catalogues["vi"]
    assert "LEGAL_PRIVACY_MESSAGES[locale]" in I18N
    for key in FIXED_KEYS:
        assert I18N.count(f'"legalPrivacy.{key}"') == 3


def test_render_legal_keeps_route_boundary_and_localizes_fixed_copy() -> None:
    renderer = _section(PORTAL, "function renderLegal(page, context)", "function safeTelegramLink")
    assert "function legalPrivacyText(" in PORTAL
    assert 'const privacy = page.path === "/privacy";' in renderer
    for key in (
        'legalPrivacyText("notice.title"',
        'legalPrivacyText("notice.legalBody"',
        'legalPrivacyText("notice.privacyBody"',
        'legalPrivacyText("row.legalFirstTitle"',
        'legalPrivacyText("row.privacyFirstTitle"',
        'legalPrivacyText("row.legalFirstBody"',
        'legalPrivacyText("row.privacyFirstBody"',
        'legalPrivacyText("row.legalSecondTitle"',
        'legalPrivacyText("row.privacySecondTitle"',
        'legalPrivacyText("row.legalSecondBody"',
        'legalPrivacyText("row.privacySecondBody"',
        'legalPrivacyText("row.thirdTitle"',
        'legalPrivacyText("row.thirdBody"',
    ):
        assert key in renderer
    assert 'data-portal-action=' not in renderer
    assert 'href="/legal"' not in renderer
    assert 'href="/privacy"' not in renderer


def test_legal_privacy_first_paint_has_route_and_locale_specific_metadata() -> None:
    expected = {
        "vi": {
            "/legal": ("Điều khoản sử dụng · TOAN AAS", "Khung hiển thị điều khoản sử dụng của TOAN AAS; văn bản chính thức được phát hành theo phiên bản và ngày hiệu lực."),
            "/privacy": ("Chính sách riêng tư · TOAN AAS", "Khung hiển thị chính sách riêng tư của TOAN AAS; văn bản chính thức được phát hành theo phiên bản và ngày hiệu lực."),
        },
        "en": {
            "/legal": ("Terms of Use · TOAN AAS", "A reviewed shell for TOAN AAS Terms of Use; the official text is published with a version and effective date."),
            "/privacy": ("Privacy Policy · TOAN AAS", "A reviewed shell for the TOAN AAS Privacy Policy; the official text is published with a version and effective date."),
        },
        "zh": {
            "/legal": ("使用条款 · TOAN AAS", "TOAN AAS 使用条款的已审核框架；正式文本会随版本和生效日期发布。"),
            "/privacy": ("隐私政策 · TOAN AAS", "TOAN AAS 隐私政策的已审核框架；正式文本会随版本和生效日期发布。"),
        },
    }
    assert '"/legal": {' in PAGES
    assert '"/privacy": {' in PAGES
    for locale, routes in expected.items():
        for route, (title, description) in routes.items():
            response = render_portal(route, interface_locale=locale)
            assert response.status_code == 200
            assert f"<title>{title}</title>".encode("utf-8") in response.body
            assert f'<meta name="description" content="{description}">'.encode("utf-8") in response.body
