# TOAN AAS Unified Teal–Sky Product Redesign

## Decision

Use one calm teal–sky product system across `toanaas.vn` and
`app.toanaas.vn`. They share colour roles, typography, alignment, focus
treatment and Vietnamese-first language, but not information architecture.

- The public landing explains what TOAN AAS is, when to use the Workspace, and
  where a visitor should start.
- The signed Workspace is a task-oriented product surface for projects,
  assets, jobs, approvals and account operations.
- The Admin ERP uses the Workspace shell and denser operational tables without
  exposing authority or data to an unauthenticated visitor.

The visual reference set for this implementation is the 2026-07-27 design
concept pass: an editorial desktop landing, balanced desktop access page,
desktop Workspace command centre and mobile Workspace empty state. The
references guide geometry and hierarchy; shipped UI remains semantic HTML/CSS/JS
and retains real route, session and provider states.

## Brand system

| Role | Token | Value | Purpose |
| --- | --- | --- | --- |
| Product ink | `--portal-ink` | `#073a45` | headings and high-trust text |
| Desktop rail | `--portal-rail` | `#063b47` | persistent signed-navigation anchor |
| Primary action | `--portal-action` | `#0f766e` | one main task action per view |
| Brand support | `--portal-brand` | `#0d9488` | mark and selected supporting controls |
| Context/focus | `--portal-context` | `#0369a1` | current location and keyboard focus |
| App canvas | `--portal-app-canvas` | `#f3fbfc` | calm, cool light background |
| Surface | `--portal-surface-light` | `#ffffff` | inputs, forms, cards and tables |
| Soft surface | `--portal-surface-soft` | `#e6f8f7` | low-emphasis grouping |
| Supporting copy | `--portal-muted` | `#456b77` | body/support copy on light surfaces |

The primary action remains dark enough for white text. Sky is not used as small
body text on white. No purple/pink, warm cream, fake metrics, fake outputs,
misleading provider availability or decorative gradients are introduced.

## App geometry and language

### Access routes

At desktop width, `/login` and `/register` use a shared 1180px access rail:
the compact header spans the rail; the left column introduces the product in one
heading and three factual trust points; the right column owns the email-first
form. The two columns begin on one horizontal line. At tablet and phone widths
the content intentionally collapses into one column, hides the non-essential
context panel and keeps controls at least 44px tall.

Signed-session, CSRF, MFA, Telegram-link and provider-enable conditions remain
unchanged. The form continues to show only configured provider methods.

### Workspace and Admin

The deep desktop rail is reserved for signed navigation. Header controls,
breadcrumbs, content headings and tables align to one content rail at normal
and ultrawide desktop widths. Light surfaces own dark title/value text and
muted secondary text through shared primitives, preventing legacy dark-theme
child colours leaking into Dashboard or Admin cards.

Mobile keeps bottom-dock clearance and label-first navigation. PWA browser
chrome and offline fallback use the same teal–sky system.

### Copy and locales

Vietnamese is concise and direct: `Không gian làm việc`, `Việc cần làm tiếp
theo`, `Tạo mới`, `Cần xác nhận`, `Chưa có dữ liệu` and `Trợ giúp đăng
nhập`. English and Simplified Chinese translate only fixed chrome with the same
intent. User records, job payloads, asset names and server values remain
untouched.

## Landing relationship

The landing is a public companion, not a reproduction of the signed Workspace.
It shares deep teal, cyan and sky hierarchy plus Vietnamese typography, but uses
an editorial 12-column public grid: a direct product statement, genuine entry
actions, a code-native Workspace preview, a four-stage workflow, a clear
Website-versus-Workspace explanation and trust information.

The landing is a separate PR in the public landing repository. It does not
change `bot.py`, Telegram handlers, PayOS, Xu, wallet, provider execution,
webhooks or production environment settings.

## Acceptance criteria

- No horizontal overflow at 375, 768, 1024, 1440 and 2560px.
- Header and main rails share geometry on signed desktop surfaces.
- Normal text on a light card has at least 4.5:1 contrast; focus remains
  visible at at least 3:1 contrast.
- Login/register preserve existing `data-portal-action`, form fields, routes,
  provider guards and server-side session boundaries.
- Dashboard/Admin light card titles and support copy use semantic light-surface
  typography primitives, not legacy pale text declarations.
- VI/EN/ZH fixed access copy has equal key coverage.
- Landing and App look related while presenting distinct roles.

## Visual fidelity ledger — 2026-07-27

| Checkpoint | Render evidence | Result |
| --- | --- | --- |
| Desktop access balance | Local /login?lang=vi at 1440px uses a 1180px rail, a 567px contextual column and a 480px real email form column. | Corrected the former narrow vertical stack; the heading aligns with the form's actual content hierarchy rather than a decorative card top edge. |
| Mobile access | Local /login?lang=vi at 390px reports scrollWidth equal to clientWidth; the optional context panel is hidden and the actual form remains one column. | Pass. There is no horizontal overflow or duplicated context. |
| Final CSS parsing | Browser CSSOM originally stopped before the access rules because the header max/calc expression was missing one closing parenthesis. | Corrected with a red/green contract; the fresh local sheet now parses 368 rules and applies the desktop grid. |
| Light signed surfaces | The final semantic layer maps shared Dashboard/Admin card title and support primitives to --portal-ink / --portal-muted. | Pass by source contract; no route or authority renderer changed. |
| Public companion | Local /welcome?lang=vi at 1440px shares the cool teal–sky canvas, deep teal action and white workflow preview while retaining public-only navigation. | Pass. It complements the signed app rather than duplicating its rail. |
| PWA chrome | Shell metadata, manifest and offline fallback use #063b47, the same deep-teal family as the signed rail. | Pass. Cache policy and private/PWA security rules were not changed. |
