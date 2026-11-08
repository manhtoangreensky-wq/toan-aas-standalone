"""First-paint locale checks through the real HTML response, without app startup."""

import html
import re

import pytest

from copyfast_pages import render_portal


ROUTES = (
    "/media-workspace",
    "/media-workspace/new",
    "/audio-hub",
    "/audio-hub/new",
    "/image-hub",
    "/image-hub/new",
    "/campaigns",
    "/media-workspace/44444444-4444-4444-8444-444444444444",
    "/audio-hub/44444444-4444-4444-8444-444444444444",
    "/image-hub/44444444-4444-4444-8444-444444444444",
    "/media-workspace/music-prompt-composer",
    "/media-workspace/music-directions",
    "/media-workspace/sfx-cue-sheet",
)
GENERIC_ENGLISH = re.compile(
    r"\b(?:Audio|Library|Briefing|Brief|Workspace|Collection|Hub|Image|Direction|Operations)\b",
    re.IGNORECASE,
)
VIETNAMESE_LETTER = re.compile(r"[À-ỹĐđ]")


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("locale", ("vi", "en", "zh"))
def test_library_first_paint_title_uses_requested_language(route, locale):
    response = render_portal(route, interface_locale=locale)
    match = re.search(r"<title>(.*?)</title>", response.body.decode("utf-8"), re.S)
    assert match, "The actual HTML response must have a document title"
    title = html.unescape(match.group(1))
    assert "TOAN AAS" in title, title
    assert title not in {"TOAN AAS Workspace", "TOAN AAS 工作台"}, (
        f"{route} must have a route-specific title, not the generic shell fallback: {title}"
    )
    if locale == "vi":
        assert not GENERIC_ENGLISH.search(title), title
    elif locale == "en":
        assert not VIETNAMESE_LETTER.search(title), title
    else:
        assert re.search(r"[\u4e00-\u9fff]", title), title
        assert not GENERIC_ENGLISH.search(title), title
        assert not VIETNAMESE_LETTER.search(title), title
