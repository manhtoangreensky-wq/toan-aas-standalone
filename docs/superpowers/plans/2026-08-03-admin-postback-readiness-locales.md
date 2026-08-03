# Postback Readiness Locale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Localize the signed, read-only canonical-admin Postback Readiness preparation guide in reviewed Vietnamese, English, and Simplified Chinese without adding a postback configuration or event surface.

**Architecture:** Add a presentation-only `adminGeneric.postbackReadiness` namespace, a narrow helper, and a backward-compatible optional label argument to `renderNotes`. The Postback renderer keeps the exact routes, server predicates, badges, read-only state, and safe HTML boundary; only fixed strings resolve through the reviewed catalogue.

**Tech Stack:** FastAPI Portal shell, vanilla JavaScript, local i18n catalogue, Python static/runtime contracts, Node syntax checks.

---

### Task 1: Lock the RED locale and safety contract

**Files:**

- Create: `tests/test_admin_postback_readiness_locale_contracts.py`
- Modify: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Require the full equal-key catalogue and narrow helper**

Create a helper that extracts `renderAdminPostbackReadiness`,
`localizedPageTitle`, `localizedPageDescription`, and `renderNotes`. Require
each closed key exactly three times in `portal-i18n.js`:

```python
for key in (
    "route.title", "route.description",
    "intro.kicker", "intro.statusTitle",
    "checkpoint.scope.title", "checkpoint.dedupe.body",
    "handoff.itemChannel.body", "limits.body",
    "boundary.noConfig.title", "boundary.noFinancial.body",
    "link.growth", "notes.integration.title", "notes.botBoundary.body",
):
    assert i18n.count(f'"adminGeneric.postbackReadiness.{key}"') == 3

assert "function adminPostbackReadinessText(key, fallback, params)" in portal
assert 'const text = (key, fallback, params) => adminPostbackReadinessText(key, fallback, params);' in renderer
assert '"Postback Readiness": "adminGeneric.postbackReadiness.route.title"' in portal
assert 'if (path === "/admin/growth/postback-readiness") return adminPostbackReadinessText("route.title", fallback);' in page_titles
assert 'if (path === "/admin/growth/postback-readiness") return adminPostbackReadinessText("route.description", fallback);' in page_descriptions
assert '"/admin/growth/postback-readiness": {"vi": "Postback Readiness · TOAN AAS", "en": "Postback Readiness · TOAN AAS", "zh": "回传准备 · TOAN AAS"}' in pages
```

- [ ] **Step 2: Lock runtime safety and fallback compatibility**

Require the unchanged server-owned behavior and absence of a control plane:

```python
for required in (
    'serverAuthorizesAdminRoute(context, "/admin/growth")',
    'serverAuthorizesAdminRoute(context, "/admin/audit")',
    'renderHero(page, context)',
    'badge("read_only")',
    'renderNotes({ ...page, notes: localizedNotes }, noteLabels)',
):
    assert required in renderer
for forbidden in ("fetch(", "api(", "data-portal-action", "<form", "localStorage", "sessionStorage", "/api/affiliate/postback"):
    assert forbidden not in renderer
assert 'text("boundary.noEvents.title", "Không gửi hoặc nhận sự kiện")' in renderer
assert 'text("notes.scope.body", "Route này chỉ giúp chuẩn bị phạm vi và handoff.' in renderer
assert 'const integrationTitle = typeof noteLabels.integrationTitle === "string"' in notes
assert "safeText(index ? safetyTitle : integrationTitle)" in notes
```

The test must also assert that `renderNotes(page)` retains the old Vietnamese
default labels when no labels object is supplied.

- [ ] **Step 3: Add Node catalogue assertions**

Extend `tests/test_portal_i18n_bundle_contracts.py` with representative
`adminGeneric.postbackReadiness.*` keys and this reviewed title check:

```javascript
const reviewedPostbackReadinessCopy = {
  vi: "Postback Readiness",
  en: "Postback Readiness",
  zh: "回传准备"
};
for (const [locale, expectedCopy] of Object.entries(reviewedPostbackReadinessCopy)) {
  if (api.t("adminGeneric.postbackReadiness.route.title", locale) !== expectedCopy) {
    throw new Error("Postback Readiness route copy diverged for " + locale);
  }
}
```

- [ ] **Step 4: Verify RED**

Run:

```powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_admin_postback_readiness_locale_contracts.py tests/test_portal_i18n_bundle_contracts.py
```

Expected: deliberate feature-missing assertions for the new catalogue,
helper, route chrome, first paint, and renderer wrapper; never a test setup
failure.

