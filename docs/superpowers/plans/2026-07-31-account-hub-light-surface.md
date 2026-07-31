# Account Hub Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the signed Account Hub to the final light teal/cyan design system while preserving profile, OAuth, Telegram handoff, session and logout behavior.

**Architecture:** Append one visual layer scoped to `.portal-page.portal-account-page` and protect it with a static contract. No renderer, `integration.js`, route, auth API, Core Bridge, Bot, PayOS, provider or account-state behavior changes are allowed.

**Tech Stack:** Python `pytest`, static CSS contracts, vanilla portal CSS/JS.

---

### Task 1: Pin the final light Account Hub contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Modify: `static/portal/portal-theme.css`
- Read: `tests/test_account_security_app_ux_contracts.py`
- Read: `tests/test_account_private_read_stale_response_contracts.py`

- [x] **Step 1: Write the failing test**

Add `test_light_account_hub_final_surface_keeps_signed_account_actions_clear`. Require the marker `/* Final light Account Hub surface */`, root scope `.portal-page.portal-account-page`, and style evidence for `.portal-settings-nav`, `.portal-account-command`, `.portal-account-command-facts`, `.portal-account-session`, `.portal-summary-item`, `.portal-oauth-method`, `.portal-bot-companion-card`, `.portal-account-assurance`, `.portal-notice`, quiet/logout/disabled/focus-visible states, `@media (max-width: 1040px)`, `@media (max-width: 700px)`, `@media (prefers-reduced-motion: reduce)` and `min-height: 44px;`. Assert all selector branches begin with root scope and the final layer has no raw hex, `rgb`/`hsl`, gradient, `transparent`, or non-`--portal-*` token.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py -k account_hub_final_surface -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast245-red
```

Expected: `1 failed` because the marker is absent.

- [x] **Step 3: Add only scoped visual CSS**

Append the marker and CSS layer in `static/portal/portal-theme.css`. Use semantic portal tokens and selector branches starting with `.portal-page.portal-account-page`. Set profile/session/OAuth/Bot-hand-off surfaces to the white/light hierarchy, keep logout semantically destructive with existing portal danger tokens, make disabled and focus states clear, and preserve 1040/700px layout and reduced motion. Do not alter interaction or data contracts.

- [x] **Step 4: Run test to verify it passes**

Run the red command again. Expected: `1 passed`.

- [x] **Step 5: Run critical account contracts**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_account_security_app_ux_contracts.py tests/test_account_private_read_stale_response_contracts.py tests/test_copyfast_auth_api.py -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast245-focused
git diff --check
```

Expected: all selected tests pass and the diff is whitespace-clean.

- [ ] **Step 6: Commit**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-07-31-account-hub-light-surface.md
git commit -m "Polish account hub light surface"
```
