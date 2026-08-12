# Feature Catalogue Locales — Design

## Owner-approved direction

Continue the professional Web App before attaching a finished sale-price catalogue. The feature directory must work as a calm, accurate UI surface in Vietnamese, English, and Simplified Chinese. It keeps the existing teal/cyan Aura light/dark system and never translates, changes, or invents workflow, provider, payment, wallet, job, or customer data.

## Problem

`/features` and `/features/{family}` already use safe, server-issued route metadata and the route-engine deferred notice. Their fixed Portal chrome is mostly Vietnamese, however: group headings, search feedback, directory navigation, readiness labels, Guided Start, Capability Hub, and family summaries do not consistently follow the reviewed interface locale.

The route engine is intentionally still deferred. Its descriptor is a closed informational object, not a model selector or price source. A separately validated public-sale catalogue already has a browser boundary, but no runtime approved catalogue is seeded in this repository.

## Design

### Presentation boundary

Add a `featureCatalog.*` namespace to the existing Portal i18n bundle. Every new key exists in exactly the reviewed `vi`, `en`, and `zh` catalogue. It owns only fixed interface chrome:

- catalogue and feature-family headings, descriptions, navigation and calls to action;
- static group title/description metadata;
- Guided Start and Capability Hub labels, counts, summaries and safe empty states;
- search input chrome and result-count sentences;
- execution taxonomy and readiness labels; and
- generic workflow-card fallbacks.

The browser must preserve server-published route records exactly. Feature titles, descriptions, readiness records, capability decisions, job states and customer content are data, not browser translation input. The result is a localized shell around truthful server data rather than a fabricated second catalogue.

### Route Engine and pricing boundary

The existing `routeEngine` normalizer and non-action notice remain unchanged:

```json
{
  "state": "deferred",
  "catalog_version": "unconfigured",
  "catalog_approval": "unconfigured",
  "price_display": false
}
```

No code in this slice reads provider, adapter, model, fallback, internal cost, currency, wallet, payment, job, output, or execution fields from it. No public-sale price is added to feature cards. The future integration point remains the strict `public_sale_catalog` projection documented in `docs/migration/ROUTE_ENGINE_PRICING_DEFERRED.md` and `docs/migration/WEB_PUBLIC_SALE_PRICING_CONTRACT.md`.

### UX and visual rules

The existing Swiss-modern Portal system remains authoritative: semantic teal/cyan tokens, 4/8px rhythm, compact readable type, 44px mobile controls, visible focus, and 150–220ms transform/opacity-only motion. No new visual component family, provider indicator, price card, or action is introduced.

Family route titles and descriptions must resolve through the reviewed locale catalogue so browser title, hero, navigation and local search feedback agree. The static Vietnamese fallback applies only if the i18n bundle is unavailable; an otherwise unsupported requested locale still resolves through the Portal's normal English locale fallback.

## Out of scope

- Bot source, provider calls, route execution, bridge changes, jobs, wallet, PayOS, checkout, pricing policy, public-sale catalogue data, credentials, ENV, deployment, and any live provider/payment test.
- Translation or reinterpretation of dynamic customer, server, provider, or Bot content.
- Video-menu information architecture, which remains intentionally deferred.

## Acceptance criteria

1. `/features` and known `/features/{family}` fixed chrome renders through reviewed VI/EN/ZH keys.
2. Server-issued feature cards and route decisions remain untouched.
3. Route Engine stays deferred and informational; public sale pricing remains a marked future integration seam only.
4. Static contracts, i18n equal-keyset runtime check, targeted route-engine comparator, Node syntax checks, and diff check have evidence.
