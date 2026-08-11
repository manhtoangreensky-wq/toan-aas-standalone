# Approved sale catalog propagation

## Goal

Keep service-package metadata readable in the signed Web App while making
every customer-visible package or membership price originate exclusively from
the versioned `public_sale_catalog` that the Core Bridge marks
`owner_approved`.

## Boundary

- `/pricing` already renders the approved sale catalog and remains the
  canonical price directory.
- `/packages` and `/membership` may render package names, benefits and
  canonical status, but a numeric price is rendered only when its package
  `code` exactly matches an approved public-sale SKU.
- A package without a matching approved SKU is rendered as metadata with the
  existing guarded no-price state. `/pricing` says "Giá bán đang chờ phát
  hành"; `/packages` preserves its existing honest "Giá chưa được Core Bridge
  cấp" copy. The browser must not infer a substitute amount from `price_vnd`,
  legacy tier fields, a feature registry, or client calculation.
- The package bridge projection removes `price_vnd` before it reaches the
  browser. The existing pricing projection is not broadened or used for
  payment, wallet, PayOS, provider, or job behavior.

## Data flow

```text
Core Bridge /pricing
  -> redacted public_sale_catalog
  -> browser validates available + owner_approved + version + unique SKU
  -> approved SKU -> sale_price_xu label

Core Bridge /packages
  -> redacted package metadata (no price_vnd)
  -> browser joins by exact package code only
  -> matching approved SKU: show sale-price label
  -> no match: guarded no-price state
```

Packages and Membership hydrate `/pricing` and `/packages` together on every
direct route visit. The approved index therefore never depends on a previous
visit to the pricing page, browser storage, or a stale account projection.
Before those reads start, and again if either read fails, both catalog
projections are cleared and the route is marked `loading` then `guarded`.
The browser must never retain an earlier approved SKU price during a current
signed-session refresh or bridge failure.

## Rejections and non-goals

- Reject an unavailable, unapproved, unversioned, malformed, duplicate or
  zero-price sale catalog.
- Do not reveal provider, model, cost, USD, FX, markup, fallback, `price_vnd`,
  payment, wallet, job, or provider state through the catalog UI.
- Do not create checkout, change PayOS, mutate Xu, alter Bot/Core Bridge,
  call providers, or change ENV/deployment.

## Verification

1. A server projector contract proves `price_vnd` is absent from `/packages`.
2. Portal contracts prove package and membership price labels use only the
   validated public-sale SKU index and use the guarded copy on a missing SKU.
3. Integration contracts prove `/packages` and `/membership` fetch `/pricing`
   on direct visits, clear prior catalogs while loading, and clear them again
   in the guarded failure path before merging their page state.
4. Existing public-sale, billing and portal regression tests remain green.
5. Static migration evidence is regenerated only after source is clean and
   passes the committed-evidence verifier.
