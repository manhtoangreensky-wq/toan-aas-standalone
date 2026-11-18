"""Direct actual HTMLResponse only: no app/server/DB/auth/session/provider."""
import hashlib
import html
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "tests/fixtures/image-enhance-meta-reviewed.json"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from copyfast_pages import render_portal

COPY = {
    "vi": ("Chỉnh ảnh", "Chọn ảnh đã lưu, chỉnh màu và độ nét rồi tải bản PNG mới. Tệp gốc được giữ nguyên."),
    "en": ("Edit images", "Choose a saved image, adjust color and sharpness, then download a new PNG. The original file stays unchanged."),
    "zh": ("调整图像", "选择已保存的图像，调整色彩和锐度，然后下载新的 PNG 文件。原文件保持不变。"),
}


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_enhance_actual_first_html_response_metadata_and_bootstrap(locale):
    raw = AUTHORITY.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "10b19e6677caea6c2f70b213aab524580321dcd07e6dbf6a4c48b0d41199d83e"
    authority = json.loads(raw)
    assert authority["review"]["schemaValid"] is True and authority["review"]["proposalExact"] is True
    assert authority["review"]["conversation"] == "92163194-4b60-4827-bdaa-436b0f8cfdf4"
    proposal = authority["proposal"]
    assert proposal["specId"] == "IMAGE-ENHANCE-OUTER-META-20261118" and proposal["revision"] == "R1"
    assert len(proposal["changes"]) == 5 and all(edit["count"] == 1 for edit in proposal["changes"])
    response = render_portal("/image/edit", interface_locale=locale)
    assert response.status_code == 200 and response.media_type == "text/html"
    body = response.body.decode("utf8")
    title = re.search(r"<title>(.*?)</title>", body)
    description = re.search(r'<meta name="description" content="([^"]*)">', body)
    bootstrap = re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', body)
    lang = re.search(r'<html\b[^>]*\blang="([^"]+)"', body)
    assert title is not None and description is not None and bootstrap is not None and lang is not None
    payload = json.loads(bootstrap[1])
    assert html.unescape(title[1]) == payload["title"] == COPY[locale][0] + " · TOAN AAS"
    assert html.unescape(description[1]) == COPY[locale][1]
    assert payload["path"] == "/image/edit" and payload["interfaceLocale"] == locale
    assert lang[1] == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert payload["apiBase"] == "/api/v1" and payload["catalogUrl"] == "/api/v1/catalog"
    assert payload["authUrl"] == "/api/v1/auth/me"
