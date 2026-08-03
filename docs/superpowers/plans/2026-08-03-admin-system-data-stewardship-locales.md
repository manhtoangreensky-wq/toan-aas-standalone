# System & Data Stewardship Locale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Localize the signed, read-only System & Data Stewardship directory in reviewed Vietnamese, English, and Simplified Chinese without changing its server-owned navigation, authorization, card state, or operational boundary.

**Architecture:** Add a presentation-only adminGeneric.systemStewardship namespace and one narrow helper beside existing Admin Generic helpers. The renderer retains the exact local/canonical card arrays and server predicates; only fixed Portal labels resolve through the reviewed catalogue. Route title, description, navigation chrome, and first paint use the same route keys.

**Tech Stack:** FastAPI Portal shell, vanilla JavaScript, local i18n catalogue, pytest static/runtime contracts, Node i18n smoke test.

---

### Task 1: Write focused RED locale contracts

**Files:**

- Create: tests/test_admin_system_data_stewardship_locale_contracts.py
- Modify: tests/test_portal_i18n_bundle_contracts.py

- [ ] **Step 1: Require equal catalogues and a narrow renderer helper**

Model the static contract on tests/test_admin_automation_monitor_locale_contracts.py. Read renderAdminSystemStewardship, localizedPageTitle, and localizedPageDescription. Require representative exact keys three times in portal-i18n.js:

~~~python
for key in (
    "adminGeneric.systemStewardship.route.title",
    "adminGeneric.systemStewardship.route.description",
    "adminGeneric.systemStewardship.card.automation.title",
    "adminGeneric.systemStewardship.card.backups.description",
    "adminGeneric.systemStewardship.authority.canonical",
    "adminGeneric.systemStewardship.action.requiresCanonical",
    "adminGeneric.systemStewardship.intro.title",
    "adminGeneric.systemStewardship.section.local.title",
    "adminGeneric.systemStewardship.boundary.noDeploy.title",
):
    assert i18n.count(f'"{key}"') == 3

assert "function adminSystemStewardshipText(key, fallback, params)" in portal
assert 'const text = (key, fallback, params) => adminSystemStewardshipText(key, fallback, params);' in renderer
assert '"System & Data Stewardship": "adminGeneric.systemStewardship.route.title"' in portal
assert 'if (path === "/admin/system-stewardship") return adminSystemStewardshipText("route.title", fallback);' in page_titles
assert 'if (path === "/admin/system-stewardship") return adminSystemStewardshipText("route.description", fallback);' in page_descriptions
assert '"/admin/system-stewardship": {"vi": "System & Data Stewardship · TOAN AAS", "en": "System & Data Stewardship · TOAN AAS", "zh": "系统与数据治理 · TOAN AAS"}' in pages
~~~

The contract must preserve the directory boundaries:

~~~python
for required in (
    "adminErpNavigation(context)",
    "hasLiveCanonicalAdmin(context)",
    "serverAuthorizesAdminRoute(context, card.route)",
    'authority !== "canonical" || canonicalAdmin',
    "badge(state)",
):
    assert required in renderer
for forbidden in ("fetch(", "/internal/", "localStorage", "sessionStorage", "data-portal-action"):
    assert forbidden.lower() not in renderer.lower()
assert not re.search(r'''["']?method["']?\s*:\s*["']post["']''', renderer, flags=re.IGNORECASE)
~~~

- [ ] **Step 2: Add Node runtime catalogue checks**

Extend the Admin Generic runtime key list in tests/test_portal_i18n_bundle_contracts.py with representative Stewardship keys for vi, en, and zh. Add this exact reviewed route-title assertion:

~~~js
const reviewedSystemStewardshipCopy = {
  vi: "System & Data Stewardship",
  en: "System & Data Stewardship",
  zh: "系统与数据治理"
};
for (const [locale, expectedCopy] of Object.entries(reviewedSystemStewardshipCopy)) {
  if (api.t("adminGeneric.systemStewardship.route.title", locale) !== expectedCopy) {
    throw new Error("System & Data Stewardship route copy diverged for " + locale);
  }
}
~~~

- [ ] **Step 3: Verify RED**

Run:

~~~powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_admin_system_data_stewardship_locale_contracts.py tests/test_portal_i18n_bundle_contracts.py
~~~

