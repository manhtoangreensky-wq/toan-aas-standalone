"""Pure first-paint shell contracts; no client, session, network or provider calls."""
import json
from pathlib import Path
import re

import pytest
from fastapi import HTTPException

from copyfast_pages import render_portal

COPY = json.loads((Path(__file__).parent / "fixtures" / "chat-page-meta-reviewed.json").read_text(encoding="utf-8"))
DETAIL = "/chat/11111111-1111-4111-8111-111111111111"


def _shell(route, locale):
    response = render_portal(route, interface_locale=locale)
    assert response.status_code == 200
    html = response.body.decode("utf-8")
    title = re.search(r"<title>(.*?)</title>", html)
    bootstrap = re.search(r'<script id="portal-bootstrap" type="application/json">([\s\S]*?)</script>', html)
    lang = re.search(r'<html\b[^>]*\blang="([^"]+)"', html)
    assert title is not None and bootstrap is not None and lang is not None
    return title.group(1), json.loads(bootstrap.group(1)), lang.group(1), html


@pytest.mark.parametrize("route", ["/chat", DETAIL])
@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_chat_first_paint_uses_reviewed_title_and_allowlisted_locale(route, locale):
    title, payload, lang, html = _shell(route, locale)
    expected = COPY[locale]["chatPageMetaUiTitle"] + " · TOAN AAS"
    assert title == expected
    assert payload["title"] == expected
    assert payload["path"] == route and payload["interfaceLocale"] == locale
    assert lang == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    assert set(payload) == {"path", "title", "interfaceLocale", "apiBase", "catalogUrl", "authUrl", "buildId"}
    assert payload["apiBase"] == "/api/v1" and payload["authUrl"] == "/api/v1/auth/me"
    assert payload["catalogUrl"] == "/api/v1/catalog"
    assert 'id="portal-bootstrap"' in html


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_chat_shell_compatibility_sentinels_keep_actual_legacy_behavior(locale):
    # /chat/new is allowed as a compatibility shell, not a UUID detail.
    title, payload, lang, _ = _shell("/chat/new", locale)
    assert title == {"vi": "TOAN AAS Workspace", "en": "TOAN AAS Workspace", "zh": "TOAN AAS 工作台"}[locale]
    assert payload["title"] == title and payload["path"] == "/chat/new"
    assert lang == {"vi": "vi", "en": "en", "zh": "zh-CN"}[locale]
    # Invalid IDs remain rejected by the actual existing route policy.
    for route in ["/chat/not-a-uuid", "/chat/00000000-0000-0000-0000-000000000000"]:
        with pytest.raises(HTTPException) as error:
            render_portal(route, interface_locale=locale)
        assert error.value.status_code == 404
    title, payload, _, _ = _shell("/dashboard", locale)
    assert title == {"vi": "Tổng quan · TOAN AAS", "en": "Overview · TOAN AAS", "zh": "概览 · TOAN AAS"}[locale]
    assert payload["title"] == title and payload["path"] == "/dashboard"
