# Command Palette and Sidebar i18n Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed customer sidebar and command palette fully reflect the reviewed Vietnamese, English and Simplified Chinese interface locale.

**Architecture:** Keep the current browser-only `uiText` locale catalogue as the single presentation source. The command palette reads its existing count and empty-state keys rather than composing Vietnamese strings; the sidebar reuses the reviewed `app.workspace` caption. No server authority, route authorization, storage, payment or provider boundary changes.

**Tech Stack:** FastAPI portal shell, browser JavaScript, Python/pytest contracts, Node VM runtime harness.

---

### Task 1: Prove the missing runtime localization

**Files:**
- Modify: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Write the failing test**

Extend the first-mount Node VM harness to render a command palette, filter it, and capture English and Chinese customer sidebar/palette output. Assert that English contains `AI Workspace`, `matching workspaces`, and `No matching workspace`; assert that Chinese contains `AI 工作台`, `个匹配工作台`, and `没有匹配的工作台`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest -q tests/test_portal_i18n_bundle_contracts.py::test_customer_sidebar_and_command_palette_follow_the_reviewed_interface_locale`

Expected: FAIL because `filterCommandPalette()` composes Vietnamese text and `renderSidebar()` hard-codes `AI Workspace`.

### Task 2: Use the reviewed locale catalogue at the two render points

**Files:**
- Modify: `static/portal/portal.js`

- [ ] **Step 1: Replace customer chrome literals**

Use `uiText("app.workspace", "TOAN AAS Workspace")` for the customer sidebar caption. Mark the rendered palette as customer or admin at render time, then in `filterCommandPalette` use `chrome.commandCount` / `chrome.commandEmpty` for customer state and retain `chrome.adminCommandCount` / `chrome.no_results` for Admin ERP state. Do not synthesize or persist locale state.

- [ ] **Step 2: Run the focused test to verify it passes**

Run: `python -m pytest -q tests/test_portal_i18n_bundle_contracts.py::test_customer_sidebar_and_command_palette_follow_the_reviewed_interface_locale`

Expected: PASS.

### Task 3: Protect navigation and i18n boundaries

**Files:**
- Modify: `tests/test_portal_navigation_ux_contracts.py`
- Modify: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Add static contracts**

Assert the sidebar uses `chrome.appCaption`; assert the command filter uses `chrome.commandCount` and `chrome.commandEmpty`; assert all three locales expose the new `chrome.appCaption` key.

- [ ] **Step 2: Run target suites**

Run: `python -m pytest -q tests/test_portal_i18n_bundle_contracts.py tests/test_portal_navigation_ux_contracts.py`

Expected: all applicable tests PASS.

### Task 4: Review, verify and commit the isolated slice

**Files:**
- Review only: `static/portal/portal.js`, `static/portal/portal-i18n.js`, focused test files

- [ ] **Step 1: Verify JavaScript parses**

Run: `node --check static/portal/portal.js` and `node --check static/portal/portal-i18n.js`.

- [ ] **Step 2: Inspect diff and protected boundaries**

Run: `git diff --check`, `git diff -- static/portal/portal.js static/portal/portal-i18n.js tests/test_portal_i18n_bundle_contracts.py tests/test_portal_navigation_ux_contracts.py`.


- [ ] **Step 3: Commit only the focused slice**

Run: `git add static/portal/portal.js tests/test_portal_i18n_bundle_contracts.py tests/test_portal_navigation_ux_contracts.py docs/superpowers/plans/2026-08-14-command-palette-sidebar-i18n.md` then commit with `Localize command palette and customer sidebar chrome`.
