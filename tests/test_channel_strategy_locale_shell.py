import re

import pytest

from copyfast_pages import render_portal


@pytest.mark.parametrize('route', [
    '/content/channel-strategy',
    '/content/channel-strategy/11111111-1111-4111-8111-111111111111',
])
@pytest.mark.parametrize('locale,title', [
    ('vi', 'Chiến lược kênh · TOAN AAS'),
    ('en', 'Channel strategy · TOAN AAS'),
    ('zh', '频道策略 · TOAN AAS'),
])
def test_channel_strategy_first_paint_has_localized_title(route, locale, title):
    html = render_portal(route, interface_locale=locale).body.decode('utf-8')
    actual = re.search(r'<title>(.*?)</title>', html)
    assert actual is not None
    assert actual.group(1) == title
    assert 'id="portal-bootstrap"' in html
