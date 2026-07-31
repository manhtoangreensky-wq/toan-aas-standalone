# Content Studio Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put every customer-facing Content Studio route on the approved teal–sky light application system without changing content creation, storage, API, provider, or job behavior.

**Architecture:** Give the native Content Studio detail page one presentation-only identity class, then add one final, route-scoped override layer to `static/portal/portal-theme.css`. This prevents a shared legacy `.portal-content-studio-detail` class from styling Channel Strategy detail by accident. The layer replaces legacy dark text, chips, borders, selected states, hover and keyboard focus with existing semantic `--portal-*` tokens; it does not edit `portal.css`, templates, API modules, runtime behavior, or Bot code.

**Tech Stack:** FastAPI server-rendered portal, static CSS, pytest contract tests.

---

## File map

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — assert the final Content Studio override remains scoped, token-only, readable and mobile-safe; assert the detail identity stays Content-Studio-specific; update the Subtitle regex boundary so later layers do not hide its test surface.
- Modify: `static/portal/portal.js` — append `portal-content-studio-workspace-detail` only to `renderContentStudioDetail`, preserving the legacy shared class and avoiding any Channel Strategy markup change.
- Modify: `static/portal/portal-theme.css` — append the final Content Studio light-surface override layer.

### Task 1: Lock the light-surface contract before CSS changes

- [ ] **Step 1: Write a failing test**

  Add `test_light_content_studio_final_surface_keeps_private_authoring_readable` to `tests/test_teal_cyan_ui_foundation_contracts.py`. Assert `renderContentStudioDetail` emits `portal-content-studio-workspace-detail` while `renderChannelStrategyDetail` does not. Extract the CSS after `/* Final light Content Studio surface */`; assert that the route selector is exactly scoped to `.portal-content-operations-board`, `.portal-content-studio-authoring`, and `.portal-content-studio-workspace-detail`; then assert token-based rules for the summary, labels/notes, chips, selected variants, history/policy, hover, focus and the 700px one-column grid. Change the preceding Subtitle layer regex to stop at the next `/* Final light ... */` marker rather than `\Z`.

- [ ] **Step 2: Run the targeted test and verify RED**

  Run:

  ```powershell
  C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py -k content_studio
  ```

  Expected: the new Content Studio contract fails because the final marker and CSS layer do not yet exist; existing unrelated tests do not fail from a malformed test.

- [ ] **Step 3: Implement the smallest final CSS layer**

  Add `portal-content-studio-workspace-detail` to the `renderContentStudioDetail` article class only, then append `/* Final light Content Studio surface */` to `static/portal/portal-theme.css`. Use only existing semantic tokens. Ensure summary surfaces are white with no legacy shadow; labels/notes are readable; chips and selected variants preserve state; policy/history dividers are visible; hover has no layout transform; focus uses `--portal-focus`; and the Content Studio grids collapse to one column at 700px.

- [ ] **Step 4: Run targeted contracts and syntax checks**

  Run:

  ```powershell
  C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py
  C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests\test_content_studio_portal_contracts.py
  node --check static\portal\portal.js
  node --check static\portal\integration.js
  git diff --check
  ```

  Expected: all commands pass. The stylesheet change must not change provider, job, payment, storage, or Bot behavior.

- [ ] **Step 5: Perform focused browser QA**

  Verify `/content-studio`, `/content-studio/new`, and a valid Content Studio detail view at desktop and mobile width: no dark legacy text, no overflow, readable selected state, visible keyboard focus, and truthful guarded authoring state. Do not exercise provider calls, payment, or jobs.

- [ ] **Step 6: Commit and hand off**

  Commit only the plan, contract test and final CSS layer with a clear UI-only message. Push the feature branch, open one PR, wait for checks, then merge only after the PR is green. Do not deploy Railway for this UI-only change.
