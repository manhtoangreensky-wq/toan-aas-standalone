# Aura Token Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a shared Aura geometry/elevation/icon/scrim token layer for the Web App's teal/cyan light and dark themes.

**Architecture:** `static/portal/portal-theme.css` remains the only token owner. Light primitives live in `:root`, dark primitives in the existing `--portal-dark-*` set, and `:root[data-portal-theme="dark"]` remaps semantic aliases. A focused Python contract test guards declarations and representative consumers; no route markup or runtime service changes are needed.

**Tech Stack:** Vanilla CSS custom properties, existing HTML/CSS/JS Portal shell, Python `pytest` contract tests.

---

### Task 1: Add the failing token contract

**Files:**
- Modify: `tests/test_portal_aura_theme_contracts.py`

- [ ] **Step 1: Write the failing test**

Add a test that extracts the light `:root` declarations, the dark primitive
declarations and the dark semantic alias block. Assert the following exact
tokens and representative consumers:

```python
def test_aura_geometry_tokens_have_light_dark_aliases_and_consumers() -> None:
    theme_source = THEME
    light = re.search(r":root\s*\{(?P<declarations>.*?)\n\}", theme_source, flags=re.DOTALL)
    dark_primitives = re.search(
        r":root\s*\{(?P<declarations>.*?--portal-dark-elevation-float:.*?\n)\}",
        theme_source,
        flags=re.DOTALL,
    )
    dark_aliases = re.search(
        r':root\[data-portal-theme="dark"\]\s*\{(?P<declarations>.*?)\n\}',
        theme_source,
        flags=re.DOTALL,
    )
    assert light and dark_primitives and dark_aliases
    light_tokens = light.group("declarations")
    primitive_tokens = dark_primitives.group("declarations")
    aliases = dark_aliases.group("declarations")

    for token in (
        "--portal-radius-md: 12px;",
        "--portal-space-1: 4px;",
        "--portal-space-2: 8px;",
        "--portal-space-3: 12px;",
        "--portal-space-4: 16px;",
        "--portal-space-6: 24px;",
        "--portal-space-8: 32px;",
        "--portal-elevation-0: none;",
        "--portal-elevation-1:",
        "--portal-elevation-2:",
        "--portal-elevation-3:",
        "--portal-icon-sm: 16px;",
        "--portal-icon-md: 18px;",
        "--portal-icon-lg: 20px;",
        "--portal-scrim:",
        "--portal-scrim-blur: 2px;",
    ):
        assert token in light_tokens

    for token in (
        "--portal-dark-elevation-1:",
        "--portal-dark-elevation-2:",
        "--portal-dark-elevation-3:",
        "--portal-dark-scrim:",
    ):
        assert token in primitive_tokens

    for token in (
        "--portal-radius-md: 12px;",
        "--portal-space-4: 16px;",
        "--portal-elevation-1: var(--portal-dark-elevation-1);",
        "--portal-elevation-2: var(--portal-dark-elevation-2);",
        "--portal-elevation-3: var(--portal-dark-elevation-3);",
        "--portal-scrim: var(--portal-dark-scrim);",
    ):
        assert token in aliases

    assert "border-radius: var(--portal-radius-md);" in theme_source
    assert "box-shadow: var(--portal-elevation-3);" in theme_source
    assert "background: var(--portal-scrim);" in theme_source
    assert "width: var(--portal-icon-md);" in theme_source
```

- [ ] **Step 2: Run the focused test and verify it fails for the missing tokens**

Run from the worktree:

```powershell
python -m pytest -q tests/test_portal_aura_theme_contracts.py -k geometry_tokens
```

Expected: FAIL because `--portal-radius-md` and the new token aliases are not
declared yet.

### Task 2: Implement the canonical Aura token layer

**Files:**
- Modify: `static/portal/portal-theme.css:1-150` (light primitives and aliases)
- Modify: `static/portal/portal-theme.css:80-145` (dark primitives)
- Modify: `static/portal/portal-theme.css:13680-13740` (dark semantic aliases)
- Test: `tests/test_portal_aura_theme_contracts.py`

- [ ] **Step 1: Add minimal light primitives and semantic aliases**

Add the 4/8px spacing tokens, `--portal-radius-md`, elevation levels, icon
sizes and `--portal-scrim`/`--portal-scrim-blur` to the canonical `:root`.
Use the existing light shadow values as the source for elevation levels and
keep all custom-property names under the `--portal-` namespace.

- [ ] **Step 2: Add dark primitives and remap semantic aliases**

Add dark elevation and scrim primitives alongside the existing dark set, then
map the semantic elevation/scrim aliases in
`:root[data-portal-theme="dark"]`. Geometry and icon sizes remain identical
across themes so layout does not jump on theme switch.

- [ ] **Step 3: Switch representative consumers to aliases**

Use `var(--portal-radius-md)` for the existing medium-radius surfaces, use
`var(--portal-elevation-3)` for the command dialog, use
`var(--portal-scrim)` and `var(--portal-scrim-blur)` for the command/sidebar
backdrops, and use `var(--portal-icon-md)` for theme/auth context icons. Keep
transitions and reduced-motion rules unchanged.

- [ ] **Step 4: Run the focused test and verify it passes**

```powershell
python -m pytest -q tests/test_portal_aura_theme_contracts.py -k geometry_tokens
```

Expected: PASS.

### Task 3: Run critical Web UI verification

**Files:** No additional files.

- [ ] **Step 1: Compile and syntax-check changed assets**

```powershell
python -m py_compile tests/test_portal_aura_theme_contracts.py
node --check static/portal/portal-theme.js
```

- [ ] **Step 2: Run focused Aura contracts**

```powershell
python -m pytest -q tests/test_portal_aura_theme_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py
```

- [ ] **Step 3: Check whitespace and scope**

```powershell
git diff --check origin/main...HEAD
git diff --name-only origin/main...HEAD
```

Expected changed scope: the contract test, `portal-theme.css`, and this
design/plan documentation only; no Bot or CSKH files.

- [ ] **Step 4: Commit and review**

```powershell
git add tests/test_portal_aura_theme_contracts.py static/portal/portal-theme.css docs/superpowers/specs/2026-08-02-aura-token-foundation-design.md docs/superpowers/plans/2026-08-02-aura-token-foundation.md
git commit -m "Add Aura geometry and surface tokens"
```

Request spec and code-quality review before pushing the PR. CI must be green
before merge; use a merge commit so the next PR starts from an auditable base.
