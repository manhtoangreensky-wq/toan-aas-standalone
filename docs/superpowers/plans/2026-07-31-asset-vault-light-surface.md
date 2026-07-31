# Asset Vault Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the private Asset Vault upload, library, archive/lifecycle inspection and recovery surfaces on the approved teal/cyan light application system while preserving its owner-scoped storage and truthful delivery boundary.

**Architecture:** Append one final CSS layer to `static/portal/portal-theme.css`, scoped exactly to `.portal-page.portal-asset-vault`. It replaces the route's inherited dark/gradient styling only with existing `--portal-*` tokens. No renderer, endpoint, database, signed-session, storage, lifecycle, archive/restore, provider, payment, Bot or PWA behavior changes.

**Tech Stack:** FastAPI server-rendered portal, static CSS, pytest static-contract tests.

---

## File map

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — bound the preceding Project Center layer extractor and add an Asset Vault light-surface contract.
- Modify: `static/portal/portal-theme.css` — append the scoped, token-only Asset Vault final layer.
- Create: `docs/superpowers/plans/2026-07-31-asset-vault-light-surface.md` — this implementation record.

### Task 1: Lock Asset Vault presentation and delivery truth before CSS changes

- [ ] **Step 1: Write the failing test**

Add `test_light_asset_vault_final_surface_keeps_private_storage_states_readable` to `tests/test_teal_cyan_ui_foundation_contracts.py`. Extract the new final layer after this exact marker:

```python
layer = re.search(
    r"/\\* Final light Asset Vault surface \\*/(?P<css>.*)\\Z",
    PORTAL_THEME.read_text(encoding="utf-8"),
    flags=re.DOTALL,
)
assert layer is not None
asset_css = layer.group("css")
route = ".portal-page.portal-asset-vault"
assert not re.search(r"(?:#[0-9a-f]{3,8}\\b|(?:linear|radial)-gradient|rgba?\\()", asset_css, re.I)
assert not re.search(r"var\\(--(?!portal-)", asset_css)
```

Change the Project Center layer extractor so it stops at the next `/* Final light … */` marker. Assert all final selectors start with `route`, and require token-only declarations for intro metrics, upload/boundary/library cards, dropzone/input/file selector button, Project-step text, filter/pagination, vault cards/meta/file type mark, lifecycle summary/list/rows, active/archived neutral state, hover, focus and 700px one-column collapse.

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py -k asset_vault_final_surface
```

Expected: FAIL because the final Asset Vault marker and declarations are absent. The failure must be the missing layer, not an invalid test.

- [ ] **Step 3: Implement the smallest final CSS layer**

Append `/* Final light Asset Vault surface */` to `static/portal/portal-theme.css`. Every selector begins with:

```css
.portal-page.portal-asset-vault
```

Use only `--portal-*` variables. Keep the white/soft surface hierarchy clear: private upload remains a real intake form, cards remain metadata not output, lifecycle data remains redacted, and archive/recovery remains a state with clear guard copy rather than a fake download. Use hover border/background feedback without translation or layout shift, 3px visible focus and 44px controls only in the small-screen media block.

- [ ] **Step 4: Verify GREEN and preserve behavior contracts**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_asset_vault_lifecycle_portal_contracts.py tests\test_copyfast_assets.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all checks pass. The diff must be limited to the plan, the static presentation contract and the final CSS layer.

- [ ] **Step 5: Perform focused read-only browser QA**

If a signed local test session is already available, inspect `/asset-vault` at desktop and 375px. Confirm readable upload, boundary, active/archived cards and lifecycle detail, visible keyboard focus and no horizontal overflow. Do not upload a file, archive/restore an asset, create data, start a job, call a provider or initiate payment.

- [ ] **Step 6: Review, commit and merge sequentially**

Review scope and final selector ownership. Commit only these files:

```powershell
git add docs/superpowers/plans/2026-07-31-asset-vault-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Asset Vault light workspace surface"
```

Push one branch, open one PR, wait for required checks, merge only after green, then fetch `main` before the Workboard UI surface. Do not deploy Railway for this UI-only change.
