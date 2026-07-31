# Project Center Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the private Project Operations Board, focused Project authoring and Project Workspace detail onto the approved teal/cyan light application system without changing their owner-scoped authoring, revision or package contracts.

**Architecture:** Append one final token-only CSS layer to `static/portal/portal-theme.css`, scoped exactly to `.portal-page:is(.portal-project-center, .portal-project-center-authoring, .portal-project-detail)`. It replaces inherited dark/gradient presentation only for these three Project Center surfaces. It does not alter `portal.js`, `integration.js`, API endpoints, database schema, signed-session logic, package export, media execution, providers, payment, Bot or PWA policy.

**Tech Stack:** FastAPI server-rendered portal, static CSS, pytest static-contract tests.

---

## File map

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — bound the preceding Music/SFX final-layer extractor and add a Project Center presentation contract.
- Modify: `static/portal/portal-theme.css` — append the scoped final Project Center light surface.
- Create: `docs/superpowers/plans/2026-07-31-project-center-light-surface.md` — this implementation record.

### Task 1: Lock Project Center's presentation and truth boundary before CSS changes

- [ ] **Step 1: Write the failing test**

Add `test_light_project_center_final_surface_keeps_authoring_and_history_readable` to `tests/test_teal_cyan_ui_foundation_contracts.py`. Extract a new final layer with the exact marker and bounded match:

```python
layer = re.search(
    r"/\\* Final light Project Center surface \\*/(?P<css>.*)\\Z",
    PORTAL_THEME.read_text(encoding="utf-8"),
    flags=re.DOTALL,
)
assert layer is not None
project_css = layer.group("css")
route = ".portal-page:is(.portal-project-center, .portal-project-center-authoring, .portal-project-detail)"
assert not re.search(r"(?:#[0-9a-f]{3,8}\\b|(?:linear|radial)-gradient|rgba?\\()", project_css, re.I)
assert not re.search(r"var\\(--(?!portal-)", project_css)
```

Change the Music/SFX extractor to stop at the next `/* Final light … */` marker. Require token-only declarations for summary/authoring intros, metric cells, primary/boundary/library panels, filter/pagination, Project cards, detail summary, Studio Document rows, empty/new-document/editor/history/version rows, package panel/action/meta/cards, hover, focus and the 700px single-column collapse. Every selector in the new layer must start with the fixed `route` prefix.

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py -k project_center_final_surface
```

Expected: FAIL because the final Project Center marker and its declarations do not exist. The failure must be the missing surface, not an invalid test.

- [ ] **Step 3: Implement the smallest final CSS layer**

Append `/* Final light Project Center surface */` to `static/portal/portal-theme.css`. Prefix every selector with:

```css
.portal-page:is(.portal-project-center, .portal-project-center-authoring, .portal-project-detail)
```

Use only shared `--portal-*` semantic tokens. Use white working surfaces, soft metadata/metric surfaces, dark-teal readable primary text/actions and sky focus treatment. Preserve the distinction between authoring metadata, explicit guarded state and immutable Package export; do not make a package look like a Bot job or invented media output. Hover must use border/background feedback without layout movement. All actionable controls retain a 3px focus outline. Mobile uses one column and 44px controls without changing the underlying interaction flow.

- [ ] **Step 4: Verify GREEN and preserve existing contracts**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_project_operations_board_contracts.py tests\test_project_package_portal_contracts.py tests\test_copyfast_projects.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all checks pass. The diff must be limited to this plan, the static presentation contract and the final CSS layer.

- [ ] **Step 5: Perform focused read-only browser QA**

With a signed local test session if one is already available, inspect `/projects`, `/projects/new` and an existing `/projects/{uuid}` at desktop and 375px. Confirm aligned summary metrics, readable authoring/editor/history/package sections, visible keyboard focus and no horizontal overflow. Do not create a Project, mutate a Studio Document, export a package, start provider work, create a job or initiate payment.

- [ ] **Step 6: Review, commit and merge sequentially**

Review scope and CSS selector ownership. Commit only these files:

```powershell
git add docs/superpowers/plans/2026-07-31-project-center-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Project Center light workspace surface"
```

Push one branch, open one PR, wait for required checks, merge only after green, then fetch `main` before the next non-video UI surface. Do not deploy Railway for this UI-only change.
