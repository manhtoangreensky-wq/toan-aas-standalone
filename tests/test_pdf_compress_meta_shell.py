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
    "vi": ("Nén PDF", "Giảm dung lượng PDF khi có thể. Tệp gốc được giữ nguyên."),
    "en": ("Compress PDF", "Reduce a PDF's file size where possible. The original stays unchanged."),
    "zh": ("压缩 PDF", "在可行时减小 PDF 文件大小。原文件将保持不变。"),
}
AUTHORITY = ROOT / "tests" / "fixtures" / "pdf-compress-meta-reviewed.json"


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_compress_actual_first_html_response_metadata_and_bootstrap(locale):
    authority = json.loads(AUTHORITY.read_text(encoding="utf8"))
    expected = authority["expectedRaw"].encode("utf8")
    proposal = authority["proposalRaw"].encode("utf8")
    assert hashlib.sha256(expected).hexdigest() == "b3d1bd271b4d2ae39a7873d9906c6aa20429da68eea4f5ddee624781d7632ab2"
    assert hashlib.sha256(proposal).hexdigest() == "225227707e2b7179359e62614a33b956d4b0439f426f955577522cfedb33506b"
    assert json.loads(expected) == json.loads(proposal)["changes"]
    response = render_portal("/documents/compress", interface_locale=locale)
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
    assert payload["path"] == "/documents/compress" and payload["interfaceLocale"] == locale
    assert lang[1] == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert payload["apiBase"] == "/api/v1"
    assert payload["catalogUrl"] == "/api/v1/catalog"
    assert payload["authUrl"] == "/api/v1/auth/me"
