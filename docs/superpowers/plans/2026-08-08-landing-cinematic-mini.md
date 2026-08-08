# Landing Cinematic Mini Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/welcome` visibly cinematic by default, with an explicit Light/Dark control and reduced-motion-safe entrance choreography, while preserving the existing TOAN AAS public landing contract.

**Architecture:** The Portal shell remains the only renderer. `portal.js` supplies landing-only semantic hooks and a two-choice theme control; `portal-motion.js` adds/removes a presentation attribute after the completed shell render; `portal-theme.js` resolves only an unsaved landing visitor to light and synchronizes the new controls. CSS consumes semantic teal–sky tokens and is scoped to the landing lifecycle attribute.

**Tech Stack:** FastAPI public shell, static ES2019 browser modules, CSS custom properties/keyframes, pytest static contract tests, Node syntax checks.

---

### Task 1: Lock the landing contract before changing presentation

**Files:**
- Create: `tests/test_landing_cinematic_mini_contracts.py`
- Modify: `tests/test_landing_motion_test1_contracts.py`
- Modify: `templates/portal_shell.html`

- [ ] **Step 1: Write the failing test**

```python
def test_cinematic_motion_is_default_only_for_welcome_with_a_safe_opt_out() -> None:
    mount = _between(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")
    assert 'window.location.pathname === "/welcome"' in mount
    assert 'new URLSearchParams(window.location.search || "").get("motion") !== "0"' in mount
    assert 'data-landing-motion="cinematic-mini"' in MOTION
```

Add focused assertions that the landing contains only `data-portal-theme-set="light"` and `"dark"`, the controller has no fetch/API/identity words, CSS has reduced-motion-safe visibility, and no selectors target `.portal-shell--workspace` or `.portal-shell--admin`.

Also assert that `portal-motion.js` loads before `portal.js`, static cinematic
classes are applied before reduced-motion skips observers, and the whole
`/welcome` route—not only its animated variant—suppresses the generic
page-enter effect.

- [ ] **Step 2: Run the new test to verify it fails**

Run: `python -m pytest -q tests/test_landing_cinematic_mini_contracts.py -p no:cacheprovider`

Expected: FAIL because the default cinematic lifecycle and two-choice landing control do not exist.

- [ ] **Step 3: Update existing TEST1 expectations to the promoted landing contract**

Replace the assertion that requires `?motion=1` with the reviewed default route plus `?motion=0` opt-out. Retain tests for lifecycle cleanup, IntersectionObserver, rAF, no storage/API, and transform-only motion.

- [ ] **Step 4: Run focused contracts**

Run: `python -m pytest -q tests/test_landing_motion_test1_contracts.py tests/test_landing_cinematic_mini_contracts.py -p no:cacheprovider`

Expected: FAIL until Tasks 2–4 implement every hook.

### Task 2: Add the landing-only Light/Dark control and predictable first paint

**Files:**
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-theme.js`
- Modify: `static/portal/portal-theme.css`

- [ ] **Step 1: Add the minimum landing switch markup**

```js
function renderLandingThemeSwitch() {
  return `<div class="portal-landing-theme-switch" role="group" aria-label="${safeText(uiText("chrome.theme_label", "Giao diện"))}">
    <button type="button" data-portal-theme-set="light">${safeText(uiText("chrome.theme_light", "Sáng"))}</button>
    <button type="button" data-portal-theme-set="dark">${safeText(uiText("chrome.theme_dark", "Tối"))}</button>
  </div>`;
}
```

Use this helper only in `.portal-landing-nav-actions`; do not alter the shared access/workspace toggle markup.

- [ ] **Step 2: Bind the switch through the existing controller**

```js
const explicit = event.target && event.target.closest
  ? event.target.closest("[data-portal-theme-set]") : null;
if (explicit && THEMES.includes(explicit.dataset.portalThemeSet)) {
  event.preventDefault();
  setPreference(explicit.dataset.portalThemeSet);
  return;
}
```

Synchronize each explicit control with `aria-pressed`, `is-active`, and a
translated title. In `readPreference`, return `"light"` only for an unsaved
`/welcome` visit; preserve an explicit saved light/dark value and retain
`"system"` defaults outside that route.

- [ ] **Step 3: Add responsive semantic CSS**

Use 44 px minimum targets, the existing `--portal-*` colors, and visible
focus rings. Keep the selector landing-only and collapse labels only when the
existing locale/navigation layout needs space.

- [ ] **Step 4: Run theme and landing contract tests**

Run: `python -m pytest -q tests/test_portal_aura_theme_contracts.py tests/test_landing_cinematic_mini_contracts.py -p no:cacheprovider`

Expected: PASS after the implementation is complete.

### Task 3: Promote the cinematic lifecycle and add the aperture entrance

**Files:**
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-motion.js`
- Modify: `static/portal/portal-theme.css`

