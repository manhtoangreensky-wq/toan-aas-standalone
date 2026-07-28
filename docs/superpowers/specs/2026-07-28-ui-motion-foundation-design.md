# TOAN AAS Web/App UI and Motion Foundation — Design Specification

**Status:** approved implementation direction

**Approval basis:** The product owner has repeatedly approved autonomous UI/UX
work with a clean teal–sky technology palette; a professional, easy-to-use
customer application; a separate internal ERP; Vietnamese-first language
support; and motion that improves page, navigation and state continuity. The
three concept references were generated only to make those already-approved
requirements concrete. They are not product assets, do not define real data,
and must not be copied into the application.

**Source baseline:** `origin/main` at
`2f162590f0e8e72978042bded7d34916f3c00a54`.

## 1. Intent and scope

TOAN AAS is an application-first product. `app.toanaas.vn` is a signed
customer workspace and `app.toanaas.vn/admin` is an internal operational ERP;
neither is a marketing landing page. `/welcome` is the public companion inside
this repository. The separate WordPress marketing-site task remains out of
scope.

This design pass improves only presentation, navigation clarity, responsive
behavior, localization coverage for touched chrome, and motion. It does not
alter Bot ownership, Core Bridge behavior, payment/PayOS handling, wallets,
provider calls, jobs, feature readiness, role enforcement, CSRF, file access,
or PWA private-cache boundaries.

### Non-goals

- Do not edit `bot.py`, the Telegram Bot, Telegram Mini App, webhook, ledger,
  provider adapters, or the LocalVideoStudio26-owned areas.
- Do not replace real server data with demo data, and do not show metrics,
  queues, readiness or customer records when a server contract does not return
  them.
- Do not rebuild the 7,673-line legacy component catalogue in one change.
- Do not add GSAP, Motion.so, a paid animation service, or another front-end
  framework.

## 2. Current-state audit

The server renders a deliberately thin portal shell via
`copyfast_pages.py` and `templates/portal_shell.html`. `portal.js` mounts the
shared sidebar, header, main region, mobile dock, command palette and toast;
`integration.js` hydrates private data. The current teal–sky semantic palette
is a correct base, but it is an override over multiple legacy CSS layers.

The critical product issue is information architecture: customer and Admin
routes share one visual shell, the customer navigation tree is followed by ERP
groups, and the customer mobile dock is shown on `/admin/*`. This is visually
confusing even though server-side authorization is already correctly enforced.

## 3. Selected direction

Three possible directions were assessed:

1. **Customer-first application system (selected).** Consolidate shared tokens
   and motion first, then deliver customer and ERP shells as distinct
   follow-up PRs. This gives a coherent product without changing business
   contracts and keeps each merge reviewable.
2. **ERP-first visual overhaul.** It would improve internal operations sooner,
   but would leave the public/customer app inconsistent and would not address
   the shared shell problem at its source.
3. **Public landing-first redesign.** It would improve promotion but would not
   solve the working product's navigation or mobile experience. It is deferred
   until the application shells are stable.

The implementation order is therefore: shared foundation, Customer Workspace,
Internal ERP, then `/welcome` alignment and broad visual QA.

## 4. Shared visual system

### Color and surfaces

`static/portal/portal-theme.css` remains the only shared visual token owner.
It will retain the signed product's light teal–sky surface family:

| Semantic purpose | Token/value |
| --- | --- |
| App canvas | `--portal-app-canvas: #f3fbfc` |
| Working surface | `--portal-surface-light: #ffffff` |
| Deep navigation rail | `--portal-rail: #063b47` |
| Primary action | `--portal-action: #0f766e` |
| Context and focus | `--portal-context: #0369a1` |
| Ink | `--portal-ink: #073a45` |
| Divider | `--portal-border: #d5e9ed` |

The foundation adds semantic spacing, elevation, z-index and motion tokens;
new components must use those tokens instead of raw hex values. Dark rails are
reserved for navigation. Operational, account, wallet and payment surfaces
stay light and high-trust. Status colors always pair with text and an icon or
label; color alone never carries meaning.

### Type and layout

The existing application scale stays compact and readable: 14–16px body text,
12px only for non-decision metadata, and 20–32px page titles. New content uses
the existing system font stack until a later dedicated font-loading change can
be validated across VI/EN/ZH; the intended family priority is `Be Vietnam Pro`,
then `Inter`, then a CJK-capable system fallback. Tabular numbers use tabular
figures. Layout uses an 8px rhythm, 40px desktop controls and 44px mobile
controls. Columns, labels and table cells must align to their shared grid.

### Components

The shared primitives are a small set: primary/quiet/destructive buttons,
fields, table rows, status labels, drawers, dialogs, toasts, empty states and
loading states. They keep visible labels, focus rings, keyboard behavior and
stable dimensions. The foundation must favor explicit component selectors over
brittle suffix selectors such as `[class$="-card"]`.

## 5. Product information architecture

### Customer Workspace

