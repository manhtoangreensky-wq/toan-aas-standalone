# Admin ERP Desktop Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/admin/*` a distinct internal desktop application by replacing the customer Workspace sidebar and quick-switch results with the server-authorized ERP navigation projection.

**Architecture:** Reuse the validated `adminErpNavigation(context)` projection already hydrated for the signed session. A shared bounded module flattener and current-route resolver will power both the desktop ERP groups and the existing mobile dock, while customer `navGroups` remains unchanged for non-Admin routes. The browser will never infer an Admin route from a role, URL prefix, or static menu; unavailable/non-ready grants render no ERP links.

**Tech Stack:** FastAPI-issued navigation metadata, vanilla browser JavaScript, existing `portal-i18n.js` locale bundle, pytest/Node static contracts, and the existing teal–sky portal shell.

---

### Task 1: Write fail-closed desktop Admin navigation contracts

**Files:**

- Modify: `tests/test_admin_erp_navigation_portal_contracts.py`
- Modify: `tests/test_portal_navigation_ux_contracts.py`
- Modify: `tests/test_portal_i18n_bundle_contracts.py`

- [x] **Step 1: Add the failing authority and sidebar tests**

Add a test that extracts the Admin desktop helpers and asserts:

```python
def test_admin_desktop_sidebar_uses_only_server_authorized_groups() -> None:
    portal = _read("static/portal/portal.js")
    desktop = portal[portal.index("function adminNavigationModules(context)"):portal.index("function navGroups(context, currentPage)")]
    navigation = portal[portal.index("function navGroups(context, currentPage)"):portal.index("function matchesRouteFamily(path, root)")]

    assert "const navigation = adminErpNavigation(context);" in desktop
    assert "navigation.routes.has(module.route)" in desktop
    assert "function adminDesktopNavGroups(context, currentPage)" in desktop
    assert "if (isAdminPortalSurface(currentPage)) return adminDesktopNavGroups(context, currentPage);" in navigation
    assert "context.isAdmin" not in desktop
    assert '"/dashboard"' not in desktop
    assert '"/features"' not in desktop
```

Extend the existing Node harness so an `/admin/jobs/<id>` page receives one current issued `/admin/jobs` link, includes `/admin` only when issued, contains no customer route, and yields `[]` for a non-ready manifest. Add locale assertions for `chrome.adminAppCaption`, `chrome.searchAdmin`, and `chrome.adminCommandCount` in Vietnamese, English, and Simplified Chinese.

- [x] **Step 2: Run only these new contracts and verify RED**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_admin_erp_navigation_portal_contracts.py tests/test_portal_navigation_ux_contracts.py tests/test_portal_i18n_bundle_contracts.py -k "admin_desktop or adminAppCaption or searchAdmin or adminCommandCount"
```

Expected: FAIL because shared Admin desktop helpers, Admin command-palette scope, and fixed locale keys do not yet exist.

### Task 2: Build the separate desktop Admin shell projection

**Files:**

- Modify: `static/portal/portal.js:9102-9200`
- Modify: `static/portal/portal.js:9341-9390`
- Modify: `static/portal/portal.js:9392-9460`
- Modify: `static/portal/portal.js:9440-9540`
- Modify: `static/portal/portal-i18n.js`

- [x] **Step 1: Extract the shared authorized module and current-route helpers**

Keep the public `isAdminMobileSurface(page)` for the existing mobile contracts, but add a generic path helper and make the mobile helper delegate to it:

```javascript
  function isAdminPortalSurface(page) {
    const sourcePath = page && (page.routePath || page.path);
    if (typeof sourcePath !== "string" || !sourcePath) return false;
    const path = normalizePath(sourcePath);
    return path === "/admin" || path.startsWith("/admin/");
  }

  function isAdminMobileSurface(page) {
    return isAdminPortalSurface(page);
  }

  function adminNavigationModules(context) {
    const navigation = adminErpNavigation(context);
    if (!navigation.groups.length) return [];
    const seen = new Set();
    const modules = [];
    navigation.groups.forEach((group) => {
      if (!group || !Array.isArray(group.modules)) return;
      group.modules.forEach((module) => {
        if (!module || !navigation.routes.has(module.route) || seen.has(module.route)) return;
        seen.add(module.route);
        modules.push(module);
      });
    });
    return modules;
  }
