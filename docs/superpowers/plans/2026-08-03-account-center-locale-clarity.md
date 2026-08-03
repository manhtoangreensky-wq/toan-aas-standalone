# Account Center Locale Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the reviewed Vietnamese, English, and Simplified Chinese presentation of Account profile/connection overview and Account Activity without changing their security or product behavior.

**Architecture:** The browser catalog owns fixed UI copy. `renderAccount` and `renderAccountActivity` read only that copy through existing `uiText`; server/account/activity records stay escaped data. The Python shell-title map provides the no-JavaScript first-paint title for `/account/activity`.

**Tech Stack:** FastAPI/Python, vanilla JavaScript, static pytest contracts, Node syntax checks.

---

## File structure

- `static/portal/portal-i18n.js`: add one closed three-locale Account Center message group and merge it into `MESSAGES`.
- `static/portal/portal.js`: finish Account/Activity fixed-copy lookup and Activity title/description routing.
- `copyfast_pages.py`: add the Activity title tuple beside the existing Account title tuples.
- `tests/test_account_center_locale_contracts.py`: lock the fixed-copy keyset, renderer boundaries, and first-paint metadata.
- `docs/superpowers/specs/2026-08-03-account-center-locale-clarity-design.md`: record the presentation-only boundary.

### Task 1: Lock the reviewed presentation boundary

**Files:**

- Modify: `tests/test_account_center_locale_contracts.py`

- [ ] Add each fixed profile, OAuth, Bot companion, upgrade, session, Activity table, empty-state, boundary, and page-metadata key to the three-catalogue assertion.
- [ ] Require `/account/activity` in `localizedPageTitle`, `localizedPageDescription`, and `_PORTAL_SHELL_TITLES`.
- [ ] Keep assertions that the Account/Activity renderers contain no network, storage, wallet, PayOS, provider, or bridge authority.
- [ ] Run `python -m pytest -q tests/test_account_center_locale_contracts.py` and verify RED before catalogue implementation.

### Task 2: Add reviewed Account Center catalogue copy

**Files:**

- Modify: `static/portal/portal-i18n.js`

- [ ] Add an `ACCOUNT_CENTER_MESSAGES` group with identical `vi`, `en`, and `zh` keysets.
- [ ] Cover profile fields, provider/OAuth notices, Bot-companion explanation and command cards, Telegram-first upgrade labels, Account overview/session labels, Activity table/empty/boundary copy, and `page.accountActivity.title`/`description`.
- [ ] Keep product names, `/commands`, `BOT_USERNAME`, provider names, and server-returned values out of translations except as escaped `{provider}` interpolation.
- [ ] Merge only the new group through the existing `Object.assign` composition.

### Task 3: Finish the existing presenters without behavior change

**Files:**

- Modify: `static/portal/portal.js`
- Modify: `copyfast_pages.py`

- [ ] Correct the incomplete Activity row callback so both fallback cells remain escaped and JavaScript parses.
- [ ] Make the remaining fixed Account profile/connection/companion/upgrade/session text use `accountCenterText`; keep action names, capabilities, form fields, request payloads, and URLs unchanged.
- [ ] Map `/account/activity` through `localizedPageTitle` and `localizedPageDescription` using reviewed UI keys.
- [ ] Add the exact `vi/en/zh` Activity shell-title tuple to `_PORTAL_SHELL_TITLES`.

### Task 4: Verify and hand off safely

**Files:**

- Modify: documentation files above only if verification findings require clarification.

- [ ] Run focused Account/locale/auth contracts, Node syntax checks, and `git diff --check`.
- [ ] Start a local-only app with a temporary session secret; smoke `/account?lang=en` and `/account/activity?lang=zh` at desktop and `375x812` without running a provider, payment, OAuth, Telegram, or write action.
- [ ] Request independent spec-compliance then code-quality review.
- [ ] Commit, push, open one PR, wait for `Verify Web App`, and merge only after green CI. Do not deploy Railway.
