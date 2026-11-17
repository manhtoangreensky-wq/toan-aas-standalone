"""Actual pure server shell; no app/database/session/provider import or calls."""
import html
import json
import re

import pytest
from copyfast_pages import render_portal

COPY = {
    "vi": ("Tách PDF", "Tạo tệp PDF từ một trang hoặc dải trang liên tiếp trong tài liệu đã lưu."),
    "en": ("Split PDF", "Create a PDF from one page or a consecutive page range in a saved document."),
    "zh": ("拆分 PDF", "从已保存的文档中提取单页或连续页面，创建 PDF。"),
}


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_split_first_paint_title_bootstrap_locale(locale):
    response = render_portal("/documents/split", interface_locale=locale)
    assert response.status_code == 200
    body = response.body.decode("utf8")
    title = html.unescape(re.search(r"<title>(.*?)</title>", body)[1])
    payload = json.loads(re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', body)[1])
    assert title == payload["title"] == COPY[locale][0] + " · TOAN AAS"
    assert payload["path"] == "/documents/split" and payload["interfaceLocale"] == locale
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert payload["apiBase"] == "/api/v1" and payload["authUrl"] == "/api/v1/auth/me"


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_split_first_paint_description(locale):
    response = render_portal("/documents/split", interface_locale=locale)
    body = response.body.decode("utf8")
    description = html.unescape(re.search(r'<meta name="description" content="([^"]*)">', body)[1])
    assert description == COPY[locale][1]
