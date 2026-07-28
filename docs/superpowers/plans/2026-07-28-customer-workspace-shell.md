# Customer Workspace Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed customer rail compact and task-oriented while keeping every existing customer route discoverable through `/features` and the server-safe command palette.

**Architecture:** `static/portal/portal.js` keeps the existing authoritative route manifest and Admin ERP projection untouched.  It replaces only the permanent customer sidebar projection with five concise groups, adds a presentation-only current-workflow cue for deep customer routes, and shows the existing Video Studio sub-tree only while the current page is in that family.  `portal-theme.css` supplies the narrow rail alignment treatment; `portal-i18n.js` supplies the one new shared chrome label in VI/EN/ZH.

**Tech Stack:** FastAPI-rendered portal shell, browser-native JavaScript/CSS, pytest static contracts, Node syntax check, no new dependencies.

**Constraints:** Do not edit Bot/Telegram/PayOS/bridge/provider/wallet logic, `C:\Users\toann\Documents\Codex\motion-kit`, `C:\Users\toann\Documents\Codex\tools\OpenMontage`, `feat/p1-localvideostudio26*`, or LocalVideoStudio26-owned capability/skills/video/QA files.  Do not change `videoStudioNavGroups` leaf routes or any feature registry.  Do not deploy.

---

### Task 1: Establish the compact-shell contract and correct the stale community assertion

**Files:**
- Modify: `tests/test_portal_navigation_ux_contracts.py`
- Modify: `tests/test_portal_safety_contracts.py`
- Test: `tests/test_portal_navigation_ux_contracts.py`
- Test: `tests/test_portal_safety_contracts.py`

- [ ] **Step 1: Add the failing customer-rail expectations**

  Add a new test named `test_customer_sidebar_uses_five_compact_groups_and_keeps_deep_routes_discoverable` that reads the `navGroups` and `commandPaletteItems` source sections.  Assert all five permanent customer group labels are present exactly once:

  ```python
  for label in ("Workspace", "Tạo mới", "Công việc", "Ví & gói", "Tài khoản & hỗ trợ"):
      assert navigation.count(f'label: "{label}"') == 1
  ```

  Assert the compact direct entry paths are retained (`/dashboard`, `/projects`, `/workboard`, `/campaigns`, `/calendar`, `/features`, `/chat`, `/content-studio`, `/image-studio`, `/workspace`, `/jobs`, `/assets`, `/asset-vault`, `/approvals`, `/wallet`, `/wallet/topup`, `/membership`, `/packages`, `/pricing`, `/account`, `/tickets`, `/support`), each permanent group has at most five links, the old dense non-video labels are absent from the permanent literals, and the command palette still enumerates `Object.values(manifest)` with server-authorized Admin filtering.

- [ ] **Step 2: Add the failing contextual-video and active-route expectations**

  In the same test, assert the existing `videoStudioNavGroups` declaration and literal `groups.splice(3, 0, ...videoStudioNavGroups);` remain, but are guarded by `matchesRouteFamily(currentRoute, "/video-studio")`.  Assert the source includes `currentCustomerWorkflowGroup`, `label: "Đang mở"`, `current: true`, and `portal-nav-group--current` so a deep active customer page remains oriented without restoring the full catalogue.

- [ ] **Step 3: Correct the stale safety expectation only**

  In `test_personal_web_memory_is_native_while_bot_companions_preserve_telegram_first_workflows`, leave `/referrals` and `/rewards` as Bot companions, but change the `/community` expectation to its established native trust-center contract:

  ```python
  assert 'customerPage("/community", "Cộng đồng"' in PORTAL
  assert 'botCompanionPage("/community", ' not in PORTAL
  ```

  This does not change production behavior: commit `faf45bf` intentionally made Community a server-checked Web trust center and the previous test was stale.

- [ ] **Step 4: Run the RED checks**

  Run:

  ```powershell
  C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_portal_navigation_ux_contracts.py tests/test_portal_safety_contracts.py
  ```

  Expected: the new compact/navigation assertions fail because `navGroups` still contains the permanent 80-link projection; the updated Community assertion passes after the test correction.

- [ ] **Step 5: Commit the contract checkpoint**

  ```powershell
  git add tests/test_portal_navigation_ux_contracts.py tests/test_portal_safety_contracts.py
  git commit -m "test: define compact customer workspace navigation"
  ```

### Task 2: Implement the safe customer navigation projection

**Files:**
- Modify: `static/portal/portal.js:9080-9300`
- Test: `tests/test_portal_navigation_ux_contracts.py`
- Test: `tests/test_admin_erp_navigation_portal_contracts.py`

