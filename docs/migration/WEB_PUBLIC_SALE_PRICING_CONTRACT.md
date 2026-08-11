# Web public sale pricing contract

## Owner decision

The Owner selected **Option 1 — strict synchronization** on 2026-08-11.
The Web App displays a sale price only after the Bot/Core Bridge has published
the same approved product catalogue. It does not use a local table as a second
pricing authority.

## Required signed Bridge projection

`GET /pricing` may include the following strictly public projection:

```json
{
  "available": true,
  "public_sale_catalog": {
    "available": true,
    "catalog_version": "owner-approved-YYYY-MM-DD",
    "approval_status": "owner_approved",
    "items": [
      {
        "code": "canonical-product-sku",
        "family": "video|image|music|audio|video_combo",
        "label": "Customer-facing service name",
        "sale_price_xu": 100,
        "status": "ready"
      }
    ]
  }
}
```

`code` must be the exact canonical Bot product code. It is never inferred from
a UI label, duration, position, legacy tier, model, or price. The Bridge must
publish a new `catalog_version` whenever a public row changes.

## Browser allow-list and rendering rules

The Web projects only these public fields:

- Catalogue: `available`, `catalog_version`, `approval_status`.
- Item: `code`, `family`, `label`, `sale_price_xu`, `status`.

The browser renders rows only when the top-level pricing projection is valid,
the public catalogue is available, the version is bounded, approval is exactly
`owner_approved`, every code is valid and unique, and every price is a positive
safe integer. Unknown, malformed, duplicate, stale, or unapproved rows are
discarded. If no valid rows remain, `/pricing` shows a guarded state.

## Prohibited Web behaviour

The Web must not publish or derive a sale price from provider details, models,
USD, FX, markup, fallback policy, legacy tier order, or a draft document. It
must not feed public rows into feature estimate/confirm, wallet, ledger, PayOS,
refund, package purchase, provider routing, or any Bot write path.

Legacy `cost_xu` fields may remain in the signed private pricing projection for
existing feature selectors, but the customer `/pricing` page never renders
them as sale prices.

## Migration gate

The requested video, image, and music price rows remain unavailable on the Web
until the Bot/Core Bridge supplies exact SKU mappings and an approved catalogue
version. This preserves the single charge authority and prevents a customer
from seeing a Web price that differs from the price at signed confirmation.
