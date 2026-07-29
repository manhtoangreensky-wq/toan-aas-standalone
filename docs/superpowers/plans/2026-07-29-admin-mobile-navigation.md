# Admin ERP Mobile Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give signed internal ERP users a compact, server-authorized mobile dock instead of the customer Workspace dock.

**Architecture:** Keep `adminErpNavigation(context)` as the sole browser input for internal navigation. A small presentation helper will flatten only its validated groups/modules that are also present in its route set, retain the longest matching current route, then the issued ERP overview when available, and fill a maximum-five projection in server order. It fails closed on an absent or non-ready grant. `mountPortal` will select that projection only on `/admin` routes; all customer routes keep the established `renderMobileNav(page)` signature and behavior.

**Tech Stack:** FastAPI server route grants, vanilla browser JavaScript, static contract tests with pytest/Node, existing teal–sky portal CSS and locale bundle.

---

### Task 1: Define the fail-closed Admin mobile dock contract

**Files:**

- Modify: `tests/test_admin_erp_navigation_portal_contracts.py`
- Modify: `tests/test_portal_navigation_ux_contracts.py`
- Modify: `static/portal/portal.js:9286-9332`

- [x] **Step 1: Write the failing contract test**

Add a focused test that reads the new Admin mobile helpers and asserts all of the following:

```python
def test_admin_mobile_dock_is_server_granted_compact_and_never_reuses_customer_routes() -> None:
    portal = _read("static/portal/portal.js")
    helpers = portal[portal.index("function isAdminMobileSurface(page)"):portal.index("function normalizeCommandSearch(value)")]

    assert "const navigation = adminErpNavigation(context);" in helpers
    assert "if (!navigation.groups.length) return [];" in helpers
    assert "const MAX_ADMIN_MOBILE_NAV_ITEMS = 5;" in helpers
    assert "navigation.routes.has(module.route)" in helpers
    assert "serverAuthorizesAdminRoute(context, path)" in helpers
    assert '"/dashboard"' not in helpers
    assert '"/features"' not in helpers
    assert "renderAdminMobileNav(page, context)" in helpers
    assert 'href="${safeText(item.route)}"' in helpers
```

Add a second focused test for the mount boundary:

```python
def test_mount_portal_selects_the_admin_dock_only_for_admin_routes() -> None:
    mount = _section("function mountPortal(override)", "function maybeRestoreFlashMessage")

    assert "isAdminMobileSurface(page) ? renderAdminMobileNav(page, context) : renderMobileNav(page)" in mount
    assert "mobileNav.hidden = !mobileNavMarkup;" in mount
```

- [x] **Step 2: Run the focused test and verify it fails for the missing helpers**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_portal_navigation_ux_contracts.py -k admin_mobile
```

Expected: FAIL because `adminMobileNavItems` and `renderAdminMobileNav` do not exist.

- [x] **Step 3: Implement the minimal projection and renderer**

In `static/portal/portal.js`, retain `renderMobileNav(page)` unchanged. Immediately after it, add:

```javascript
  function isAdminMobileSurface(page) {
    const path = normalizePath(page && (page.routePath || page.path));
    return path === "/admin" || path.startsWith("/admin/");
  }

  function isAdminMobileNavCurrent(module, path, context) {
    if (!module || !module.route || !path) return false;
    if (path === module.route) return true;
    if (!serverAuthorizesAdminRoute(context, path)) return false;
    return (module.route === "/admin/jobs" && path.startsWith("/admin/jobs/"))
      || (module.route === "/admin/support" && path.startsWith("/admin/support/"));
  }

  const MAX_ADMIN_MOBILE_NAV_ITEMS = 5;

  function adminMobileNavItems(page, context) {
    const navigation = adminErpNavigation(context);
    if (!navigation.groups.length) return [];
    const seen = new Set();
    const modules = [];
    navigation.groups.forEach((group) => {
      group.modules.forEach((module) => {
        if (!module || !navigation.routes.has(module.route) || seen.has(module.route)) return;
        seen.add(module.route);
        modules.push(module);
      });
    });
    if (!modules.length) return [];
    const path = normalizePath(page && (page.routePath || page.path));
    const current = modules.reduce((matched, module) => (
      isAdminMobileNavCurrent(module, path, context) && (!matched || module.route.length > matched.route.length)
        ? module
        : matched
    ), null);
    const compact = [];
    const include = (module) => {
      if (module && !compact.some((item) => item.route === module.route) && compact.length < MAX_ADMIN_MOBILE_NAV_ITEMS) compact.push(module);
    };
    include(current);
    include(modules.find((module) => module.route === "/admin"));
    modules.forEach(include);
    return compact.map((module) => ({ ...module, current: Boolean(current && current.route === module.route) }));
  }

  function renderAdminMobileNav(page, context) {
    return adminMobileNavItems(page, context).map((item) => {
      return `<a class="portal-mobile-nav-link" href="${safeText(item.route)}"${item.current ? ' aria-current="page"' : ""}>
        <span class="portal-mobile-nav-icon" aria-hidden="true">${portalIcon(item.icon)}</span>
        <span class="portal-mobile-nav-label">${safeText(item.title)}</span>
      </a>`;
    }).join("");
  }
