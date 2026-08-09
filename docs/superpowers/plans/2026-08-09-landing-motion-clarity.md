# Landing Motion Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Make landing scroll and pointer motion visibly section-specific while keeping opt-out and keyboard behavior correct.

**Architecture:** Keep the existing `TOAN AASPortalMotion.mountLanding` lifecycle and CSS custom-property scroll signal. Add one small replay availability helper, scoped CSS variants, and static contract tests; no new runtime dependency or business-state path.

**Tech Stack:** Vanilla browser JavaScript, semantic HTML rendered by `static/portal/portal.js`, tokenized CSS, pytest contract tests.

---

### Task 1: Lock the regression contracts

**Files:**
- Modify: `tests/test_landing_scroll_motion_contracts.py`

- [ ] Add tests asserting static/reduced-motion landing states hide and disable `[data-landing-motion-replay]`.
- [ ] Add a test asserting replay focus is excluded from the broad hero focus reveal override.
- [ ] Add a test extracting `portal-landing-preview-scan` and asserting it contains `opacity`/`transform` but no `box-shadow` keyframe declarations.
- [ ] Add a test for preview/workflow/trust pointer-specific selectors.
- [ ] Run `pytest -q tests/test_landing_scroll_motion_contracts.py`; expected result is RED because the current branch has none of these contracts.

### Task 2: Make opt-out controls truthful

**Files:**
- Modify: `static/portal/portal-motion.js`
- Modify: `static/portal/portal.js`

- [ ] Add a helper that sets replay `hidden`, `disabled`, and a `data-landing-motion-replay-disabled` marker together.
- [ ] Call it before the reduced-motion early return and restore it during lifecycle cleanup.
- [ ] In `mountLandingMotion`, hide/disable the replay control when `/welcome?motion=0` skips the motion module.

### Task 3: Polish the motion language by section

**Files:**
- Modify: `static/portal/portal-theme.css`

- [ ] Remove `box-shadow` interpolation from the finite preview scan keyframes.
- [ ] Exclude replay focus from the keyboard reveal override.
- [ ] Add bounded preview pointer tilt and distinct workflow/trust pointer responses using existing CSS variables and 150–300ms token timing.
- [ ] Keep reduced-motion selectors forcing visible, non-transformed content.

### Task 4: Verify and hand off

**Files:** none

- [ ] Run focused tests, `node --check static/portal/portal-motion.js`, `node --check static/portal/portal.js`, and `git diff --check`.
- [ ] Run the Browser smoke path `/welcome → scroll workflow → scroll final`, inspect state changes and console logs, then test `?motion=0` and both themes.
- [ ] Commit the focused change, push one PR, wait for CI, and merge only after the gate is green.
