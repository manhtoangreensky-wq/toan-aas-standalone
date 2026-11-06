"""The server's first paint must identify Publishing in the chosen language."""
import re

import pytest

from copyfast_pages import render_portal


@pytest.mark.parametrize("locale,title", [
    ("vi", "Đăng bài tự động · TOAN AAS"),
    ("en", "AutoPost Hub · TOAN AAS"),
    ("zh", "自动发布中心 · TOAN AAS"),
])
def test_publishing_first_paint_title_follows_interface_language(locale, title):
    html = render_portal("/publishing", interface_locale=locale).body.decode("utf-8")
    actual = re.search(r"<title>(.*?)</title>", html)
    assert actual is not None
    assert actual.group(1) == title
    assert 'id="portal-bootstrap"' in html
