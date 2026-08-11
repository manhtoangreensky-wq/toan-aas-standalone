# Approved Sale Catalog Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure Packages and Membership render a price only from a matching
Core Bridge `public_sale_catalog` marked `owner_approved`.

**Architecture:** Keep package metadata and the public sale catalog as
separate read-only projections. Strip package `price_vnd` at the server
boundary, then join a validated SKU-to-sale-price map in the browser. A
missing or unapproved sale catalog is a guarded no-price state, never a
fallback calculation.

**Tech Stack:** FastAPI/Python projection, vanilla JavaScript Portal, pytest.

---

### Task 1: Establish failing strict-propagation contracts

**Files:**

- Modify: `tests/test_public_sale_pricing_projection_contracts.py`

- [ ] **Step 1: Add a failing server projection test**

```python
def test_package_projection_never_exposes_unapproved_price_vnd() -> None:
    projected = _project_surface_data(
        {"available": True, "monthly": [{"code": "starter", "label": "Starter", "price_vnd": 99000}]},
        "packages",
    )
    assert projected["monthly"] == [{"code": "starter", "label": "Starter", "items": {}}]
```

- [ ] **Step 2: Add a failing Portal contract**

```python
def test_package_and_membership_prices_use_only_approved_public_sale_skus() -> None:
    package_catalog = _section(PORTAL, "function canonicalPackageCatalog(value)", "function safePayosCheckout")
    assert "price_vnd" not in package_catalog
    assert "function approvedPublicSalePriceIndex(catalog)" in PORTAL
    assert "approvedPublicSalePriceIndex(publicSalePricing)" in _section(PORTAL, "function renderCatalog(page, context)", "const JOB_FILTERS")
```

- [ ] **Step 3: Run the focused test file and observe RED**

Run:

```powershell
python -m pytest -q tests/test_public_sale_pricing_projection_contracts.py -p no:cacheprovider
```

Expected: failure because `/packages` still projects `price_vnd` and the
approved price index does not yet exist.

### Task 2: Strip package prices and overlay approved sale prices

**Files:**

- Modify: `copyfast_api.py:surface == "packages"`
- Modify: `static/portal/portal.js:canonicalPackageCatalog`,
  `membershipCatalogEntries`, `renderMembership`, and `renderCatalog`

- [ ] **Step 1: Remove `price_vnd` from the packages projection allowlist**

```python
package_fields = ("code", "type", "label", "note", "default_days", "manual")
```

- [ ] **Step 2: Keep package metadata price-free in the Portal normalizer**

```javascript
return {
  code,
  label: canonicalShortText(item.label, 120) || code,
  note: canonicalShortText(item.note, 240) || "Gói canonical do Core Bridge cấp.",
  manual: item.manual === true,
  status: "read_only"
};
```

- [ ] **Step 3: Add one pure approved-price index**

```javascript
function approvedPublicSalePriceIndex(catalog) {
  if (!catalog || !Array.isArray(catalog.items)) return new Map();
  return new Map(catalog.items.map((item) => [item.code, item.priceLabel]));
}
```

The index is constructed only from `canonicalPublicSalePricingCatalog`; it
does not read package numeric fields.

- [ ] **Step 4: Use exact package-code matches in Membership and Packages**

For each package row, set `priceLabel` only from
`approvedPublicSalePriceIndex(publicSalePricing).get(code) || ""`. Render the
existing public-sale missing-price copy and guarded badge if absent.

- [ ] **Step 5: Run the focused test file and observe GREEN**

Run:

```powershell
python -m pytest -q tests/test_public_sale_pricing_projection_contracts.py -p no:cacheprovider
```

Expected: all tests pass.

### Task 3: Verify regression and evidence

**Files:**

- Modify: generated `docs/migration/*` and `reports/migration/*` only if the
  static audit changes the committed evidence.

- [ ] **Step 1: Run pricing/billing and portal static contracts**

```powershell
python -m pytest -q tests/test_public_sale_pricing_projection_contracts.py tests/test_billing_canonical_journey_portal_contracts.py tests/test_portal_safety_contracts.py -p no:cacheprovider
```

- [ ] **Step 2: Regenerate and verify migration evidence with the clean feature revision**

```powershell
python -B scripts/migration/audit_bot_to_web.py --bot-root 'D:\TOANAAS\bot telegram' --web-root . --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 --web-revision <HEAD> --report-dir reports/migration --docs-dir docs/migration
python -B scripts/migration/audit_bot_to_web.py --verify-web-evidence --web-root . --report-dir reports/migration --docs-dir docs/migration --web-revision <HEAD>
```

- [ ] **Step 3: Review and commit a narrow diff**

```powershell
git diff --check
git add copyfast_api.py static/portal/portal.js tests/test_public_sale_pricing_projection_contracts.py docs/migration reports/migration
git commit -m "Propagate approved public sale pricing"
```

The final diff must not modify Bot source, ENV, deployment, provider,
wallet, payment, or service-worker behavior.
