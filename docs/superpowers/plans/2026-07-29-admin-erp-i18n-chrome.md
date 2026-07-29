# Admin ERP Localized Chrome Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed Admin ERP home and shared horizontal-table guidance fully readable in the already-supported Vietnamese, English, and Simplified Chinese interface locales without altering any authority, route, data, or write contract.

**Architecture:** Keep the existing server-authorized Admin navigation and data renderers unchanged. Extend the browser-only locale bundle with fixed `adminHome.*` and `table.horizontalScroll.*` chrome, then consume it through the established `uiText()` + `safeText()` boundary in `renderAdminDirectory`, `renderAdminWorkQueues`, `renderAdminOverview`, and `renderDataTableWrap`.

**Tech Stack:** FastAPI portal shell, browser-native JavaScript, static i18n bundle, pytest static/runtime contracts.

---

### Task 1: Lock the missing localized chrome with focused regression contracts

**Files:**

- Modify: `tests/test_app_first_ui_system_contracts.py`
- Modify: `tests/test_product_harmony_ui_contracts.py`
- Modify: `tests/test_portal_i18n_bundle_contracts.py`

- [x] **Step 1: Write failing tests for table guidance and Admin ERP copy**

```python
assert 'uiText("table.horizontalScroll.region"' in table_helper
assert 'uiText("table.horizontalScroll.hint"' in table_helper
assert '"adminHome.directory.title"' in ADMIN_HOME_KEYS
assert '"adminHome.readiness.emptyTitle"' in ADMIN_HOME_KEYS
assert I18N.count('"table.horizontalScroll.region"') == 3
```

- [x] **Step 2: Run the focused tests and verify the current source fails for the missing keys/calls**

Run:

```powershell
python -m pytest -q tests/test_app_first_ui_system_contracts.py tests/test_product_harmony_ui_contracts.py tests/test_portal_i18n_bundle_contracts.py
```

Expected: failure because the table wrapper and Admin renderer still include fixed Vietnamese strings and the new keyset is absent.

### Task 2: Add reviewed fixed-copy translations and consume them safely

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.js`

- [x] **Step 1: Add exactly matching keys for `vi`, `en`, and `zh`**

```javascript
// vi
"table.horizontalScroll.region": "Bảng dữ liệu có thể cuộn ngang. Dùng phím mũi tên trái và phải để xem toàn bộ cột.",
"table.horizontalScroll.hint": "Cuộn ngang để xem các cột còn lại.",
"adminHome.directory.title": "Danh mục Admin ERP",
"adminHome.queues.support.title": "CSKH & Support",
"adminHome.guard.verifiedBody": "Mọi thao tác đọc/ghi vẫn cần capability và Core Bridge; shell không tự thực hiện tác vụ quản trị.",
"adminHome.readiness.emptyTitle": "Chưa có readiness được cấp"
```

Add the same six keys with these reviewed values in the two remaining locale maps:

```javascript
// en
"table.horizontalScroll.region": "This data table scrolls horizontally. Use the Left and Right Arrow keys to view all columns.",
"table.horizontalScroll.hint": "Scroll horizontally to view the remaining columns.",
"adminHome.directory.title": "Admin ERP directory",
"adminHome.queues.support.title": "Customer support",
"adminHome.guard.verifiedBody": "Every read and write still requires a capability and the Core Bridge; this shell does not perform administrative work on its own.",
"adminHome.readiness.emptyTitle": "No readiness has been granted"

// zh
"table.horizontalScroll.region": "此数据表可水平滚动。使用左右箭头键查看所有列。",
"table.horizontalScroll.hint": "水平滚动以查看其余列。",
"adminHome.directory.title": "Admin ERP 目录",
"adminHome.queues.support.title": "客户支持",
"adminHome.guard.verifiedBody": "所有读写操作仍需 capability 和 Core Bridge；此界面不会自行执行管理操作。",
"adminHome.readiness.emptyTitle": "尚未授予就绪状态"
```

Add the remaining fixed renderer keys in every locale map: `adminHome.directory.kicker`, `adminHome.directory.mode.canonicalAdmin`, `adminHome.directory.mode.supportRole`, `adminHome.directory.mode.webLocalAdmin`, `adminHome.directory.mode.serverAuthorized`, `adminHome.directory.description`, `adminHome.directory.moduleCount`, `adminHome.directory.openAction`, `adminHome.guard.pendingBody`, `adminHome.metrics.usersNote`, `adminHome.metrics.engineJobsNote`, `adminHome.metrics.workerJobsNote`, `adminHome.metrics.paymentsNote`, `adminHome.metrics.readinessNote`, `adminHome.readiness.refresh`, `adminHome.readiness.table.feature`, `adminHome.readiness.table.status`, `adminHome.readiness.table.adapter`, `adminHome.readiness.emptyBody`, plus the `title` and `body` pairs for the `support`, `failedJobs`, `jobs`, `payments`, `users`, and `audit` queue entries. All values are fixed interface text only. Keep server-provided module titles, group descriptions, adapter names, IDs, and record data out of the translation catalog.

- [x] **Step 2: Replace only fixed renderer chrome with the existing safe translation boundary**

```javascript
const tableRegion = safeText(uiText(
  "table.horizontalScroll.region",
  "Bảng dữ liệu có thể cuộn ngang. Dùng phím mũi tên trái và phải để xem toàn bộ cột."
));
const tableHint = safeText(uiText(
  "table.horizontalScroll.hint",
  "Cuộn ngang để xem các cột còn lại."
));
return `<div class="portal-data-table-wrap" data-portal-table-scroll tabindex="0" role="region" aria-label="${tableRegion}"><p class="portal-data-table-scroll-hint">${tableHint}</p>${tableMarkup}</div>`;
```

```javascript
const adminText = (key, fallback, params) => uiText(`adminHome.${key}`, fallback, params);
```

Preserve `authorized.routes.has(route)`, `serverAuthorizesAdminRoute`, all hrefs, `role="region"`, `tabindex="0"`, table markup, and keyboard scrolling behavior.

- [x] **Step 3: Run the focused tests and verify they pass**

Run:

```powershell
python -m pytest -q tests/test_app_first_ui_system_contracts.py tests/test_product_harmony_ui_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_admin_erp_navigation_portal_contracts.py tests/test_portal_navigation_ux_contracts.py
```

Expected: all selected tests pass with equal three-locale keysets and Admin navigation authority unchanged.

### Task 3: Review, verify, and hand off one contained PR

**Files:**

- Verify: `static/portal/portal.js`
- Verify: `static/portal/portal-i18n.js`
- Verify: `tests/test_app_first_ui_system_contracts.py`
- Verify: `tests/test_product_harmony_ui_contracts.py`
- Verify: `tests/test_portal_i18n_bundle_contracts.py`

- [x] **Step 1: Check syntax and whitespace**

```powershell
python -m py_compile copyfast_pages.py
git diff --check
```

- [x] **Step 2: Inspect the diff for scope and safety**

```powershell
git diff -- static/portal/portal.js static/portal/portal-i18n.js tests/
```

Expected: no Bot, provider, PayOS, wallet, bridge, role, or route change.

- [ ] **Step 3: Commit and open the PR only after the fresh verification evidence is green**

```powershell
git add static/portal/portal.js static/portal/portal-i18n.js tests/ docs/superpowers/plans/2026-07-29-admin-erp-i18n-chrome.md
git commit -m "Localize Admin ERP chrome and table guidance"
git push -u origin feature/p0-webapp-copyfast173-admin-erp-i18n-chrome
```
