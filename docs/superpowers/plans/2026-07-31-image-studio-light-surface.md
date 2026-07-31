# Image Studio Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the private Image Studio artboard and direction routes on the approved light teal/cyan application system without changing Image Studio authoring, ownership, API, provider, job, wallet, payment, asset, delivery, or Bot behavior.

**Architecture:** Append one final, route-scoped CSS layer to `static/portal/portal-theme.css`, scoped only to `.portal-page:is(.portal-image-studio, .portal-image-studio-detail)`. It must reuse the existing `--portal-*` semantic tokens and deliberately exclude Image Hub, legacy `/image/*` utilities, Video, and every runtime boundary. A static contract in the foundation suite locks readable summaries, artboards, direction creation and metadata, guarded state, revision/activity history, keyboard focus, no layout-shifting hover, and a one-column 700px layout.

**Tech Stack:** FastAPI server-rendered portal, static CSS, pytest static-contract tests.

---

## File map

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — add one isolated Image Studio final-layer contract.
- Modify: `static/portal/portal-theme.css` — append the final token-only Image Studio presentation layer after the Voice Studio layer.
- Create: `docs/superpowers/plans/2026-07-31-image-studio-light-surface.md` — this scoped implementation record.

### Task 1: Lock the Image Studio presentation contract before CSS changes

- [ ] **Step 1: Write the failing test**

Add `test_light_image_studio_final_surface_keeps_artboards_truthful_and_readable` to `tests/test_teal_cyan_ui_foundation_contracts.py`. Extract only the final layer and use this fixed route scope:

```python
layer = re.search(
    r"/\\* Final light Image Studio surface \\*/(?P<css>.*)\\Z",
    PORTAL_THEME.read_text(encoding="utf-8"),
    flags=re.DOTALL,
)
assert layer is not None
image_css = layer.group("css")
route = ".portal-page:is(.portal-image-studio, .portal-image-studio-detail)"
assert ".portal-image-hub" not in image_css
assert not re.search(r"(?:#[0-9a-f]{3,8}\\b|(?:linear|radial)-gradient|rgba?\\()", image_css, re.I)
assert not re.search(r"var\\(--(?!portal-)", image_css)
```

Require token-based declarations for the intro/detail summary, metrics, create/editor/direction-create/estimate/reference/boundary/activity surfaces, artboard/direction cards, metadata tags, guarded status, filters and pagination, revision/activity history, hover, focus, and the 700px single-column grids. The test must assert `transform: none;` for hover and `outline: 3px solid var(--portal-focus) !important;` for keyboard focus.

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py -k image_studio_final_surface
```

Expected: FAIL because the `Final light Image Studio surface` marker and its declarations do not yet exist. The failure must be the missing final layer, not an invalid test.

- [ ] **Step 3: Implement the smallest final CSS layer**

Append `/* Final light Image Studio surface */` to `static/portal/portal-theme.css`. Use exactly this route prefix for every selector:

```css
.portal-page:is(.portal-image-studio, .portal-image-studio-detail)
```

Apply `--portal-surface-light`, `--portal-surface-soft`, `--portal-ink`, `--portal-muted`, `--portal-border`, `--portal-border-strong`, `--portal-action`, `--portal-danger`, `--portal-focus`, and `--portal-light-hover-surface` only where semantic state needs them. Keep artboard direction and revision history clearly authoring-only; do not add image preview, thumbnail, provider, job, payment, asset download, or success-result presentation. Use `box-shadow: none;` on legacy dark cards, `transform: none;` on card hover, and a `@media (max-width: 700px)` rule that changes the Image Studio grids to one column.

- [ ] **Step 4: Verify GREEN and guard the boundary**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests\test_image_studio_portal_contracts.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all checks pass. Inspect the diff: only the plan, the regression contract, and the final CSS layer may change.

- [ ] **Step 5: Perform focused browser QA without mutating product data**

With a signed local test session when available, open `/image-studio`, `/image-studio/new`, and an already-owned Image Studio detail at desktop and mobile width. Confirm the authoring-only guard remains truthful, summaries and metadata are readable, focus is visible, and there is no horizontal overflow. Do not submit a form, create an artboard, mutate a direction, call a provider, initiate payment, or create a job.

- [ ] **Step 6: Review, commit, and merge sequentially**

Perform spec-compliance review followed by code-quality review. Commit only the plan, contract, and CSS layer with:

```powershell
git add docs/superpowers/plans/2026-07-31-image-studio-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Image Studio light workspace surface"
```

Push the branch, open one PR, wait for its required checks, merge only after they are green, then fetch `main` before choosing the next non-video UI surface. Do not deploy Railway for this UI-only PR.
