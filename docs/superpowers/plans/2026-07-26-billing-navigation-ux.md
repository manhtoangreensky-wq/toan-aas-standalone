# Billing Navigation UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a responsive, app-first navigation strip that connects the four existing Billing routes without changing payment or ledger authority.

**Architecture:** `portal.js` owns a small pure renderer for the Billing route
links and calls it from the existing wallet/catalog renderers. `portal.css`
styles the strip with the existing dark-slate/teal tokens. A static Python
contract protects route coverage and the canonical safety boundary.

**Tech Stack:** FastAPI portal shell, vanilla JavaScript renderer, CSS, pytest
source contracts.

---

### Task 1: Lock the navigation and safety contract

**Files:**
- Create: `tests/test_billing_navigation_app_ux_contracts.py`
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal.css`

- [ ] **Step 1: Write the failing test**

```python
def test_billing_nav_covers_each_existing_route_without_actions() -> None:
    assert 'function renderBillingWorkspaceNav(currentPath)' in PORTAL
    for path in ("/wallet", "/wallet/topup", "/packages", "/pricing"):
        assert f'path: "{path}"' in nav
        assert f'renderBillingWorkspaceNav("{path}")' in PORTAL
    assert "data-portal-action" not in nav
```

Also assert that the Billing CSS scope contains the nav, 44px minimum link
height, `overflow-x: auto`, `scroll-snap-type`, focus styling, the mobile rule,
and a reduced-motion rule.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest -q tests/test_billing_navigation_app_ux_contracts.py
```

Expected: the test fails because `renderBillingWorkspaceNav` does not exist.

- [ ] **Step 3: Add the minimal route-only renderer**

```js
function renderBillingWorkspaceNav(currentPath) {
  const activePath = normalizePath(currentPath || "/wallet");
  const items = [
    { path: "/wallet", label: "Ví Xu" },
    { path: "/wallet/topup", label: "Nạp Xu" },
    { path: "/packages", label: "Gói" },
    { path: "/pricing", label: "Bảng giá" }
  ];
  return `<nav class="portal-billing-nav" aria-label="Điều hướng thanh toán">...</nav>`;
}
```

Call it after `renderHero` from `renderWallet` and `renderCatalog`. Use
`aria-current="page"` only for the exact current route. Do not change the
payment form, bridge calls, wallet projection, catalog projection, or existing
actions.

- [ ] **Step 4: Add tokenized responsive styles**

```css
.portal-billing-nav { overflow-x: auto; scroll-snap-type: x mandatory; }
.portal-billing-nav a { min-height: 44px; scroll-snap-align: start; }
@media (prefers-reduced-motion: reduce) {
  .portal-billing-nav a { transition: none; }
}
```

Use existing `--portal-*` tokens, internal horizontal scrolling only, and the
same active/focus treatment as the signed Account settings navigation. Do not
introduce gradients, raw payment branding, or an extra navigation system.

- [ ] **Step 5: Run focused verification**

Run:

```powershell
python -m pytest -q tests/test_billing_navigation_app_ux_contracts.py tests/test_billing_canonical_journey_contracts.py
node --check static/portal/portal.js
git diff --check
```

Expected: all tests pass, JavaScript syntax is valid, and there are no
whitespace errors.

### Task 2: Validate the rendered customer flow

**Files:**
- Modify: no additional files

- [ ] **Step 1: Start the local FastAPI app with a temporary session database**

Use a temporary `WEBAPP_SESSION_DB_PATH`, a local `WEB_SESSION_SECRET`, disabled
provider/payment flags, and `WEB_COOKIE_SECURE=false`. Do not configure or call
PayOS, a provider, Telegram, or Core Bridge.

- [ ] **Step 2: Verify the route flow in the in-app browser**

Navigate `/wallet` → `/wallet/topup` → `/packages` → `/pricing`. Confirm the
active tab changes exactly with the route, all four links are anchors, and
there are no console warnings/errors.

- [ ] **Step 3: Verify mobile containment**

At a 375px viewport, confirm the Billing strip itself can scroll horizontally,
the page has no horizontal overflow, and each link has a 44px-or-greater touch
height. Reset the viewport and remove the temporary QA server/state after the
check.