```

The `current` projection above is intentionally computed once, so only the longest matching authorized module receives `aria-current="page"`. Detail inheritance is deliberately limited to the two exact server rules already defined in `serverAuthorizesAdminRoute`: `/admin/jobs/*` and `/admin/support/*`. No text, route, permission or group may originate outside `adminErpNavigation(context)`.

- [x] **Step 4: Run the focused test and verify it passes**

Run the command from Step 2. Expected: PASS.

### Task 2: Switch the signed shell without fabricating an empty dock

**Files:**

- Modify: `static/portal/portal.js:27950-27965`
- Test: `tests/test_portal_navigation_ux_contracts.py`
- Test: `tests/test_portal_safety_contracts.py`

- [x] **Step 1: Write the failing shell-boundary contract**

Extend the route-boundary test to assert that `mountPortal` selects the Admin renderer only via `isAdminMobileSurface(page)`, hides the landmark when the selected renderer returns an empty string, and retains the signed-session-only `showMobileNav` guard. Update `tests/test_portal_safety_contracts.py` so the existing mobile-dock test expects `mobileNav.hidden = !mobileNavMarkup;` rather than the old authenticated-only visibility assignment, while retaining customer dock signature, five-column layout and touch-target assertions.

- [x] **Step 2: Run the focused test and verify it fails**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_portal_navigation_ux_contracts.py tests/test_portal_safety_contracts.py -k "admin_mobile or mobile_workspace_dock"
```

Expected: FAIL because the route selection and empty-dock hiding are not present.

- [x] **Step 3: Implement the shell selection and responsive presentation**

In `mountPortal`, calculate this from the already-selected signed page:

```javascript
const mobileNavMarkup = showMobileNav
  ? (isAdminMobileSurface(page) ? renderAdminMobileNav(page, context) : renderMobileNav(page))
  : "";
mobileNav.hidden = !mobileNavMarkup;
mobileNav.innerHTML = mobileNavMarkup;
```

Retain the already localized generic quick-navigation ARIA label and existing dock styling: it already supplies truncation, five columns, 54px mobile targets, an 8px gap, reduced-motion behavior, and the teal–sky light application surface. Do not add counts, provider state, customer routes, browser role checks, new API calls, locale keys, or CSS.

- [x] **Step 4: Run focused contracts, syntax, and diff hygiene**

Run:

```powershell
& 'C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pytest -q tests/test_portal_navigation_ux_contracts.py tests/test_admin_erp_navigation_portal_contracts.py tests/test_portal_safety_contracts.py
node --check static/portal/portal.js
git diff --check
```

Expected: all selected static contracts and JavaScript syntax checks pass with no whitespace errors. The known local FastAPI/Pydantic runtime mismatch is excluded because it fails while loading an unrelated upload route before the locale test reaches this feature.

### Task 3: Review, commit, PR, and deployment verification

**Files:**

- Modify: `docs/superpowers/plans/2026-07-29-admin-mobile-navigation.md`

- [x] **Step 1: Perform spec-compliance review**

Verify the diff implements only the mobile Admin navigation task, has no Bot/provider/PayOS/ledger changes, retains `renderMobileNav(page)`, shows no customer routes on `/admin`, and fails closed if grants are absent.

- [x] **Step 2: Perform code-quality review**

Verify longest-route current-state selection prevents duplicate `aria-current`, labels are escaped, touch targets remain at least 44px, `prefers-reduced-motion` remains in force, and no browser-held role grants a route.

- [ ] **Step 3: Commit and open the focused PR**

Run:

```powershell
git add static/portal/portal.js tests/test_admin_erp_navigation_portal_contracts.py tests/test_portal_navigation_ux_contracts.py tests/test_portal_safety_contracts.py docs/superpowers/plans/2026-07-29-admin-mobile-navigation.md
git commit -m "Add server-authorized Admin mobile navigation"
git push -u origin feature/p0-webapp-copyfast174-admin-mobile-navigation
gh pr create --base main --head feature/p0-webapp-copyfast174-admin-mobile-navigation --title "Add server-authorized Admin mobile navigation" --body "## Summary`n- separate the internal Admin ERP mobile dock from customer navigation`n- project only signed server-authorized Admin routes and fail closed on empty grants`n- retain an accessible five-item mobile dock without a new client authority path`n`n## Tests`n- selected pytest navigation/admin/safety contracts`n- node --check static/portal/portal.js`n- git diff --check"
```

- [ ] **Step 4: Merge only after CI is green, then verify Railway health**

After the PR check passes, merge it through GitHub. Verify `https://app.toanaas.vn/health` returns HTTP 200 and the deployed `portal.js` contains `renderAdminMobileNav` before moving to the next sequential feature.

---

## Plan self-review

- **Spec coverage:** The plan covers the distinct internal mobile experience, server-issued route projection, current-route accessibility, empty-grant fail-closed behavior, existing localization/touch/motion preservation, tests, review, PR, merge, and deployment check.
- **Scope:** No Bot, provider, PayOS, webhook, ledger, customer dock, Video menu, or LocalVideoStudio files are modified.
- **Ambiguity resolved:** The compact dock is a maximum-five ordered projection of server-authorized modules. It starts with the current authorized module, includes the issued ERP overview when available, then follows server order. Longest route wins the sole current state, and only `/admin/jobs/*` or `/admin/support/*` inherit their already-authorized parent module.
