# Wallet & Billing Light Surface Design

## Status and approval basis

This design applies the already-approved TOAN AAS app-first direction: a
professional light teal/cyan workspace, white working surfaces, dark-teal
actions, visible sky focus states, compact operational spacing, and
reduced-motion support. It is deliberately a presentation-only slice. It does
not alter the canonical Bot/Core Bridge wallet, PayOS, package, manual-payment,
provider, job, or delivery authority.

## Purpose

The customer billing area must make the current truth understandable at first
glance. A customer should be able to distinguish a verified Xu balance from a
loading, guarded, or failed read; choose only a canonical top-up path; see that
manual reconciliation remains an external/Bot handoff; and move predictably
between Wallet, Top up, Packages, and Pricing.

## Scope

The visual layer covers the existing signed routes:

| Route | Customer purpose | UI outcome |
| --- | --- | --- |
| `/wallet` | Read canonical Xu and ledger history | Clear balance/status rail, readable history and honest empty/guarded states. |
| `/wallet/topup` | Start an already-authorized payment path | Distinct, stationary entry cards; explicit PayOS and manual-handoff statuses. |
| `/packages` | Read canonical package catalog | Clean catalog surface with no invented benefit, price, or availability. |
| `/pricing` | Read canonical pricing catalog | Same catalog hierarchy, clear source/read status and no inferred discount. |

The layer is rooted only at
`.portal-page:is(.portal-wallet-page, .portal-billing-catalog-page)` and is
appended after all existing theme layers. It may override legacy dark/translucent
children that belong to these routes, but it must not modify `portal.js`,
`integration.js`, APIs, route ownership, form attributes, payment callbacks, or
server data.

## Visual and interaction design

1. Use `--portal-*` semantic tokens only. Working panels are white/light
   surfaces; muted copy and secondary fields keep readable contrast; dark teal
   remains the action color; sky is used for keyboard focus/context.
2. Give the canonical read state one prominent but compact status panel. Loading
   remains visibly loading, guarded and failed states retain their textual
   explanation, and none may look like `0 Xu` or a completed payment.
3. Present payment entry cards as a stable two-column desktop layout that stacks
   on small screens. Hover/focus feedback changes border/background only;
   layout-shifting transforms and elevated shadows are removed.
4. Keep the horizontal route strip readable on narrow viewports. At 700px,
   cards and the billing journey become one column; all actionable controls are
   at least 44px high; no table, card, or route strip can exceed the viewport.
5. Focus-visible treatment is explicit and keyboard-safe. Reduced motion
   removes cosmetic transitions/transforms from cards, route links and primary
   billing controls without hiding content.

## Authority and safety boundaries

- The Web only renders canonical wallet/history/catalog/payment data already
  returned by its established boundary. It never calculates Xu, creates a
  second ledger/order, finalizes a PayOS redirect, or exposes a secret.
- Manual payment is a truthful handoff only. This slice accepts no Telegram
  ID, bill, TXID, image, amount, method, pending-deposit record, approval or
  rejection action.
- Package and pricing data remain read-only canonical projections. Missing or
  invalid source data stays guarded; the UI must not produce a price, discount,
  entitlement, checkout result, or success claim.
- Existing CSRF, signed-session, idempotency, payment result, support and
  ownership checks remain unmodified.

## Acceptance checks

- A CSS contract isolates the final marker/layer, verifies the root scope,
  token-only values, focus/checked/disabled/guarded styling, mobile layout, and
  reduced-motion behavior.
- Existing billing contracts continue to prove canonical read-state handling,
  no zero coercion, safe payment entrypoints, and manual-payment boundaries.
- Targeted test execution covers the new CSS contract and the canonical billing
  journey/navigation contracts. `git diff --check` must be clean.
- Browser/QE evidence may inspect public/login surfaces, but a browser visual
  pass is never claimed for private routes unless a signed local browser session
  can actually be attached.

## Deliberate non-goals

- No manual top-up workflow, TXID/upload support, new payment webhook, PayOS
  credential, automatic refund, wallet write, provider call, Bot callback
  replay, asset delivery, or deployment.
- No Video UI or media-runtime change.

## Local verification record

- The final surface contract was written red-first and passes after the scoped
  layer was added. It now rejects non-portal custom-property declarations and
  case-insensitive `var()` calls that do not reference the exact lowercase
  `--portal-*` token namespace, and protects semantic `ready`, `read_only`,
  `guarded`, `failed`, and `failed_no_charge` badge colors in addition to the
  wallet, card, focus, mobile and reduced-motion rules. At 700px the four
  billing routes become a stable 2×2 navigation grid instead of an overflowing
  horizontal strip.
- The focused customer billing and bridge compatibility suite passed all
  runnable tests (`122 passed, 26 deselected`). The deselected variants require
  the absent `trio` package in this local UI QA environment; this is recorded
  as an environment limitation, not a product pass for those variants.
- A local temporary-session smoke confirmed anonymous `/wallet` redirects to
  `/login?next=/wallet`. No financial, provider, Bot, file or manual-payment
  action was submitted. The in-app browser could not attach its webview, so
  this document deliberately makes no private-route visual-browser claim.
