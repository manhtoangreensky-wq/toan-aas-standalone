# Teal–Sky UI Motion Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Add a small, accessible presentation-only motion foundation to the existing teal–sky portal without changing feature, data, payment, provider or authorization behavior.

**Architecture:** Keep portal.js as the renderer and add one small non-module portal-motion.js utility loaded after it. The utility wraps only the existing synchronous DOM replacement and falls back to a regular render when View Transitions or motion are unavailable. The theme owns timing/easing/keyframes; the renderer only supplies surface and one-shot lifecycle attributes.

**Tech Stack:** FastAPI, server-rendered HTML shell, vanilla JavaScript, vanilla CSS, pytest static contracts.

---

## File structure and ownership

| File | Responsibility |
| --- | --- |
| static/portal/portal-motion.js | Browser-only lifecycle utility; no data, storage, routing or authority behavior. |
| static/portal/portal-theme.css | Canonical semantic motion/elevation tokens and motion rules. |
| static/portal/portal.js | Supplies landing/auth/workspace surface mode and calls the utility around the existing renderer. |
| templates/portal_shell.html | Deterministic script order. |
| copyfast_pages.py | Asset build hash and no-environment fallback shell. |
| static/portal/service-worker.js | Public shell asset allow-list only. |
| docs/UX_APP_FIRST_REDESIGN.md | Correct teal–sky app-first and motion direction. |
| design-system/toan-aas-web-app/MASTER.md | Documents token/lifecycle ownership. |
| tests/test_portal_motion_foundation_contracts.py | New asset-graph, no-authority, token and mount contracts. |
| tests/test_app_first_ui_system_contracts.py | Ensures the app-first document remains accurate. |

### Task 1: Define the red presentation contract

**Files:**

- Create: tests/test_portal_motion_foundation_contracts.py
- Modify: tests/test_app_first_ui_system_contracts.py

- [ ] **Step 1: Write the failing test file.**

Create tests/test_portal_motion_foundation_contracts.py with this exact starting content:

    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    SHELL = (ROOT / "templates" / "portal_shell.html").read_text(encoding="utf-8")
    PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")
    WORKER = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
    PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
    MOTION = ROOT / "static" / "portal" / "portal-motion.js"

    MOTION_SCRIPT = '<script src="/static/portal/portal-motion.js?v=__PORTAL_ASSET_VERSION__" defer></script>'
    PORTAL_SCRIPT = '<script src="/static/portal/portal.js?v=__PORTAL_ASSET_VERSION__" defer></script>'
    INTEGRATION_SCRIPT = '<script src="/static/portal/integration.js?v=__PORTAL_ASSET_VERSION__" defer></script>'

    def test_motion_asset_is_public_shell_only_and_loads_between_renderer_and_hydration() -> None:
        assert MOTION.is_file()
        assert SHELL.index(PORTAL_SCRIPT) < SHELL.index(MOTION_SCRIPT) < SHELL.index(INTEGRATION_SCRIPT)
        assert '"portal-motion.js",' in PAGES
        assert MOTION_SCRIPT in PAGES.replace('\\"', '"')
        shell_block = WORKER[WORKER.index("const SHELL = Object.freeze([") : WORKER.index("]);\nconst SHELL_PATHS")]
        assert '"/static/portal/portal-motion.js",' in shell_block

    def test_motion_utility_is_presentation_only_and_has_a_reduced_motion_fallback() -> None:
        source = MOTION.read_text(encoding="utf-8")
        assert "window.TOANAASPortalMotion = Object.freeze(" in source
        assert "document.startViewTransition" in source
        assert "prefers-reduced-motion: reduce" in source
        for forbidden in ("fetch(", "localStorage", "sessionStorage", "innerHTML", "/api/", "csrf"):
            assert forbidden not in source

    def test_theme_owns_shared_motion_tokens_and_one_shot_transform_opacity_rules() -> None:
        root = THEME[THEME.index(":root {") : THEME.index("\n}", THEME.index(":root {"))]
        for token in (
            "--portal-motion-fast: 140ms;",
            "--portal-motion-base: 220ms;",
            "--portal-motion-slow: 420ms;",
            "--portal-motion-distance: 10px;",
            "--portal-motion-ease-standard: cubic-bezier(.2, .8, .2, 1);",
            "--portal-motion-ease-emphasis: cubic-bezier(.16, 1, .3, 1);",
        ):
            assert token in root
        assert "@keyframes portal-motion-enter" in THEME
        assert "@keyframes portal-motion-pop" in THEME
        assert '[data-portal-motion="enter"]' in THEME
        assert '[data-portal-motion="pop"]' in THEME
        assert "@media (prefers-reduced-motion: reduce)" in THEME

    def test_mount_exposes_surface_mode_and_delegates_only_the_dom_swap_to_motion() -> None:
        start = PORTAL.index("function mountPortal(override)")
        mount = PORTAL[start : PORTAL.index("window.TOANAASPortal", start)]
        assert 'const surface = isLanding ? "landing" : (isAuth ? "auth" : "workspace");' in mount
        assert "shell.dataset.portalSurface = surface;" in mount
        assert "document.body.dataset.portalSurface = surface;" in mount
        assert "const renderShell = () => {" in mount
        assert "motion.replace(shell, main, renderShell);" in mount
        assert "restoreFocus(focus);" in mount

