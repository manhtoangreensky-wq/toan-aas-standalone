# A09 Admin Exhaustive Locale/UI Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a deterministic, executable audit ledger for all 50 page-defined/server-permitted canonical Admin routes and select exactly one evidence-ranked follow-up fix spec.

**Architecture:** Parse the finite route registry and server authority branches from source, then execute the real portal renderer through an isolated Node/browser harness with synthetic non-sensitive fixtures. Store findings as data rather than converting known defects into false passing UI. No production behavior changes in this audit spec.

**Tech Stack:** FastAPI source contracts, vanilla JavaScript portal, Python pytest, Node.js and Playwright fallback for localhost rendered evidence.

**Spec:** `C:/Users/toann/Documents/Codex/2026-07-10/1-ngu-n-ch-nh-v/A09-ADMIN-EXHAUSTIVE-AUDIT-CONTRACT-20260912.md`

## Global Constraints

- Repository: `manhtoangreensky-wq/toan-aas-standalone` only.
- Base: `d929d0e16387278e6ca894430b0978d735f87e92`.
- Account for the exact union: 49 navigation-registry routes plus page-defined `/admin/export` = 50 canonical root routes.
- Fixed UI copy may be localized; dynamic canonical data must not be translated.
- No changes to runtime/API/auth/schema/payment/wallet/provider/ENV/production data.
- No new dependency and no paid or external provider call.
- One worker and one complex spec at a time.

---

### Task 1: Route and authority inventory

**Files:**
- Create: `tests/test_a09_admin_exhaustive_locale_audit.py`
- Create: `reports/audit/A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.json`

**Interfaces:**
- Consumes: `ADMIN_ERP_ROUTE_I18N`, `adminPage(...)` registrations and the portal fallback authorization branch in `app.py`.
- Produces: `routes[]` rows with `route`, `authority`, `layout`, `renderer_family`, `aliases` and `coverage`.

- [ ] **Step 1:** Write a failing test asserting the ledger contains exactly 50 unique page/server routes, the registry contains 49, `/admin/export` is the sole registry omission, and every route has a non-empty authority/layout/renderer classification.
- [ ] **Step 2:** Run `python -m pytest tests/test_a09_admin_exhaustive_locale_audit.py -q -p no:cacheprovider`; expected RED is a missing report or incomplete 49-row ledger.
- [ ] **Step 3:** Generate only the deterministic route/authority/layout rows from exact source evidence; do not import `app.py` or execute services.
- [ ] **Step 4:** Re-run the test; expected GREEN for the 50-row inventory assertions while locale findings may remain recorded as data.

### Task 2: Direct locale and executable coverage ledger

**Files:**
- Modify: `tests/test_a09_admin_exhaustive_locale_audit.py`
- Modify: `reports/audit/A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.json`

**Interfaces:**
- Consumes: existing `tests/test_admin_*.py`, `tests/test_a09_*.py`, `localizedPageTitle`, `localizedPageDescription` and locale catalogues.
- Produces: per-route `title_owned`, `description_owned`, `coverage=FULL|PARTIAL|NONE`, exact test references and fixed-copy findings.

- [ ] **Step 1:** Add a RED test requiring coverage counts to sum to 50 and every FULL/PARTIAL row to cite an existing test path/function.
- [ ] **Step 2:** Run the audit test; expected RED identifies missing route coverage rows rather than failing on known product copy.
- [ ] **Step 3:** Fill the ledger with exact static evidence and keep all uncovered/mixed routes as findings.
- [ ] **Step 4:** Verify the test exits `0`, route total remains 50 and `owned_both + locale_gap = 50`.

### Task 3: Rendered and PWA evidence

**Files:**
- Create: `reports/audit/A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.md`
- Create outside repository: `C:/Users/toann/Documents/Codex/2026-07-10/1-ngu-n-ch-nh-v/tmp/a09-admin-exhaustive-browser-audit.js`
- Create outside repository: `C:/Users/toann/Documents/Codex/2026-07-10/1-ngu-n-ch-nh-v/evidence/a09-admin-exhaustive-20260912/`

**Interfaces:**
- Consumes: real portal shell and static assets with synthetic, non-sensitive Admin bootstrap/API fixtures.
- Produces: per-route/locale findings, renderer-family viewport evidence and three explicit PWA answers.

- [ ] **Step 1:** Run VI/EN/ZH fixed-copy audit for all 50 routes; classify dynamic server data separately and record unobservable states as `NOT_TESTED`.
- [ ] **Step 2:** Test one representative route per renderer family at `1440`, `768`, `390` and `360`; capture overflow, clipping, target size, mobile cell width and console/write-request counts.
- [ ] **Step 3:** Inspect manifest/service worker/navigation source for offline, update and standalone-back truth; do not infer real-device PASS from DevTools.
- [ ] **Step 4:** Write the Markdown report using measured counts and maximum 15 ranked findings.

### Task 4: Consistency gate and next-spec selection

**Files:**
- Modify: `tests/test_a09_admin_exhaustive_locale_audit.py`
- Modify: `reports/audit/A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.json`
- Modify: `reports/audit/A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.md`

**Interfaces:**
- Consumes: route ledger and rendered/PWA evidence.
- Produces: exactly one `next_spec` with dependency, severity, allowlist, protected files and RED command.

- [ ] **Step 1:** Add tests that parse both reports and compare route/finding/count fields exactly.
- [ ] **Step 2:** Select the highest-impact cohesive renderer family; do not pick multiple parallel implementation specs.
- [ ] **Step 3:** Run the audit pytest, Node syntax checks and `git diff --check`; expected `0` failures for audit integrity.
- [ ] **Step 4:** Request independent read-only review. Audit remains unaccepted if Critical or Important report-integrity findings remain.

## Self-review

- Spec coverage: tasks map all contract checklist groups; implementation fixes are intentionally excluded.
- Placeholder scan: no `TBD`, `TODO`, “similar to” or conversation-relative instruction is present.
- Type consistency: the single route-row schema and `next_spec` output are used by every task.
