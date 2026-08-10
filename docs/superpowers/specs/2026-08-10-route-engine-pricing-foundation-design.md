# Route Engine Pricing Foundation Design

## Goal

Build a pure, server-side route selector for a future Web-native media
executor. It ranks approved ShopAIKey/Key4U candidates by exact normalized
cost, returns the lowest-cost primary and cost-ordered fallbacks, and prices a
route at `ceil(max(eligible candidate cost) × 3)`.

This slice deliberately contains no ShopAIKey or Key4U credentials, no API
client, no HTTP route, no database, no environment loader, no wallet/Xu,
PayOS, Bot, webhook, job, file or provider call. It must fail closed until an
approved canonical cost catalog is supplied by a later task.

## Inputs and authority

The current source inventory has no provider/model-level, exact, approved cost
table. A handoff from the Bot team identifies a public-price UI quote source,
but explicitly marks every ShopAIKey/Key4U row as provisional: it has no
`verified_by`, invoice/dashboard evidence, Owner approval record, or complete
canonical adapter aliases. That data is not copied into this repository or
used to create a route/price catalog. Draft pricing, public estimates and
ordinal cost tiers are not accepted. A later catalog record must declare:

- provider and adapter keys;
- capability and exact model keys;
- currency and billable unit;
- exact normalized `cost_minor` value;
- catalog version and source reference;
- canonical approval and fallback eligibility.

The catalog is supplied in memory by trusted server code. Browser values are
never accepted by this module.

Any provisional or unknown approval value is normalized to an unconfigured
catalog and therefore returns `guarded`; it cannot become a customer quote by
accident.

## Decision rules

1. A catalog must have `approval_status="canonical_approved"`.
2. A candidate must be explicitly approved, have a positive integer
   `cost_minor`, and exactly match capability, model, currency and billable
   unit.
3. Candidates are sorted by `(cost_minor, provider_key, adapter_key)`.
4. The first candidate is the primary. Later fallback-eligible candidates are
   the fallback chain, in the same ordering.
5. The quote uses the greatest cost among candidates that can be selected for
   this request, multiplied by three and rounded up in minor currency units.
6. Missing price, draft catalog, mismatched shape/unit/currency or no eligible
   candidate returns a `guarded` decision with no primary, fallback or price.
7. A future executor may only fallback before a provider returns its task ID;
   once an external task is accepted it must not dispatch to another provider.

## Boundaries

`copyfast_route_engine.py` is pure Python. It can be imported in tests and
future server-side adapters, but must not import or reference `bot`,
`copyfast_bridge`, `httpx`, `requests`, `subprocess`, database modules,
environment access or payment modules. No endpoint is registered in this
slice, preventing provider/cost details from becoming browser output.

## Verification

- Tests exercise canonical approval, exact cost gate, stable cheapest-first
  ordering, fallback order, `max × 3` pricing, and mismatch guards.
- A static contract test rejects forbidden imports and executable provider or
  network surfaces.
- No real provider, Bot, wallet, PayOS, webhook, ENV or deployment action is
  permitted.
