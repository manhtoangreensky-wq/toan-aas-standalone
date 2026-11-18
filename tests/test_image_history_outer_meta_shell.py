"""Actual copyfast_pages HTMLResponse only; no app/server/DB/ENV/auth/provider import."""
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "tests" / "fixtures" / "image-history-outer-meta-reviewed.json"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from copyfast_pages import render_portal

COPY = {
    "vi": ("Lịch sử ảnh", "Xem lại các lần chỉnh ảnh và tải ảnh đã hoàn tất."),
    "en": ("Image history", "Review your image edits and download completed images."),
    "zh": ("图像记录", "查看您的图像编辑记录并下载已完成的图像。"),
}


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_history_actual_first_html_response_metadata_and_bootstrap(locale):
    raw = AUTHORITY.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "6ecd6c9c47a0c24c0f7d059e28034f112019e4bd54f066437a063db4b27eca54"
    authority = json.loads(raw)
    assert authority["review"]["schemaValid"] is True and authority["review"]["proposalExact"] is True
    assert authority["review"]["conversation"] == "98527f67-e77f-47a1-95aa-521c06aa2c58"
    proposal = authority["proposal"]
    assert proposal["specId"] == "IMAGE-HISTORY-OUTER-META-20261119" and proposal["revision"] == "R1"
    assert len(proposal["changes"]) == 5 and all(row["count"] == 1 for row in proposal["changes"])
    assert {row["file"] for row in proposal["changes"]} == {
        "copyfast_pages.py", "static/portal/portal.js", "static/portal/portal-i18n.js"}
    response = render_portal("/image/history", interface_locale=locale)
    assert response.status_code == 200 and response.media_type == "text/html"
    body = response.body.decode("utf8")
    title = re.search(r"<title>(.*?)</title>", body)
    description = re.search(r'<meta name="description" content="([^"]*)">', body)
    bootstrap = re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', body)
    language = re.search(r'<html\b[^>]*\blang="([^"]+)"', body)
    assert title is not None and description is not None and bootstrap is not None and language is not None
    payload = json.loads(bootstrap[1])
    assert html.unescape(title[1]) == payload["title"] == COPY[locale][0] + " · TOAN AAS"
    assert html.unescape(description[1]) == COPY[locale][1]
    assert payload["path"] == "/image/history" and payload["interfaceLocale"] == locale
    assert language[1] == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert payload["apiBase"] == "/api/v1" and payload["catalogUrl"] == "/api/v1/catalog"
    assert payload["authUrl"] == "/api/v1/auth/me"
