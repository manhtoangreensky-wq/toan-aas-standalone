# Customer PWA Navigation and Motion Implementation Plan

> For agentic workers: execute this plan task by task with review checkpoints.

**Goal:** Make the five-item customer PWA dock describe the route the customer is actually using, and give AI Studio and Workspace Menu calm, reduced-motion-safe reveal and interaction feedback.

**Architecture:** Keep the signed server route manifest and action boundaries unchanged. A browser-only presentation helper maps only already-selected customer paths to dock groups and enhances fixed workspace DOM landmarks after Portal has rendered them; CSS owns motion tokens, transforms and reduced-motion fallback.

**Tech Stack:** FastAPI portal shell, vanilla JavaScript, vanilla CSS, pytest static and Node harness contracts.

---

### Task 1: Define the customer navigation and motion contract

**Files:**

- Create: `tests/test_customer_pwa_navigation_motion_contracts.py`
- Test: `tests/test_customer_pwa_navigation_motion_contracts.py`
- [ ] Write a Node-backed contract for the real `isMobileNavCurrent()` helper.
- [ ] Require these route outcomes: `/workspace/setup` -> dashboard; `/video-studio/story-video-plan` and `/documents/ocr` -> studio; `/projects/project-42`, `/workboard/board-42` and `/jobs/job-42` -> jobs; `/prompt-library/library-42` and `/asset-vault` -> assets; `/account/security` and `/tickets/ticket-42` -> account; `/admin/jobs` -> no customer dock item.
- [ ] Require a browser-only workspace lifecycle with no request, storage or authority APIs, plus CSS reveal, pointer feedback and a reduced-motion fallback.
- [ ] Run the focused test and observe a red failure before implementation.

### Task 2: Implement fixed customer dock semantics

**Files:**

- Modify: `static/portal/portal.js`
- Test: `tests/test_customer_pwa_navigation_motion_contracts.py`
- [ ] Add a fixed exact/prefix customer route map for dashboard, studio, jobs, assets and account.
- [ ] Reject `/admin` and `/admin/*` before matching and do not read roles, route authorization, records, wallet, capability or engine state.
- [ ] Keep the five dock destinations unchanged: `/dashboard`, `/features`, `/jobs`, `/assets`, `/account`.
- [ ] Run the dock contract until green.

### Task 3: Add bounded workspace reveal and feedback

**Files:**

- Modify: `static/portal/portal-motion.js`
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_customer_pwa_navigation_motion_contracts.py`
- [ ] Enhance only completed customer landmarks: catalogue context, catalogue heading, guided start, capability hub, search, feature jumps/groups, workspace-menu intro/groups/boundary.
- [ ] Use IntersectionObserver when available; focus reveals a target immediately; unsupported browsers leave content visible.
- [ ] Clean observer, focus listeners and added classes before the next Portal mount.
- [ ] Use existing 140/220ms tokens, opacity/transform only, first-six item stagger, 1px fine-pointer lift, `.985` coarse-pointer press and a full reduced-motion reset.
- [ ] Mount only after the completed workspace shell render; do not alter rendering, authorization, hydration, action dispatch, PWA cache, session or focus restoration.
- [ ] Run focused motion contract and Node syntax checks until green.

### Task 4: Review and verification

**Files:**

- Modify: `docs/UX_APP_FIRST_REDESIGN.md`
- Review: Task 1-3 files only
- [ ] Document that route grouping and workspace reveal are presentation-only and honor reduced motion.
- [ ] Run targeted PWA, motion, navigation, feature-catalogue and workspace-menu contracts, Node syntax checks and `git diff --check`.
- [ ] Inspect that the diff excludes Bot, bridge, provider, wallet, PayOS, pricing, session, service-worker, credential and deployment changes.

### Completion notes

- The dock keeps fixed customer destinations and never exposes an admin active
  state. Route aliases retain the meaning of their canonical flow: notably,
  `/voice/vault` follows `/voice/saved` into Create rather than becoming a
  Library route merely from its label.
- Workspace reveal is deliberately semantic-landmark scoped and does not
  observe records, state, readiness or account data. It cleans itself up on
  Portal remount and if the operating system enables reduced motion during an
  open page.
- Cross-document View Transitions are CSS-only progressive enhancement for
  normal signed server navigations. They are disabled by the reduced-motion
  media query and do not intercept links, replace the server router or change
  CSRF/session behavior.
