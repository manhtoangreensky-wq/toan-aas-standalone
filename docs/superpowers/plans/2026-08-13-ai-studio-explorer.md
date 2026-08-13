# AI Studio Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the existing `/features` catalogue into a focused, responsive AI Studio directory without inventing routes or readiness.

**Architecture:** Keep all route and catalogue authority in `portal.js`; add only semantic DOM attributes and local filtering hooks. Keep visual tokens and motion in the existing `portal-theme.css` and `portal-motion.js` layers.

**Tech Stack:** Vanilla JavaScript, semantic HTML, CSS custom properties, pytest static contracts.

---

### Task 1: Directory contract

**Files:**
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-motion.js`
- Test: `tests/test_feature_catalog_app_ux_contracts.py`

- [ ] Add stable group/jump attributes while retaining manifest-derived routes.
- [ ] Hide stale jump links whenever local search hides their group; restore them when the query clears.
- [ ] Add the control region as one workspace-motion target, never as a per-card hidden item.

### Task 2: Aura presentation

**Files:**
- Modify: `static/portal/portal-theme.css`

- [ ] Add token-only desktop/mobile control-region layout with 44px controls and wrapped mobile navigation.
- [ ] Add explicit dark-theme and reduced-motion rules.

### Task 3: Verification and handoff

**Files:**
- No additional production files.

- [ ] Run the focused contract plus existing feature-family, dashboard-motion and teal foundation tests.
- [ ] Run JavaScript syntax checks and `git diff --check`.
- [ ] Review the complete diff, then request an independent review before push/PR.
