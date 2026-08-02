# Aura ERP Data Surfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make existing Admin ERP tables easier to scan while preserving only source-backed data and authority boundaries.

**Architecture:** `portal.js` gains a generic presentation-only Admin table toolbar and an explicit numeric-display guard. It consumes the existing admin response only; no filter, storage, URL state, API or adapter changes are introduced. `portal-i18n.js` owns fixed toolbar chrome and `portal-theme.css` gives the surface token-driven responsive presentation. A focused Python/Node contract test proves the truthful data boundary, numeric behavior, ticket state label and semantic CSS.

**Tech Stack:** Vanilla JavaScript, CSS custom properties, existing Portal shell, Python `pytest`, Node syntax/harness checks.

---

### Task 1: Add the failing Admin data-surface contract

**Files:**
- Create: `tests/test_aura_erp_data_surfaces_contracts.py`

- [x] **Step 1: Write the failing test**

Create a test module that reads `portal.js`, `portal-theme.css` and
`portal-i18n.js`. It must require a generic `renderAdminDataSurface(module,
data, content)` with a named `portal-admin-data-surface`, source-backed count,
textual badge and no `api(`, `fetch(`, `dispatchAction(`, `merge(`, storage or
URL query call. It must require Audit to retain its early return.

Use a minimal Node harness against new `adminNumericValue`/`adminNumber`
functions (with a local `localizedNumber` stub) and require:

```python
assert payload == {
    "zero": "0 đ",
    "null": "— đ",
    "blank": "— đ",
    "text": "— đ",
}
```

The test must require the generic Tickets renderer to call
`ticketStatusCell(item)`, three reviewed `adminDataSurface.*` locales, and a
final scoped CSS block that has only semantic Aura tokens, retains the table
scroll wrapper, and gives `failed_no_charge` the shared danger treatment.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m pytest -q tests/test_aura_erp_data_surfaces_contracts.py
```

Expected: fail because the table toolbar/numeric guard/catalog/style do not
exist yet.

### Task 2: Implement truthful Admin table chrome

**Files:**
- Modify: `static/portal/portal.js:24466-24656`
- Modify: `static/portal/portal-i18n.js:2872-3599`

- [x] **Step 1: Add exact numeric handling**

Add `adminNumericValue(value)` before `adminNumber`. Accept finite numbers or
non-empty finite numeric strings; return `null` for `null`, `undefined`,
blank and malformed values. Change `adminNumber` to render a true zero through
the existing locale formatter and render `—` for `null`.

- [x] **Step 2: Add presentation-only data surface markup**

Add `renderAdminDataSurface(module, data, content)`. It may derive only:
`Array.isArray(data.items)`, `data.items.length`, and
`data.compatibility_guarded`. It returns a concise count/scope/status toolbar
and the supplied existing content. It must have no new input, button,
`data-portal-action`, filter/search, fetch/bridge/request/storage call or URL
mutation.

- [x] **Step 3: Route generic tables through the surface**

Within `renderAdminDataTable`, keep Audit Explorer unchanged. Wrap the current
users/payments/jobs/providers/tickets/fallback return content with a single
`surface(content)` closure. Preserve all current notices, columns, badges,
empty state copy, `renderDataTableWrap` and row escaping. The ticket table
uses `ticketStatusCell(item)` so a canonical `closed` ticket keeps its text
label beside its visual state.

- [x] **Step 4: Add reviewed locale entries**

Add Vietnamese, English and Simplified Chinese entries for the table heading,
returned-row count, server-read scope, guarded scope and unavailable scope.
Merge them into the existing local presentation catalog; do not translate
values returned by the server.

- [x] **Step 5: Run the focused test and verify GREEN**

Run the Task 1 command. Expected: pass, including the Node numeric harness.

### Task 3: Apply Aura responsive styling

**Files:**
- Modify: `static/portal/portal-theme.css` (append a final scoped Aura ERP data-surface layer)
- Test: `tests/test_aura_erp_data_surfaces_contracts.py`

- [x] **Step 1: Use semantic surface, type and geometry tokens**

Create a scoped final layer for toolbar copy, count, scope and table wrapper.
Use `--portal-space-*`, `--portal-radius-md`, `--portal-elevation-*`,
`--portal-surface-*`, `--portal-border`, `--portal-ink`, `--portal-muted`,
`--portal-context` and `--portal-danger`; add no raw hex, raw rgba or
page-local paint/shadow.

- [x] **Step 2: Keep the table responsive without changing its meaning**

Default to a stacked toolbar and use the existing `@media (min-width: 921px)`
breakpoint for the desktop split. Preserve `max-width: 100%` and horizontal
scrolling only inside `.portal-data-table-wrap`; never hide columns or turn
record tables into fake cards. Add `failed_no_charge` to the shared Admin
danger badge selector.

- [x] **Step 3: Run the focused test again**

Run the Task 1 command. Expected: pass with the CSS assertions.

### Task 4: Verify critical behavior and review

**Files:** No additional files.

- [x] **Step 1: Static and targeted verification**

```powershell
python -m py_compile tests/test_aura_erp_data_surfaces_contracts.py
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
python -m pytest -q tests/test_aura_erp_data_surfaces_contracts.py tests/test_product_harmony_ui_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_portal_i18n_bundle_contracts.py
git diff --check
```

- [x] **Step 2: Run local visual QA**

Use the built-in browser against a local, mock-only FastAPI session. Inspect
the Admin table surface at desktop and 375px in light/dark modes. Confirm a
known zero is visible, an unavailable source is not displayed as a zero, the
table scroll region remains keyboard-visible, and there is no console error or
page-level horizontal overflow.

- [x] **Step 3: Independent spec and quality review**

Run a spec-compliance review followed by a code-quality review. Address every
P0/P1 issue and rerun the focused checks after any change.

- [x] **Step 4: Commit and prepare the sequential PR**

```powershell
git add static/portal/portal.js static/portal/portal-i18n.js static/portal/portal-theme.css tests/test_aura_erp_data_surfaces_contracts.py docs/superpowers/specs/2026-08-02-aura-erp-data-surfaces-design.md docs/superpowers/plans/2026-08-02-aura-erp-data-surfaces.md
git commit -m "Improve Aura ERP data surfaces"
```

Create one PR from `feature/p0-webapp-aura-erp-data-surfaces`, wait for CI,
then merge with a merge commit before the next sequential UI/core slice.
