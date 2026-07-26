# Billing Navigation UX Design

## Goal

Make the signed Billing workspace feel like one coherent application area by
giving `/wallet`, `/wallet/topup`, `/packages`, and `/pricing` a shared,
deep-linkable navigation layer.

## Chosen approach

Use a compact horizontal Billing navigation strip directly below the existing
page hero. It has four explicit destinations: **Ví Xu**, **Nạp Xu**, **Gói**,
and **Bảng giá**. The active route is exposed with `aria-current="page"`.

This is preferred over a new billing landing page or another sidebar because
the app shell already owns global navigation and the customer needs quick,
predictable movement inside one small Billing cluster.

## Interaction and responsive behavior

- Every link is a normal anchor, so browser Back/Forward and direct links keep
  working without client state.
- Desktop uses one aligned, compact row.
- At narrow widths the strip scrolls horizontally inside itself, snaps each
  touch target into view, and never makes the page itself overflow.
- Links have a minimum 44px height, visible hover/focus states, and no
  decorative motion beyond the existing reduced-motion-aware color transition.

## Authority and safety boundary

The strip only navigates between existing routes. It must not add a payment
form, provider call, webhook, payment-order creation, wallet write, manual
proof upload, QR, TXID, price, package, or ledger calculation.

`/wallet` and `/wallet/topup` remain projections/handoffs governed by the
signed Core Bridge and canonical Bot. `/packages` and `/pricing` remain
read-only canonical catalogs.

## Verification

- Static contract confirms the shared nav is rendered on all four routes,
  marks the exact active path, and contains only anchors.
- CSS contract confirms 44px controls, focus styling, intentional internal
  scroll behavior, mobile handling, and reduced-motion coverage.
- Existing billing canonical journey contracts remain green.
