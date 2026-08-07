# Data Controls Locale Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Localize the signed Web Data Control Center for Vietnamese, English,
and Chinese while retaining its privacy, ownership, and request semantics.

**Architecture:** Fixed presentation copy lives in the existing Portal i18n
bundle under `accountCenter.dataControls.*`. `portal.js` and
`integration.js` read only fixed keys through narrow locale helpers; canonical
server projections and protocol literals remain untouched. The source commit
precedes generated audit evidence.

**Tech Stack:** FastAPI first-paint shell, vanilla Portal JavaScript, Python
static contract tests, GitHub Actions.

---

### Task 1: Lock the locale and security boundary with failing tests

**Files:**

- Create: `tests/test_data_controls_locale_contracts.py`
- Modify: `tests/test_data_controls_portal_contracts.py`
- Modify: `.github/workflows/webapp-quality.yml`

- [ ] **Step 1: Write failing static contracts**

```python
def test_data_controls_fixed_copy_has_complete_vi_en_zh_catalogue() -> None:
    assert I18N.count('"accountCenter.dataControls.guardedTitle"') == 3
    assert 'function dataControlsText(key, fallback, params)' in PORTAL

def test_data_control_action_messages_localize_without_changing_requests() -> None:
    assert 'function dataControlsText(key, fallback, params)' in INTEGRATION
    assert 'acknowledgement: DATA_CONTROLS_ERASURE_ACKNOWLEDGEMENT' in actions
    assert 'acknowledgement: DATA_CONTROLS_CANCEL_ACKNOWLEDGEMENT' in actions
```

The existing portal contract must stop requiring Vietnamese literals and instead
require the helper and the unchanged route/action/confirmation attributes.

- [ ] **Step 2: Run the contracts and verify RED**

Run:

```powershell
python -m pytest -q tests/test_data_controls_locale_contracts.py tests/test_data_controls_portal_contracts.py
```

Expected: the new locale contract fails because the catalogue/helper does not
exist; existing safety assertions remain meaningful.

### Task 2: Add fixed-copy catalogue and renderer localization

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.js`
- Modify: `copyfast_pages.py`

- [ ] **Step 1: Add one equal-key catalogue**

Add each reviewed `accountCenter.dataControls.*` key exactly once to vi/en/zh.
Include route title/description, protected/loading/empty states, category and
request-state labels, form/confirmation/disabled copy, data boundary copy, and
fixed dynamic sentence templates.

- [ ] **Step 2: Use only the presentation helper**

```js
function dataControlsText(key, fallback, params) {
  return accountCenterText(`dataControls.${key}`, fallback, params);
}
```

Replace fixed literal presentation strings in `renderAccountDataControls`,
`dataControlsRequestStateLabel`, category metadata, and route title/description
with the helper. Keep `safeText` around dynamic count/timestamp/request/revision
projections and keep route/actions/form attributes byte-for-byte compatible.

- [ ] **Step 3: Add first-paint parity**

Add `/account/data-controls` vi/en/zh entries to `_PORTAL_SHELL_TITLES`, and
map its title/description through the i18n bundle in `portal.js`.

- [ ] **Step 4: Run the contracts and verify GREEN**

Run:

```powershell
python -m pytest -q tests/test_data_controls_locale_contracts.py tests/test_data_controls_portal_contracts.py
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
```

Expected: all focused tests pass and the Portal bundles parse.

### Task 3: Localize browser-only action feedback

**Files:**

- Modify: `static/portal/integration.js`

- [ ] **Step 1: Resolve browser-created fallback text**

```js
function dataControlsText(key, fallback, params) {
  return portalText(`accountCenter.dataControls.${key}`, fallback, params);
}
```

Use it for route/capability/validation/projection errors and success/pending
toasts under the four Data Controls actions. Preserve `result.message ||
dataControlsText(...)`, all API paths, payload fields, and the existing
submission/refresh sequence.

- [ ] **Step 2: Run request-shape regression tests**

Run:

```powershell
python -m pytest -q tests/test_data_controls_portal_contracts.py tests/test_data_controls_locale_contracts.py
```

Expected: fixed fallbacks localize; canonical payload values remain unchanged.

### Task 4: Verify, audit, and merge sequentially

**Files:**

- Modify only if generated output changes: `docs/migration/README.md`,
  `reports/migration/preflight.json`, `reports/migration/web_inventory.json`

- [ ] **Step 1: Run bounded final gates**

Run the focused Data Controls/auth/i18n contracts, `compileall`, all Portal
syntax checks, `git diff --check`, and a local private-route smoke test with an
ephemeral `WEB_SESSION_SECRET` and bridge/provider/payment variables unset.

- [ ] **Step 2: Commit source before audit output**

Commit source, tests, workflow, and these design/plan documents first. Do not
commit generated evidence with a dirty source snapshot.

- [ ] **Step 3: Regenerate static evidence**

Run `scripts/migration/audit_bot_to_web.py` against frozen Bot SHA
`b29d0d474974075f4cba963d2c510f49d2d1b3e4`, then retain only the permitted
README, preflight, and Web inventory changes. Verify on final `HEAD` with
`--verify-web-evidence`.

- [ ] **Step 4: Push one reviewed PR**

Push `feature/p0-webapp-data-controls-locales`, open one PR against `main`,
wait for `Verify Web App`, and merge only after checks and independent review
are clean. Do not deploy Railway or call Bot, provider, PayOS, wallet, job,
webhook, or Telegram flows.
