import re
from pathlib import Path

from copyfast_pages import render_portal


def _get_body_tag(html_content: str) -> str:
    tags = re.findall(r"<body\b[^>]*>", html_content)
    assert len(tags) == 1, f"Expected exactly one body tag, found {len(tags)}"
    return tags[0]


def _body_classes(body_tag: str) -> list[str]:
    match = re.search(r'class="([^"]+)"', body_tag)
    assert match is not None, "Missing body class attribute"
    return match.group(1).split()


def test_dashboard_receives_stable_marker() -> None:
    html = render_portal("/dashboard").body.decode("utf-8")
    classes = _body_classes(_get_body_tag(html))

    assert classes == ["portal-body", "portal-body--dashboard-stable"]
    assert classes.count("portal-body--dashboard-stable") == 1


def test_other_routes_do_not_receive_marker() -> None:
    paths = (
        "/features",
        "/admin/jobs",
        "/login",
        "/register",
        "/video-studio/new",
        "/wallet",
    )
    for path in paths:
        html = render_portal(path).body.decode("utf-8")
        classes = _body_classes(_get_body_tag(html))

        assert "portal-body--dashboard-stable" not in classes
        if path == "/features":
            assert classes == ["portal-body", "portal-body--features"]


def test_css_contains_exact_media_query_and_no_main_workspace_marker() -> None:
    css_path = Path(__file__).resolve().parents[1] / "static" / "portal" / "portal.css"
    css_content = css_path.read_text(encoding="utf-8")
    dashboard_rule = (
        "@media (min-width: 701px) { "
        ".portal-body--dashboard-stable .portal-header { min-height: 67px; } }"
    )

    assert dashboard_rule in css_content
    for selector in (".portal-main", "#portal-main", ".portal-workspace", "#portal-workspace"):
        assert f".portal-body--dashboard-stable {selector}" not in css_content


def test_css_locked_comparators() -> None:
    css_path = Path(__file__).resolve().parents[1] / "static" / "portal" / "portal.css"
    css_content = css_path.read_text(encoding="utf-8")
    expected_feature_rule = ".portal-body--features .portal-header { min-height: 67px; }"
    expected_route_rules = (
        f"{expected_feature_rule} @media (min-width: 701px) {{ "
        ".portal-body--dashboard-stable .portal-header { min-height: 67px; } }"
    )

    assert expected_route_rules in css_content
    menu_button_block = css_content.split(".portal-menu-button {")[1].split("}")[0]
    assert "border-radius: 10px;" in menu_button_block


def test_source_does_not_touch_client_mount_and_uses_exact_normalized_dashboard() -> None:
    pages_path = Path(__file__).resolve().parents[1] / "copyfast_pages.py"
    pages_content = pages_path.read_text(encoding="utf-8")
    dashboard_conditions = re.findall(
        r'^\s*if normalized == "/dashboard":\s*$',
        pages_content,
        flags=re.MULTILINE,
    )
    assert len(dashboard_conditions) == 1

    portal_js_path = Path(__file__).resolve().parents[1] / "static" / "portal" / "portal.js"
    integration_js_path = Path(__file__).resolve().parents[1] / "static" / "portal" / "integration.js"
    assert "portal-body--dashboard-stable" not in portal_js_path.read_text(encoding="utf-8")
    assert "portal-body--dashboard-stable" not in integration_js_path.read_text(encoding="utf-8")
