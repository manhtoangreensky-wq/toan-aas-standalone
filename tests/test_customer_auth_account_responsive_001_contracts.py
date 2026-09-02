import os


def extract_balanced_body(content: str, start_index: int) -> str:
    """Return only the body owned by the first balanced CSS block."""
    brace_start = content.find("{", start_index)
    if brace_start == -1:
        raise AssertionError("Opening brace not found")

    depth = 0
    for index in range(brace_start, len(content)):
        if content[index] == "{":
            depth += 1
        elif content[index] == "}":
            depth -= 1

        if depth == 0:
            return content[brace_start + 1 : index]

    raise AssertionError("Closing brace not found")


def test_account_mobile_nav_declarations() -> None:
    css_path = os.path.join(os.path.dirname(__file__), "../static/portal/portal.css")
    with open(css_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    marker = "/* Account & Security workspace UX."
    marker_index = content.rfind(marker)
    assert marker_index != -1, "Marker not found"

    desktop_selector = ".portal-account-page .portal-settings-nav,"
    desktop_selector_index = content.find(desktop_selector, marker_index)
    assert desktop_selector_index != -1, "Desktop selector not found"
    desktop_body = extract_balanced_body(content, desktop_selector_index)
    assert "overflow-x: auto;" in desktop_body
    assert "scroll-snap-type: x mandatory;" in desktop_body

    media_query = "@media (max-width: 700px)"
    media_index = content.find(media_query, marker_index)
    assert media_index != -1, "Media query not found"
    media_body = extract_balanced_body(content, media_index)

    nav_selector_index = media_body.find(desktop_selector)
    assert nav_selector_index != -1, "Mobile nav selector not found"
    nav_body = extract_balanced_body(media_body, nav_selector_index)
    for declaration in (
        "display: grid;",
        "grid-template-columns: minmax(0, 1fr);",
        "overflow-x: visible;",
        "overscroll-behavior-x: auto;",
        "scroll-snap-type: none;",
    ):
        assert declaration in nav_body

    link_selector = ".portal-account-page .portal-settings-nav a,"
    link_selector_index = media_body.find(link_selector)
    assert link_selector_index != -1, "Mobile link selector not found"
    link_body = extract_balanced_body(media_body, link_selector_index)
    for declaration in (
        "width: 100%;",
        "min-width: 0;",
        "min-height: 44px;",
        "justify-content: flex-start;",
        "text-align: left;",
        "white-space: normal;",
        "overflow-wrap: anywhere;",
        "scroll-snap-align: none;",
    ):
        assert declaration in link_body


def test_forgot_password_touch_target() -> None:
    css_path = os.path.join(os.path.dirname(__file__), "../static/portal/portal-theme.css")
    with open(css_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    marker = "/* AUTH-LOGIN-BRAND-VIEWPORT-001 */"
    marker_index = content.rfind(marker)
    assert marker_index != -1, "Marker not found"

    media_query = "@media (max-width: 600px)"
    media_index = content.find(media_query, marker_index)
    assert media_index != -1, "Media query not found"
    media_body = extract_balanced_body(content, media_index)

    selector = ".portal-auth-page--access .portal-auth-forgot-link"
    selector_index = media_body.find(selector)
    assert selector_index != -1, "Mobile forgot link selector not found"
    selector_body = extract_balanced_body(media_body, selector_index)
    for declaration in (
        "display: inline-flex;",
        "min-height: 44px;",
        "align-items: center;",
        "padding-block: 8px;",
    ):
        assert declaration in selector_body
