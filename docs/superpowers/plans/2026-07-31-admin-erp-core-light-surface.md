# Admin ERP Core Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the protected Admin ERP home, navigation directory and domain centers into a compact teal/cyan internal control center with clear hierarchy, density and no browser-authority implication.

**Architecture:** Append a final CSS-only layer scoped to the admin-core route classes. It restyles existing summary, directory, authority and domain DOM without modifying signed-session/role checks, canonical authority, admin data, core bridge, finance or other server behavior.

**Tech Stack:** Server-rendered portal shell, vanilla JavaScript renderer, CSS custom properties, pytest static contracts.

---

### Task 1: Lock the Admin ERP light-surface contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py`

- [x] **Step 1: Add the failing test**

Add `test_light_admin_erp_core_final_surface_keeps_protected_control_center_readable`. It finds `/* Final light Admin ERP core surface */`, captures only through the next final-light marker or EOF, and requires:

```python
required = (
    ".portal-admin-home",
    ".portal-admin-domain",
    ".portal-admin-system-stewardship",
    ".portal-admin-guard",
    ".portal-admin-grid",
    ".portal-admin-work-queues",
    ".portal-admin-work-queue",
    ".portal-admin-authority",
    ".portal-admin-directory",
    ".portal-admin-directory-group",
    ".portal-admin-domain-intro",
    ".portal-admin-domain-card",
    ".portal-stewardship-intro",
    ":focus-visible",
    "@media (max-width: 700px)",
)
```

Reject raw hex, `rgba(`, gradients and custom variables outside `--portal-*`. Update the preceding Support Desk extractor to stop at the next final-light marker.

- [x] **Step 2: Run RED**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\admin-erp-238-foundation-qa tests\test_teal_cyan_ui_foundation_contracts.py
```

Expected: only the new admin final-layer contract fails because its marker is missing.

### Task 2: Append a scoped Admin ERP core layer

**Files:**
- Modify: `static/portal/portal-theme.css`

- [x] **Step 1: Add the token-only CSS**

Scope every selector under:

```css
.portal-page:is(.portal-admin-home, .portal-admin-domain, .portal-admin-system-stewardship)
```

Use only `--portal-*` colors. Cover the guard/authority state, KPI grid, work queues, readiness tables, authority disclosure, directory groups/cards, domain intro/cards/boundaries and Stewardship intro/status. Preserve control-center density, non-shifting hover, focus-visible treatment and guarded/read-only truth. At `700px`, collapse grids/rows safely and enforce 44px controls. Do not modify `portal.js`, routes, admin permission checks, APIs, Core Bridge, payments, providers, Bot or data.

- [x] **Step 2: Run GREEN**

Run the same test command. Expected: all foundation contracts pass.

### Task 3: Verify protected admin navigation, then commit

**Files:**
- Test: `tests/test_admin_erp_navigation_portal_contracts.py`
- Test: `tests/test_admin_erp_navigation.py`
- Test: `tests/test_admin_domain_centers_contracts.py`
- Test: `tests/test_admin_audit_portal_contracts.py`

- [x] **Step 1: Run targeted checks**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\admin-erp-238-contract-qa tests\test_admin_erp_navigation_portal_contracts.py tests\test_admin_erp_navigation.py tests\test_admin_domain_centers_contracts.py tests\test_admin_audit_portal_contracts.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
```

Expected: all commands pass. The UI change cannot grant a role, mutate canonical state, expose raw audit/evidence or create a provider/payment/Bot action.

- [x] **Step 2: Commit**

```powershell
git add docs/superpowers/plans/2026-07-31-admin-erp-core-light-surface.md tests/test_teal_cyan_ui_foundation_contracts.py static/portal/portal-theme.css
git commit -m "Refine Admin ERP core light control center"
```
