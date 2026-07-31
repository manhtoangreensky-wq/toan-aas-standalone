# Music & SFX Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the private Music Library, Music Prompt Composer, Music Directions and SFX Cue Sheet customer routes on the approved teal/cyan light application system while preserving their truthful metadata/planning-only boundary.

**Architecture:** Append one final CSS layer to `static/portal/portal-theme.css`, scoped exactly to `.portal-page:is(.portal-music-library, .portal-music-prompt-composer, .portal-music-directions, .portal-sfx-cue-sheet)`. It replaces inherited raw dark panels only for these routes with the shared `--portal-*` semantic surface, text, status, focus and responsive tokens. No JavaScript, endpoint, database, provider, audio, player, catalog, job, wallet, payment, asset, delivery or Bot behavior changes.

**Tech Stack:** FastAPI server-rendered portal, static CSS, pytest static-contract tests.

---

## File map

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — add a final Music/SFX surface contract and make the preceding Image Studio extractor stop at the next final-layer marker.
- Modify: `static/portal/portal-theme.css` — append the token-only Music/SFX final light layer.
- Create: `docs/superpowers/plans/2026-07-31-music-sfx-light-surface.md` — this bounded implementation record.

### Task 1: Lock the Music/SFX presentation contract before CSS changes

- [ ] **Step 1: Write the failing test**

Add `test_light_music_sfx_final_surface_keeps_audio_planning_truthful_and_readable` to `tests/test_teal_cyan_ui_foundation_contracts.py`. Extract the final CSS after this exact marker:

```python
layer = re.search(
    r"/\\* Final light Music and SFX surface \\*/(?P<css>.*)\\Z",
    PORTAL_THEME.read_text(encoding="utf-8"),
    flags=re.DOTALL,
)
assert layer is not None
music_css = layer.group("css")
route = ".portal-page:is(.portal-music-library, .portal-music-prompt-composer, .portal-music-directions, .portal-sfx-cue-sheet)"
assert not re.search(r"(?:#[0-9a-f]{3,8}\\b|(?:linear|radial)-gradient|rgba?\\()", music_css, re.I)
assert not re.search(r"var\\(--(?!portal-)", music_css)
```

Require declarations for all four intro/summary surfaces; their metrics; composer/directions/SFX forms, boundaries, receipts and review cards; the Music Library board/guard/boundary/cards; preset choices and selected state; guard state; metadata and cue/direction rows; warning/review state; hover and focus; and the 700px mobile grids. Require the CSS to use `transform: none;` on hover, `outline: 3px solid var(--portal-focus) !important;` for focus, and no selectors outside the fixed route prefix.

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py -k music_sfx_final_surface
```

Expected: FAIL because the final Music and SFX marker and declarations are not present. The failure must be the missing surface, not an invalid test.

- [ ] **Step 3: Implement the smallest final CSS layer**

Append `/* Final light Music and SFX surface */` to `static/portal/portal-theme.css`. Prefix each new selector with:

```css
.portal-page:is(.portal-music-library, .portal-music-prompt-composer, .portal-music-directions, .portal-sfx-cue-sheet)
```

Use only existing `--portal-surface-light`, `--portal-surface-soft`, `--portal-light-hover-surface`, `--portal-ink`, `--portal-muted`, `--portal-border`, `--portal-border-strong`, `--portal-action`, `--portal-danger`, `--portal-warning` and `--portal-focus` tokens. Summary and working panels become readable white surfaces; selected presets and deterministic direction metadata remain visibly distinct; guarded and review states stay explicit rather than looking like generated audio. Do not introduce a player, audio file, track, provider, catalog mutation, job, payment, export or delivery UI.

- [ ] **Step 4: Verify GREEN and preserve the boundary**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_teal_cyan_ui_foundation_contracts.py
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q tests\test_music_media_portal_contracts.py tests\test_music_directions_portal_contracts.py tests\test_music_prompt_composer_portal_contracts.py tests\test_sfx_cue_sheet_portal_contracts.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all checks pass. Review the diff: only the plan, the static regression contract and the final CSS layer may change.

- [ ] **Step 5: Perform focused read-only browser QA**

When a signed local test session is available, inspect the four Music/SFX routes at desktop and 375px width. Confirm readable state, clear audio/planning guard copy, visible keyboard focus and no horizontal overflow. Do not submit a brief, compose directions/cues, save a note, change a library collection, start a provider call, create a job or initiate payment.

- [ ] **Step 6: Review, commit and merge sequentially**

Perform a scope review and code-quality review. Commit only these files with:

```powershell
git add docs/superpowers/plans/2026-07-31-music-sfx-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Music and SFX light workspace surfaces"
```

Push one branch, open one PR, wait for required checks, merge only after green, then fetch `main` before choosing the next non-video UI surface. Do not deploy Railway for this UI-only change.