- [ ] **Step 1: Change the landing activation boundary**

```js
const landingMotionRoute = isLanding
  && window.location.pathname === "/welcome";
const landingMotionEnabled = landingMotionRoute
  && new URLSearchParams(window.location.search || "").get("motion") !== "0";
```

Set `main.dataset.portalMotionSkipEnter` from `landingMotionRoute`, not only
`landingMotionEnabled`, so the opt-out page has no generic replacement
animation. Call `motion.unmountLanding()` before every shell replacement and call
`motion.mountLanding(main)` only after the landing HTML has rendered. Do not
change routes, initial server HTML, API requests, or the content of existing
CTAs.

- [ ] **Step 2: Add the minimal motion state**

```js
root.setAttribute("data-landing-motion", "cinematic-mini");
hero.classList.add("landing-motion-hero", "landing-cinematic-hero");
preview.classList.add("landing-cinematic-preview");
```

Apply these static classes before any `prefersReducedMotion()` early return.
Load `portal-motion.js` before `portal.js` in `templates/portal_shell.html` so
the initial mount cannot miss the lifecycle. Keep current header, observer,
rAF, `focusin`, and cleanup behaviours. Stage
the four existing `.portal-landing-preview-steps > span` elements with classes
only; do not insert synthetic workflow data.

- [ ] **Step 3: Add tokenized CSS effects**

Define landing-local duration/easing aliases in `:root` and scope every new
rule under `[data-landing-motion="cinematic-mini"]` inside
`prefers-reduced-motion: no-preference`. Implement a one-time clip-path/opacity
hero reveal, a shallow transform/opacity aperture frame, and four staged
preview-step reveals. Use pseudo-elements for the static abstract frame; do
not use images, video, infinite animation, `will-change`, size animation, or
scroll-linked JavaScript.

- [ ] **Step 4: Keep reduced-motion and focus states truthful**

```css
@media (prefers-reduced-motion: reduce) {
  [data-landing-motion] .landing-cinematic-preview,
  [data-landing-motion] .landing-motion-hero * {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
    clip-path: none !important;
  }
}
```

Use the project’s existing global visibility fallback rather than hiding any
content in initial HTML. Give decorative pseudo-elements `pointer-events: none`
and reset `clip-path` in the existing focus override so focused controls are
never visually delayed.

- [ ] **Step 5: Run focused contracts and JavaScript syntax checks**

Run: `python -m pytest -q tests/test_landing_motion_test1_contracts.py tests/test_landing_cinematic_mini_contracts.py tests/test_portal_aura_theme_contracts.py -p no:cacheprovider`

Run: `node --check static/portal/portal.js; node --check static/portal/portal-motion.js; node --check static/portal/portal-theme.js`

Expected: PASS with no syntax errors.

### Task 4: Verify public route safety and review the rendered result

**Files:**
- Modify: `design-system/toan-aas-web-app/pages/welcome.md`
- Create: `docs/ui-qa/2026-08-08-landing-cinematic-mini-fidelity.md`

- [ ] **Step 1: Document the approved override**

Record that `/welcome` defaults to Light only when no explicit browser choice
exists, exposes two explicit choices, and uses a presentation-only aperture
motion. State that the customer app/ERP, routes, APIs, sessions and providers
are not changed.

- [ ] **Step 2: Start a local server and review real rendering**

Use the Browser plugin at `/welcome`, `/welcome?motion=0`, and a 375 px mobile
viewport. Verify header compaction, light/dark controls, first hero entrance,
scroll reveal, card/CTA focus, and reduced motion.

- [ ] **Step 3: Write the fidelity ledger**

Compare the supplied reference and rendered landing at five points: cinematic
opening rhythm, teal–sky palette retention, title hierarchy, abstract aperture
instead of copied spa imagery, and mobile frame/controls. Record any
intentional deviation: TOAN AAS uses a semantic product preview rather than a
photographic background.

- [ ] **Step 4: Run release-local verification**

Run: `python -m pytest -q tests/test_landing_motion_test1_contracts.py tests/test_landing_cinematic_mini_contracts.py tests/test_portal_aura_theme_contracts.py tests/test_welcome_public_companion_contracts.py -p no:cacheprovider`

Run: `git diff --check`

Expected: all selected tests pass and whitespace check emits no output.
