"""Direct actual HTMLResponse only: no app/server/DB/session/login/provider."""
import hashlib
import html
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from copyfast_pages import render_portal

COPY = {
    "vi": ("Ảnh thành PDF", "Chọn ảnh và ghép thành một tệp PDF. Ảnh gốc được giữ nguyên."),
    "en": ("Images to PDF", "Choose images and combine them into one PDF file. The original images stay unchanged."),
    "zh": ("图像转 PDF", "选择图像并合成为一个 PDF 文件。原图像保持不变。"),
}
AUTHORITY = ROOT / "tests" / "fixtures" / "image-to-pdf-meta-reviewed.json"


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_image_to_pdf_actual_first_html_response_metadata_and_bootstrap(locale):
    raw = AUTHORITY.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "6168254dabd2ba87f5364368ea3bf6383bb1a00cb3d746bb9250af913516c08f"
    authority = json.loads(raw)
    assert authority["review"]["proposalExact"] is True
    assert len(authority["proposal"]["changes"]) == 5
    assert authority["proposal"]["specId"] == "IMAGE-TO-PDF-OUTER-META-20261118"
    response = render_portal("/documents/image-to-pdf", interface_locale=locale)
    assert response.status_code == 200
    assert response.media_type == "text/html"
    body = response.body.decode("utf8")
    title = re.search(r"<title>(.*?)</title>", body)
    description = re.search(r'<meta name="description" content="([^"]*)">', body)
    bootstrap = re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', body)
    lang = re.search(r'<html\b[^>]*\blang="([^"]+)"', body)
    assert title is not None and description is not None and bootstrap is not None and lang is not None
    payload = json.loads(bootstrap[1])
    assert html.unescape(title[1]) == payload["title"] == COPY[locale][0] + " · TOAN AAS"
    assert html.unescape(description[1]) == COPY[locale][1]
    assert payload["path"] == "/documents/image-to-pdf" and payload["interfaceLocale"] == locale
    assert lang[1] == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert payload["apiBase"] == "/api/v1"
    assert payload["catalogUrl"] == "/api/v1/catalog"
    assert payload["authUrl"] == "/api/v1/auth/me"
