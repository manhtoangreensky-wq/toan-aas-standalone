# Memory and Prompt Library Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring Memory Center, Reminders, Prompt Library and template detail into the compact light teal/cyan workspace system without changing private data, revision or schedule behavior.

**Architecture:** Append one scoped final CSS layer after existing final-light route layers. It covers the present DOM structure only and reuses `--portal-*` tokens; all signed API, owner checks, archive/version/recovery, preview and reminder transitions are left untouched.

**Tech Stack:** Server-rendered portal shell, vanilla JavaScript renderer, CSS custom properties, pytest static contracts.

---

### Task 1: Add a failing Memory and Prompt Library surface contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [ ] **Step 1: Add the static contract**

Add `test_light_memory_and_prompt_library_final_surface_keeps_private_work_readable`. It must find `/* Final light Memory and Prompt Library surface */`, capture only that layer through the next final-light marker or EOF, and require:

```python
required = (
    ".portal-memory-center",
    ".portal-memory-reminders",
    ".portal-prompt-library",
    ".portal-prompt-library-detail",
    ".portal-memory-intro",
    ".portal-memory-note",
    ".portal-memory-reminder-card",
    ".portal-memory-event",
    ".portal-prompt-library-intro",
    ".portal-prompt-library-card",
    ".portal-prompt-library-filter",
    ".portal-prompt-library-preview-result",
    ".portal-prompt-library-events",
    ":focus-visible",
    "@media (max-width: 700px)",
)
```

Reject raw hex, `rgba(`, `linear-gradient`, `radial-gradient`, and CSS variables outside `--portal-*`. Update the Campaign Planner final-layer extractor so it ends at the next final-light marker.

- [ ] **Step 2: Run RED**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\memory-prompt-236-foundation-qa tests\test_teal_cyan_ui_foundation_contracts.py
```

Expected: only the new contract fails due to the missing final-layer marker.

### Task 2: Append the bounded light UI layer

**Files:**
- Modify: `static/portal/portal-theme.css`

- [ ] **Step 1: Add `Final light Memory and Prompt Library surface`**

Scope every selector under:

```css
.portal-page:is(.portal-memory-center, .portal-memory-reminders, .portal-prompt-library, .portal-prompt-library-detail)
```

Use token-only colors. Cover intros/metrics, note cards, tags/priority, filter/pagination, editor/boundary/linked records, reminder cards/meta/overdue/edit/event history, prompt create/editor/boundary/preview, library cards/meta/tags, filters, import/provenance and event history. Guarded/archived/disabled states must remain truthful. Hover must not shift layouts; provide focus-visible outlines. At `700px`, use one-column layouts and 44px controls. Do not change the renderer, routes, API, database, schedules, providers, payments or Bot.

- [ ] **Step 2: Run GREEN**

Run the same command from Task 1. Expected: all foundation contracts pass.

### Task 3: Check privacy and lifecycle regressions, then commit

**Files:**
- Test: `tests/test_memory_portal_contracts.py`
- Test: `tests/test_memory_category_filter_portal_contracts.py`
- Test: `tests/test_copyfast_memory.py`
- Test: `tests/test_prompt_library_portal_contracts.py`
- Test: `tests/test_copyfast_prompt_library.py`

- [ ] **Step 1: Run relevant checks**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\memory-prompt-236-contract-qa tests\test_memory_portal_contracts.py tests\test_memory_category_filter_portal_contracts.py tests\test_copyfast_memory.py tests\test_prompt_library_portal_contracts.py tests\test_copyfast_prompt_library.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all commands pass. The UI update creates no note, reminder, prompt, provider call, payment, Bot state or user data.

- [ ] **Step 2: Commit**

```powershell
git add docs/superpowers/plans/2026-07-31-memory-prompt-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Memory and Prompt Library light workspace surfaces"
```
