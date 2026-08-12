# Route engine pricing: deferred integration gate

## Current state

The Web App publishes a fixed, display-only route-engine descriptor through
`GET /api/v1/catalog`:

```json
{
  "state": "deferred",
  "catalog_version": "unconfigured",
  "catalog_approval": "unconfigured",
  "price_display": false
}
```

This is deliberately not a route decision. The browser cannot select a
provider, adapter, model, fallback, currency, billable unit, cost, or retail
price from this descriptor. It also cannot grant a capability, create a job,
or authorize payment, wallet, or delivery behavior.

The pending integration point is intentionally named `route_engine` in the
catalog response and `routeEngine` in Portal bootstrap state. Do not replace
it with a client-side selector or a static pricing table.

## Required canonical catalogue before enabling routing

All items below are required. A public model page, provisional estimate,
historical quote, or unverified dashboard screenshot is not enough.

1. One owner-approved, versioned catalog record with exact mappings for:
   - `provider` key;
   - `adapter` key;
   - `capability` key;
   - `model` key and exact model alias;
   - `billable unit`;
   - `currency` and normalized minor-unit scale;
   - canonical `cost` evidence for each selectable route;
   - an explicit fallback eligibility decision.
2. Evidence for each record: verifier identity, verification time, durable
   dashboard or invoice reference, and the Owner approval identifier. The
   catalog must define its effective version and replacement/rollback policy.
3. A separately owner-approved `public sale` SKU catalog. Public sale prices
   must be versioned and may be displayed only through the existing
   `public_sale_catalog` projection. Internal provider cost, margin, FX,
   fallback ordering and routing data must stay server-private.
4. A reviewed Core Bridge contract that supplies the canonical catalog and
   public sale catalog as separate, authenticated server reads. It must define
   validation, timeout, idempotency, audit behavior and fail-closed behavior
   when a catalog is absent, stale, mismatched, or withdrawn.
5. Route-engine tests proving exact matching by capability/model/currency/
   billable unit, approval and fallback behavior, plus an explicit no-output
   path when the catalog is not canonical.
6. Browser contract tests proving no provider, adapter, model, fallback,
   internal cost, retail route value, currency, or execution grant crosses the
   catalog/Portal boundary. The only permitted price surface is the reviewed
   public sale SKU projection.

## Safe implementation sequence

1. Store the signed canonical catalog server-side; do not put it in browser
   storage or static source.
2. Validate it against the pure `copyfast_route_engine` structures and keep
   `resolve_route()` server-only.
3. Extend the authenticated Core Bridge read contract first, with schema tests
   and sanitized error handling. Do not add a new provider webhook or browser
   provider call.
4. Add a server-side public projection only after the catalog is
   owner-approved. The generic `pricing` projection must continue to exclude
   internal cost fields.
5. Update the deferred descriptor only after all new server, bridge, Portal,
   payment-safety and ownership contract tests are green.
6. Obtain explicit Owner approval for the precise catalog version before
   enabling an action or displaying a public sale SKU.

## Explicitly prohibited while deferred

- Copying provisional provider prices into Web code, templates, JavaScript or
  browser storage.
- Calling a provider, calculating a quote, choosing a fallback, or exposing
  a provider/model name from the Portal.
- Treating this descriptor as an execution, capability, job, payment, wallet,
  PayOS, refund, output, or delivery authorization.
- Promoting an estimate to an owner-approved price without the evidence above.

## Verification when this gate is revisited

At a minimum, add or update a contract test for the server catalog shape, Core
Bridge schema, failure/timeout behavior, no internal-price browser leakage,
exact route matching, ownership checks, and idempotent confirmation. Run the
affected route-engine, public-sale pricing, bridge, payment safety and Portal
test suites before proposing a deploy. A passing contract test does not itself
approve a catalog or authorize a production provider call.
