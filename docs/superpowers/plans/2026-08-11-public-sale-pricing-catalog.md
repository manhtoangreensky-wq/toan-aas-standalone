# Canonical Public Sale Pricing Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Web App render an exact Bot/Core Bridge public sale catalogue while never leaking internal pricing or changing any financial behaviour.

**Architecture:** `copyfast_api.py` redacts the signed Bridge response into a strict `public_sale_catalog` schema. `static/portal/portal.js` validates that schema and uses it only for `/pricing`; feature form tier choices retain their existing canonical data path. A missing/malformed catalogue is guarded, not replaced by a local table.

**Tech Stack:** FastAPI, vanilla JavaScript, static-contract pytest suites, existing portal i18n.

---

### Task 1: Write the RED contract for an upstream sale projection

**Files:**
- Create: `tests/test_public_sale_pricing_projection_contracts.py`
- Test: `tests/test_public_sale_pricing_projection_contracts.py`

- [x] **Step 1: Write a failing projection allow-list test**

```python
def test_pricing_projection_has_a_strict_public_sale_catalog_allow_list() -> None:
    assert '"public_sale_catalog"' in API
    assert '"catalog_version"' in API
    assert '"approval_status"' in API
    assert '"sale_price_xu"' in API
```

- [x] **Step 2: Write a failing portal rendering test**

```python
def test_pricing_page_renders_only_validated_public_sale_prices() -> None:
    assert "function canonicalPublicSalePricingCatalog(value)" in PORTAL
    assert 'approval_status !== "owner_approved"' in PORTAL
    assert "publicSaleCatalogEntries(publicSalePricing)" in PORTAL
```

- [x] **Step 3: Run the test and verify RED**

Run: `python -m pytest -q tests/test_public_sale_pricing_projection_contracts.py`

Expected: FAIL because neither projection nor validator exists yet.

### Task 2: Add the server-safe projection

**Files:**
- Modify: `copyfast_api.py:1357-1362`
- Test: `tests/test_public_sale_pricing_projection_contracts.py`

- [x] **Step 1: Define the public item field allow-list**

```python
public_sale_fields = ("code", "family", "label", "sale_price_xu", "status")
public_sale_catalog = value.get("public_sale_catalog")
if isinstance(public_sale_catalog, dict):
    result["public_sale_catalog"] = {
        **_project_record(public_sale_catalog, ("available", "catalog_version", "approval_status")),
        "items": _project_items(public_sale_catalog.get("items"), public_sale_fields),
    }
```

Do not add `provider`, `model`, `cost`, `cost_xu`, USD, FX, markup, fallback,
route, payment, or wallet fields to this projection.

- [x] **Step 2: Run the projection contract and verify GREEN for the server part**

Run: `python -m pytest -q tests/test_public_sale_pricing_projection_contracts.py`

Expected: the server allow-list assertion passes; the portal assertion remains RED.

### Task 3: Render only the approved public-sale projection

**Files:**
- Modify: `static/portal/portal.js:18600-18840`
- Modify: `static/portal/portal-i18n.js:7896-8063`
- Modify: `copyfast_pages.py:182-186`
- Modify: `tests/test_billing_catalog_locale_contracts.py`
- Test: `tests/test_public_sale_pricing_projection_contracts.py`

- [x] **Step 1: Add the bounded browser validator**

```javascript
function canonicalPublicSalePricingCatalog(value) {
  const source = value && typeof value === "object" && !Array.isArray(value)
    ? value.public_sale_catalog
    : null;
  if (!source || source.available !== true || source.approval_status !== "owner_approved") return null;
  const version = canonicalCatalogCode(source.catalog_version);
  if (!version || !Array.isArray(source.items) || source.items.length > 100) return null;
  const seenCodes = new Set();
  const items = source.items.flatMap((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return [];
    const code = canonicalCatalogCode(item.code);
    const salePrice = canonicalNonnegativeInteger(item.sale_price_xu);
    if (!code || salePrice === null || salePrice <= 0 || seenCodes.has(code)) return [];
    seenCodes.add(code);
    return [{ code, family: canonicalShortText(item.family, 80) || "service", label: canonicalShortText(item.label, 120) || code, priceLabel: `${salePrice} Xu`, status: "read_only" }];
  });
  return items.length ? { version, items } : null;
}
```

- [x] **Step 2: Make `/pricing` use only validated public sale rows**

```javascript
const pricing = canonicalPricingCatalog(context.pricingCatalog);
const publicSalePricing = pricing ? canonicalPublicSalePricingCatalog(context.pricingCatalog) : null;
const catalog = pricingPage
  ? publicSaleCatalogEntries(publicSalePricing, publicSaleFamilyLabels)
  : !pricingPage && packages
    ? [
      ...packages.monthly.map((item) => ({ title: item.label, description: item.note, priceLabel: item.priceLabel, status: item.status, family: billingCatalogText("catalog.family.monthly", "Gói tháng") })),
      ...packages.combos.map((item) => ({ title: item.label, description: item.note, priceLabel: item.priceLabel, status: item.status, family: billingCatalogText("catalog.family.combo", "Combo") }))
    ]
    : [];
```

Keep `canonicalPricingCatalog(context.pricingCatalog)` in existing form-choice
code. Do not pass public rows into estimate, confirmation, payment, or wallet
behaviour.

- [x] **Step 3: Localize fixed guarded/public-catalogue copy in vi/en/zh**

Add identical billing catalogue keys for public-pricing heading, approved
status, missing-catalogue title, missing-catalogue body, and generic family.
Product labels remain Core Bridge data and are escaped at render time.

- [x] **Step 4: Run the new contract test and verify GREEN**

Run: `python -m pytest -q tests/test_public_sale_pricing_projection_contracts.py`

Expected: PASS.

### Task 4: Document and verify boundaries

**Files:**
- Create: `docs/migration/WEB_PUBLIC_SALE_PRICING_CONTRACT.md`
- Modify: `tests/test_public_sale_pricing_projection_contracts.py`

- [x] **Step 1: Record contract and migration gate**

Document the required upstream fields, exact no-local-inference rule, no
internal-cost fields, no charge mutations, and the fact that the supplied
draft table requires an approved Bot SKU/version before it can appear.

- [x] **Step 2: Run focused regression tests**

Run: `python -m pytest -q tests/test_public_sale_pricing_projection_contracts.py tests/test_billing_canonical_journey_contracts.py tests/test_billing_catalog_locale_contracts.py tests/test_billing_navigation_app_ux_contracts.py tests/test_copyfast_bridge.py`

Expected: zero failures.

- [x] **Step 3: Run protected checks**

Run: `node --check static/portal/portal.js`, `node --check static/portal/portal-i18n.js`, `git diff --check`, and `git diff -- bot.py`

Expected: every command exits 0 and no Bot diff exists.

- [ ] **Step 4: Commit after independent review**

```bash
git add copyfast_api.py copyfast_pages.py static/portal/portal.js static/portal/portal-i18n.js tests/test_public_sale_pricing_projection_contracts.py tests/test_billing_catalog_locale_contracts.py docs/migration/WEB_PUBLIC_SALE_PRICING_CONTRACT.md docs/superpowers/specs/2026-08-11-public-sale-pricing-catalog-design.md docs/superpowers/plans/2026-08-11-public-sale-pricing-catalog.md
git commit -m "Add canonical public sale pricing projection"
```
