# Customer Dashboard Decision Motion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the customer dashboard feel responsive and intentional while preserving immediate visibility of canonical information.

**Architecture:** Reuse the existing browser-only workspace lifecycle. Add a closed dashboard decision-landmark list, presentation classes and CSS-only motion; do not alter Portal rendering or the data boundary.

**Tech Stack:** FastAPI static Portal, vanilla JavaScript, CSS, pytest and Node lifecycle harness.

---

### Task 1: Lock the dashboard presentation boundary

**Files:**

- Create: `tests/test_customer_dashboard_motion_contracts.py`
- Test: `tests/test_customer_dashboard_motion_contracts.py`

- [x] Write a failing contract for the exact five decision landmarks and explicit exclusion of dashboard summary/canonical read lane.
- [x] Write a Node lifecycle harness showing observer reveal, focus reveal, remount/reduced-motion cleanup and no canonical target.
- [x] Run `python -m pytest -q tests/test_customer_dashboard_motion_contracts.py` and observe RED.

### Task 2: Add browser-only decision reveal

**Files:**

- Modify: `static/portal/portal-motion.js`
- Test: `tests/test_customer_dashboard_motion_contracts.py`

- [x] Add a closed `dashboardDecisionSelector` to `mountWorkspace()`.
- [x] Keep its targets separate from dashboard summary and canonical read content.
- [x] Mark up to six already-rendered decision controls for a stagger and remove every added class/inline property during cleanup.
- [x] Run the focused contract until GREEN.

### Task 3: Add theme-safe motion presentation

**Files:**

- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_customer_dashboard_motion_contracts.py`

- [x] Add opacity/transform-only reveal rules using the shared motion tokens.
- [x] Add 1px fine-pointer and `.985` coarse-pointer feedback to decision cards only.
- [x] Add a full reduced-motion reset for dashboard motion classes.
- [x] Run the focused contract and `node --check static/portal/portal-motion.js` until GREEN.

### Task 4: Record and verify the surface contract

**Files:**

- Modify: `docs/UX_APP_FIRST_REDESIGN.md`
- Review: Task 1–3 files only

- [x] Record the presentation-only dashboard motion rule and canonical visibility boundary.
- [x] Run targeted motion/PWA/dashboard contracts and `git diff --check`.
- [x] Inspect that no Bot, bridge, provider, wallet, PayOS, route authorization, auth, database, PWA worker/cache, ENV or deployment file changed. The route-scoped motion marker is server-rendered presentation metadata only.
