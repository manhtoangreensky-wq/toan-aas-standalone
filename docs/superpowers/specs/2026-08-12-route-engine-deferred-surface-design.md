# Route Engine Deferred Surface — Design

## Owner-approved direction

The Web App must connect the route-engine boundary and improve the feature
catalogue before pricing is finalized. The product keeps its teal/cyan visual
system, supports the existing light/dark-ready semantic tokens, and does not
show, infer, calculate, or charge a price from provisional provider data.

## Problem

`copyfast_route_engine.py` is intentionally a pure, fail-closed server-side
selector. It already has an `unconfigured_catalog()` default but `/api/v1/catalog`
does not disclose that the selector is deliberately deferred. The Portal can
therefore show workflow availability without explaining the pricing/engine
boundary. Legacy `cost_xu` and `price_vnd` fields also reach generic browser
pricing projections, creating a path for a provisional value to be displayed
outside the owner-approved public-sale catalogue.

## Design

### Server descriptor

`GET /api/v1/catalog` will publish only this fixed projection:

```json
{
  "route_engine": {
    "state": "deferred",
    "catalog_version": "unconfigured",
    "catalog_approval": "unconfigured",
    "price_display": false
  }
}
```

The descriptor is derived from `unconfigured_catalog()` but never invokes
`resolve_route()`. It carries no provider, model, adapter, cost, retail price,
currency, fallback, payment, wallet, job, output, or capability grant.

The generic `pricing` surface retains only non-price metadata needed to choose
a canonical workflow tier. It strips `cost_xu`, `price_vnd`, `display_price`,
and aggregate cost values. Public sale prices remain a separate, strict
`public_sale_catalog` projection and only render when its owner-approved
versioned contract is available.

### Portal state and UI

`integration.js` reads the descriptor only from the fresh `/catalog` response
and resets it on every bootstrap. `portal.js` projects the descriptor through a
closed normalizer; absent or malformed data becomes `loading`/`guarded`, never
a guessed deferred/ready state.

The `/features` catalogue and each `/features/{family}` page render one calm
route-engine boundary notice:

- deferred: engine routing awaits a canonical approved catalogue; no provider
  or fallback is selected and no price is shown;
- loading: the signed catalogue is still being read;
- guarded: the descriptor did not pass its browser contract.

The notice is informational only. It has no checkout, confirmation, provider,
or job control and is never consulted by `canAct`, form enablement, estimate,
confirmation, or payment logic.

Fixed notice copy is added to the reviewed Vietnamese, English, and Simplified
Chinese interface catalogues. Dynamic server data remains untouched.

### Visual and motion rules

The new notice extends the existing TOAN AAS teal/cyan surface with semantic
Portal tokens only; no purple palette from the generic design search is used.
It is responsive as a two-column desktop card and one-column mobile card, with
44px-safe controls not needed because the surface has no action. The entrance
uses the shared motion-kit values (220ms, emphasis easing, transform/opacity
only) and its `prefers-reduced-motion` fallback disables the animation.

## Explicit pricing return gate

The implementation creates `docs/migration/ROUTE_ENGINE_PRICING_DEFERRED.md`.
The next pricing task may proceed only after all of these are recorded:

1. exact canonical provider/adapter/capability/model/unit/currency mapping;
2. owner-approved catalog version and sale SKU mapping;
3. verifier and approval evidence, not public estimates;
4. a Core Bridge contract that projects public sale data without internal cost;
5. contract tests proving no provider/cost/fallback field reaches the browser.

## Out of scope

- Bot source, provider calls, Key4U/ShopAIKey calls, route execution, jobs,
  wallet/Xu, PayOS, checkout, webhooks, ENV, deployment, and a global visual
  redesign.
- Replacing the current app stack or adding a paid motion dependency.

## Verification

- TDD contract suite for descriptor shape, browser projection, stale-state
  clearing, i18n coverage, no price fields, and non-authorizing render use.
- Focused existing route-engine and public-sale projection suites.
- `py_compile`, `node --check`, `git diff --check`, and a rendered signed
  Portal smoke at desktop and mobile widths with reduced motion checked.