In tests/test_app_first_ui_system_contracts.py, add these assertions to test_app_first_direction_is_documented_without_changing_authority_boundaries:

    assert "light teal application canvas with white working surfaces" in REDESIGN
    assert "dark slate foundation" not in REDESIGN
    assert "prefers-reduced-motion" in REDESIGN

- [ ] **Step 2: Run the new test to verify it fails.**

Run:

    & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_portal_motion_foundation_contracts.py tests/test_app_first_ui_system_contracts.py

Expected: FAIL because the asset, deterministic registration, root tokens and mount lifecycle do not exist yet.

- [ ] **Step 3: Commit only the red contract.**

    git add tests/test_portal_motion_foundation_contracts.py tests/test_app_first_ui_system_contracts.py
    git commit -m "test: define portal motion foundation contract"

### Task 2: Add the public motion asset and deterministic registrations

**Files:**

- Create: static/portal/portal-motion.js
- Modify: templates/portal_shell.html
- Modify: copyfast_pages.py:58-67,335
- Modify: static/portal/service-worker.js:30-40

- [ ] **Step 1: Write the smallest safe browser utility.**

Create static/portal/portal-motion.js exactly as follows:

    (() => {
      "use strict";

      const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";

      function prefersReducedMotion() {
        return typeof window.matchMedia === "function" && window.matchMedia(REDUCED_QUERY).matches;
      }

      function finish(element) {
        if (element) element.removeAttribute("data-portal-motion");
      }

      function enter(element, kind = "enter") {
        if (!element || prefersReducedMotion()) {
          finish(element);
          return;
        }
        element.setAttribute("data-portal-motion", kind === "pop" ? "pop" : "enter");
        element.addEventListener("animationend", () => finish(element), { once: true });
      }

      function replace(shell, main, render) {
        const apply = () => render();
        if (prefersReducedMotion() || typeof document.startViewTransition !== "function") {
          apply();
          enter(main);
          return;
        }
        const transition = document.startViewTransition(apply);
        transition.ready.catch(() => {});
        transition.finished.catch(() => {});
        enter(main);
      }

      window.TOANAASPortalMotion = Object.freeze({ enter, replace, prefersReducedMotion });
    }());

This file intentionally does not read session data, route data, DOM HTML strings, local/session storage or APIs.

- [ ] **Step 2: Register it in every public shell code path.**

In templates/portal_shell.html and the fallback string from copyfast_pages._fallback_template(), insert this exact line after portal.js and before integration.js:

    <script src="/static/portal/portal-motion.js?v=__PORTAL_ASSET_VERSION__" defer></script>

Insert "portal-motion.js", directly after "portal.js", in _PORTAL_BUILD_SOURCE_FILES. Insert "/static/portal/portal-motion.js", after the portal renderer entry in the service worker SHELL allow-list. Do not add API data, signed routes or a runtime cache rule.

- [ ] **Step 3: Run the asset-only test subset.**

Run:

    & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_portal_motion_foundation_contracts.py -k 'motion_asset_is_versioned_between_portal_and_integration_and_pre_cached or motion_utility_is_browser_only_progressive_enhancement'

Expected: PASS. Theme and mount assertions remain red until Task 3.

- [ ] **Step 4: Commit the isolated asset graph.**

    git add static/portal/portal-motion.js templates/portal_shell.html copyfast_pages.py static/portal/service-worker.js
    git commit -m "feat: add portal motion shell utility"

### Task 3: Add semantic motion tokens and mount lifecycle

**Files:**

- Modify: static/portal/portal-theme.css:4-86 and final semantic layer
- Modify: static/portal/portal.js:25741-25749,27819-27905

- [ ] **Step 1: Add canonical tokens to the first theme root.**

Place these declarations beside --portal-transition in the first root block:

    --portal-motion-fast: 140ms;
    --portal-motion-base: 220ms;
    --portal-motion-slow: 420ms;
    --portal-motion-distance: 10px;
    --portal-motion-ease-standard: cubic-bezier(.2, .8, .2, 1);
    --portal-motion-ease-emphasis: cubic-bezier(.16, 1, .3, 1);
    --portal-elevation-float: 0 12px 30px rgba(2, 20, 29, .16);

