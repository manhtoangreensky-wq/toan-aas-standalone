# TOAN AAS Dashboard Reviewed Locales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Localize the core `/dashboard` command-center chrome into reviewed
Vietnamese, English and Simplified Chinese without changing customer data or
Dashboard authority.

**Architecture:** `portal-i18n.js` owns a closed `dashboard.*` catalogue;
`portal.js` receives a tiny presentation helper only inside Dashboard render
functions. Existing data helpers retain their `safeText` treatment and
canonical read models, so locale affects words around data rather than the
data itself.

**Tech Stack:** FastAPI shell, vanilla JavaScript/CSS, Portal i18n, pytest and
Node VM browser-bundle contracts.

---

### Task 1: Fence the Dashboard catalogue with a failing runtime contract

**Files:**

- Modify: `tests/test_portal_i18n_bundle_contracts.py`
- Modify: `static/portal/portal-i18n.js`

- [x] Add a Node runtime assertion requiring a complete `dashboard.*` key set
  for `vi`, `en` and `zh`, including summary, guide, lane, action-center,
  launchpad, table and empty-state labels.
- [x] Run the focused test and confirm it fails because the catalogue is
  absent.
- [x] Add `DASHBOARD_MESSAGES` with equivalent, reviewed copy in all three
  catalogues and merge it alongside the existing Portal extension catalogues.
- [x] Rerun the focused test and confirm all three catalogues remain equal and
  non-empty.

### Task 2: Move fixed command-center copy behind reviewed keys

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `tests/test_dashboard_workspace_command_center_contracts.py`

- [x] Add a failing source contract for a Dashboard-local `dashboardText`
  helper, reviewed key use in all command-center render functions, SVG-only
  structural icons and unchanged real routes.
- [x] Run the contract and confirm it fails on current hard-coded labels.
- [x] Refactor the summary, recent cards, guide, account lane and visible
  section headings for canonical work, action center and launchpad. Keep all
  user/canonical fields passed through existing `safeText` unchanged.
- [x] Rerun the Dashboard contracts. Confirm no new fetch, persistence,
  provider, wallet, payment, job-write or delivery action was added.

### Task 3: Verify the signed presentation boundary and commit

**Files:**

- Modify: `docs/superpowers/plans/2026-07-26-dashboard-reviewed-locales.md`
- Test: focused dashboard/i18n/PWA contracts

- [x] Run:

```powershell
python -m pytest -q `
  tests/test_dashboard_workspace_command_center_contracts.py `
  tests/test_portal_i18n_bundle_contracts.py `
  tests/test_portal_safety_contracts.py `
  tests/test_interface_locale_narrow_update_and_first_paint.py `
  tests/test_teal_cyan_ui_foundation_contracts.py
python -m compileall -q .
git diff --check
```

- [x] Confirm a `zh` signed shell retains `zh-CN` metadata while no raw
  account/project data appears in shell HTML.
- [x] Commit only this Dashboard locale slice with
  `git commit -m "Localize dashboard command center"`.

### Verification recorded before commit

- Focused presentation, i18n, safety, locale-first-paint and teal-cyan
  foundation suite: `116 passed`.
- `python -m compileall -q .` and `git diff --check` completed successfully.
- The ready Dashboard uses Dashboard-local translated delivery helpers, so it
  does not leak fixed Vietnamese output/delivery labels through shared global
  helpers when the signed display locale is English or Simplified Chinese.