### Task 2: Localize fixed Postback guide copy

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.js`
- Modify: `copyfast_pages.py`

- [ ] **Step 1: Add the equal-key `adminGeneric.postbackReadiness` catalogue**

Add all of the following keys to `vi`, `en`, and `zh`, directly after the
adjacent Admin Generic reviewed namespaces:

```text
route.{title,description}
intro.{kicker,title,body,statusTitle,statusBody}
checklist.{kicker,title,body}
checkpoint.{scope,dedupe,handoff}.{title,body}
handoff.{kicker,title,body,itemScope,itemAuthority,itemChannel}.{title,body}
limits.{kicker,title,body}
boundary.{noConfig,noEvents,noFinancial}.{title,body}
link.{growth,audit}
notes.{integration,safety}.{title}
notes.{scope,botBoundary}.{body}
```

Use reviewed professional copy that states only preparation/handoff and never
introduces configuration, event, tracking, attribution, or payment claims.

- [ ] **Step 2: Add one helper and localize the route chrome**

Directly after the other Admin Generic helpers, add:

```javascript
function adminPostbackReadinessText(key, fallback, params) {
  return adminGenericText("postbackReadiness." + key, fallback, params);
}
```

Add the exact closed navigation mapping and title/description path branches:

```javascript
"Postback Readiness": "adminGeneric.postbackReadiness.route.title",
if (path === "/admin/growth/postback-readiness") return adminPostbackReadinessText("route.title", fallback);
if (path === "/admin/growth/postback-readiness") return adminPostbackReadinessText("route.description", fallback);
```

Add the server first-paint mapping:

```python
"/admin/growth/postback-readiness": {
    "vi": "Postback Readiness · TOAN AAS",
    "en": "Postback Readiness · TOAN AAS",
    "zh": "回传准备 · TOAN AAS",
},
```

- [ ] **Step 3: Localize renderer and note presentation without changing behavior**

At the top of `renderAdminPostbackReadiness`, define:

```javascript
const text = (key, fallback, params) => adminPostbackReadinessText(key, fallback, params);
```

Replace only the fixed checkpoint/boundary arrays, authorized link labels,
intro, checklist, handoff, and limits strings with `text()` calls. Keep the
existing fallback literals verbatim and keep both `serverAuthorizesAdminRoute`
conditions, route strings, cards, icons, badges, and `safeText()` boundaries.

Make `renderNotes` backward compatible:

```javascript
function renderNotes(page, labels) {
  const notes = page.notes && page.notes.length ? page.notes : ["Trạng thái bên ngoài chỉ được dùng sau khi backend kiểm tra quyền sở hữu và capability."];
  const noteLabels = labels && typeof labels === "object" ? labels : {};
  const integrationTitle = typeof noteLabels.integrationTitle === "string" ? noteLabels.integrationTitle : "Trạng thái tích hợp";
  const safetyTitle = typeof noteLabels.safetyTitle === "string" ? noteLabels.safetyTitle : "Nguyên tắc an toàn";
  return `<div class="portal-panel-list">${notes.map((note, index) => `<div class="portal-panel-row"><span class="portal-panel-row-icon" aria-hidden="true">${portalIcon(index ? ICONS.security : ICONS.legal)}</span><div><strong>${safeText(index ? safetyTitle : integrationTitle)}</strong><span>${safeText(note)}</span></div></div>`).join("")}</div>`;
}
```

Within the Postback renderer, keep the route page immutable and call:

```javascript
const localizedNotes = [
  text("notes.scope.body", "Route này chỉ giúp chuẩn bị phạm vi và handoff. Browser không nhận Telegram identity, cấu hình mạng, thông tin kết nối nhạy cảm, affiliate/job reference, event, attribution, doanh thu hay payout từ Bot/Core Bridge."),
  text("notes.botBoundary.body", "Postback canonical tiếp tục thuộc Bot. Web không tạo cấu hình, không gửi bản thử, không nhận sự kiện, không thay đổi referral/reward và không tạo audit event thay thế.")
];
const noteLabels = {
  integrationTitle: text("notes.integration.title", "Trạng thái tích hợp"),
  safetyTitle: text("notes.safety.title", "Nguyên tắc an toàn")
};
```

Then render only `renderNotes({ ...page, notes: localizedNotes }, noteLabels)`.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_admin_postback_readiness_locale_contracts.py tests/test_postback_readiness_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py
node --check static/portal/portal-i18n.js
node --check static/portal/portal.js
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m compileall -q copyfast_pages.py
git diff --check
```

### Task 3: Review, evidence, and sequential merge

**Files:**

- Modify only if generated evidence changes: `docs/migration/README.md`, `reports/migration/preflight.json`, `reports/migration/web_inventory.json`

- [ ] **Step 1: Review source scope and invariants**

Reject changes outside the three implementation files, the two locale tests,
and the plan/spec/evidence. Confirm `app.py`, `integration.js`, navigation
registry, CSS, audit logic, Bot/bridge/billing code, and canonical gate remain
unchanged. Confirm `renderNotes` defaults preserve all non-Postback callers.

- [ ] **Step 2: Run proportional release gates**

Run the focused GREEN gate, migration evidence verification, JavaScript
syntax/compile checks, and the bounded critical Web App suite listed in
`.github/workflows/webapp-quality.yml`. Do not run Bot compilation, providers,
PayOS, wallet, Telegram, or Railway live flows.

- [ ] **Step 3: Commit source and refresh static evidence**

Commit the plan/spec and source/test changes separately. Run
`scripts/migration/audit_bot_to_web.py` static-only against Bot baseline
`b29d0d474974075f4cba963d2c510f49d2d1b3e4` using the existing baseline
worktree `C:\Users\toann\Documents\Codex\2026-07-21\p0-admin-broadcast2`.
Record the source commit SHA, stage only the three evidence files listed
above, commit evidence separately, and run `--verify-web-evidence` at final
HEAD.

- [ ] **Step 4: Push, open, and merge one PR**

Push `feature/p0-webapp-admin-postback-readiness-locales`, open `Localize
Postback Readiness`, wait for GitHub `Verify Web App` success, and merge only
when green. Do not deploy Railway.