```

Retain the existing exact plus server-authorized `/admin/jobs/*` and `/admin/support/*` inheritance rule. Use it to calculate one longest current module; do not add a generic `/admin/*` prefix match.

- [x] **Step 2: Return Admin-only desktop groups for an Admin route**

Implement a shared current resolver and `adminDesktopNavGroups(context, currentPage)` from the same issued groups/modules:

```javascript
  function currentAdminNavigationModule(page, context, modules) {
    const sourcePath = page && (page.routePath || page.path);
    const path = typeof sourcePath === "string" && sourcePath ? normalizePath(sourcePath) : "";
    return modules.reduce((matched, module) => (
      isAdminMobileNavCurrent(module, path, context) && (!matched || module.route.length > matched.route.length)
        ? module
        : matched
    ), null);
  }

  function adminDesktopNavGroups(context, currentPage) {
    const navigation = adminErpNavigation(context);
    if (!navigation.groups.length) return [];
    const issued = adminNavigationModules(context);
    if (!issued.length) return [];
    const issuedRoutes = new Set(issued.map((module) => module.route));
    const current = currentAdminNavigationModule(currentPage, context, issued);
    const seen = new Set();
    return navigation.groups.map((group) => {
      const modules = (Array.isArray(group.modules) ? group.modules : []).filter((module) => {
        if (!module || !issuedRoutes.has(module.route) || seen.has(module.route)) return false;
        seen.add(module.route);
        return true;
      });
      const groupCurrent = Boolean(current && modules.some((module) => module.route === current.route));
      return {
        label: `ERP · ${group.title}`,
        defaultOpen: groupCurrent,
        current: groupCurrent,
        links: modules.map((module) => [module.route, module.title, module.icon, Boolean(current && module.route === current.route)])
      };
    }).filter((group) => group.links.length);
  }
```

Deduplicate routes across groups, reject modules absent from `navigation.routes`, and return `[]` when the projection is non-ready or empty. At the start of `navGroups(context, currentPage)`, use:

```javascript
if (isAdminPortalSurface(currentPage)) return adminDesktopNavGroups(context, currentPage);
```

The existing five customer groups, current-workflow cue, and deferred Video Studio tree must remain only in the non-Admin branch.

- [x] **Step 3: Make sidebar and quick switch match the same scope**

In `renderSidebar`, honor the optional fourth tuple item as a supplied current state; use `isNavCurrent` only for customer groups. On an Admin route:

- use `chrome.adminAppCaption` in the brand caption;
- replace the `/features` “new workflow” shortcut with an issued `/admin` overview link only when `adminErpNavigation(context).routes.has("/admin")`; otherwise omit the primary link;
- use `chrome.searchAdmin` for the sidebar search label;
- retain the focus button, account chip, legal link, keyboard handling, and signed-session behavior.

In `commandPaletteItems`, when `isAdminPortalSurface(page)` is true, admit only a manifest page with `access === "admin"` whose route exists in `authorizedAdminRoutes`. Customer pages must remain available only on customer routes. Use `chrome.adminCommandCount` for its fixed count copy. In `renderHeader`, use `chrome.searchAdmin` for the quick-switch control on an Admin route.

Add exact Vietnamese, English and Simplified Chinese copy:

```text
adminAppCaption: Admin ERP | Admin ERP | 管理 ERP
searchAdmin: Tìm điều hướng ERP | Search ERP navigation | 搜索 ERP 导航
adminCommandCount: {count} mục ERP có thể mở trong phiên này. | {count} ERP destinations available in this session. | 此会话可打开 {count} 个 ERP 入口。
```

Do not translate server-supplied module titles/descriptions in the browser, add new API calls, call providers, expose a count/record/secret, or change an authority check.

- [x] **Step 4: Run GREEN and focused regression checks**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_portal_navigation_ux_contracts.py tests/test_admin_erp_navigation_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_safety_contracts.py
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
git diff --check
```

Expected: all selected contracts pass; customer navigation stays unchanged outside `/admin/*`; Admin navigation is empty rather than fabricated when its server grant is absent.

### Task 3: Review and integrate the focused PR

**Files:**

- Modify: `docs/superpowers/plans/2026-07-29-admin-desktop-navigation.md`

- [ ] **Step 1: Perform independent spec and code-quality reviews**

Verify no Customer Workspace route is rendered in the desktop Admin sidebar or Admin command palette, no browser role authorizes a route, exactly one current Admin link is announced, server titles are escaped, desktop keyboard/focus behavior remains intact, and the mobile dock continues to use the same shared authority boundary.

- [ ] **Step 2: Commit, PR, CI, merge, and production check**

After the focused checks pass, commit only task files with message `Separate Admin desktop navigation from customer workspace`, push `feature/p0-webapp-copyfast175-admin-desktop-navigation`, open a PR against `main`, and merge only after `Verify Web App` passes. Then verify `https://app.toanaas.vn/health` returns HTTP 200 and production `portal.js` contains `adminDesktopNavGroups`.

---

## Plan self-review

- **Scope coverage:** Separates the two desktop app shells, preserves server authority and mobile behavior, fixes menu/current-state ambiguity, localizes only fixed chrome, and includes targeted regression, review, CI, merge and Railway verification.
- **Explicit exclusions:** No Bot change, provider/payment/PayOS/webhook/ledger work, Video menu work, backend route/grant change, destructive migration, or LocalVideoStudio/motion-kit modification.
- **Ambiguity resolved:** An Admin session with no ready navigation projection shows no Admin shortcut rather than falling back to customer navigation. A support operator remains scoped to its issued modules and is never visually promoted to canonical Admin.
