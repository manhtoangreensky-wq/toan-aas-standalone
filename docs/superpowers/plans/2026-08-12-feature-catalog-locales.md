# Feature Catalogue Locales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Localize the fixed `/features` and `/features/{family}` Portal chrome into Vietnamese, English, and Simplified Chinese without changing route, execution, or pricing authority.

**Architecture:** Keep the server-issued catalogue as the sole source of dynamic feature data. Add a compact `featureCatalog.*` i18n namespace and route every fixed label through a presentation helper; the existing Route Engine descriptor and public-sale price boundary remain untouched.

**Tech Stack:** FastAPI static Portal, vanilla JavaScript, Portal i18n bundle, pytest, Node syntax checks.

---

### Task 1: Lock the presentation and safety contract

**Files:**

- Create: `tests/test_feature_catalog_locale_contracts.py`
- Test: `tests/test_feature_catalog_locale_contracts.py`

- [ ] Write a failing locale contract requiring the `featureCatalog.*` keys in all three reviewed locales.
- [ ] Write a failing renderer contract requiring `featureCatalogText` and `featureCatalogGroupCopy` in both catalogue renderers and excluding `public_sale_catalog` from the feature catalogue renderer.
- [ ] Run `python -m pytest -q tests/test_feature_catalog_locale_contracts.py` and observe RED.

### Task 2: Add reviewed presentation copy

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Test: `tests/test_feature_catalog_locale_contracts.py`

- [ ] Add complete equal `vi`, `en`, and `zh` keysets for fixed directory chrome, all eleven groups, Guided Start, Capability Hub, family summary, search, engine labels, and readiness labels.
- [ ] Merge `FEATURE_CATALOG_MESSAGES[locale]` into the existing message bundle without inserting provider, model, cost, price, workflow or route records.
- [ ] Run the focused locale and i18n bundle tests; message-key assertions should turn GREEN.

### Task 3: Consume the locale catalogue in feature surfaces

**Files:**

- Modify: `static/portal/portal.js`
- Test: `tests/test_feature_catalog_locale_contracts.py`

- [ ] Add `featureCatalogText` and `featureCatalogGroupCopy` helpers.
- [ ] Use those helpers only for fixed chrome in `renderFeatureCatalog`, `renderFeatureFamily`, `renderFeatureGuidedStart`, Capability Hub, card fallbacks, engine/readiness labels, and `filterFeatureCatalog`.
- [ ] Add known family title/description lookup to `localizedPageTitle()` and `localizedPageDescription()`.
- [ ] Leave `normalizeRouteEngineDescriptor`, `renderRouteEngineBoundary`, `canonicalPublicSalePricingCatalog`, bridge calls, and action guards unchanged.
- [ ] Run targeted pytest contracts, Node syntax checks, and `git diff --check`.

### Task 4: Review, evidence refresh, and handoff

**Files:**

- Modify: generated `docs/migration/*` and `reports/migration/*.json` only if the static audit reports a source fingerprint update.
- Review: all Task 1–3 files.

- [ ] Inspect the full diff and confirm no Bot, provider, PayOS, wallet, credential, pricing, bridge, or deployment file changed.
- [ ] Commit the implementation first as `feat: localize feature catalogue chrome`.
- [ ] Refresh static migration evidence against that implementation SHA, commit generated evidence separately only when changed, then verify the final evidence SHA.
