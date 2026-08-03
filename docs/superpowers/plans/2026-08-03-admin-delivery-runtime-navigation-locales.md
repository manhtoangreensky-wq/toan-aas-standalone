# Admin Delivery & Runtime Navigation Locale Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translate only the reviewed Admin ERP Delivery & Runtime route chrome in VI/EN/ZH without changing server authorization, route availability, jobs, providers, payments, or runtime behavior.

**Architecture:** A closed route/group locale projection operates after `adminErpNavigation` has accepted the server-issued manifest. It uses existing Job Recovery locale keys and a new `adminGeneric.deliveryRuntimeNavigation` namespace for the other eight fixed routes. Page hero and server first-paint titles use the same closed route map.

**Tech Stack:** FastAPI/Python portal shell, vanilla JavaScript, static locale catalogue, pytest, Node syntax checks.

---

### Task 1: Lock a RED route-projection contract

**Files:**

- Create: `tests/test_admin_delivery_runtime_navigation_locale_contracts.py`
- Inspect: `tests/test_admin_job_recovery_guide_locale_contracts.py`
- Inspect: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Write the failing contract**

Create a static test with this exact route map:

```python
ROUTES = {
    "/admin/jobs": "jobs",
    "/admin/jobs/failed": "failedJobs",
    "/admin/providers": "providers",
    "/admin/provider-cost": "providerCost",
    "/admin/workers": "workers",
    "/admin/features": "features",
    "/admin/freezes": "freezes",
    "/admin/runtime": "runtime",
}
```

Assert all `group.title`, `group.description` and each route `title`/`description` key occur once in each `vi`, `en`, and `zh` Admin Generic catalogue. Assert the exact Job Recovery path is mapped to its existing `adminGeneric.jobRecoveryGuide.route.title` / `.description` keys, not duplicated.

Require a closed helper/map in `portal.js`; page title/description branches for all nine paths; first-paint titles for all nine paths; and localized navigation projection only after `safeCatalogRoute`, route admission and state normalization occur in `adminErpNavigation`.

The contract must reject new `fetch(`, `api(`, `data-portal-action`, `<form`, `<button`, `localStorage`, `sessionStorage`, `setInterval`, `adminData`, `jobId`, `/admin/modules/`, payment/wallet/provider mutation endpoints, and any change to `serverAuthorizesAdminRoute`.

- [ ] **Step 2: Verify RED**

Run:

```powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_admin_delivery_runtime_navigation_locale_contracts.py
```

Expected: feature-missing failures for the closed projection catalogue/map; no Python import, database or external-service failure.

### Task 2: Add the closed presentation-only projection

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.js`
- Modify: `copyfast_pages.py`
- Test: `tests/test_admin_delivery_runtime_navigation_locale_contracts.py`

- [ ] **Step 1: Add reviewed equal-key copy**

Insert the following 18 keys in all three dictionaries:

```text
adminGeneric.deliveryRuntimeNavigation.group.title
adminGeneric.deliveryRuntimeNavigation.group.description
adminGeneric.deliveryRuntimeNavigation.jobs.{title,description}
adminGeneric.deliveryRuntimeNavigation.failedJobs.{title,description}
adminGeneric.deliveryRuntimeNavigation.providers.{title,description}
adminGeneric.deliveryRuntimeNavigation.providerCost.{title,description}
adminGeneric.deliveryRuntimeNavigation.workers.{title,description}
adminGeneric.deliveryRuntimeNavigation.features.{title,description}
adminGeneric.deliveryRuntimeNavigation.freezes.{title,description}
adminGeneric.deliveryRuntimeNavigation.runtime.{title,description}
```

Keep Vietnamese fallbacks exactly equal to current route metadata. Write English and Simplified Chinese as read-only/canonical status copy; do not promise a retry, refund, provider call, payment effect, repair, deploy, restart or output.

- [ ] **Step 2: Add closed key maps and use them after server admission**

Add a frozen route map with exactly the nine allowed paths and a frozen group map with exactly `delivery_runtime`. Use helpers shaped as follows:

```javascript
function adminDeliveryRuntimeNavigationText(route, field, fallback) {
  const entry = DELIVERY_RUNTIME_ROUTE_I18N[normalizePath(route)];
  return entry && entry[field] ? uiText(entry[field], fallback) : fallback;
}

function adminDeliveryRuntimeGroupText(groupId, field, fallback) {
  const entry = DELIVERY_RUNTIME_GROUP_I18N[String(groupId || "")];
  return entry && entry[field] ? uiText(entry[field], fallback) : fallback;
}
```

Do not call either helper before `safeCatalogRoute` and route/state validation in `adminErpNavigation`. Preserve each route, authority, state, icon and `routes` set exactly. Unknown server metadata uses its original title/description.

- [ ] **Step 3: Map route heroes and first paint**

Add exact `localizedPageTitle` and `localizedPageDescription` branches for each route. Use the dedicated Job Recovery helper for `/admin/job-recovery-guide`; use the route map for the other eight. Add title values in `_PORTAL_SHELL_TITLES` for the same nine exact paths only.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_admin_delivery_runtime_navigation_locale_contracts.py tests/test_admin_job_recovery_guide_locale_contracts.py tests/test_job_lock_recovery_guide_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py
node --check static/portal/portal-i18n.js
node --check static/portal/portal.js
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m compileall -q copyfast_pages.py
git diff --check
```

### Task 3: Evidence, PR, CI, and sequential merge

**Files:**

- Modify only if output changes: `docs/migration/README.md`, `reports/migration/preflight.json`, `reports/migration/web_inventory.json`

- [ ] **Step 1: Commit source after green checks**

Commit the design/plan, RED contract and three implementation files with:

```powershell
git commit -m "Localize Admin Delivery and Runtime navigation"
```

- [ ] **Step 2: Refresh and verify static evidence**

Run `scripts/migration/audit_bot_to_web.py` against Bot baseline `b29d0d474974075f4cba963d2c510f49d2d1b3e4` at the source commit. Stage only README, preflight and Web inventory if they changed; commit them separately. Verify evidence at final HEAD.

- [ ] **Step 3: Run proportional CI-equivalent gates and merge one PR**

Run the bounded critical Web App suite from `.github/workflows/webapp-quality.yml`, push one branch, open one PR, wait for `Verify Web App`, and merge only when green. Do not deploy Railway or call a live Bot, provider, PayOS, wallet, webhook, job or Telegram flow.
