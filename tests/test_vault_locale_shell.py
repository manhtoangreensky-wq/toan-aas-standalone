"""Real shell HTMLResponse only; no server, authentication or file action."""
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
HERE = ROOT / "tests/fixtures"
BASE = "5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from copyfast_pages import render_portal

WORDS = {
    "vi": ("Kho tệp", "Lưu, tìm và quản lý các tệp của bạn. Xem thông tin tệp và tải lại khi cần."),
    "en": ("File library", "Save, find and manage your files. View file details and download them when needed."),
    "zh": ("文件库", "保存、查找并管理您的文件。查看文件详情，并在需要时下载。"),
}


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_vault_actual_first_response(locale):
    raw = (HERE / "vault-customer-copy-reviewed.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "2b895f84f77c8656811c4e732506926a677dda1eb6aa824f854670e127e8228b"
    authority = json.loads(raw)
    assert authority["base"] == BASE and len(authority["canonicalChanges"]) == 12
    assert all(row["schemaValid"] and row["proposalExact"] for row in authority["sourceAuthorities"])
    response = render_portal("/asset-vault", interface_locale=locale)
    assert response.status_code == 200 and response.media_type == "text/html"
    body = response.body.decode("utf8")
    title = re.search(r"<title>(.*?)</title>", body)
    description = re.search(r'<meta name="description" content="([^"]*)">', body)
    bootstrap = re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', body)
    lang = re.search(r'<html\b[^>]*\blang="([^"]+)"', body)
    assert all([title, description, bootstrap, lang])
    payload = json.loads(bootstrap[1])
    assert html.unescape(title[1]) == payload["title"] == WORDS[locale][0] + " · TOAN AAS"
    assert html.unescape(description[1]) == WORDS[locale][1]
    assert payload["path"] == "/asset-vault" and payload["interfaceLocale"] == locale
    assert lang[1] == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert (payload["apiBase"], payload["catalogUrl"], payload["authUrl"]) == ("/api/v1", "/api/v1/catalog", "/api/v1/auth/me")


def test_vault_shell_does_not_change_delivered_routes():
    source = subprocess.check_output(["git", "show", BASE + ":copyfast_pages.py"], cwd=ROOT, text=True, encoding="utf8")
    module = types.ModuleType("_vault_pages_baseline")
    module.__file__ = str(ROOT / "copyfast_pages.py")
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    for route in ["/documents/ocr", "/documents/pdf-ocr", "/documents/pdf-ocr-to-word", "/documents/pdf-to-images", "/documents/pdf-to-word", "/image/edit", "/image/history", "/image/resize", "/login"]:
        for locale in ["vi", "en", "zh"]:
            assert render_portal(route, interface_locale=locale).body == module.render_portal(route, interface_locale=locale).body
