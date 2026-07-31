# Voice Studio Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every Voice Studio authoring route to the approved light teal/cyan application system while preserving its truthful Web-native boundary: directions and scripts only, with no TTS, clone, preview, audio asset, provider, payment or delivery behavior.

**Architecture:** Append one final, route-scoped CSS override layer to `static/portal/portal-theme.css` for `.portal-voice-studio` and `.portal-voice-studio-detail`. It replaces legacy orange/dark text, cards, filters, tags, selected/default states, consent/guard information, history and keyboard focus with existing `--portal-*` semantic tokens. No JavaScript, route, API, database, provider, Bot or payment code changes are required because the route identities are Voice-Studio-specific already.

**Tech Stack:** FastAPI server-rendered portal, static CSS, pytest contract tests.

---

## File map

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — add a final Voice Studio light-surface contract that asserts route scope, semantic token usage, readable text/state, focus, no raw legacy colour/gradient and mobile grids.
- Modify: `static/portal/portal-theme.css` — append the final Voice Studio token-only override layer after the Content Studio layer.

### Task 1: Lock Voice Studio presentation before CSS changes

- [ ] **Step 1: Write a failing test**

  Add `test_light_voice_studio_final_surface_keeps_direction_and_consent_readable` to `tests/test_teal_cyan_ui_foundation_contracts.py`. Extract the CSS following `/* Final light Voice Studio surface */`. Assert the exact route scope is `.portal-page:is(.portal-voice-studio, .portal-voice-studio-detail)` and assert tokenised rules for summary, metrics, authoring panels, guard rows, vault/default and script cards, metadata, filters, consent cue sheet, history/event text, hover, focus and the 700px one-column grid. Assert the final layer contains no raw hex/gradient/rgba and no non-portal token.

- [ ] **Step 2: Run the targeted test and verify RED**

  Run:

  ```powershell
  C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py -k voice_studio_final_surface
  ```

  Expected: FAIL because the final Voice Studio marker and rules do not exist.

- [ ] **Step 3: Implement the smallest final CSS layer**

  Append `/* Final light Voice Studio surface */` to `static/portal/portal-theme.css`. Use only existing semantic tokens. Keep white working surfaces, teal action/context, muted secondary text, tokenised consent/guard states, no layout-shifting hover and a visible focus ring. Do not change any declared Voice Studio truth boundary or runtime behavior.

- [ ] **Step 4: Run focused verification**

  Run:

  ```powershell
  C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py
  C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests\test_voice_studio_portal_contracts.py
  node --check static\portal\portal.js
  node --check static\portal\integration.js
  git diff --check
  ```

  Expected: all checks pass. The diff must remain UI-only and leave provider, payment, jobs, storage and Bot behavior untouched.

- [ ] **Step 5: Perform focused browser QA**

  Verify `/voice-studio` and `/voice-studio/new` at desktop and mobile width when a signed local test session is available. Confirm that the guarded state is truthful, text is readable and the layout has no horizontal overflow. Do not create a direction, submit a form or exercise any external workflow.

- [ ] **Step 6: Commit and hand off**

  Commit only the plan, final CSS layer and regression contract. Push the feature branch, open one PR, wait for green CI, merge sequentially, and do not deploy Railway for this UI-only change.
