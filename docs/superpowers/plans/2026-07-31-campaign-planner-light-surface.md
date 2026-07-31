# Campaign Planner Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Campaign Planner, its authoring/detail views, Calendar and self-review queue feel like one compact, readable teal/cyan workspace without changing campaign data or lifecycle behavior.

**Architecture:** Add one final CSS-only layer in `portal-theme.css`. Every selector is scoped to the four existing campaign route classes and uses only `--portal-*` visual tokens. Existing signed-session checks, campaign actions, calendar filtering, self-review transitions, schedule intents, APIs and storage remain untouched.

**Tech Stack:** Server-rendered portal shell, vanilla JavaScript renderer, CSS custom properties, pytest static contracts.

---

### Task 1: Define the final Campaign surface contract first

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [ ] **Step 1: Add the failing static contract**

Add `test_light_campaign_planner_final_surface_keeps_planning_calendar_and_review_readable`. It finds `/* Final light Campaign Planner surface */`, extracts only through the next final-light marker or EOF, and requires the following literal CSS evidence:

```python
required = (
    ".portal-campaign-planner",
    ".portal-campaign-detail",
    ".portal-campaign-calendar",
    ".portal-campaign-approvals",
    ".portal-campaign-operations-summary",
    ".portal-campaign-operations-primary",
    ".portal-campaign-card",
    ".portal-calendar",
    ".portal-calendar-cell",
    ".portal-calendar-event",
    ".portal-calendar-agenda-item",
    ".portal-campaign-metrics",
    ".portal-campaign-boundary",
    ":focus-visible",
    "@media (max-width: 700px)",
)
```

The test rejects raw hex, `rgba(`, `linear-gradient`, `radial-gradient`, and any custom property outside the `--portal-*` namespace. Update the preceding Workboard extractor to stop at the next final-light marker instead of `\\Z`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\campaign-235-foundation-qa tests\test_teal_cyan_ui_foundation_contracts.py
```

Expected: the new test fails only because the Campaign final-layer marker does not exist.

### Task 2: Append a bounded final-light Campaign layer

**Files:**
- Modify: `static/portal/portal-theme.css`

- [ ] **Step 1: Add final CSS without changing behavior**

Append `/* Final light Campaign Planner surface */` after the current final-light layers. Scope all selectors under:

```css
.portal-page:is(.portal-campaign-planner, .portal-campaign-detail, .portal-campaign-calendar, .portal-campaign-approvals)
```

Use only `--portal-*` color tokens and no gradients, raw colors, `rgba` or unscoped selector rules. Cover the board/authoring summary, metrics and primary action; campaign cards/facts/detail review blocks; boundaries and guarded states; calendar filter, seven-column calendar, cells, event status, agenda and overflow; self-review metrics/cards; focus-visible, non-shifting hover and disabled states. At `700px`, preserve the calendar as a horizontal seven-day grid when necessary, collapse authoring/detail/metrics/cards and filters safely, and ensure controls meet 44px height. Do not modify renderer, route, data, scheduling, API, database, provider, payment or Bot files.

- [ ] **Step 2: Run the focused contract and verify GREEN**

Run the same command from Task 1. Expected: all UI-foundation contracts pass.

### Task 3: Preserve campaign behavior and ship the focused PR

**Files:**
- Test: `tests/test_campaign_operations_board_contracts.py`
- Test: `tests/test_campaign_calendar_window_contracts.py`
- Test: `tests/test_campaign_schedule_intents.py`
- Test: `tests/test_campaign_schedule_rate_limits.py`

- [ ] **Step 1: Run the behavior and syntax checks**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\campaign-235-contract-qa tests\test_campaign_operations_board_contracts.py tests\test_campaign_calendar_window_contracts.py tests\test_campaign_schedule_intents.py tests\test_campaign_schedule_rate_limits.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all commands pass; no schedule, campaign, provider, payment, Bot or server state is created or changed by this UI PR.

- [ ] **Step 2: Commit the focused change**

Run:

```powershell
git add docs/superpowers/plans/2026-07-31-campaign-planner-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Campaign Planner light workspace surface"
```
