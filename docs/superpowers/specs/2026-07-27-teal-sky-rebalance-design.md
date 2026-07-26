# TOAN AAS Workspace — Teal–Sky Rebalance Design

## Decision

`app.toanaas.vn` remains the signed AI Workspace, not a marketing surface.
It adopts a light teal–sky application canvas: white working surfaces, deep
teal navigation chrome, a dark teal primary action and sky-blue contextual
states.  This replaces the visually conflicting legacy dark access layer and
the unbalanced desktop login split shown in the reported screenshot.

The visual source references are the generated concept screens:

- Landing concept: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-6ca14dbd-6b32-4e59-8d8c-979c4ceeb44d.png`
- Workspace/access concept: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-c13a9979-52a2-4897-b48b-7ab6855e63f8.png`

They specify visual hierarchy only.  No concept metric, job, balance,
customer, provider or completion claim becomes product data.

## Shared visual contract

| Role | Token/value | Use |
| --- | --- | --- |
| App canvas | `#F4FBFC` | Signed main canvas and access background |
| Surface | `#FFFFFF` | Cards, forms, tables and dialogs |
| Ink | `#083344` | Primary text and deep teal rail |
| Primary action | `#0F766E` | High-contrast teal actions with white text |
| Brand/support | `#14B8A6` | Selected accents and non-text decoration |
| Context/focus | `#0284C7` / `#38BDF8` | Links, focus and informational states |
| Divider | `#D7ECEF` | Flat structural separation |
| Muted text | `#486B75` | Supporting copy only; never below AA contrast |

The final stylesheet owns semantic values.  New page rules must use tokens;
raw hex values are limited to that token declaration.  Motion is
opacity/transform only (150–220ms) and disabled by `prefers-reduced-motion`.
Every interactive control has an obvious focus state, semantic label and a
minimum 44px touch target on mobile.

## Access flow

The email/password route stays server-owned and does not change session,
CSRF, password, OAuth or Telegram-link behavior.

The access page becomes a single balanced reading column:

1. Compact brand, locale control and introduction link share one header row.
2. A concise title and explanation sit above—not beside—the form.
3. Login/register switch, visible labels, helper copy, password visibility,
   recovery and one primary submit action stay within a 480px form surface.
4. Telegram/OAuth remains optional progressive disclosure; it must not imply
   a linked identity or render unavailable providers as working.
5. At 920px and below, the same sequence persists without a layout jump;
   at 600px all controls remain 44px and no line is clipped or horizontal.

This directly removes the oversized empty left column, vertical divider and
right-edge card pressure from the previous access page.

## Signed workspace and ERP

The workspace uses a dark teal rail only for orientation; its header and main
working surface use the light canvas.  Tables, cards, filters, empty states,
forms and status rows align to a consistent container and border rhythm.
The information architecture, owner checks, server-issued route manifest,
canonical data boundary and guarded feature language remain unchanged.

The desktop shell keeps a sidebar.  The phone shell preserves the existing
five labelled top-level destinations; it does not introduce a second
competing navigation pattern.  Admin screens inherit the same operational
grammar, while danger/guarded states remain textual as well as coloured.

## Locale and content rule

Vietnamese is the source copy.  Fixed interface labels introduced or changed
by this work must have reviewed `vi`, `en` and `zh` equivalents in the
existing i18n catalogue.  Customer/project/provider values are never
browser-translated.  Vietnamese wording should say what happens next in
ordinary language, not expose Bot/internal implementation terms.

## Safety and validation

This is presentation work only.  It must not alter wallet/Xu authority,
PayOS, webhooks, providers, CSRF/session rules, private delivery checks,
role enforcement or private PWA caching.  Verify at 375px, 768px, 1024px and
desktop; check contrast, keyboard focus, no horizontal overflow, and the
real anonymous login path without submitting a credential.

## Implementation ledger — 2026-07-27

- `portal-theme.css` is now the final semantic authority for the signed app:
  `--portal-app-canvas` and `--portal-surface-light` provide the light working
  plane, `--portal-rail` is limited to navigation, `--portal-action` provides
  the dark-teal primary action with white on-action text, and mint/sky remain
  distinct brand and context roles.
- The obsolete late access block was removed from `portal.css`. The final
  theme now owns the balanced access frame: one centred 480px column ordered
  as header, introduction, then form; it has no dark canvas, vertical divider
  or 11ch heading cap. Mobile controls retain the 44px minimum.
- This change did not alter route rendering, DOM action bindings, auth/session
  handling, CSRF, provider availability, PayOS, wallet/Xu, webhook, role, PWA
  or Bot behavior. No fixed visible copy changed, so the i18n bundle remains
  unchanged.
- Spec review found two light-surface cascade regressions before merge: the
  access password-visibility control retained pale-on-dark legacy text, and
  Music/SFX Direction preset cards retained pale text after their surfaces
  became white. Final semantic overrides now give those controls dark-teal
  text, muted supporting copy, visible focus/selection treatment and the same
  light working-surface grammar; their form, provider and job boundaries are
  unchanged.
- Browser QA then exposed the register-route profile-default notice still
  using pale-on-dark legacy copy. The access theme now gives that informational
  notice a sky contextual surface, dark heading, 12px+ supporting text and
  unchanged server-owned registration behavior.
- Static validation evidence:
  `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest -q --noconftest
  tests/test_teal_cyan_ui_foundation_contracts.py
  tests/test_login_app_ux_contracts.py
  tests/test_dashboard_workspace_command_center_contracts.py
  tests/test_portal_i18n_bundle_contracts.py
  tests/test_portal_safety_contracts.py` completed with **125 passed**.
- A live visual-browser check could not run in this environment because the
  available Browser runtime reported no browser targets. The responsive layout
  invariants are covered by the static contracts; verify `/login` and
  `/register` at 375px, 768px, 1024px and desktop when a browser target is
  available, without submitting credentials.
