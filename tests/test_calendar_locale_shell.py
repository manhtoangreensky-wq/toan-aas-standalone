import re

import pytest

from copyfast_pages import render_portal


@pytest.mark.parametrize('locale,title', [
    ('vi', 'Lịch nội dung · TOAN AAS'),
    ('en', 'Content calendar · TOAN AAS'),
    ('zh', '内容日历 · TOAN AAS'),
])
def test_calendar_first_paint_title_uses_the_reviewed_interface_language(locale, title):
    html = render_portal('/calendar', interface_locale=locale).body.decode('utf-8')
    assert re.search(r'<title>(.*?)</title>', html).group(1) == title
    assert 'id="portal-bootstrap"' in html
