# Wallet & Billing Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed Wallet, Top up, Packages and Pricing journey a clear, professional teal/cyan light workspace without changing canonical billing behavior.

**Architecture:** Append one token-only final CSS layer scoped strictly to `.portal-page:is(.portal-wallet-page, .portal-billing-catalog-page)`. Preserve all existing `portal.js` rendering, signed session/CSRF, canonical wallet and catalog validation, PayOS request status, manual-payment Bot handoff, package authority, Core Bridge behavior and route ownership. The new contract must parse declarations from only this final layer and reject raw colors, gradients, unscoped selectors and non-portal custom properties.

**Tech Stack:** Server-rendered FastAPI portal shell, vanilla JavaScript renderer, `portal-theme.css`, Python `pytest` static contracts.

---

### Task 1: Define a strict final-surface contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Read: `tests/test_billing_canonical_journey_contracts.py`
- Read: `tests/test_billing_navigation_app_ux_contracts.py`

- [x] **Step 1: Write the failing declaration-level test**

Add `test_light_billing_final_surface_keeps_canonical_payment_truth_readable`.
Use the existing `_parse_css_rules` and `_css_declarations_for` helpers to
isolate only this marker:

```python
layer = re.search(
    r"/\* Final light Wallet and Billing surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
    theme_source,
    flags=re.DOTALL,
)
root_scope = ".portal-page:is(.portal-wallet-page, .portal-billing-catalog-page)"
```

Require exact declarations for these selectors:

```python
assert_declarations(f"{root_scope} .portal-wallet-command", {"background": "var(--portal-surface-light)"})
assert_declarations(f"{root_scope} .portal-wallet-read-status", {"background": "var(--portal-surface-soft)"})
assert_declarations(f"{root_scope} .portal-billing-journey", {"background": "var(--portal-surface-light)"})
assert_declarations(f"{root_scope} .portal-billing-entrypoints .portal-payment-entry", {"background": "var(--portal-surface-light)"})
assert_declarations(f"{root_scope} .portal-billing-catalog-card", {"background": "var(--portal-surface-light)"})
assert_declarations(f"{root_scope} .portal-billing-nav", {"background": "var(--portal-surface-soft)"})
assert_declarations(f'{root_scope} .portal-billing-nav a[aria-current="page"]', {"background": "var(--portal-light-accent-soft)"})
assert_declarations(f"{root_scope} :is(button, a, input, select, textarea):focus-visible", {"outline": "3px solid var(--portal-focus) !important"})
```

Also require a stationary payment-card hover/focus rule, 700px one-column
journey/payment/catalog layout with 44px controls, and a reduced-motion rule
with both `transition: none` and `transform: none`. Reject selectors outside
the root scope, raw hex/rgb/hsl/gradients/`transparent`, and `var(--*)` tokens
not starting with `--portal-`.

- [x] **Step 2: Verify RED**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py -k billing_final_surface -p no:cacheprovider --basetemp C:\tmp\copyfast248-red
```

Expected: one failure because `Final light Wallet and Billing surface` does
not exist yet; do not change production code until this is the failure.

### Task 2: Add only the scoped light billing layer

**Files:**
- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [x] **Step 1: Append the marker and root scope**

Append `/* Final light Wallet and Billing surface */` after every existing
final-light layer. Every selector begins with exactly
`.portal-page:is(.portal-wallet-page, .portal-billing-catalog-page)`.

- [x] **Step 2: Normalize wallet and canonical status surfaces**

Use `--portal-surface-light`, `--portal-surface-soft`, `--portal-border`,
`--portal-ink`, `--portal-muted`, `--portal-action`, and
`--portal-light-accent-soft` only. Style the existing wallet command rail,
wallet facts, read-status, journey head/lanes, payment entry cards,
catalog intro/cards, route nav and empty/error/guarded panels. Keep status
text and badges visible; do not alter markup, labels, URLs, `data-*`
attributes, form actions or disabled behavior.

- [x] **Step 3: Preserve stationary interaction and accessible response**

For `.portal-payment-entry` and `.portal-billing-catalog-card` hover/focus,
use border/background feedback with `box-shadow: none` and `transform: none`.
Provide a 3px sky focus ring for interactive controls. At 700px, make the
journey lanes, entry cards and catalog grid one column, stack route controls
without overflow, and set the current existing primary/quiet controls to a
minimum height of 44px. Under reduced motion, remove transitions and
transforms from cards, route links and billing controls.

- [x] **Step 4: Verify GREEN**

Run the Task 1 command again. Expected: the new test passes.

### Task 3: Protect canonical financial boundaries

**Files:**
- Test: `tests/test_billing_canonical_journey_contracts.py`
- Test: `tests/test_billing_navigation_app_ux_contracts.py`
- Test: `tests/test_copyfast_bridge.py`

- [x] **Step 1: Run the focused behavioral suite**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_billing_canonical_journey_contracts.py tests/test_billing_navigation_app_ux_contracts.py tests/test_copyfast_bridge.py -p no:cacheprovider --basetemp C:\tmp\copyfast248-focused
git diff --check
```

Expected: UI contracts pass; wallet read state remains canonical; the Web does
not coerce missing values to zero; payment/manual routes keep their existing
authority boundaries; diff is whitespace-clean.

Verification record: the focused suite passed every runnable test after
excluding the unavailable Trio backend: `122 passed, 26 deselected`. The
unfiltered command's 26 failures are all `test_copyfast_bridge.py` Trio
variants that cannot import `trio` in this local UI QA environment; they are
not code failures. `git diff --check` is clean.

- [x] **Step 2: Verify no runtime surface moved**

```powershell
git diff --name-only origin/main...HEAD
```

Expected: only this plan/design document, the theme and the UI foundation test
are present. `portal.js`, `integration.js`, `copyfast_api.py`,
`copyfast_bridge.py`, payment code, webhook code and `bot.py` must be absent.

### Task 4: Browser smoke and handoff

**Files:**
- Modify: `docs/superpowers/specs/2026-07-31-billing-light-surface-design.md`
- Modify: `docs/superpowers/plans/2026-07-31-billing-light-surface.md`

- [x] **Step 1: Attempt a safe local browser smoke**

Use the local FastAPI server only. Confirm anonymous `/wallet` redirects to
`/login?next=/wallet`; do not submit a payment, manual top-up, file, TXID,
provider or Bot action. If a signed local browser session is available, inspect
the Wallet and Top up first viewport at desktop and 375px. If it is not
available, record the browser-attachment limitation and do not claim visual
browser pass.

Verification record: a local temporary-secret smoke confirmed anonymous
`/wallet` returns `307` to `/login?next=/wallet`; no payment, manual top-up,
file, TXID, provider or Bot action was submitted. The in-app browser was also
attempted against the local server but could not attach its webview, so no
private-route visual/browser pass is claimed.

- [ ] **Step 2: Commit the isolated slice**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/specs/2026-07-31-billing-light-surface-design.md docs/superpowers/plans/2026-07-31-billing-light-surface.md
git commit -m "Polish wallet and billing light surface"
```

Expected: one focused UI-only commit ready for normal push, PR, CI and merge;
no Railway deployment is part of this slice.
