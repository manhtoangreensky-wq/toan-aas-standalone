# Finance Workspace Locale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Present the existing Web-owned Finance Operations Planning workspace in reviewed Vietnamese, English and Simplified Chinese without changing finance data, authority or workflow behavior.

**Architecture:** Add a closed `financePlanning.*` presentation namespace to the existing browser locale catalog. A small Portal helper maps fixed chrome and known lifecycle tokens through `uiText`, while `localizedNumber` replaces the hard-coded `vi-VN` display formatter. Server-provided rows and labels remain escaped data and never become translation inputs.

**Tech Stack:** Browser-native JavaScript, the existing `TOANAASI18n` catalog, pytest static contracts, Node bundle runtime contract.

---

### Task 1: Establish the red localization and boundary contracts

**Files:**
- Modify: `tests/test_finance_planning_portal_contracts.py`
- Modify: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Add a Finance Planning renderer localization contract.**

Add a test that obtains the source of `financePlanningMoney`, `financePlanningStateLabel`, `financePlanningStateActions`, `financePlanningPeriodControl`, `financePlanningPagination`, `financePlanningLiveStatus`, and `renderAdminFinancePlanning`, then requires the helper and existing defensive presentation utilities:

```python
assert 'function financePlanningText(key, fallback, params)' in portal
assert 'uiText(`financePlanning.${key}`, fallback, params)' in portal
assert 'localizedNumber(amount)' in money
assert 'new Intl.NumberFormat("vi-VN"' not in money
for forbidden in ("fetch(", "/internal/", "localStorage", "sessionStorage", "translate("):
    assert forbidden not in renderer
```

Require the renderer to preserve escaped data boundaries for category, vendor, purpose, period, revision and row values via `safeText`, rather than passing them to `financePlanningText`.

- [ ] **Step 2: Add a red runtime catalog contract.**

Extend `_node_i18n_snapshot` with the exact keys below and assert that every reviewed locale resolves a non-empty string:

```python
finance_keys = [
    "financePlanning.currency", "financePlanning.state.active",
    "financePlanning.state.archived", "financePlanning.state.draft",
    "financePlanning.state.review", "financePlanning.state.approved",
    "financePlanning.state.guarded", "financePlanning.transition.none",
    "financePlanning.period.label", "financePlanning.period.view",
    "financePlanning.pagination.previous", "financePlanning.pagination.next",
    "financePlanning.status.guarded", "financePlanning.status.loading",
    "financePlanning.status.ready", "financePlanning.status.failed",
    "financePlanning.guard.retry", "financePlanning.guard.back",
    "financePlanning.metrics.activeBudget", "financePlanning.metrics.planned",
    "financePlanning.metrics.remaining", "financePlanning.metrics.review",
    "financePlanning.budget.title", "financePlanning.cost.title",
]
```

Also assert `api.formatNumber(1234567, "en")` and `api.formatNumber(1234567, "zh")` are used by a Finance Planning localized money helper through a narrow Node source/runtime assertion. Do not mount the FastAPI app or import Bot code.

- [ ] **Step 3: Run the red contracts.**

Run:

```powershell
$py="$env:TEMP\toanaas-webapp-py311-pinned-20260729\Scripts\python.exe"
& $py -m pytest -q tests/test_finance_planning_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py
```

Expected: the new locale assertions fail because `financePlanning.*` messages and the Portal helper do not exist; existing tests must still collect without importing `bot.py`.

### Task 2: Add equal reviewed locale catalog coverage

**Files:**
- Modify: `static/portal/portal-i18n.js`

- [ ] **Step 1: Add the same `financePlanning.*` key set to `vi`, `en`, and `zh`.**

Use fixed interface copy only. Include the state labels, currency token, period controls, pagination, guarded/loading/ready/failed messages, confirmation template, metric labels/notes, planning/budget/cost form labels, empty states and the explicit boundary notice that planning does not create payment, ledger, PayOS, provider or Bot actions.

