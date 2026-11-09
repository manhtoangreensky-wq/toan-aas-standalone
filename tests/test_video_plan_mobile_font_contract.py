"""Static isolation guard for the measured Video Plan mobile field font fix.

Actual CSS-engine measurements are in the native matrix; this protects the
configuration scope without importing app/config or changing account state.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CSS_TEXT = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")


def _mobile_blocks(source: str):
    source = re.sub(r"/\*[\s\S]*?\*/", "", source)
    for match in re.finditer(r"@media\s*\(max-width:\s*620px\)\s*\{", source):
        begin = match.end()
        depth = 1
        end = begin
        while end < len(source) and depth:
            depth += (source[end] == "{") - (source[end] == "}")
            end += 1
        assert depth == 0, "Mobile media block must be balanced"
        yield source[begin:end - 1]


def test_video_plan_mobile_font_configuration_stays_editable_customer_only():
    rules = []
    for block in _mobile_blocks(CSS_TEXT):
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", block):
            if 'data-portal-action="video-plan-create"' in match.group(1):
                rules.append(match.groups())
    assert len(rules) == 1, "Exactly one scoped mobile field sizing rule is required"
    selector, declarations = rules[0]
    assert re.sub(r"\s+", "", selector) == (
        '.portal-shell[data-portal-surface="customer"]'
        'form[data-portal-action="video-plan-create"]:is(input,select,textarea)'
    )
    properties = re.findall(r"([\w-]+)\s*:\s*([^;{}]+);", declarations)
    assert properties == [("font-size", "16px")], "No buttons, target, motion or color changes"
