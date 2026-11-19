"""Actual first HTMLResponse metadata; no app/server/database/login/provider."""
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = "a589008be5d7be371789551ffc11e750db46270b"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from copyfast_pages import render_portal

COPY = {
    "/documents/pdf-to-images": {
        "vi": ("PDF sang ảnh", "Chuyển các trang PDF thành ảnh PNG. Nhiều trang được tải trong một tệp ZIP; tệp gốc được giữ nguyên."),
        "en": ("PDF to images", "Convert PDF pages into PNG images. Multiple pages download in one ZIP file; the original stays unchanged."),
        "zh": ("PDF 转图像", "将 PDF 页面转换为 PNG 图像。多页通过一个 ZIP 文件下载，原文件保持不变。"),
    },
    "/documents/pdf-to-word": {
        "vi": ("PDF sang Word", "Chuyển phần chữ có thể bôi chọn trong PDF sang Word. Không chuyển chữ trong ảnh hoặc giữ nguyên cách dàn trang."),
        "en": ("PDF to Word", "Convert selectable PDF text into Word. Text in images and the original page layout are not converted."),
        "zh": ("PDF 转 Word", "将 PDF 中可选择的文字转换为 Word。不转换图像中的文字，也不保留原页面布局。"),
    },
}


@pytest.mark.parametrize("route", list(COPY))
@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_document_conversion_actual_first_response_has_locale_correct_metadata(route, locale):
    raw = (ROOT / "tests/fixtures/document-convert-customer-copy-reviewed.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "e162e15e4ddff0899dcf69bee7134576c7fac7a2fb35fb1857e555d1e70c6b63"
    authority = json.loads(raw)
    assert authority["base"] == BASE and len(authority["canonicalChanges"]) == 13
    assert all(row["proposalExact"] and row["schemaValid"] for row in authority["sourceAuthorities"])
    response = render_portal(route, interface_locale=locale)
    assert response.status_code == 200 and response.media_type == "text/html"
    body = response.body.decode("utf8")
    title = re.search(r"<title>(.*?)</title>", body)
    description = re.search(r'<meta name="description" content="([^"]*)">', body)
    bootstrap = re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', body)
    lang = re.search(r'<html\b[^>]*\blang="([^"]+)"', body)
    assert title is not None and description is not None and bootstrap is not None and lang is not None
    payload = json.loads(bootstrap[1])
    assert html.unescape(title[1]) == payload["title"] == COPY[route][locale][0] + " · TOAN AAS"
    assert html.unescape(description[1]) == COPY[route][locale][1]
    assert payload["path"] == route and payload["interfaceLocale"] == locale
    assert lang[1] == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert payload["apiBase"] == "/api/v1" and payload["catalogUrl"] == "/api/v1/catalog"
    assert payload["authUrl"] == "/api/v1/auth/me"


def test_document_conversion_metadata_does_not_change_other_route_first_responses():
    source = subprocess.check_output(["git", "show", BASE + ":copyfast_pages.py"], cwd=ROOT, text=True, encoding="utf8")
    module = types.ModuleType("_document_convert_pages_baseline")
    module.__file__ = str(ROOT / "copyfast_pages.py")
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    for route in ["/documents/split", "/documents/merge", "/documents/compress", "/documents/image-to-pdf", "/image/edit", "/image/history", "/image/resize", "/login"]:
        for locale in ["vi", "en", "zh"]:
            old = module.render_portal(route, interface_locale=locale)
            current = render_portal(route, interface_locale=locale)
            assert current.status_code == old.status_code
            assert current.body == old.body, (route, locale)
