# Account Security Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the signed `/account/security` portal surface into the shared light teal/cyan system without changing any security action, signed-session rule, API, form, capability, or server state.

**Architecture:** Append one final, root-scoped CSS layer rather than changing the legacy renderer or global security contracts. A static contract pins selector scope, semantic-token-only styling, keyboard focus, disabled controls, responsive posture layout, and reduced-motion behavior; existing account-security tests continue to prove the sensitive workflows are untouched.

**Tech Stack:** Python `pytest`, static CSS contracts, vanilla portal CSS/JS, FastAPI account-security contract tests.

---

### Task 1: Pin the final light Security Center contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Read: `tests/test_account_security_app_ux_contracts.py`
- Read: `tests/test_account_security_center.py`
- Read: `tests/test_account_security_portal_contracts.py`

- [ ] **Step 1: Write the failing test**

Add a test named `test_light_account_security_final_surface_keeps_signed_actions_clear` that searches for the marker `/* Final light Account Security Center surface */`, extracts only that final layer, and requires root scope `.portal-page.portal-account-security`. Require these surfaces: `.portal-settings-nav`, `.portal-security-posture`, `.portal-security-posture-facts`, `.portal-panel-row`, `.portal-security-assurance`, `.portal-notice`, `.portal-password-toggle`, `.portal-button--quiet`, checked/disabled/focus-visible controls, `@media (max-width: 1040px)`, `@media (max-width: 700px)`, `@media (prefers-reduced-motion: reduce)`, and `min-height: 44px;`. Assert every parsed selector branch starts with the root scope and that the layer has no raw hex, `rgb`/`hsl`, gradients, `transparent`, or non-`--portal-*` token.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py -k account_security_final_surface -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast242-red
```

Expected: `1 failed` because the final-light marker is absent.

- [ ] **Step 3: Add only the scoped visual layer**

Append the marker and CSS to `static/portal/portal-theme.css`. Use selectors beginning with `.portal-page.portal-account-security` and semantic `--portal-*` values only. Set the security posture, session/OAuth/MFA cards, assurance disclosure, nav, notices, password toggle, disabled controls, quiet actions and focus ring onto light surfaces. Keep hover states in place (no transform) and preserve explicit disabled affordance. At `1040px`, reduce posture facts to two columns; at `700px`, use one column and 44px touch controls; in `prefers-reduced-motion`, disable only this layer's motion. Do not edit `portal.js`, `integration.js`, `app.py`, `copyfast_auth.py`, or existing account-security behavior.

- [ ] **Step 4: Run test to verify it passes**

Run the red command again. Expected: `1 passed`.

- [ ] **Step 5: Run critical regression contracts**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_account_security_app_ux_contracts.py tests/test_account_security_center.py tests/test_account_security_portal_contracts.py tests/test_totp_mfa_portal_contracts.py -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast242-focused
git diff --check
```

Expected: all selected tests pass and the diff is whitespace-clean.

- [ ] **Step 6: Commit**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-07-31-account-security-light-surface.md
git commit -m "Polish account security light surface"
```