- [ ] **Step 1: Replace only the permanent customer link matrix**

  At the start of `navGroups(context, currentPage)`, compute the already-rendered path and build exactly these permanent groups:

  ```javascript
  const currentRoute = normalizePath(currentPage && (currentPage.routePath || currentPage.path));
  const groups = [
    { label: "Workspace", defaultOpen: true, links: [
      ["/dashboard", "Tổng quan", ICONS.dashboard],
      ["/projects", "Project Center", ICONS.dashboard],
      ["/workboard", "Workboard", ICONS.workboard],
      ["/campaigns", "Kế hoạch nội dung", ICONS.prompt],
      ["/calendar", "Lịch nội dung", ICONS.system]
    ]},
    { label: "Tạo mới", links: [
      ["/features", "Tất cả công cụ", ICONS.prompt],
      ["/chat", "Content & Chat", ICONS.chat],
      ["/content-studio", "Content Studio", ICONS.prompt],
      ["/image-studio", "Image Studio", ICONS.image]
    ]},
    { label: "Công việc", links: [
      ["/workspace", "Bản nháp", ICONS.prompt],
      ["/jobs", "Job Center", ICONS.jobs],
      ["/assets", "Tài sản", ICONS.assets],
      ["/asset-vault", "Asset Vault", ICONS.assets],
      ["/approvals", "Tự rà soát", ICONS.security]
    ]},
    { label: "Ví & gói", links: [
      ["/wallet", "Ví Xu", ICONS.wallet],
      ["/wallet/topup", "Nạp Xu", ICONS.payments],
      ["/membership", "Membership", ICONS.pricing],
      ["/packages", "Gói dịch vụ", ICONS.pricing],
      ["/pricing", "Bảng giá", ICONS.pricing]
    ]},
    { label: "Tài khoản & hỗ trợ", links: [
      ["/account", "Tài khoản", ICONS.account],
      ["/tickets", "Ticket của tôi", ICONS.ticket],
      ["/support", "Hỗ trợ", ICONS.support]
    ]}
  ];
  ```

  Do not remove any manifest entry, page definition, registry record, `isNavCurrent` rule, command-palette route, API call, access check or background behavior.

- [ ] **Step 2: Add a presentation-only current workflow helper**

  Directly before `navGroups`, add `currentCustomerWorkflowGroup(currentPage, groups)`.  It must use `safeCatalogRoute` and `normalizePath`, return `null` for an Admin route, return `null` when one compact link is already current, and otherwise return one `defaultOpen: true, current: true` group labelled `"Đang mở"` with exactly the loaded route/title and `ICONS.prompt`.  It must not read/write storage, fetch, mutate `manifest`, infer roles, or create a route that was not already rendered.

  Insert the helper result with `groups.unshift(currentGroup)` only when non-null.

- [ ] **Step 3: Keep Video local and ERP server-authorized**

  Keep the full existing `videoStudioNavGroups` declaration byte-for-byte in meaning.  Change only its insertion to:

  ```javascript
  if (matchesRouteFamily(currentRoute, "/video-studio")) {
    groups.splice(3, 0, ...videoStudioNavGroups);
  }
  ```

  Keep the existing `adminErpNavigation(context)` and `erp.groups.forEach` mapping.  Append ERP groups only if `currentRoute === "/admin" || currentRoute.startsWith("/admin/")`; do not derive entitlement from browser role or expose an ERP shortcut on customer routes.

- [ ] **Step 4: Mark the current-workflow group structurally**

  In `renderSidebar`, append ` portal-nav-group--current` to the native `<details>` class only when `group.current === true`.  Keep the same `<details>/<summary>` semantics, open behavior, link escaping, focus management and `aria-current="page"` calculation.

- [ ] **Step 5: Run the GREEN contract checks**

  Run:

  ```powershell
  C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_portal_navigation_ux_contracts.py tests/test_portal_safety_contracts.py tests/test_admin_erp_navigation_portal_contracts.py
  ```

  Expected: all selected tests pass; Admin navigation remains server-manifest based and the existing mobile five-item dock test still passes unchanged.

- [ ] **Step 6: Commit the JavaScript projection**

  ```powershell
  git add static/portal/portal.js tests/test_portal_navigation_ux_contracts.py
  git commit -m "feat: streamline customer workspace navigation"
  ```

### Task 3: Localize and align the current-workflow rail treatment

