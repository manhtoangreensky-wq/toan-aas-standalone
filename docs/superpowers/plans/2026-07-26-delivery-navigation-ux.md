# Delivery Workspace Navigation UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Add a route-only Delivery navigator that consistently connects Job Center, canonical Assets, and the Web-owned Asset Vault without changing delivery authority or lifecycle behavior.

**Architecture:** A small presentation helper in \`portal.js\` returns three normal same-origin anchors from the current route. The four existing delivery renderers insert the helper directly after their hero. \`portal.css\` supplies a tokenized, horizontal, responsive strip that is independently scrollable on small screens. Static source contracts protect the exact route and safety boundary; existing job and Asset Vault contracts protect the authority boundary.

**Tech Stack:** FastAPI static portal, vanilla JavaScript, CSS custom properties, pytest static-source contracts.

---

### Task 1: Establish the Delivery navigation contract (RED)

**Files:**
- Create: \`tests/test_delivery_navigation_app_ux_contracts.py\`
- Read: \`docs/superpowers/specs/2026-07-26-delivery-navigation-ux-design.md\`
- Read: \`static/portal/portal.js:17662,18009-18215,19900\`
- Read: \`static/portal/portal.css:7041-7092\`

- [ ] **Step 1: Write failing static contract tests**

\`\`\`python
def test_delivery_navigation_has_only_the_three_approved_routes():
    source = function_source(PORTAL_JS, "renderDeliveryWorkspaceNav")
    assert source.count('path: "/jobs"') == 1
    assert source.count('path: "/assets"') == 1
    assert source.count('path: "/asset-vault"') == 1
    assert source.count('path: "') == 3


def test_delivery_navigation_keeps_job_details_in_job_center():
    source = function_source(PORTAL_JS, "renderDeliveryWorkspaceNav")
    assert 'const normalized = normalizePath(currentPath || "/jobs");' in source
    assert 'const activePath = normalized.startsWith("/jobs/") ? "/jobs" : normalized;' in source
    assert 'aria-current="page"' in source


def test_delivery_navigation_is_inserted_after_each_delivery_hero():
    for name in ("renderJobs", "renderJobDetail", "renderAssets", "renderAssetVault"):
        source = function_source(PORTAL_JS, name)
        assert "renderHero(page, context) + renderDeliveryWorkspaceNav" in source
\`\`\`

- [ ] **Step 2: Run the contract to verify it fails because the navigator does not exist**

Run: \`python -m pytest -q tests/test_delivery_navigation_app_ux_contracts.py\`

Expected: FAIL reporting \`renderDeliveryWorkspaceNav\` missing or an approved-route assertion failure.

- [ ] **Step 3: Add boundary and responsive assertions to the same test file**

\`\`\`python
def test_delivery_navigation_stays_route_only_and_uses_tokenized_mobile_safe_css():
    js = function_source(PORTAL_JS, "renderDeliveryWorkspaceNav")
    assert not any(token in js for token in (
        "fetch(", "data-portal-action", "payment", "payos", "provider", "wallet",
        "telegram", "download", "upload", "retry", "refund", "ledger",
    ))
    css = css_block(PORTAL_CSS, ".portal-delivery-nav")
    for token in ("max-width: 100%", "overflow-x: auto", "scroll-snap-type: x mandatory"):
        assert token in css
    assert "min-height: 44px" in css
    assert ".portal-delivery-nav a:focus-visible" in PORTAL_CSS.read_text(encoding="utf-8")
    assert "@media (max-width: 700px)" in PORTAL_CSS.read_text(encoding="utf-8")
    assert "@media (prefers-reduced-motion: reduce)" in PORTAL_CSS.read_text(encoding="utf-8")
\`\`\`

### Task 2: Implement the route-only Delivery navigator (GREEN)

**Files:**
- Modify: \`static/portal/portal.js:before renderJobOutputAssets; renderJobs; renderJobDetail; renderAssets; renderAssetVault\`
- Modify: \`static/portal/portal.css:after .portal-billing-nav styles\`
- Test: \`tests/test_delivery_navigation_app_ux_contracts.py\`

- [ ] **Step 1: Add the smallest navigation renderer required by the failing tests**

\`\`\`javascript
function renderDeliveryWorkspaceNav(currentPath) {
  const normalized = normalizePath(currentPath || "/jobs");
  const activePath = normalized.startsWith("/jobs/") ? "/jobs" : normalized;
  const items = [
    { path: "/jobs", label: t("nav.jobs", "Job Center") },
    { path: "/assets", label: t("nav.assets", "Tài sản") },
    { path: "/asset-vault", label: "Asset Vault" }
  ];
  return '<nav class="portal-delivery-nav" aria-label="' + safeText(t("shellNav.delivery", "Delivery")) + '">' + items.map((item) =>
    '<a href="' + item.path + '"' + (item.path === activePath ? ' aria-current="page"' : "") + '>' + safeText(item.label) + '</a>'
  ).join("") + "</nav>";
}
\`\`\`

- [ ] **Step 2: Insert the renderer immediately after the hero in all four renderers**

\`\`\`javascript
return '<article class="portal-page">' + renderHero(page, context)
  + renderDeliveryWorkspaceNav(page.routePath || page.path)
  + /* existing page-only content, unchanged */;
\`\`\`

Keep \`renderJobOutputAssets\` and all job/asset input data unchanged. Use the existing route-specific article class and current route data in each renderer.

- [ ] **Step 3: Add scoped CSS that mirrors the approved Billing strip behavior**

\`\`\`css
.portal-delivery-nav {
  display: flex;
  width: 100%;
  max-width: 100%;
  gap: 8px;
  overflow-x: auto;
  overscroll-behavior-inline: contain;
  scroll-snap-type: x mandatory;
}
.portal-delivery-nav a { min-height: 44px; scroll-snap-align: start; }
.portal-delivery-nav a:focus-visible { outline: 2px solid var(--portal-teal); }
@media (max-width: 700px) { .portal-delivery-nav a { flex: 0 0 auto; } }
@media (prefers-reduced-motion: reduce) { .portal-delivery-nav a { transition: none; } }
\`\`\`

Reuse the existing dark-slate/teal token family. Do not add behavior, click handlers, forms, actions, storage, API calls, provider calls, payment terms, or assets.

- [ ] **Step 4: Run the test to verify the implementation passes**

Run: \`python -m pytest -q tests/test_delivery_navigation_app_ux_contracts.py\`

Expected: PASS.

### Task 3: Verify no delivery authority regression and inspect the rendered paths

**Files:**
- Test: \`tests/test_delivery_navigation_app_ux_contracts.py\`
- Test: \`tests/test_delivery_center_record_identity_contracts.py\`
- Test: \`tests/test_asset_vault_lifecycle_portal_contracts.py\`
- Test: \`tests/test_portal_safety_contracts.py\`

- [ ] **Step 1: Run focused regression checks and syntax validation**

Run:

\`\`\`powershell
python -m pytest -q tests/test_delivery_navigation_app_ux_contracts.py tests/test_delivery_center_record_identity_contracts.py tests/test_asset_vault_lifecycle_portal_contracts.py tests/test_portal_safety_contracts.py
node --check static/portal/portal.js
git diff --check
\`\`\`

Expected: all tests pass; JavaScript syntax succeeds; no whitespace errors.

- [ ] **Step 2: Run local browser QA with safe flags**

Start a fresh local FastAPI process with a temporary database/session secret and \`WEBAPP_PROVIDER_CALLS_ENABLED=false\`, \`WEBAPP_PAYMENT_ENABLED=false\`, \`WEBAPP_PWA_ENABLED=false\`, and \`WEBAPP_ADMIN_ERP_ENABLED=false\`.

Exercise: \`/jobs\` → click **Tài sản** → click **Asset Vault**; then open \`/jobs/{id}\` in a local seeded/safe signed-account state. Verify a single active tab, conventional route changes, no console errors, and no framework overlay. Repeat at \`375×812\`; verify links are at least 44px tall, only the strip scrolls horizontally, and the page has no horizontal overflow.

- [ ] **Step 3: Review and commit the isolated slice**

Run: \`git diff --check && git status --short\`

Commit only the navigator, its CSS, its contract test, and this plan with:

\`\`\`powershell
git add static/portal/portal.js static/portal/portal.css tests/test_delivery_navigation_app_ux_contracts.py docs/superpowers/plans/2026-07-26-delivery-navigation-ux.md
git commit -m "Add Delivery workspace navigation"
\`\`\`

Then request spec-compliance and code-quality review before creating a PR. Do not deploy Railway or contact external providers.
