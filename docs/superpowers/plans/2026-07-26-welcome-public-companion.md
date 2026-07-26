# TOAN AAS `/welcome` Public Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/welcome` a polished, responsive and reviewed vi/en/zh public
companion for the TOAN AAS Web App without changing Bot, bridge, payment,
provider, session or customer-workflow authority.

**Architecture:** `app.py` accepts a narrow, exact public `lang` display value
only for `/welcome` and passes it into the existing inert shell bootstrap.
`portal-i18n.js` owns the reviewed copy; `portal.js` renders the landing from
that catalog and real internal routes; `portal-theme.css` owns the page’s
responsive layout using existing semantic tokens.  No client persistence,
fetch, provider call or account data is added.

**Tech Stack:** FastAPI, server-rendered shell, vanilla JavaScript/CSS, local
Portal i18n bundle, pytest, local Playwright smoke checks.

**Accepted design:**

- `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-b7eb9379-ddf6-4614-90c8-34ad2e14248b.png`
- `design-system/toan-aas-web-app/MASTER.md`
- `design-system/toan-aas-web-app/pages/welcome.md`

**Scope note:** production `toanaas.vn` is served by the Bot repository and
is deliberately out of scope. This plan changes only `app.toanaas.vn/welcome`.

---

## File structure

- `app.py` — exact public `/welcome?lang=` allowlist; no profile/session/Bot
  locale authority is introduced.
- `static/portal/portal-i18n.js` — reviewed fixed landing copy in `vi`, `en`
  and `zh` catalogues.
- `static/portal/portal.js` — safe, data-driven `renderLanding` markup,
  locale links, real CTA routes and existing SVG icons.
- `static/portal/portal-theme.css` — final responsive landing rules and
  semantic token-only styling.
- `tests/test_welcome_public_companion_contracts.py` — route, locale, renderer
  and safety contracts.
- `tests/test_portal_i18n_bundle_contracts.py` — extends the browser bundle
  keyset contract for landing copy.
- `docs/superpowers/specs/2026-07-26-welcome-public-companion-design.md` —
  approved boundary and design.

### Task 1: Fence the public display locale with a failing route test

**Files:**

- Create: `tests/test_welcome_public_companion_contracts.py`
- Modify: `app.py:2470-2600`

- [ ] **Step 1: Write the failing test**

```python
def test_welcome_allows_only_exact_reviewed_public_display_locales(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        for locale, html_lang in (("vi", "vi"), ("en", "en"), ("zh", "zh-CN")):
            response = client.get(f"/welcome?lang={locale}")
            assert response.status_code == 200
            assert f'<html lang="{html_lang}" dir="ltr" data-portal-locale="{locale}">' in response.text
            assert f'"interfaceLocale": "{locale}"' in response.text

        invalid = client.get("/welcome?lang=zh-TW")
        legacy = client.get("/welcome?locale=zh")
        assert 'data-portal-locale="vi"' in invalid.text
        assert 'data-portal-locale="vi"' in legacy.text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest -q tests/test_welcome_public_companion_contracts.py::test_welcome_allows_only_exact_reviewed_public_display_locales`

Expected: `en` and `zh` currently render the default Vietnamese shell.

- [ ] **Step 3: Add the narrow `/welcome` locale resolver**

```python
PUBLIC_WELCOME_INTERFACE_LOCALES = frozenset({"vi", "en", "zh"})

def _public_welcome_interface_locale(request: Request) -> str:
    candidate = request.query_params.get("lang")
    return candidate if candidate in PUBLIC_WELCOME_INTERFACE_LOCALES else "vi"
```

Inside `page`, directly before the final `render_portal` call, add only:

```python
if normalized == "/welcome":
    portal_interface_locale = _public_welcome_interface_locale(request)
```

Do not read a signed profile, a cookie, a header, Bot state or a `locale`
query parameter. Do not widen the helper to `/login`, `/register` or other
public/signed routes.

- [ ] **Step 4: Run the route test to verify it passes**

Run: `python -m pytest -q tests/test_welcome_public_companion_contracts.py::test_welcome_allows_only_exact_reviewed_public_display_locales`

Expected: `1 passed`.

### Task 2: Add reviewed landing copy to all three catalogues

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Modify: `tests/test_portal_i18n_bundle_contracts.py`
- Test: `tests/test_portal_i18n_bundle_contracts.py`

- [ ] **Step 1: Add a failing catalog contract**

Add this required key list to the existing Node bundle keyset assertion:

