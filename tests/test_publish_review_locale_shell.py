import re

import pytest

from copyfast_pages import render_portal


@pytest.mark.parametrize('locale,title', [
    ('vi', 'Gói rà soát trước khi đăng · TOAN AAS'),
    ('en', 'Pre-publish review pack · TOAN AAS'),
    ('zh', '发布前审核包 · TOAN AAS'),
])
def test_publish_review_first_paint_title_uses_the_interface_language(locale, title):
    html = render_portal('/content/publish-review', interface_locale=locale).body.decode('utf-8')
    assert re.search(r'<title>(.*?)</title>', html).group(1) == title
    assert 'id="portal-bootstrap"' in html
