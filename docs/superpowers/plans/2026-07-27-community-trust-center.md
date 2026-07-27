# Community & Official Channels Trust Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `/community` a signed, multilingual, anti-impersonation Trust Center based on the public intent of Bot community commands, without importing Bot state or external authority.

**Architecture:** A small server-owned catalog validates a closed set of internal and externally configured official destinations. The portal hydrates and validates that catalog before rendering cards; it never accepts URLs or Telegram data from the browser. The existing bot-companion page is replaced, not extended.

**Tech Stack:** FastAPI, existing signed-session helpers, vanilla Portal JavaScript/CSS, pytest.

---

### Task 1: Add the server-owned safe Trust Center catalog

**Files:**

- Create: `copyfast_community_trust.py`
- Create: `tests/test_copyfast_community_trust.py`
- Modify: `app.py`

- [ ] **Step 1: Write failing endpoint tests**

Test unauthenticated `401`, signed profile-locale authority, no-store headers, valid `BOT_USERNAME` and community URL output, invalid URL guarding, and false execution boundaries.

- [ ] **Step 2: Run the test to verify it fails**

Run `python -m pytest -q tests/test_copyfast_community_trust.py`; it must fail because the module is absent.

- [ ] **Step 3: Implement the closed catalog and router**

Use `require_account`, `normalize_interface_locale`, and `envelope`; validate URLs with `urllib.parse.urlsplit`, construct Bot URLs only from the existing validated username, return a new JSON object for every request, and mount the router under `/api/v1/community`.

- [ ] **Step 4: Run the test to verify it passes**

Run `python -m pytest -q tests/test_copyfast_community_trust.py`; it must pass.

- [ ] **Step 5: Commit the server slice**

Stage only `copyfast_community_trust.py`, `app.py`, and its test, then commit with `feat: add safe community trust catalog`.

### Task 2: Replace the Bot-command page with a Trust Center renderer

**Files:**

- Modify: `copyfast_registry.py`
- Modify: `static/portal/portal.js`
- Modify: `static/portal/integration.js`
- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.css`
- Modify: `static/portal/service-worker.js`
- Create: `tests/test_community_trust_center_portal_contracts.py`

- [ ] **Step 1: Write failing portal contracts**

Assert the new page type, strict catalog normalizer, signed API hydration, closed URL/route rules, no raw command/Telegram ID/browser persistence, localized copy, `noopener noreferrer`, responsive/reduced-motion CSS, and private service-worker policy.

- [ ] **Step 2: Run the test to verify it fails**

Run `python -m pytest -q tests/test_community_trust_center_portal_contracts.py`; it must fail because the renderer and hydration do not exist.

- [ ] **Step 3: Implement Portal and integration behavior**

Replace the `botCompanionPage("/community", ...)` declaration with a read-only customer page, add loading/failed/guarded/ready states, validate API data before rendering, and ensure only ready external cards receive a new-window link.

- [ ] **Step 4: Run the test to verify it passes**

Run `python -m pytest -q tests/test_community_trust_center_portal_contracts.py`; it must pass.

- [ ] **Step 5: Commit the client slice**

Stage only the registry, portal files, and portal-contract test, then commit with `feat: render community trust center`.

### Task 3: Verify the migration boundary and submit the PR

**Files:**

- Modify: `docs/migration/FEATURE_PARITY_MATRIX.md`
- Modify: `docs/migration/TELEGRAM_TO_WEB_ROUTE_MAP.md`
- Modify: `docs/migration/KNOWN_GAPS_AND_GUARDS.md`
- Modify: `reports/migration/parity_gap.json`
- Modify: `tests/test_migration_audit.py`

- [ ] **Step 1: Write a failing static-audit assertion**

Require the five public Bot commands to map to `/community` as `WEB_NATIVE_READ_ONLY` with an explicit no-state-replay boundary.

- [ ] **Step 2: Run the test to verify it fails**

Run `python -m pytest -q tests/test_migration_audit.py -k community`; it must fail because the current catalog labels `/community` a Bot handoff.

- [ ] **Step 3: Update inventory through the existing audit script**

Teach the static mapping only about the new navigation/read-only disposition; do not turn callbacks, Bot state, or URL configuration into browser actions.

- [ ] **Step 4: Run targeted verification**

Run `python -m pytest -q tests/test_copyfast_community_trust.py tests/test_community_trust_center_portal_contracts.py tests/test_migration_audit.py -k "community or trust"`; it must pass.

- [ ] **Step 5: Commit and open the PR**

Commit only migration docs/reports/audit changes with `docs: map community commands to web trust center`, push `feature/p0-webapp-community-trust-center`, and open a PR titled `Add community trust center to web app`.
