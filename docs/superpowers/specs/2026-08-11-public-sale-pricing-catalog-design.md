# Canonical Public Sale Pricing Projection — Design

## Owner request and current evidence

The Owner requested that the Web App show customer sale prices only, with the
same prices as the Bot. Read-only inspection found that the current Core Bridge
pricing response contains only image/video tiers with `cost_xu`; it has no
versioned public-sale catalogue, no approved SKU mapping for all requested
video/image products, and no music rows. The supplied table is explicitly
marked `DRAFT_OWNER_STANDARD` and its image/video/music rows cannot be mapped
to current Bot product codes without guessing.

## Design

The Web App will support an upstream-issued `public_sale_catalog` projection
inside the existing signed `/pricing` response. It is a read-only display
surface and can only render when all of the following are supplied by the
Core Bridge:

- `available: true`;
- a bounded `catalog_version`;
- `approval_status: "owner_approved"`;
- public item codes, category, label, and positive `sale_price_xu` values.

The browser projection is a strict allow-list. It discards any provider,
model, USD, FX, markup, fallback, internal-cost, or route metadata that may
exist upstream. Existing `cost_xu` tier data remains only for current Web
feature selectors and is never rendered by the `/pricing` page.

## Safety boundary

The Web does not infer a SKU from label, duration, ordering, price, or model.
It does not hard-code the draft table as a second pricing authority. A missing
or malformed public catalogue renders an honest guarded state rather than a
zero price, stale price, or unsupported product. Quote, confirmation, wallet,
PayOS, provider routing, and Bot source are out of scope.

## Customer experience

When the canonical public catalogue is available, `/pricing` groups the
published customer rows by product family and shows only the public label and
`N Xu` price. The page contains no action that can purchase, charge, or alter
credits. Until the Bot/Core Bridge publishes the exact approved version, it
clearly states that the public price catalogue is not yet available instead of
displaying provisional numbers as active prices.
