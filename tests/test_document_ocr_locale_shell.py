"""Actual first HTMLResponse; no app/server/auth/provider or OCR execution."""
from pathlib import Path
import hashlib
import html
import json
import re
import subprocess
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = "8ba0d0452f86dcc3d72e5087351134902eb4e659"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from copyfast_pages import render_portal

COPY = {
    "/documents/ocr": {
        "vi": ("Đọc chữ từ ảnh", "Đọc chữ trong ảnh đã lưu và tải về tệp văn bản. Ảnh gốc được giữ nguyên."),
        "en": ("Read text from images", "Read text in a saved image and download a text file. The original image stays unchanged."),
        "zh": ("识别图像文字", "识别已保存图像中的文字并下载文本文件。原图像保持不变。"),
    },
    "/documents/pdf-ocr": {
        "vi": ("Đọc chữ từ PDF", "Đọc chữ trong PDF đã lưu và tải về tệp văn bản. Tệp gốc được giữ nguyên."),
        "en": ("Read text from PDF", "Read text in a saved PDF and download a text file. The original stays unchanged."),
        "zh": ("识别 PDF 文字", "识别已保存 PDF 中的文字并下载文本文件。原文件保持不变。"),
    },
    "/documents/pdf-ocr-to-word": {
        "vi": ("PDF quét sang Word", "Đọc chữ trong PDF quét để tạo tài liệu Word. Không giữ hình ảnh, bảng, phông chữ hay cách dàn trang."),
        "en": ("Scanned PDF to Word", "Read text in a scanned PDF to create a Word document. Images, tables, fonts and page layout are not retained."),
        "zh": ("扫描版 PDF 转 Word", "识别扫描版 PDF 中的文字并生成 Word 文档。不保留图像、表格、字体或页面布局。"),
    },
}


@pytest.mark.parametrize("route", list(COPY))
@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_ocr_actual_first_response_metadata_and_bootstrap(route, locale):
    raw = (ROOT / "tests/fixtures/document-ocr-customer-copy-reviewed.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "2784e5ec2bf31f4921f4d39fd495175dbb9871f860947d1c9b363218a453839f"
    authority = json.loads(raw)
    assert authority["base"] == BASE and len(authority["canonicalChanges"]) == 19
    assert all(row["schemaValid"] and row["proposalExact"] for row in authority["sourceAuthorities"])
    response = render_portal(route, interface_locale=locale)
    assert response.status_code == 200 and response.media_type == "text/html"
    body = response.body.decode("utf8")
    title = re.search(r"<title>(.*?)</title>", body)
    description = re.search(r'<meta name="description" content="([^"]*)">', body)
    bootstrap = re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', body)
    lang = re.search(r'<html\b[^>]*\blang="([^"]+)"', body)
    assert all([title, description, bootstrap, lang])
    payload = json.loads(bootstrap[1])
    assert html.unescape(title[1]) == payload["title"] == COPY[route][locale][0] + " · TOAN AAS"
    assert html.unescape(description[1]) == COPY[route][locale][1]
    assert payload["path"] == route and payload["interfaceLocale"] == locale
    assert lang[1] == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert (payload["apiBase"], payload["catalogUrl"], payload["authUrl"]) == ("/api/v1", "/api/v1/catalog", "/api/v1/auth/me")


def test_ocr_first_response_does_not_change_previously_delivered_route_html():
    source = subprocess.check_output(["git", "show", BASE + ":copyfast_pages.py"], cwd=ROOT, text=True, encoding="utf8")
    module = types.ModuleType("_ocr_pages_baseline")
    module.__file__ = str(ROOT / "copyfast_pages.py")
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    for route in ["/documents/pdf-to-images", "/documents/pdf-to-word", "/documents/image-to-pdf", "/documents/compress", "/documents/split", "/image/edit", "/image/history", "/image/resize", "/login"]:
        for locale in ["vi", "en", "zh"]:
            assert render_portal(route, interface_locale=locale).body == module.render_portal(route, interface_locale=locale).body
