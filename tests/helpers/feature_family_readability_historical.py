"""Finite four-rule CSS inverse for historical QA, never application code."""
FILE = "static/portal/portal-theme.css"
FAIL = "Unreviewed feature-family readability"
SCOPE = '[data-portal-main][data-portal-presentation-route="default"] > .portal-page:has(> .portal-feature-jumps)'
MARKER = "/* Keep family-directory text readable without changing surfaces or motion. */"
SELECTORS = [
    'html:not([data-portal-theme="dark"]) ' + SCOPE + ' > .portal-feature-jumps a.portal-feature-jump:is(:hover, :focus-visible)',
    'html[data-portal-theme="dark"] ' + SCOPE + ' > .portal-feature-jumps .portal-feature-jump--current',
    'html:not([data-portal-theme="dark"]) ' + SCOPE + ' > .portal-feature-catalog > .portal-empty p',
    'html:not([data-portal-theme="dark"]) ' + SCOPE + ' > .portal-hero .portal-eyebrow',
]
ADDITION = "\n" + MARKER + "\n" + "\n".join(selector + " {\n  color: var(--portal-text);\n}" for selector in SELECTORS) + "\n"
ANCHOR = "/* Clean end-user catalog cards: hide technical engine, boundary and readiness labels */\n.portal-module-card-signals,\n.portal-boundary-label,\n.portal-engine-label,\n.portal-readiness-label {\n  display: none !important;\n}\n\n"


def feature_family_readability_historical_source(source: str, target: str) -> str:
    assert isinstance(source, str), FAIL
    if target != FILE or (MARKER not in source and SCOPE not in source):
        return source
    assert source.count(MARKER) == 1, FAIL
    assert source.count(SCOPE) == 4, FAIL
    assert all(source.count(selector) == 1 for selector in SELECTORS), FAIL
    assert source.count(ANCHOR) == 1, FAIL
    assert source.count(ADDITION) == 1, FAIL
    assert source.count(ANCHOR + ADDITION) == 1, FAIL
    return source.replace(ANCHOR + ADDITION, ANCHOR, 1)
