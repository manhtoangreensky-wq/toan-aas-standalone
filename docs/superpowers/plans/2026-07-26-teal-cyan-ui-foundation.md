# TOAN AAS Teal–Cyan UI Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce one final, tokenized teal–cyan presentation layer for the Portal shell, access pages and `/welcome` without changing business, session, route or bridge behaviour.

**Architecture:** Keep `portal.css` as the existing component catalogue and
load a small, final `portal-theme.css` immediately after it.  The final file
owns the canonical semantic tokens and scoped visual overrides, so legacy
selectors do not require risky rewrites in this slice.  `portal.js`,
`integration.js`, route handlers and browser data authority remain untouched.

**Tech Stack:** FastAPI, server-rendered HTML, vanilla CSS/JavaScript, pytest.

---

## File structure

- `templates/portal_shell.html` — load the final presentation stylesheet after
  the legacy component catalogue and before Portal scripts.
- `static/portal/portal-theme.css` — canonical tokens and visual rules for the
  signed shell, auth/public surfaces, controls, responsive behaviour and
  accessibility states.
- `tests/test_teal_cyan_ui_foundation_contracts.py` — static presentation
  contracts that make ordering, token ownership and accessibility requirements
  explicit.
- `docs/superpowers/specs/2026-07-26-teal-cyan-ui-system-design.md` — approved
  visual system and scope boundary.

### Task 1: Specify the new presentation boundary with a failing test

**Files:**

- Create: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [x] **Step 1: Write the failing test**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
THEME = ROOT / "static" / "portal" / "portal-theme.css"


def test_final_teal_cyan_theme_loads_after_the_component_catalogue() -> None:
    assert THEME.exists()
    base = SHELL.index('/static/portal/portal.css?v=__PORTAL_ASSET_VERSION__')
    theme = SHELL.index('/static/portal/portal-theme.css?v=__PORTAL_ASSET_VERSION__')
    portal = SHELL.index('/static/portal/portal.js?v=__PORTAL_ASSET_VERSION__')
    assert base < theme < portal


def test_theme_uses_semantic_teal_cyan_tokens_and_keeps_accessibility_rules() -> None:
    source = THEME.read_text(encoding="utf-8")
    for token in (
        '--portal-bg: #07141d;', '--portal-surface: #0d2330;',
        '--portal-accent: #0e9f9a;', '--portal-info: #0284c7;',
        '.portal-theme-control:focus-visible',
        '@media (prefers-reduced-motion: reduce)',
        '@media (max-width: 920px)',
        'min-height: 44px;',
    ):
        assert token in source
```

- [x] **Step 2: Run the test to verify it fails for the missing theme**

Run: `python -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py`

Expected: `FAIL` because `portal-theme.css` does not exist and the template
does not load it.

### Task 2: Load the final visual layer in the inert Portal shell

**Files:**

- Modify: `templates/portal_shell.html:10-12`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [x] **Step 1: Add the final stylesheet directly after the component catalogue**

```html
<link rel="stylesheet" href="/static/portal/portal.css?v=__PORTAL_ASSET_VERSION__">
<link rel="stylesheet" href="/static/portal/portal-theme.css?v=__PORTAL_ASSET_VERSION__">
```

Do not move the manifest, skip link, `portal-bootstrap` node or JavaScript
tags.  Do not change the `portal-i18n.js → portal.js → integration.js` order.

- [x] **Step 2: Run the new test**

Run: `python -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py`

Expected: the first contract progresses past missing shell ordering and fails
only because the stylesheet is still absent.

### Task 3: Implement the final tokenized visual layer

**Files:**

- Create: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [x] **Step 1: Add canonical tokens and shared interaction rules**

```css
/* Canonical teal–cyan Portal system. Loaded after portal.css. */
:root {
  --portal-bg: #07141d;
  --portal-bg-deep: #041018;
  --portal-surface: #0d2330;
  --portal-surface-strong: #112b39;
  --portal-surface-soft: #153544;
  --portal-border: #234555;
  --portal-border-strong: #2b8f9c;
  --portal-text: #edf8fa;
  --portal-muted: #9bb9c3;
  --portal-muted-strong: #c9e2e7;
  --portal-accent: #0e9f9a;
  --portal-accent-deep: #0b756f;
  --portal-accent-ink: #efffff;
  --portal-info: #0284c7;
}

.portal-button:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--portal-info) 68%, white);
  outline-offset: 2px;
}
```

- [x] **Step 2: Add scoped app, access and public companion rules**

The stylesheet must use the existing classes, not new JavaScript state:

```css
.portal-shell:not(.portal-shell--auth):not(.portal-shell--landing) {
  background: var(--portal-bg);
}
.portal-sidebar, .portal-header { background: #081b26; backdrop-filter: none; }
.portal-shell--auth { background: #f6fcfc; color: #06212b; }
.portal-shell--landing, .portal-landing { background: #f6fcfc; color: #06212b; }
@media (max-width: 920px) { .portal-mobile-nav { min-height: 64px; } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
```

Complete the rules with the existing `.portal-button`, `.portal-auth-*`,
`.portal-landing-*`, `.portal-sidebar`, `.portal-header` and
`.portal-mobile-nav` selectors.  Keep desktop controls at least 40px and
mobile controls at least 44px.  The auth public canvas may be light, but must
not change its data attributes, field markup, OAuth gating or Telegram flow.

- [x] **Step 3: Run the focused test and expected regression contracts**

Run:

```powershell
python -m pytest -q `
  tests/test_teal_cyan_ui_foundation_contracts.py `
  tests/test_app_first_ui_system_contracts.py `
  tests/test_login_app_ux_contracts.py `
  tests/test_auth_entrypoint_layout_contracts.py `
  tests/test_secure_access_first_run_contracts.py `
  tests/test_portal_i18n_bundle_contracts.py
```

Expected: all selected tests pass; no test is deleted or weakened to mask a
session, auth, locale, focus, mobile or public-landing invariant.

### Task 4: Record scope and verify the branch before review

**Files:**

- Create: `docs/superpowers/specs/2026-07-26-teal-cyan-ui-system-design.md`
- Modify: `docs/superpowers/plans/2026-07-26-teal-cyan-ui-foundation.md`
- Test: focused suite from Task 3

- [x] **Step 1: Confirm the specification records the actual production boundary**

The spec must state that this repository owns `app.toanaas.vn` and `/welcome`,
not the separately hosted production `toanaas.vn` landing site.

- [x] **Step 2: Run static and syntax verification**

Run:

```powershell
python -m compileall -q .
git diff --check
```

Expected: exit code `0`, with no whitespace errors or Python syntax errors.

- [x] **Step 3: Commit the focused slice**

```powershell
git add templates/portal_shell.html static/portal/portal-theme.css `
  tests/test_teal_cyan_ui_foundation_contracts.py `
  docs/superpowers/specs/2026-07-26-teal-cyan-ui-system-design.md `
  docs/superpowers/plans/2026-07-26-teal-cyan-ui-foundation.md
git commit -m "Unify portal teal cyan UI foundation"
```

## Plan self-review

- **Coverage:** the plan creates one authority for shared visual tokens;
  protects script order, access safety, responsive targets, focus, motion and
  public/signed surface separation; later slices intentionally own changed
  runtime copy and page-specific data layouts.
- **No placeholders:** every code-editing task names exact files, test intent,
  commands and expected outcome.
- **Consistency:** `portal-theme.css` is the one loaded final layer referenced
  by the test and template; CSS variables match the specification table.