The status and confirmation templates must use bounded interpolation names only:

```javascript
"financePlanning.status.ready": "Loaded {period}: {budgets} budgets and {costs} cost plans.",
"financePlanning.transition.confirm": "Move {noun} to ‘{state}’? This changes only the Web planning lifecycle; it creates no payment, ledger, or PayOS action.",
"financePlanning.pagination.status": "Showing {start}–{end} / {total} {label}.",
```

Vietnamese and Simplified Chinese must express the same non-financial boundary; English is the approved fallback, not a new locale.

- [ ] **Step 2: Preserve catalog invariants.**

Keep `verifyEqualKeysets()` valid by adding each key to all three objects in the same commit. Do not add persistence, requests, browser storage, route behavior, workflow/source language keys, category labels or server values to the catalog.

### Task 3: Localize Finance Planning presentation only

**Files:**
- Modify: `static/portal/portal.js`

- [ ] **Step 1: Add the closed helper and locale-aware money formatter.**

Place the helper directly above `financePlanningMoney`:

```javascript
function financePlanningText(key, fallback, params) {
  return uiText(`financePlanning.${key}`, fallback, params);
}

function financePlanningMoney(value) {
  const amount = Number.isSafeInteger(value) ? value : 0;
  return `${localizedNumber(amount)} ${financePlanningText("currency", "VND")}`;
}
```

Map only the known lifecycle tokens (`active`, `archived`, `draft`, `review`, `approved`) to `financePlanning.state.*`; use `financePlanning.state.guarded` for every unknown token.

- [ ] **Step 2: Convert fixed Finance Planning chrome.**

Replace fixed strings in the Finance Planning helper/render functions with `financePlanningText`. Pass only bounded presentation parameters (`period`, `budgets`, `costs`, `start`, `end`, `total`, `label`, `noun`, `state`) to interpolation. Continue passing category labels, vendor labels, purposes, IDs, revisions, currency values and server data through `safeText` exactly as before.

Keep all existing `data-portal-action`, `data-portal-route`, capability checks, confirmation attributes, `aria-live`, server authorization and disabled-state conditions byte-for-byte equivalent except for localized fixed copy.

- [ ] **Step 3: Keep the data/authority boundary explicit.**

Do not add `fetch`, `api`, `/internal/`, `localStorage`, `sessionStorage`, payment, wallet, provider, bridge, Bot or export actions to the renderer or catalog. Do not localize `policy.categories`, `summary`, `budgets` or `costPlans`; only their UI labels and surrounding copy change.

### Task 4: Verify and integrate the isolated locale change

**Files:**
- Verify: `static/portal/portal-i18n.js`, `static/portal/portal.js`, both focused test modules

- [ ] **Step 1: Run green focused tests and JavaScript syntax checks.**

Run:

```powershell
$py="$env:TEMP\toanaas-webapp-py311-pinned-20260729\Scripts\python.exe"
& $py -m pytest -q tests/test_finance_planning_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py
node --check static/portal/portal-i18n.js
node --check static/portal/portal.js
git diff --check
```

Expected: all focused tests pass, the catalog has equal `vi`/`en`/`zh` keys, and no Bot/bridge/payment/runtime behavior is introduced.

- [ ] **Step 2: Inspect the staged scope.**

Stage only the two Portal files, the two focused tests, the design and this plan. Confirm no `bot.py`, Video Studio, provider, payment, route, service worker or generated migration files are staged.

- [ ] **Step 3: Commit, push, PR and merge only after a green GitHub gate.**

```powershell
git add static/portal/portal-i18n.js static/portal/portal.js tests/test_finance_planning_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py docs/superpowers/specs/2026-07-29-finance-workspace-locale-design.md docs/superpowers/plans/2026-07-29-finance-workspace-locale.md
git commit -m "Localize Finance Planning workspace"
```

Railway deployment and production checks happen only after the normal PR gate; this task never calls live Bot, provider, PayOS or finance APIs.
