# Global UI Shell Brand Mark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the temporary text-only `TA` stamp with one consistent, accessible SVG mark across the customer workspace, Admin ERP, mobile shell, access pages, and public companion page.

**Architecture:** `static/portal/portal.js` owns a closed, presentation-only SVG helper; it accepts no server or browser input and is reused by every existing brand-mark location. `static/portal/portal-theme.css` supplies only semantic-token styling for that helper, preserving the existing routing, signed-session, locale, PWA, Bridge, wallet, PayOS, provider, and job boundaries.

**Tech Stack:** FastAPI static portal, vanilla browser JavaScript, semantic CSS tokens, pytest static-contract tests.

---

### Task 1: Lock the brand-mark rendering contract

**Files:**

- Create: `tests/test_global_ui_shell_contracts.py`
- Read: `static/portal/portal.js`
- Read: `static/portal/portal-theme.css`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS = ROOT / "static" / "portal" / "portal.js"
PORTAL_THEME = ROOT / "static" / "portal" / "portal-theme.css"


def test_brand_mark_is_a_closed_vector_used_by_every_portal_shell() -> None:
    source = PORTAL_JS.read_text(encoding="utf-8")

    assert "function portalBrandMark()" in source
    assert 'class="portal-brand-mark-symbol"' in source
    assert 'aria-hidden="true" focusable="false"' in source
    assert source.count("portalBrandMark()") >= 5
    assert 'class="portal-brand-mark" aria-hidden="true">TA' not in source


def test_brand_mark_uses_the_shared_semantic_theme_layer() -> None:
    theme = PORTAL_THEME.read_text(encoding="utf-8")

    assert ".portal-brand-mark-symbol" in theme
    assert "stroke: currentColor" in theme
    assert "fill: none" in theme
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_global_ui_shell_contracts.py`

Expected: FAIL because `portalBrandMark()` and `.portal-brand-mark-symbol` do not yet exist.

### Task 2: Add the closed shared vector helper

**Files:**

- Modify: `static/portal/portal.js` near `portalIcon()` and the four current `portal-brand-mark` render sites

- [ ] **Step 1: Implement the minimal closed helper**

```javascript
function portalBrandMark() {
  return `<svg class="portal-brand-mark-symbol" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
    <path d="m16 3 11 6.3v13.4L16 29 5 22.7V9.3z"/>
    <path d="m9.5 12.9 6.5 3.7 6.5-3.7M16 16.6V24"/>
    <path d="m9.5 19.1 6.5 3.7 6.5-3.7"/>
  </svg>`;
}
```

- [ ] **Step 2: Replace each text-only mark**

Use `${portalBrandMark()}` inside the existing brand-mark spans in `renderSidebar`, `renderAccessPage`, the public landing navigation, and the public landing footer. Keep all existing `aria-hidden`, titles, links, labels, locale routes, and visible `TOAN AAS` copy unchanged.

- [ ] **Step 3: Run the focused test to verify it passes**

Run: `python -m pytest -q tests/test_global_ui_shell_contracts.py`

Expected: PASS.

### Task 3: Style the shared mark without adding a second visual language

**Files:**

- Modify: `static/portal/portal-theme.css` after shared shell token overrides

- [ ] **Step 1: Add semantic SVG geometry rules**

```css
.portal-brand-mark { overflow: hidden; }

.portal-brand-mark-symbol {
  display: block;
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.9;
}
```

- [ ] **Step 2: Keep small-screen geometry proportional**

Use the same symbol class with existing 36–42px mark containers; do not add motion, browser state, new colors, gradients, local storage, requests, or route-specific badges.

- [ ] **Step 3: Run UI regression tests**

Run: `python -m pytest -q tests/test_global_ui_shell_contracts.py tests/test_portal_motion_foundation_contracts.py tests/test_app_first_ui_system_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_portal_navigation_ux_contracts.py tests/test_portal_i18n_bundle_contracts.py`

Expected: PASS with existing deprecation warning only.

### Task 4: Visual and syntax verification

**Files:**

- Verify: `static/portal/portal.js`
- Verify: `static/portal/portal-theme.css`
- Verify: local `/login`, `/dashboard`, and a 375px dashboard preview

- [ ] **Step 1: Check JavaScript and whitespace**

Run: `node --check static/portal/portal.js` and `git diff --check`

Expected: both exit 0.

- [ ] **Step 2: Verify rendered surfaces**

Use the in-app browser to inspect `/login` and a signed local `/dashboard` at desktop and 375px. Confirm the mark is an inline SVG, visible copy remains unchanged, no horizontal overflow appears at 375px, the labelled mobile dock remains fixed, and reduced motion leaves the UI usable.

- [ ] **Step 3: Commit**

```powershell
git add static/portal/portal.js static/portal/portal-theme.css tests/test_global_ui_shell_contracts.py docs/superpowers/plans/2026-08-01-global-ui-shell-brand-mark.md
git commit -m "feat: unify portal brand mark"
```