Expected: feature-missing failures for the new catalogue, helper, route branches, and first-paint mapping; never a test setup failure.

### Task 2: Localize Portal-owned Stewardship copy

**Files:**

- Modify: static/portal/portal-i18n.js
- Modify: static/portal/portal.js
- Modify: copyfast_pages.py

- [ ] **Step 1: Add the full closed systemStewardship keyset**

Add identical keys to vi, en, and zh:

~~~text
route.{title,description}
authority.{local,canonical}
action.{open,requiresCanonical,waitingServer,guardedAria}
card.{automation,security,access,governance,archive,system,runtime,backups}.{title,description}
manifest.{ready,guarded}
intro.{kicker,title,boundary,statusVerified,statusSeparated,statusBody}
section.local.{kicker,title,body}
section.canonical.{kicker,title,body}
boundary.{kicker,title,body,noDeploy.{title,body},noProvider.{title,body},noLedger.{title,body}}
~~~

guardedAria takes title only after the title remains safe presentation input. Do not turn routes, server outcomes, badges, manifest group values, or authority states into key names.

- [ ] **Step 2: Add one helper and route every fixed renderer label through it**

Directly after adminAutomationMonitorText, add:

~~~js
function adminSystemStewardshipText(key, fallback, params) {
  return adminGenericText("systemStewardship." + key, fallback, params);
}
~~~

At the top of renderAdminSystemStewardship, define text as the local wrapper. Replace only fixed local/canonical card title and description, authority marker, open/guarded labels, manifest message, intro/section chrome, and three boundary items. Preserve card routes, the exact allowed predicate, safeText around every interpolated value, anchor/div behavior, canonicalAdmin branch, badge(state), and navigation groups logic.

- [ ] **Step 3: Localize route chrome and first paint**

Add the closed navigation mapping plus the exact path branches:

~~~js
"System & Data Stewardship": "adminGeneric.systemStewardship.route.title",
if (path === "/admin/system-stewardship") return adminSystemStewardshipText("route.title", fallback);
if (path === "/admin/system-stewardship") return adminSystemStewardshipText("route.description", fallback);
~~~

Add this first-paint map entry:

~~~python
"/admin/system-stewardship": {
    "vi": "System & Data Stewardship · TOAN AAS",
    "en": "System & Data Stewardship · TOAN AAS",
    "zh": "系统与数据治理 · TOAN AAS",
},
~~~

Do not edit app.py, integration.js, copyfast_admin_erp_navigation.py, the adminPage manifest, API routes, or destination pages.

- [ ] **Step 4: Verify GREEN**

Run:

~~~powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_admin_system_data_stewardship_locale_contracts.py tests/test_system_data_stewardship_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py
node --check static/portal/portal-i18n.js
node --check static/portal/portal.js
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m compileall -q copyfast_pages.py
git diff --check
~~~

### Task 3: Review, evidence, and sequential merge

**Files:**

- Modify only when generated evidence changes: docs/migration/README.md, reports/migration/preflight.json, reports/migration/web_inventory.json

- [ ] **Step 1: Review source scope and safety invariants**

Reject any source change outside the three implementation files and the two locale-test files. Confirm that app.py signed guard, action none/read only page manifest, routes, local/canonical card split, server predicates, safeText, and non-action state all remain unchanged.

- [ ] **Step 2: Run proportional gates**

Run the focused gate above, syntax/compile/diff checks, and the bounded critical suite listed in .github/workflows/webapp-quality.yml. Do not run Bot compilation, provider, Telegram, PayOS, wallet, or Railway live flow.

- [ ] **Step 3: Refresh evidence after source commit**

Commit source/test changes first. Run scripts/migration/audit_bot_to_web.py statically against frozen Bot baseline b29d0d474974075f4cba963d2c510f49d2d1b3e4 with the source commit SHA. Stage only the three evidence files, commit evidence separately, and run --verify-web-evidence at final HEAD.

- [ ] **Step 4: Push, open, and merge one PR**

Push feature/p0-webapp-admin-system-stewardship-locales, open Localize System & Data Stewardship, wait for GitHub Verify Web App success, and merge only when green. Do not deploy Railway.
