# Reference-first Feature Catalog and Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing feature directory and Media Studio into a polished, reference-informed TOAN AAS customer flow without copying third-party source/assets or changing business authority.

**Architecture:** Preserve the registry-driven feature directory and use a static, route-only Studio rail. The Portal i18n bundle owns fixed copy, the Portal motion helper enhances existing semantic content, and final theme overrides own token-based presentation.

**Tech Stack:** FastAPI static Portal, vanilla JavaScript, CSS custom properties, Portal i18n, pytest, Node syntax checks and browser visual QA.

---

### Task 1: Lock the reference-first boundary with RED contracts

**Files:**

- Create: `tests/test_reference_first_catalog_studio_contracts.py`
- Test: `tests/test_reference_first_catalog_studio_contracts.py`

- [ ] Write contracts for equal VI/EN/ZH `mediaStudio.*` keys.
- [ ] Require a route-only six-stage Studio rail with registered destination paths.
- [ ] Exclude request/action/provider/payment/wallet/output fabrication from the renderer.
- [ ] Require localized Studio document title and description plus workspace/reduced-motion selectors.
- [ ] Run the focused test and record expected RED failures.

### Task 2: Add reviewed Studio fixed copy

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Test: `tests/test_reference_first_catalog_studio_contracts.py`

- [ ] Add identical `mediaStudio.*` keysets to VI, EN and ZH.
- [ ] Merge only the fixed interface namespace into the Portal bundle.
- [ ] Keep all server/customer/provider values outside the translation catalog.

### Task 3: Replace the legacy Studio sequence with the route-only rail

**Files:**

- Modify: `static/portal/portal.js`
- Test: `tests/test_reference_first_catalog_studio_contracts.py`

- [ ] Add a small `mediaStudioText` presentation helper.
- [ ] Render Discover → Brief → Plan → Review → Jobs → Assets using existing customer routes.
- [ ] Add localized `/studio` title and description routing.
- [ ] Do not introduce network requests, browser action dispatch, price, provider, payment, wallet, job or output authority.

### Task 4: Add Aura rail presentation and lifecycle motion

**Files:**

- Modify: `static/portal/portal-theme.css`
- Modify: `static/portal/portal-motion.js`
- Test: `tests/test_reference_first_catalog_studio_contracts.py`

- [ ] Add narrowly scoped semantic CSS for the Studio intro, connected rail and responsive layout.
- [ ] Include Studio shell/steps in the existing workspace reveal lifecycle.
- [ ] Extend the reduced-motion reset for every new Studio motion class.

### Task 5: Review and verify

**Files:**

- Review: `static/portal/portal.js`, `static/portal/portal-i18n.js`, `static/portal/portal-theme.css`, `static/portal/portal-motion.js`, `tests/test_reference_first_catalog_studio_contracts.py`

- [ ] Run focused contracts, adjacent feature/motion/safety regressions, Node syntax checks and `git diff --check`.
- [ ] Use the browser to inspect `/features` and `/studio` at desktop/mobile in light/dark; check focus, no horizontal overflow and reduced-motion behavior.
- [ ] Inspect the full diff, confirm protected domains did not change, then commit the cohesive slice only after fresh evidence.
