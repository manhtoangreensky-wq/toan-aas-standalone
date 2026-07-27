# TOAN AAS Teal–Sky Product Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Web App and public landing feel like one professional
Vietnamese-first teal–sky product system while retaining all security and
workflow authority boundaries.

**Architecture:** The Web App uses the shared Portal shell. A final semantic CSS
layer owns paint and shared geometry; `portal.js` adds only the semantic
desktop access-context markup needed for a balanced access layout;
`portal-i18n.js` owns fixed copy. The public landing is implemented after the
Web App merge in its separate repository, using the documented token roles
without importing Web App files.

**Tech Stack:** FastAPI-rendered Portal, semantic HTML, vanilla JavaScript, CSS
custom properties, Python/pytest static contracts, and a separate static public
landing.

---

## File map

- `static/portal/portal-theme.css` — semantic tokens, geometry, light-card
  typography primitives and responsive access layout.
- `static/portal/portal.js` — access renderer; preserves actions/forms while
  adding an i18n-backed context panel.
- `static/portal/portal-i18n.js` — equal VI/EN/ZH fixed access copy.
- `templates/portal_shell.html`, `static/portal/manifest.webmanifest`, and
  `static/portal/offline.html` — browser/PWA chrome only.
- `tests/test_teal_sky_product_redesign_contracts.py` — narrow static
  contracts for visual ownership and access safety.
- `tests/test_login_app_ux_contracts.py` and
  `tests/test_teal_cyan_ui_foundation_contracts.py` — assertions intentionally
  superseded by the approved colour values and desktop access rail.

### Task 1: Add the regression contract before visual implementation

**Files:**
- Create: `tests/test_teal_sky_product_redesign_contracts.py`
- Modify: `tests/test_login_app_ux_contracts.py`
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [ ] Write a failing source contract for the final redesign marker, new
  semantic access context, desktop `intro card` grid, shared light-card
  typography and aligned header/content geometry.
- [ ] Run:

  ```powershell
  python -m pytest -q tests/test_teal_sky_product_redesign_contracts.py tests/test_login_app_ux_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py -p no:cacheprovider
  ```

  Expected: failure until the design layer and access context exist.
- [ ] Keep the assertions focused on route/session ownership; do not assert
  fake data or visual text unrelated to the redesign.

### Task 2: Implement token, shared-card and PWA visual ownership

**Files:**
- Modify: `static/portal/portal-theme.css`
- Modify: `templates/portal_shell.html`
- Modify: `static/portal/manifest.webmanifest`
- Modify: `static/portal/offline.html`

- [ ] Change only root semantic values to the approved palette:
  `#f3fbfc`, `#0d9488`, `#0369a1`, `#063b47`, `#073a45`,
  `#456b77` and `#e6f8f7`.
- [ ] Append a single final token-only layer with the marker
  `/* Teal–Sky Product Redesign -- final semantic layer. */`.
- [ ] Scope that layer to signed non-auth/non-landing shells and reset audited
  title/value primitives to `--portal-ink`, support copy to
  `--portal-muted`, and safe non-status links/icons to the accessible teal
  action token.
- [ ] Use the same content-centering calculation for the desktop header and
  main rail; retain existing mobile safe-area rules.
- [ ] Set template, manifest and offline chrome to the same deep teal family.
  Do not change service worker cache policy or app route behaviour.
- [ ] Run:

  ```powershell
  python -m pytest -q tests/test_teal_sky_product_redesign_contracts.py tests/test_product_harmony_ui_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py -p no:cacheprovider
  ```

### Task 3: Implement the balanced access rail and reviewed locale copy

**Files:**
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal-theme.css`
- Modify: `tests/test_login_app_ux_contracts.py`
- Modify: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] Add reviewed VI/EN/ZH keys for an access-context label, title, three
  concise factual points and a help label.
- [ ] Add one semantic `.portal-auth-context` inside the existing
  `.portal-auth-shell`, with an existing inline SVG icon. It must not add a
  new provider, action, field, session state or product claim.
- [ ] At `min-width: 981px`, make the access shell a two-column grid with
  `minmax(420px, 480px)` for the real form, a bounded contextual left column,
  aligned top edges, and a shared 1180px outer rail.
- [ ] Below that breakpoint, return to one column, hide the context panel and
  retain 44px locale/control touch targets.
- [ ] Run:

  ```powershell
  python -m pytest -q tests/test_login_app_ux_contracts.py tests/test_auth_entrypoint_layout_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_i18n_locale_contracts.py -p no:cacheprovider
  ```

### Task 4: Verify and ship the Web App PR

**Files:**
- Modify: `docs/superpowers/specs/2026-07-27-unified-teal-sky-product-redesign.md`
- Modify: `docs/superpowers/plans/2026-07-27-teal-sky-product-redesign.md`

- [ ] Run:

  ```powershell
  python -m pytest -q tests/test_teal_sky_product_redesign_contracts.py tests/test_product_harmony_ui_contracts.py tests/test_teal_cyan_ui_foundation_contracts.py tests/test_login_app_ux_contracts.py tests/test_auth_entrypoint_layout_contracts.py tests/test_dashboard_workspace_command_center_contracts.py tests/test_admin_erp_navigation_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_i18n_locale_contracts.py -p no:cacheprovider
  python -m compileall -q app.py copyfast_pages.py
  git diff --check
  ```

- [ ] Inspect `/login`, `/dashboard`, `/admin` and `/welcome` at 375,
  1440 and 2560px. Compare against the four design concepts and add a
  five-point visual-fidelity ledger.
- [ ] Commit one focused Web App PR with no changes to payments, providers,
  bridge authority, session logic or server role gates.

### Task 5: Implement Landing-only follow-up after Web App merge

**Files:**
- Modify: `index.html` in a fresh public-landing worktree from current
  `origin/main`
- Modify/Create: focused landing UI contracts in that repository

- [ ] Establish equivalent local token roles; do not copy a stylesheet across
  repositories and do not touch `bot.py`.
- [ ] Align header, hero, workflow and Website-versus-Workspace explanation to
  a 12-column public rail; preserve only genuine Workspace and Telegram links.
- [ ] Run relevant landing contracts, `git diff --check`, and browser checks
  at 375 and 1440px before a separate Landing-only PR.

## Self-review

- This plan changes presentation and fixed UI copy only. It has no task that
  mutates Bot runtime, payments, provider calls, wallet ledgers, webhooks,
  sessions or role gates.
- The Web App and Landing remain separate PRs and repositories.
- Every implementation task has an independent verification command.
