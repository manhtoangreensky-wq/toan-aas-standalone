# Security & Access Posture Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the signed `/admin/security` and `/admin/access` aggregate-only posture views a compact, high-trust light teal/cyan ERP surface without changing access/security data, session enforcement, authorization, redaction, or control boundaries.

**Architecture:** Keep the shared `renderAdminSecurityAccessPosture` renderer and all server/API logic untouched. Add one CSS layer rooted only at `.portal-page.portal-admin-security-access-posture`, plus a static contract. The layer presents existing aggregate metrics and run rows clearly while preserving the fact that neither route is a credential manager, audit log, bridge view or control plane.

**Tech Stack:** FastAPI Portal shell, vanilla CSS, existing Portal JavaScript, Python static and authority contract tests.

---

## File structure

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py` — route-scoped visual contract.
- Modify: `static/portal/portal-theme.css` — final Security & Access CSS only.
- Create: `docs/superpowers/plans/2026-08-01-admin-security-access-light-surface.md` — this record.

## Design constraints

- This is a light, dense observability surface; no faux real-time dashboard, security claim, secret or user identity is introduced.
- Existing metrics stay aggregate-only and status badges retain visible labels. `read_only` is contextual/info, `guarded` warning, `failed` danger.
- Cards and run rows align data without creating a table or new action control. The page keeps its existing plain read-only behavior.
- The desktop operations grid collapses at 980px; metrics become one column and controls remain 44px on mobile; reduced-motion remains intact.
- Every new selector is rooted at the exact page class and every color comes from existing portal tokens.

### Task 1: Add a failing visual contract

**Files:**

- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_security_access_final_surface_keeps_aggregate_boundary_clear`

- [x] **Step 1: Write red test**

Extract `renderAdminSecurityAccessPosture`, assert its exact root class, then isolate:

```python
layer = re.search(
    r"/\* Final light Security and Access Posture surface \*/(?P<css>.*?)(?=/\* Final light [^*]*\*/|\Z)",
    theme_source,
    flags=re.DOTALL,
)
assert layer is not None
root_scope = ".portal-page.portal-admin-security-access-posture"
```

Require tokenized styles for root, admin intro, metrics, cards, operations rows, boundary, quiet controls, focus and `read_only`/`guarded`/`failed` badges. Require 980px one-column grid, 700px metrics and 44px controls, and reduced motion. Use parser helpers to reject scope leakage, raw colors/gradients/transparent and non-portal variables.

- [x] **Step 2: Prove red**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_security_access_final_surface_keeps_aggregate_boundary_clear
```

Expected: marker missing only.

### Task 2: Append the smallest visual layer

**Files:**

- Modify: `static/portal/portal-theme.css`
- Test: `tests/test_teal_cyan_ui_foundation_contracts.py::test_light_admin_security_access_final_surface_keeps_aggregate_boundary_clear`

- [x] **Step 1: Add route-scoped token CSS**

Append `/* Final light Security and Access Posture surface */` after Reliability. Style root, existing intro/metrics/cards/run rows/boundary/quiet controls/focus/badges with portal tokens only. Keep status colors semantic, stationary hover and disabled controls visible; do not add DOM, JS, requests, navigation, write affordance or text.

- [x] **Step 2: Add responsive/reduced-motion rules**

At 980px, collapse only the root's `portal-operations-admin-grid`. At 700px, make its metrics one column and retain 44px primary/quiet controls. Under reduced motion, disable transition/transform only for this root's cards, metrics, runs and buttons.

- [x] **Step 3: Prove green**

Run Task 1 focused test; expected `1 passed`.

### Task 3: Preserve read-only security authority

**Files:**

- Test: `tests/test_admin_security_access_posture.py`
- Test: `tests/test_admin_security_access_portal_contracts.py`
- Test: `tests/test_admin_erp_navigation.py`

- [x] **Step 1: Run regression**

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_admin_security_access_posture.py tests/test_admin_security_access_portal_contracts.py tests/test_admin_erp_navigation.py
```

Expected: all pass; no identity/secret/raw audit data, session mutation, role control or browser authority appears.

- [x] **Step 2: Verify diff scope**

```powershell
git diff --check
git diff -- static/portal/portal.js static/portal/integration.js app.py copyfast_admin_security_access.py copyfast_auth.py
```

Expected: clean and no behavior-file changes.

- [x] **Step 3: Commit**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-08-01-admin-security-access-light-surface.md
git commit -m "Polish Security and Access Posture light surface"
```

## Self-review

- One shared root owns both routes without styling any unrelated Admin surface.
- The UI remains a redacted observation surface and cannot visually overpromise a security posture or auto-remediation.
- Focused tests cover the boundary most likely to regress: signed server data, no browser role/identity, no write/control surface and mobile-safe presentation.