```javascript
const landingKeys = [
  "landing.nav.features", "landing.nav.workflow", "landing.nav.trust",
  "landing.nav.language", "landing.cta.start", "landing.cta.signIn",
  "landing.hero.title", "landing.hero.body", "landing.hero.explore",
  "landing.proof.webOwned", "landing.proof.noFakeOutput",
  "landing.proof.companionOptional", "landing.preview.title",
  "landing.workflow.title", "landing.trust.title", "landing.footer.legal"
];
for (const locale of expected) {
  for (const key of landingKeys) {
    if (!api.t(key, locale)) throw new Error(`Missing ${key} translation for ${locale}`);
  }
}
```

- [ ] **Step 2: Run the bundle test to verify it fails**

Run: `python -m pytest -q tests/test_portal_i18n_bundle_contracts.py`

Expected: the Node catalog check reports missing `landing.*` keys.

- [ ] **Step 3: Add equivalent Vietnamese, English and Simplified Chinese copy**

Add the same `landing.*` keys to each `MESSAGES.vi`, `MESSAGES.en` and
`MESSAGES.zh` object.  Use these reviewed hero messages:

```text
vi: Biến ý tưởng thành quy trình nội dung rõ ràng.
en: Turn ideas into a clear content workflow.
zh: 将创意转化为清晰的内容工作流。
```

The matching body must say that projects and briefs are Web-owned and an
engine/companion connects only when its capability is ready.  Preserve the
real boundaries in every language: no browser provider calls, no fabricated
output and private delivery after ownership checks.

- [ ] **Step 4: Run the bundle test to verify it passes**

Run: `python -m pytest -q tests/test_portal_i18n_bundle_contracts.py`

Expected: all catalogues have the same keyset and landing copy is non-empty in
all three reviewed locales.

### Task 3: Replace the landing renderer with real-route, locale-safe markup

**Files:**

- Modify: `static/portal/portal.js:24371-24379`
- Modify: `tests/test_welcome_public_companion_contracts.py`
- Test: `tests/test_welcome_public_companion_contracts.py`

- [ ] **Step 1: Add renderer safety and structure tests**

```python
def test_public_landing_uses_i18n_real_routes_and_portal_svg_icons() -> None:
    landing = _between(PORTAL, "function renderLanding(page, context)", "function renderVideoFinalization")
    for token in (
        'uiText("landing.hero.title"', 'uiText("landing.cta.start"',
        'portalIcon(ICONS.arrowRight)', 'portalIcon(ICONS.check)',
        'href="/register"', 'href="/login"', 'href="/legal"', 'href="/privacy"',
        'href="/welcome?lang=vi"', 'href="/welcome?lang=en"', 'href="/welcome?lang=zh"',
    ):
        assert token in landing
    for forbidden in ("fetch(", "api(", "payment", "provider", "wallet", "✦", "↗", "⌁"):
        assert forbidden not in landing
```

- [ ] **Step 2: Run the renderer test to verify it fails**

Run: `python -m pytest -q tests/test_welcome_public_companion_contracts.py::test_public_landing_uses_i18n_real_routes_and_portal_svg_icons`

Expected: the current renderer contains hard-coded Vietnamese and glyph-based
decorations instead of reviewed catalog and SVG values.

- [ ] **Step 3: Implement small landing helpers and semantic sections**

Add a local helper inside `renderLanding` that uses the existing catalog and
safe text boundary:

```javascript
const text = (key, fallback, params) => safeText(uiText(`landing.${key}`, fallback, params));
const locale = portalI18n() && typeof portalI18n().getLocale === "function"
  ? portalI18n().getLocale() : "vi";
const languageHref = (code) => `/welcome?lang=${encodeURIComponent(code)}`;
```

Render header, hero, studio grid, four-step workflow, trust section, final
CTA and footer from fixed local arrays.  Each card must use `portalIcon` with
an existing `ICONS` value and only an established internal route.  Keep the
anonymous/signed primary action decision:

```javascript
const primaryHref = signedIn ? "/dashboard" : "/register";
const secondaryHref = signedIn ? "/account" : "/login";
```

The locale switcher is a labelled `<nav>` of three anchors.  Set
`aria-current="true"` only on the active locale.  Do not call `setLocale`,
write browser storage or attach an event handler; navigation supplies the
server-validated display locale.

- [ ] **Step 4: Run the renderer test to verify it passes**

Run: `python -m pytest -q tests/test_welcome_public_companion_contracts.py`

Expected: all landing route, locale and no-side-effect contracts pass.

### Task 4: Apply the balanced public layout with final theme tokens

**Files:**

- Modify: `static/portal/portal-theme.css`
- Modify: `tests/test_welcome_public_companion_contracts.py`
- Test: `tests/test_welcome_public_companion_contracts.py`

