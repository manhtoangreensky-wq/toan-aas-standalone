# Public Landing Auth Entry Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `/welcome` hero CTA pair truthfully direct anonymous visitors to registration/login and signed visitors to workspace/features without changing authentication or header density.

**Architecture:** Keep `renderLanding` as the sole public-companion presenter. Replace its fixed secondary hero anchor with a state-derived ordinary anchor that reuses existing reviewed i18n keys. No CSS, API, storage, session, provider, payment, Bot, or capability code changes are part of this plan.

**Tech Stack:** FastAPI portal shell, vanilla JavaScript, pytest, Node syntax checks, Browser visual QA.

---

### Task 1: Lock a RED public hero account-entry contract

**Files:**

- Create: `tests/test_public_landing_auth_entry_contracts.py`
- Inspect: `tests/test_welcome_public_companion_contracts.py`
- Inspect: `static/portal/portal.js`
- Inspect: `static/portal/portal-i18n.js`

- [ ] **Step 1: Write the failing contract**

Create `tests/test_public_landing_auth_entry_contracts.py`:

```python
"""Contracts for truthful public hero account-entry actions."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


def test_public_landing_hero_actions_describe_the_next_exact_destination() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")
    assert "const heroSecondaryAction = signedIn" in landing
    assert 'href="/login"' in landing
    assert 'text("cta.signIn")' in landing
    assert 'href="/features"' in landing
    assert 'text("hero.explore")' in landing
    assert '${primaryAction}${heroSecondaryAction}' in landing
    assert 'href="/login?next=/features"' not in landing


def test_public_landing_hero_auth_entry_reuses_reviewed_copy_and_stays_presentation_only() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")
    action_start = landing.index("const heroSecondaryAction = signedIn")
    action_end = landing.index("const studioHref", action_start)
    hero_action = landing[action_start:action_end]
    for key in ("landing.cta.signIn", "landing.hero.explore"):
        assert I18N.count(f'"{key}"') == 3
    for forbidden in ("fetch(", "api(", "localStorage", "sessionStorage", "data-portal-action", "<form", "payment", "wallet", "provider", "telegram"):
        assert forbidden.lower() not in hero_action.lower()
```

- [ ] **Step 2: Verify RED**

Run `& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' -m pytest -q tests/test_public_landing_auth_entry_contracts.py`.

Expected: the contract fails because `renderLanding` has no `heroSecondaryAction` and still uses `/login?next=/features` for the anonymous secondary hero action.

### Task 2: Render exact state-aware hero actions

**Files:**

- Modify: `static/portal/portal.js`
- Test: `tests/test_public_landing_auth_entry_contracts.py`
- Test: `tests/test_welcome_public_companion_contracts.py`

- [ ] **Step 1: Add the minimal state-derived anchor**

Immediately after `primaryAction` in `renderLanding`, add:

```javascript
    const heroSecondaryAction = signedIn
      ? `<a class="portal-button" href="/features"><span>${text("hero.explore")}</span><span aria-hidden="true">${portalIcon(ICONS.arrowRight)}</span></a>`
      : `<a class="portal-button" href="/login"><span>${text("cta.signIn")}</span><span aria-hidden="true">${portalIcon(ICONS.arrowRight)}</span></a>`;
```

Replace the fixed second anchor in `.portal-landing-hero-actions` with:

```javascript
<div class="portal-landing-hero-actions">${primaryAction}${heroSecondaryAction}</div>
```

Do not modify `primaryAction`, `navigationAction`, `secondaryAction`, `studioHref`, locale keys, headers, CSS, route manifests, or auth code.

- [ ] **Step 2: Verify GREEN**

Run the exact Task 1 pytest command together with `tests/test_welcome_public_companion_contracts.py`, `tests/test_portal_i18n_bundle_contracts.py`, and `tests/test_portal_i18n_locale_contracts.py`; then run `node --check static/portal/portal.js` and a whitespace diff check. Expected: all focused contracts pass and Portal JavaScript parses.

### Task 3: Visual QA, provenance, and sequential merge

**Files:**

- Modify only if generated output changes: `docs/migration/README.md`, `reports/migration/preflight.json`, `reports/migration/web_inventory.json`

- [ ] **Step 1: Visual QA locally, without a live mutation**

Start `app:app` locally with an ephemeral `WEB_SESSION_SECRET`, clear the three `CORE_BRIDGE_*` variables, and use port `8765`. With Browser at desktop and `375x812`, confirm anonymous hero labels `Bắt đầu Workspace` and `Đăng nhập`, exact `/login` destination, no horizontal overflow, and no console error. Inspect both Aura themes, restore `system`, and do not submit a form or use a production account.

- [ ] **Step 2: Commit source after fresh checks**

Stage only `static/portal/portal.js`, the new contract, this design/plan pair, then commit `Clarify public landing account entry`.

- [ ] **Step 3: Refresh and verify static evidence**

Run `scripts/migration/audit_bot_to_web.py` against frozen Bot baseline `b29d0d474974075f4cba963d2c510f49d2d1b3e4` at the source commit. Stage only the permitted README, preflight, and Web inventory artifacts; restore other audit-generated migration documents. Verify evidence at final `HEAD`.

- [ ] **Step 4: Run gates, push one PR, and merge only after GitHub success**

Run `compileall`, all four Portal JavaScript syntax checks, the focused landing/i18n contracts, and the bounded critical suite from `.github/workflows/webapp-quality.yml`. Check the branch diff against `origin/main`, push `feature/p0-webapp-public-entry-mobile-ux`, create one PR titled `Clarify public landing account entry`, and merge only after GitHub `Verify Web App` is successful. Do not deploy Railway or call a live Bot, provider, PayOS, wallet, job, webhook, or Telegram flow.
