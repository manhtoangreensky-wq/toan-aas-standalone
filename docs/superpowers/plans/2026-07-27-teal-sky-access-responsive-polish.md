# Teal–Sky Access Responsive Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the approved teal–sky access screen visually balanced at tablet widths and usable at a 320px mobile viewport without changing authentication behavior.

**Architecture:** This is a CSS-only layout correction in the final teal–sky semantic layer. The access shell remains two columns only when its 420px form rail, readable intro and gutter fit together; otherwise it reuses the existing one-column access state. A narrow-screen header rule keeps all three locale choices discoverable and preserves the existing 44px targets.

**Tech Stack:** Flask-rendered portal, vanilla JavaScript renderer, CSS, pytest static contract tests.

---

### Task 1: Lock the responsive contract before changing CSS

**Files:**
- Modify: `tests/test_teal_sky_product_redesign_contracts.py`
- Verify: `static/portal/portal-theme.css`

- [ ] **Step 1: Write the failing tablet breakpoint assertion**

```python
assert '@media (min-width: 1081px)' in redesign
assert '@media (max-width: 1080px)' in redesign
assert '@media (min-width: 981px)' not in redesign
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest -q tests/test_teal_sky_product_redesign_contracts.py`

Expected: the test fails because the committed theme still begins the two-column rail at 981px.

- [ ] **Step 3: Write the failing 320px header assertion**

```python
assert '@media (max-width: 380px)' in redesign
assert '.portal-auth-page--access .portal-auth-brand > span:last-child {' in redesign
assert 'clip-path: inset(50%);' in redesign
assert '.portal-auth-page--access .portal-auth-header { gap: 6px; }' in redesign
```

- [ ] **Step 4: Run the focused test and verify RED**

Run: `python -m pytest -q tests/test_teal_sky_product_redesign_contracts.py`

Expected: the new narrow-header assertion fails because this exception has not been implemented.

### Task 2: Implement the minimal responsive correction

**Files:**
- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_sky_product_redesign_contracts.py`

- [ ] **Step 1: Defer the final two-column access rail to 1081px**

Change the final semantic layer's `@media (min-width: 981px)` to `@media (min-width: 1081px)` and change its paired fallback from `@media (max-width: 980px)` to `@media (max-width: 1080px)`. Keep the existing 560px single-column main width, intro/card grid areas and hidden context card exactly as they are.

- [ ] **Step 2: Add the narrow-header exception**

At `@media (max-width: 380px)`, reduce only the header gap to 6px and visually hide the second span of the header brand with the standard clipped accessible-text pattern. Do not shrink or remove the 44px locale/back targets, do not remove a locale option, and do not alter JavaScript, route links, session or provider behavior.

- [ ] **Step 3: Run focused tests and verify GREEN**

Run: `python -m pytest -q tests/test_teal_sky_product_redesign_contracts.py tests/test_login_app_ux_contracts.py`

Expected: all tests pass.

- [ ] **Step 4: Run scope and whitespace checks**

Run: `git diff --check` and `git diff -- static/portal/portal-theme.css tests/test_teal_sky_product_redesign_contracts.py`

Expected: only the CSS breakpoint/header exception and its contract are changed.

- [ ] **Step 5: Commit**

```bash
git add static/portal/portal-theme.css tests/test_teal_sky_product_redesign_contracts.py docs/superpowers/plans/2026-07-27-teal-sky-access-responsive-polish.md
git commit -m "fix: balance teal sky access responsiveness"
```

### Task 3: Rendered quality gate and handoff

**Files:**
- Verify: `static/portal/portal-theme.css`

- [ ] **Step 1: Verify the entry flow**

Check `/login` at a desktop viewport and a narrow mobile viewport. Confirm the page has meaningful content, no error overlay, no relevant console error, all three locale choices remain visible, and the Desktop rail does not appear below 1081px.

- [ ] **Step 2: Record the visual decision**

Confirm the following five points: teal–sky tokens remain unchanged, title/intro does not crowd the form at tablet width, form controls retain their height, locale/back targets retain 44px touch size, and the header does not horizontally overflow at 320px.

## Self-review

- Scope is limited to access-layout CSS and its static contract; no auth, Bot, PayOS, provider, session or localized copy changes are in scope.
- The two changed breakpoints form a contiguous boundary: one-column through 1080px, two columns from 1081px.
- The narrow exception retains all interaction targets and visually removes only redundant brand text while keeping its accessible name at the smallest size.