The customer shell is calm, guided and task-oriented:

- Desktop uses a persistent deep-teal rail, concise primary groups and a
  server-authorized command palette. Long feature catalogues live in grouped
  routes/search, not a permanently expanded navigation wall.
- The top bar holds route context, command search, language and account
  controls. It never becomes a second sidebar.
- Mobile has a fixed five-item dock: Workspace, Studio, Jobs, Assets and
  Account. The full customer tree is accessible from the focus-managed drawer.
- A page has one obvious primary action; guarded features show their true
  status and a safe next step rather than a fake result.

### Internal ERP

The Admin shell is a separate internal product, not a customer theme with more
links:

- `/admin/*` receives an explicit admin surface mode and a compact ERP rail.
  Navigation groups are Overview, Operations, Customers, Finance and System;
  each is shown only from server-authorized Admin navigation data.
- Desktop favors dense tables, filters, queues, audit/readiness states and
  right-side operational context. It does not use promotional cards or fake
  KPI tiles.
- Mobile uses a distinct five-item ERP dock: Overview, Operations, Customers,
  Finance and System. Its drawer exposes the full authorized ERP tree.
- Role and route checks remain server-owned. Browser state can style a granted
  screen but cannot discover, manufacture or authorize an admin route.

### Public companion

`/welcome` uses the same teal–sky identity with more breathing room and one
clear route into the signed application. It will not inherit dense customer or
ERP chrome. WordPress/toanaas.vn work is deliberately deferred to its own
task.

## 6. Motion system

The shared motion kit is applied as a progressive enhancement, locally copied
into the portal's token and utility conventions rather than imported from its
external workspace.

| State | Treatment | Constraint |
| --- | --- | --- |
| Route/page entry | opacity + 8–10px Y transition, 220ms emphasis easing | restore focus after mount; no hidden content fallback |
| Sidebar/drawer | transform-only slide, 220ms standard easing | retain current dialog/focus trap behavior |
| Modal/toast/success/error | small opacity/scale pop, 140–220ms | accessible text remains the source of meaning |
| Lists and status changes | subtle one-time fade/outline of changed region | never reorder, move or fabricate data |
| Loading | bounded pulse/spinner with text and `aria-live` | never block a safe primary action unnecessarily |
| Hover/focus | 1–2px transform or color/shadow transition | keyboard focus stays visible and is never hover-only |

`portal-motion.js` will be a focused presentation utility. It may use the View
Transition API when it exists and reduced motion is not requested; all other
browsers receive the same semantic page update without an animation. It will
not own routing, data fetching, authorization or feature actions.

`prefers-reduced-motion: reduce` disables or reduces every non-essential
transition. Core flows must work identically with animations off.

## 7. Accessibility, localization and performance

- Preserve the skip link, native headings, keyboard drawer/dialog behavior,
  visible focus rings and 44px mobile targets.
- VI is the primary copy. New shared chrome must be added to the existing
  VI/EN/ZH dictionary rather than hard-coded in a renderer. Existing untouched
  feature copy is not silently translated in the foundation PR.
- No private content enters the service-worker cache. Animation state is never
  persisted as account/job state.
- Do not introduce an animation library. The new utility must be small,
  transform/opacity-only and maintain a no-JavaScript legible shell.
- Baseline bundle loading is already large; the foundation must not make it
  larger materially. Bundle splitting is a separately measured follow-up.

## 8. Delivery sequence and test strategy

1. **PR 1 — shared teal–sky + motion foundation.** Add canonical tokens,
   `portal-motion.js`, route/surface lifecycle hooks and static contracts;
   reconcile the conflicting app-first design documentation.
2. **PR 2 — Customer shell and mobile IA.** Narrow the customer rail and dock
   without changing the registry, API or access contract.
3. **PR 3 — ERP shell and mobile IA.** Add server-grant-respecting ERP visual
   mode, rail and dock, preserving canonical/local/support authority split.
4. **PR 4 — public companion, locale sweep and visual polish.** Align
   `/welcome`, localize touched chrome and conduct desktop/mobile/reduced
   motion fidelity QA.

Each PR gets targeted static/behavioral tests, `git diff --check`, and
browser verification at 375, 768, 1024 and 1440px. The initial baseline tests
for existing shared UI/navigation/i18n contracts passed: **43 passed**.

## 9. Concept ledger

The following preview-only concept files are retained outside the repository:

- Customer desktop: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-2f0ee084-832d-451a-b3fc-ac67206f9cbb.png`
- ERP desktop: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-bfd4c8c3-d924-46be-a783-14f9162959a1.png`
- Customer mobile: `C:\Users\toann\.codex\generated_images\019f4b14-cdaa-7d90-8869-cf654fcab17a\exec-7b667941-9a84-4a79-95c7-2c3a52aa6a0b.png`

Only their palette, density, hierarchy and responsive intent are accepted.
Invented names, numbers, provider labels, queues and metrics in concept images
are explicitly prohibited from implementation.
