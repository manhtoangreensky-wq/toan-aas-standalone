# Onboarding Light Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the signed optional Telegram onboarding route feel like a calm, professional light teal/cyan Workspace journey without altering Web-first, link, or Bot authority behavior.

**Architecture:** Append one token-only final visual layer scoped to `.portal-page.portal-onboarding-page`. Keep the existing renderer, signed-session checks, link-code expiry/replay rules, disabled guarded action, continuation routing, API contracts, Bot, bridge, PayOS and providers unchanged. The global motion foundation remains progressive enhancement; this slice must remain fully usable with reduced motion.

**Tech Stack:** Python `pytest`, static CSS contracts, vanilla portal CSS/JS.

---

### Task 1: Pin the final light onboarding contract

**Files:**
- Modify: `tests/test_teal_cyan_ui_foundation_contracts.py`
- Modify: `static/portal/portal-theme.css`
- Create: `docs/superpowers/plans/2026-07-31-onboarding-light-surface.md`
- Read: `tests/test_onboarding_ux_contracts.py`
- Read: `tests/test_copyfast_auth_api.py`

- [x] **Step 1: Write the failing test**

Add `test_light_onboarding_final_surface_keeps_web_first_path_and_guarded_link_clear`. It must locate `/* Final light Onboarding surface */`, require root scope `.portal-page.portal-onboarding-page`, verify the action card, guarded notice, independent Workspace choice, progress rail/current step, route card, assurance disclosure, quiet/disabled/focus states, 820px/520px responsive blocks and reduced-motion block. Assert exact evidence that the Web-first action remains light teal/cyan, guarded controls remain visibly disabled without pretending success, touch targets are at least `44px`, and all final selectors stay inside root scope with portal tokens only.

- [x] **Step 2: Run test to verify it fails**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py -k onboarding_final_surface -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast246-red
```

Expected: `1 failed` because the final marker is absent.

- [x] **Step 3: Add only scoped visual CSS**

Append the marker and a final CSS layer in `static/portal/portal-theme.css`. Use only `--portal-*` tokens. Make the Web-independent action clear, maintain the Telegram link as an honest guarded secondary path when unavailable, normalize progress/route/assurance surfaces, preserve focus visibility and 44px controls, arrange action before progress at small widths, and disable cosmetic transitions under `prefers-reduced-motion`. Do not change HTML, renderer logic, label text, action attributes, link availability or any API/state behavior.

- [x] **Step 4: Run test to verify it passes**

Run the Step 2 command again. Expected: `1 passed`.

- [x] **Step 5: Run critical onboarding and account contracts**

Run:

```powershell
& 'C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\subtitle-ui-qa\Scripts\python.exe' -m pytest -q tests/test_teal_cyan_ui_foundation_contracts.py tests/test_onboarding_ux_contracts.py tests/test_copyfast_auth_api.py -k 'onboarding or web_owned_profile_defaults or bot_companion_routes or telegram_first_account_can_add_email_password or signed_session_csrf_and_telegram_link' -p no:cacheprovider --basetemp C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\tmp\copyfast246-focused
git diff --check
```

Expected: selected tests pass and the diff is whitespace-clean.

- [ ] **Step 6: Commit**

```powershell
git add static/portal/portal-theme.css tests/test_teal_cyan_ui_foundation_contracts.py docs/superpowers/plans/2026-07-31-onboarding-light-surface.md
git commit -m "Polish onboarding light surface"
```
