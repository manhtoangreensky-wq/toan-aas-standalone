"""Exercise the actual pure shell, without app/database/provider/session imports."""
import html
import json
import re
import pytest
from copyfast_pages import render_portal

COPY = {
    "vi": ("Đổi kích thước ảnh", "Chọn ảnh đã lưu, đặt kích thước và tạo bản PNG mới. Tệp gốc được giữ nguyên."),
    "en": ("Resize images", "Choose a saved image, set its size and create a new PNG. The original stays unchanged."),
    "zh": ("调整图像尺寸", "选择已保存的图像，设置尺寸并创建新的 PNG。原文件将保持不变。"),
}


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_resize_initial_html_title_and_bootstrap_use_locale(locale):
    response = render_portal("/image/resize", interface_locale=locale)
    assert response.status_code == 200
    body = response.body.decode("utf8")
    title = html.unescape(re.search(r"<title>(.*?)</title>", body)[1])
    bootstrap = json.loads(re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', body)[1])
    assert title == bootstrap["title"] == COPY[locale][0] + " · TOAN AAS"
    assert bootstrap["path"] == "/image/resize" and bootstrap["interfaceLocale"] == locale
    assert set(bootstrap) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_resize_initial_html_description_uses_locale(locale):
    body = render_portal("/image/resize", interface_locale=locale).body.decode("utf8")
    description = html.unescape(re.search(r'<meta name="description" content="([^"]*)">', body)[1])
    assert description == COPY[locale][1]