Append one scoped final-theme block instead of changing route CSS:

    @keyframes portal-motion-enter {
      from { opacity: 0; transform: translateY(var(--portal-motion-distance)); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes portal-motion-pop {
      from { opacity: 0; transform: scale(.96); }
      to { opacity: 1; transform: scale(1); }
    }

    @media (prefers-reduced-motion: no-preference) {
      [data-portal-main][data-portal-motion="enter"] {
        animation: portal-motion-enter var(--portal-motion-base) var(--portal-motion-ease-emphasis) both;
      }
      [data-portal-motion="pop"] {
        animation: portal-motion-pop var(--portal-motion-fast) var(--portal-motion-ease-standard) both;
      }
      .portal-sidebar,
      .portal-command-dialog,
      .portal-toast {
        transition-duration: var(--portal-motion-base);
        transition-timing-function: var(--portal-motion-ease-standard);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      [data-portal-motion] { animation: none !important; transform: none !important; }
    }

The change must animate only opacity/transform. It must not animate grid, width, height, table rows or scroll position.

- [ ] **Step 2: Wrap only the current DOM swap.**

In mountPortal, immediately after isLanding/isAuth, add:

    const surface = isLanding ? "landing" : (isAuth ? "auth" : "workspace");
    shell.dataset.portalSurface = surface;
    document.body.dataset.portalSurface = surface;

Replace only the three direct sidebar/header/main innerHTML assignments with:

    const renderShell = () => {
      sidebar.innerHTML = renderSidebar(page, context);
      header.innerHTML = renderHeader(page, context);
      main.innerHTML = renderPage(page, context);
    };
    const motion = window.TOANAASPortalMotion;
    if (motion && typeof motion.replace === "function") motion.replace(shell, main, renderShell);
    else renderShell();

Keep all existing post-render form synchronization, interaction binding and restoreFocus(focus) in the same sequence. In showToast, after append and before the existing 4800ms timeout, add:

    const motion = window.TOANAASPortalMotion;
    if (motion && typeof motion.enter === "function") motion.enter(toast, "pop");

- [ ] **Step 3: Run the focused contract suite.**

Run:

    & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_portal_motion_foundation_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_teal_sky_product_redesign_contracts.py tests/test_app_first_ui_system_contracts.py

Expected: PASS. If a legacy theme test fails, preserve its documented visual boundary with a final theme override; do not weaken data or authority tests.

- [ ] **Step 4: Commit the presentation lifecycle.**

    git add static/portal/portal-theme.css static/portal/portal.js tests/test_portal_motion_foundation_contracts.py
    git commit -m "feat: add portal motion lifecycle"

### Task 4: Reconcile documentation and verify safety

**Files:**

- Modify: docs/UX_APP_FIRST_REDESIGN.md
- Modify: design-system/toan-aas-web-app/MASTER.md
- Modify: tests/test_app_first_ui_system_contracts.py

- [ ] **Step 1: Correct the conflicting visual direction.**

In docs/UX_APP_FIRST_REDESIGN.md, replace the obsolete phrase quiet dark slate foundation with the exact phrase light teal application canvas with white working surfaces. State that deep teal is reserved for the navigation rail. Replace the motion line with:

    - **Motion:** route, drawer, modal, toast and status feedback use the shared 140/220/420ms token family with opacity/transform only; all non-essential motion respects prefers-reduced-motion.

In design-system/toan-aas-web-app/MASTER.md, add a short Motion ownership section that names portal-theme.css as the token authority and portal-motion.js as the lifecycle utility. State that Customer and ERP will use distinct visual shells while server-issued access remains canonical.

- [ ] **Step 2: Run regression, syntax and whitespace checks.**

Run:

    & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m py_compile copyfast_pages.py
    & 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_portal_motion_foundation_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_teal_sky_product_redesign_contracts.py tests/test_app_first_ui_system_contracts.py tests/test_portal_navigation_ux_contracts.py tests/test_portal_i18n_bundle_contracts.py
    git diff --check

Expected: all targeted tests pass, Python compilation passes and git diff --check has no output.

- [ ] **Step 3: Perform focused browser verification.**

Start the FastAPI app using safe local flags only, then inspect /login, /dashboard, /admin and /welcome at 375, 768, 1024 and 1440px. Verify page content renders without JavaScript errors; reduced motion removes one-shot animation but keeps content/focus/navigation usable; drawer and command palette retain keyboard focus behavior; toast text remains readable; and the public service-worker allow-list does not add a private route.

Capture browser screenshots for the PR fidelity ledger. Do not put generated concept images in static/.

- [ ] **Step 4: Commit docs and verification-facing contract.**

    git add docs/UX_APP_FIRST_REDESIGN.md design-system/toan-aas-web-app/MASTER.md tests/test_app_first_ui_system_contracts.py
    git commit -m "docs: align teal sky motion system"

### Task 5: Prepare one narrow PR

**Files:**

- Verify: only files named in Tasks 1–4

- [ ] **Step 1: Inspect scope.**

Run:

    git status --short
    git diff origin/main...HEAD --check
    git diff --stat origin/main...HEAD

Expected: only the shell asset, theme/renderer presentation hooks, docs and targeted tests changed. No Bot, payment, provider, bridge, registry, database or LocalVideoStudio26 file may be included.

- [ ] **Step 2: Push and open the PR.**

    git push -u origin feature/p0-webapp-ui-motion-foundation
    gh pr create --base main --head feature/p0-webapp-ui-motion-foundation --title "Add teal sky portal motion foundation" --body "Summary: reduced-motion-safe portal lifecycle utility; teal-sky motion tokens; no business, payment, provider or authorization change. Verification: targeted static contracts, py_compile, diff check and browser QA at 375/768/1024/1440."

Expected: a focused PR that can merge before the Customer Workspace shell PR begins.