**Files:**
- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal-theme.css`
- Modify: `tests/test_portal_i18n_bundle_contracts.py`
- Test: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Add the failing locale coverage contract**

  Add `"nav.currentWorkflow"` to the required key list in `_node_i18n_snapshot`.  The assertion must run for every reviewed locale and therefore fail before messages are added.

- [ ] **Step 2: Run the RED locale check**

  Run:

  ```powershell
  C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_portal_i18n_bundle_contracts.py
  ```

  Expected: FAIL because `nav.currentWorkflow` is absent from the equal VI/EN/ZH message bundles.

- [ ] **Step 3: Add reviewed copy and consume it in the helper**

  Add the same key to all three locale bundles in `static/portal/portal-i18n.js`:

  ```javascript
  // vi / en / zh
  "nav.currentWorkflow": "Đang mở" / "Open now" / "当前工作"
  ```

  In `currentCustomerWorkflowGroup`, use `uiText("nav.currentWorkflow", "Đang mở")` for the group label rather than leaving shared chrome hard-coded.

- [ ] **Step 4: Add final-theme rules without touching `portal.css`**

  Append a small scoped block to `static/portal/portal-theme.css` after the current signed-workspace rail rules:

  ```css
  .portal-nav-group--current { border-bottom-color: var(--portal-border-strong); }
  .portal-nav-group--current .portal-nav-summary,
  .portal-nav-group--current .portal-nav-label { color: var(--portal-nav-active-text); }
  .portal-nav-group--current .portal-nav-group-count {
    min-width: 2ch;
    color: var(--portal-nav-active-icon);
    font-variant-numeric: tabular-nums;
    text-align: end;
  }
  ```

  Limit the change to semantic tokens, no raw colors, no animation beyond the foundation tokens, no layout-shifting hover, and no change to the fixed five-item mobile dock.

- [ ] **Step 5: Run the GREEN locale and syntax checks**

  Run:

  ```powershell
  C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_portal_i18n_bundle_contracts.py
  node --check static/portal/portal.js
  ```

  Expected: locale test passes with equal VI/EN/ZH keysets and JavaScript syntax check exits 0.

- [ ] **Step 6: Commit the shared chrome alignment**

  ```powershell
  git add static/portal/portal-i18n.js static/portal/portal-theme.css tests/test_portal_i18n_bundle_contracts.py
  git commit -m "feat: align compact customer workspace rail"
  ```

### Task 4: Verify the customer shell and prepare the dependent PR

**Files:**
- Modify: `docs/superpowers/plans/2026-07-28-customer-workspace-shell.md` (checkboxes only)
- Test: `tests/test_portal_navigation_ux_contracts.py`
- Test: `tests/test_portal_safety_contracts.py`
- Test: `tests/test_admin_erp_navigation_portal_contracts.py`
- Test: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Run focused final checks**

  Run:

  ```powershell
  C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests/test_portal_navigation_ux_contracts.py tests/test_portal_safety_contracts.py tests/test_admin_erp_navigation_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py
  C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m py_compile copyfast_pages.py
  node --check static/portal/portal.js
  node --check static/portal/portal-motion.js
  git diff --check origin/feature/p0-webapp-ui-motion-foundation...HEAD
  ```

  Expected: all checks pass.  No provider, payment, Bot, worker, webhook or production request is invoked.

- [ ] **Step 2: Run rendered customer-shell QA**

  Start the existing local test server with mocked/local-only state.  Verify `/dashboard` and a deep customer route at 375, 768, 1024 and 1440px, then verify reduced-motion.  Confirm:

  - desktop rail has only the five compact groups outside Video Studio;
  - `/features` and Ctrl/⌘K still expose the complete customer catalogue;
  - a deep route gets the one current-workflow cue;
  - the mobile dock stays Workspace, Studio, Jobs, Assets, Account;
  - customer pages do not show ERP groups even for a context containing server-authorized Admin data;
  - no console errors, horizontal overflow, broken focus ring, or fake job/payment/provider state appears.

- [ ] **Step 3: Record fidelity evidence and clean local artifacts**

  Compare the rendered 1440px and 375px screenshots against the accepted Customer desktop/mobile concept files listed in `docs/superpowers/specs/2026-07-28-ui-motion-foundation-design.md`.  Record at least five checks: rail hierarchy, palette, typography, control alignment, five-item dock, and motion/reduced-motion.  Delete temporary servers, screenshots and logs outside the repository when QA completes.

- [ ] **Step 4: Commit the checked plan state and publish a dependent PR**

  ```powershell
  git add docs/superpowers/plans/2026-07-28-customer-workspace-shell.md
  git commit -m "docs: record customer workspace shell verification"
  git push -u origin feature/p0-webapp-customer-workspace-shell
  ```

  Create a PR with base `feature/p0-webapp-ui-motion-foundation` while PR #168 remains unmerged, title `Streamline customer workspace shell`, and a body that documents the stale Community test correction, the unchanged Video route ownership, and the no-API/no-authority scope.