- [ ] **Step 1: Write a failing layout contract**

```python
def test_landing_has_balanced_responsive_layout_and_accessible_controls() -> None:
    for selector in (
        ".portal-landing-locale-nav", ".portal-landing-hero",
        ".portal-landing-preview", ".portal-landing-studios",
        ".portal-landing-workflow", ".portal-landing-trust-grid",
        "@media (max-width: 920px)", "@media (max-width: 600px)",
    ):
        assert selector in THEME
    assert "min-height: 44px;" in _rule(THEME, ".portal-landing-locale-link")
    assert "var(--portal-light-canvas)" in THEME
    assert not _hex_literals_outside_root(THEME)
```

- [ ] **Step 2: Run the layout test to verify it fails**

Run: `python -m pytest -q tests/test_welcome_public_companion_contracts.py::test_landing_has_balanced_responsive_layout_and_accessible_controls`

Expected: the current landing lacks the locale control and the updated
semantic section layout.

- [ ] **Step 3: Add final scoped CSS**

Use only `--portal-*` tokens already declared in `:root`.  Keep the hero grid
balanced on desktop and single-column below 920px:

```css
.portal-landing-hero {
  grid-template-columns: minmax(0, 1fr) minmax(380px, .92fr);
  align-items: center;
  gap: clamp(40px, 7vw, 88px);
}
.portal-landing-locale-link {
  min-height: 44px;
  color: var(--portal-light-action);
}
@media (max-width: 920px) {
  .portal-landing-hero { grid-template-columns: minmax(0, 1fr); }
}
```

Keep light-surface focus rules and safe-area gutters from the UI foundation.
Do not add raw hex literals outside `:root`, decorative gradients, animated
background blobs or an app sidebar to the public route.

- [ ] **Step 4: Run the layout test to verify it passes**

Run: `python -m pytest -q tests/test_welcome_public_companion_contracts.py`

Expected: all responsive, token and touch-target contracts pass.

### Task 5: Verify rendered public flows and commit the slice

**Files:**

- Modify: `docs/superpowers/plans/2026-07-26-welcome-public-companion.md`
- Test: focused test suite and local browser smoke flow

- [ ] **Step 1: Run focused contracts and syntax checks**

Run:

```powershell
python -m pytest -q `
  tests/test_welcome_public_companion_contracts.py `
  tests/test_portal_i18n_bundle_contracts.py `
  tests/test_teal_cyan_ui_foundation_contracts.py `
  tests/test_auth_entrypoint_layout_contracts.py `
  tests/test_portal_service_worker_lifecycle.py `
  tests/test_pwa_scope_offline_contracts.py
python -m compileall -q .
git diff --check
```

Expected: all selected tests pass, no syntax or whitespace error.

- [ ] **Step 2: Verify desktop and mobile public flows locally**

Run the local app with a test-only `WEB_SESSION_SECRET`, then capture:

```text
/welcome?lang=vi  at 1440×960 and 390×844
/welcome?lang=en  at 1440×960
/welcome?lang=zh  at 390×844
```

For each page prove: HTTP 200, meaningful `<main>`, no framework overlay, no
relevant console error, no horizontal overflow and a visible real CTA. Click
only the password-visibility control on `/login` as an interaction smoke; do
not submit login, provider, payment, upload or job forms.

- [ ] **Step 3: Compare the implementation with the accepted design**

Inspect the accepted landing concept and each final desktop/mobile screenshot
side by side. Record at least five points: teal/cyan palette, editorial hero
balance, navigation/CTA hierarchy, preview treatment, section rhythm,
typography, touch targets and responsive collapse. Fix material visual drift
before commit.

- [ ] **Step 4: Commit the focused slice**

```powershell
git add app.py static/portal/portal-i18n.js static/portal/portal.js `
  static/portal/portal-theme.css tests/test_welcome_public_companion_contracts.py `
  tests/test_portal_i18n_bundle_contracts.py `
  design-system/toan-aas-web-app/pages/welcome.md `
  docs/superpowers/specs/2026-07-26-welcome-public-companion-design.md `
  docs/superpowers/plans/2026-07-26-welcome-public-companion.md
git commit -m "Refine public welcome companion"
```

## Plan self-review

- **Coverage:** the plan separates locale input, reviewed copy, renderer,
  layout and visual QA; it keeps Bot/live-root landing, providers, payments
  and signed workflow authorities outside the change.
- **No placeholders:** every change names the owning file, test intent and
  expected command/result.
- **Sequencing:** the public landing is one mergeable PR.  Customer dashboard,
  feature workspaces and Admin ERP remain the following independent slices.
