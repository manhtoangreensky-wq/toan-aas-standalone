# Landing Motion Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the public `/welcome` cinematic sequence visibly replay whenever the Landing route mounts, while preserving reduced-motion safety and keeping the animation presentation-only.

**Architecture:** The existing Portal motion helper remains the sole lifecycle owner. It will publish a small `intro → settled` state on the rendered Landing root, schedule every route mount independently, and clean all timers/listeners when unmounted. CSS stays scoped to the public Landing root and uses that state only for one-shot visual sequencing and scroll reveals.

**Tech Stack:** FastAPI portal shell, vanilla JavaScript, CSS keyframes, Python static contract tests, Browser rendered QA.

---

### Task 1: Lock the repeatable visible lifecycle

**Files:**

- Create: `tests/test_landing_motion_visible_contracts.py`
- Modify: `static/portal/portal-motion.js`

- [ ] **Step 1: Write the failing lifecycle contract**

```python
def test_landing_intro_replays_on_each_mount_and_has_a_real_lifecycle() -> None:
    state = _run_motion_harness()
    assert state["first"] == {"phase": "settled", "ready": True}
    assert state["second_before_frame"] == {"phase": "intro", "ready": False}
    assert state["second"] == {"phase": "settled", "ready": True}
    assert state["frame_requests"] == 2
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest -q tests/test_landing_motion_visible_contracts.py`

Expected: FAIL because the old global `landingHeroHasEntered` bypasses the animation frame on the second Landing mount and no lifecycle phase exists.

- [ ] **Step 3: Implement the minimal lifecycle repair**

```javascript
root.setAttribute("data-landing-motion-phase", "intro");
heroFrame = window.requestAnimationFrame(() => hero.classList.add("is-ready"));
settledTimer = window.setTimeout(
  () => root.setAttribute("data-landing-motion-phase", "settled"),
  LANDING_SEQUENCE_SETTLE_DELAY_MS
);
```

Remove the cross-route `landingHeroHasEntered` gate. `unmountLanding()` must cancel the frame/timer and remove both Landing data attributes.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `python -m pytest -q tests/test_landing_motion_visible_contracts.py`

Expected: PASS.

### Task 2: Make the one-shot sequence visible without creating background activity

**Files:**

- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_landing_motion_visible_contracts.py`

- [ ] **Step 1: Extend the failing contract for visible state sequencing**

```python
assert '[data-landing-motion-phase="intro"]' in THEME
assert "--portal-landing-motion-sequence" in THEME
assert "@media (prefers-reduced-motion: reduce)" in THEME
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest -q tests/test_landing_motion_visible_contracts.py`

Expected: FAIL because the current stylesheet has no lifecycle phase or shared sequence duration token.

- [ ] **Step 3: Add the scoped sequence styles**

Use a 1.8–2.0 second one-shot sequence for the curtain, aperture, preview and four preview steps. Keep transforms/opacity/clip-path only, preserve the existing scroll-reveal choreography, and add no fetches, storage, provider calls, infinite animation, or authenticated-route selector.

- [ ] **Step 4: Run focused tests and syntax validation**

Run:

```powershell
python -m pytest -q tests/test_landing_motion_visible_contracts.py tests/test_landing_cinematic_mini_contracts.py tests/test_landing_motion_test1_contracts.py
node --check static/portal/portal-motion.js
git diff --check
```

Expected: all commands exit 0.

### Task 3: Verify the rendered result and ship the focused fix

**Files:**

- Modify: no additional production files unless rendered QA finds a defect

- [ ] **Step 1: Render `/welcome` at desktop and mobile**

Verify fresh load, SPA-style remount, scroll reveal, light/dark theme and `prefers-reduced-motion` fallback. Check console errors and capture the intro and settled states.

- [ ] **Step 2: Commit and open a focused PR**

```powershell
git add static/portal/portal-motion.js static/portal/portal-theme.css tests/test_landing_motion_visible_contracts.py docs/superpowers/plans/2026-08-09-landing-motion-visible.md
git commit -m "fix: make landing motion visibly replay"
git push -u origin feature/p0-web-landing-motion-visible
```

- [ ] **Step 3: Merge only after checks pass**

Verify the GitHub quality gate, merge the focused PR into `main`, then check the deployed `/welcome` asset version and motion lifecycle.
