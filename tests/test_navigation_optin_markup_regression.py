"""Parse early navigation opt-in markup without importing the application.

Run this isolated gate with ``python -m pytest --noconftest <this-file>``;
the repository-wide conftest imports the app for unrelated integration tests.
"""
from __future__ import annotations

import ast
from html.parser import HTMLParser
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
SHELL_TEXT = (ROOT / "templates/portal_shell.html").read_text(encoding="utf-8")
PAGES_TEXT = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
APP_TEXT = (ROOT / "app.py").read_text(encoding="utf-8")
THEME_TEXT = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")


def _fallback_markup(source: str) -> str:
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "_fallback_template")
    returns = [node for node in function.body if isinstance(node, ast.Return)]
    assert len(returns) == 1, "Fallback must have one static HTML result"
    markup = ast.literal_eval(returns[0].value)
    assert isinstance(markup, str)
    return markup


class Markup(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.styles: list[dict] = []
        self.scripts: list[dict] = []
        self.in_head = False
        self.index = 0
        self.active: dict | None = None
        self.feed(source)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        self.index += 1
        if tag == "head":
            self.in_head = True
        if tag in {"style", "script"}:
            item = {"attrs": dict(attrs), "index": self.index,
                    "head": self.in_head, "text": ""}
            (self.styles if tag == "style" else self.scripts).append(item)
            self.active = item

    def handle_endtag(self, tag: str):
        if tag in {"style", "script"}:
            self.active = None
        if tag == "head":
            self.in_head = False

    def handle_data(self, data: str):
        if self.active is not None:
            self.active["text"] += data


def _optin(document: Markup) -> dict:
    matches = [item for item in document.styles
               if "data-portal-view-transition-optin" in item["attrs"]]
    assert len(matches) == 1, "Each HTML path needs exactly one early opt-in"
    return matches[0]


def _navigation_modes(style: dict) -> tuple[str, str]:
    # This intentionally accepts only the two presentation descriptors: no
    # selectors, script URLs, imports, content hiding or extra CSS properties.
    compact = re.sub(r"\s+", "", style["text"]).lower()
    match = re.fullmatch(
        r"@view-transition\{navigation:(auto|none);?\}"
        r"@media\(prefers-reduced-motion:reduce\)\{"
        r"@view-transition\{navigation:(auto|none);?\}\}", compact,
    )
    assert match is not None, "Opt-in must contain only the approved descriptors"
    return match.group(1), match.group(2)


def _ordinary_csp(source: str) -> dict[str, list[str]]:
    function = next(node for node in ast.parse(source).body
                    if isinstance(node, ast.AsyncFunctionDef)
                    and node.name == "security_headers")
    values = [node.value for node in ast.walk(function) if isinstance(node, ast.Assign)
              and isinstance(node.value, ast.IfExp)
              and any(isinstance(target, ast.Subscript)
                      and isinstance(target.slice, ast.Constant)
                      and target.slice.value == "Content-Security-Policy"
                      for target in node.targets)]
    assert len(values) == 1, "Inspect the ordinary portal CSP assignment"
    value = values[0]
    while isinstance(value, ast.IfExp):
        value = value.orelse
    policy = ast.literal_eval(value)
    return {parts[0]: parts[1:] for segment in policy.split(";")
            if (parts := segment.strip().split())}


@pytest.fixture(params=["normal", "fallback"])
def document(request) -> Markup:
    return Markup(SHELL_TEXT if request.param == "normal"
                  else _fallback_markup(PAGES_TEXT))


def test_optin_is_present_before_synchronous_theme_bootstrap(document: Markup):
    style = _optin(document)
    themes = [script for script in document.scripts
              if script["attrs"].get("src", "").startswith("/static/portal/portal-theme.js?")]
    assert len(themes) == 1
    assert style["head"] is True and themes[0]["head"] is True
    assert style["index"] < themes[0]["index"], "Theme code must see parsed opt-in CSS"
    assert "async" not in themes[0]["attrs"] and "defer" not in themes[0]["attrs"]


def test_optin_only_enables_normal_navigation_and_disables_reduced_motion(document: Markup):
    style = _optin(document)
    assert set(style["attrs"]) == {"data-portal-view-transition-optin"}
    assert _navigation_modes(style) == ("auto", "none")


def test_bootstrap_stays_inert_and_application_scripts_stay_external(document: Markup):
    bootstraps = [script for script in document.scripts
                  if script["attrs"].get("id") == "portal-bootstrap"]
    assert len(bootstraps) == 1
    assert bootstraps[0]["attrs"].get("type") == "application/json"
    assert bootstraps[0]["text"].strip() == "__PORTAL_BOOTSTRAP__"
    for script in document.scripts:
        if script is bootstraps[0]:
            assert "src" not in script["attrs"]
        else:
            assert script["attrs"].get("src", "").startswith("/static/portal/")
            assert "?v=__PORTAL_ASSET_VERSION__" in script["attrs"]["src"]
            assert not script["text"].strip(), "No inline executable JavaScript"
    sources = [script["attrs"].get("src", "").split("?")[0] for script in document.scripts]
    assert sources.index("/static/portal/portal-motion.js") < sources.index("/static/portal/portal.js")
    assert sources.index("/static/portal/portal.js") < sources.index("/static/portal/integration.js")


def test_existing_csp_allows_the_inline_style_but_not_inline_scripts():
    policy = _ordinary_csp(APP_TEXT)
    assert "'unsafe-inline'" in policy["style-src"]
    assert policy["script-src"] == ["'self'"]


def test_early_policy_matches_the_existing_stylesheet_motion_preferences():
    default = re.search(r"@view-transition\s*\{\s*navigation:\s*(auto|none);", THEME_TEXT)
    reduced = re.search(
        r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*"
        r"@view-transition\s*\{\s*navigation:\s*(auto|none);", THEME_TEXT,
    )
    assert default is not None and reduced is not None
    expected = (default.group(1), reduced.group(1))
    assert expected == ("auto", "none")
    assert _navigation_modes(_optin(Markup(SHELL_TEXT))) == expected
    assert _navigation_modes(_optin(Markup(_fallback_markup(PAGES_TEXT)))) == expected
