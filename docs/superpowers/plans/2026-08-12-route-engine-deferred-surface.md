# Route Engine Deferred Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the feature catalogue explain the unconfigured route-engine safely while removing provisional tier prices from browser display.

**Architecture:** `copyfast_api.py` publishes one closed, read-only deferred descriptor derived from the pure route engine. The Portal receives it only through the existing catalogue hydration, re-projects it defensively, and renders a localized informational notice on `/features` and each feature-family page. Pricing remains delegated to the existing owner-approved `public_sale_catalog` path.

**Tech Stack:** FastAPI, Python 3.12, vanilla JavaScript, Portal CSS, existing portal i18n, pytest, Node syntax checks.

---

### Task 1: Write the deferred-boundary contract (RED)

**Files:**

- Create: `tests/test_route_engine_deferred_portal_contracts.py`
- Test: `tests/test_route_engine_deferred_portal_contracts.py`

- [ ] **Step 1: Write the server descriptor tests**

```python
from copyfast_api import _route_engine_deferred_descriptor

def test_route_engine_deferred_descriptor_is_closed_and_price_free() -> None:
    assert _route_engine_deferred_descriptor() == {
        "state": "deferred",
        "catalog_version": "unconfigured",
        "catalog_approval": "unconfigured",
        "price_display": False,
    }
```

- [ ] **Step 2: Write static browser-boundary tests**

```python
def test_catalog_and_portal_keep_route_engine_deferred_without_price_or_authority() -> None:
    assert '"route_engine": _route_engine_deferred_descriptor()' in API
    assert "function normalizeRouteEngineDescriptor(value)" in PORTAL
    assert "function renderRouteEngineBoundary(context)" in PORTAL
    for forbidden in ("provider", "model", "fallback", "cost_xu", "retail_price_minor", "price_vnd"):
        assert forbidden not in route_engine_sections()
```

- [ ] **Step 3: Write stale-state, localization, and legacy-price tests**

```python
def test_catalog_hydration_replaces_route_engine_state_and_copy_is_reviewed() -> None:
    assert "const routeEngine = catalogData.route_engine" in INTEGRATION
    assert "routeEngine," in INTEGRATION
    for locale in ("vi", "en", "zh"):
        assert f'routeEngine.notice.deferred.title' in locale_messages(locale)

def test_legacy_tier_prices_are_not_projected_or_rendered() -> None:
    assert '"cost_xu"' not in pricing_projection()
    assert '"price_vnd"' not in pricing_projection()
    assert "tier.cost_xu" not in field_option_renderer()
```

- [ ] **Step 4: Run the focused test and observe RED**

Run:

```powershell
python -m pytest -q tests/test_route_engine_deferred_portal_contracts.py
```

Expected: FAIL because no descriptor, browser normalizer, notice, or no-price
projection exists yet.

### Task 2: Publish the safe server descriptor and remove legacy price fields

**Files:**

- Modify: `copyfast_api.py`
- Test: `tests/test_route_engine_deferred_portal_contracts.py`

- [ ] **Step 1: Add the pure descriptor helper**

```python
from copyfast_route_engine import unconfigured_catalog

def _route_engine_deferred_descriptor() -> dict[str, str | bool]:
    route_catalog = unconfigured_catalog()
    return {
        "state": "deferred",
        "catalog_version": route_catalog.version,
        "catalog_approval": route_catalog.approval_status.value,
        "price_display": False,
    }
```

Include it in `feature_catalog()` as `"route_engine"`. Do not call
`resolve_route()`.

- [ ] **Step 2: Remove provisional cost fields from the generic pricing projection**

```python
result = _project_record(value, ("available", "billing_mode", "price_table_source"))
tier_fields = ("code", "label", "note", "retry_warranty_count")
combo_fields = ("code", "label", "summary")
```

Keep `public_sale_catalog` unchanged because it is separately validated.

- [ ] **Step 3: Run the focused test and verify the server portion is GREEN**

Run:

```powershell
python -m pytest -q tests/test_route_engine_deferred_portal_contracts.py
```

Expected: only browser/i18n assertions remain RED.

### Task 3: Hydrate, normalize, and render the deferred boundary

**Files:**

- Modify: `static/portal/integration.js`
- Modify: `static/portal/portal.js`
- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.css`
- Test: `tests/test_route_engine_deferred_portal_contracts.py`

- [ ] **Step 1: Hydrate only the current catalogue descriptor**

```javascript
const routeEngine = catalogData.route_engine && typeof catalogData.route_engine === "object"
  ? catalogData.route_engine
  : {};

merge({ ...context, routeEngine, /* existing catalogue fields */ });
```

- [ ] **Step 2: Add a closed Portal normalizer and localized text helper**

```javascript
function routeEngineText(key, fallback, params) {
  return uiText(`routeEngine.${key}`, fallback, params);
}

function normalizeRouteEngineDescriptor(value) {
  const source = value && typeof value === "object" && !Array.isArray(value) ? value : null;
  if (!source) return { state: "loading" };
  if (source.state !== "deferred" || source.catalog_version !== "unconfigured"
    || source.catalog_approval !== "unconfigured" || source.price_display !== false) {
    return { state: "guarded" };
  }
  return { state: "deferred", catalogVersion: "unconfigured" };
}
```

Project it from `normalizeBootstrap()` and never pass it into action guards.

- [ ] **Step 3: Render one non-action notice in both feature surfaces**

```javascript
function renderRouteEngineBoundary(context) {
  const routeEngine = context.routeEngine || { state: "loading" };
  if (routeEngine.state === "deferred") {
    return `<section class="portal-route-engine-notice portal-route-engine-notice--deferred" role="status">...</section>`;
  }
  return `<section class="portal-route-engine-notice" role="status">...</section>`;
}
```

Insert the result before the feature cards in `renderFeatureCatalog()` and
`renderFeatureFamily()`. Remove `cost_xu` and `price_vnd` label construction
from selector options while preserving their server-provided tier codes.

- [ ] **Step 4: Add vi/en/zh copy and motion-safe CSS**

Add identical `routeEngine.notice.*` keys to all three `MESSAGES` locale blocks.
Style the notice with Portal semantic tokens, a 220ms opacity/transform entrance,
and a reduced-motion override. Do not introduce an external animation library.

- [ ] **Step 5: Run the focused contracts and syntax checks**

Run:

```powershell
python -m pytest -q tests/test_route_engine_deferred_portal_contracts.py tests/test_route_engine.py tests/test_route_engine_contracts.py tests/test_public_sale_pricing_projection_contracts.py
python -m py_compile copyfast_api.py
node --check static/portal/integration.js
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
git diff --check
```

Expected: all commands exit 0.

### Task 4: Document the return gate and visually verify

**Files:**

- Create: `docs/migration/ROUTE_ENGINE_PRICING_DEFERRED.md`
- Review: `copyfast_api.py`, `static/portal/integration.js`, `static/portal/portal.js`, `static/portal/portal-i18n.js`, `static/portal/portal.css`

- [ ] **Step 1: Document exact inputs required before pricing work resumes**

Record the owner-approved catalog version, provider/adapter mapping, verified
cost evidence, public-sale SKU contract, and tests required before the UI can
show a price or invoke a route selector.

- [ ] **Step 2: Verify the rendered Portal**

Start the existing local app using its documented command, sign in with a local
test account only, and check `/features` plus one `/features/{family}` route at
desktop and 375px widths. Confirm the notice is visible, no price/provider text
is present, keyboard focus remains visible, and `prefers-reduced-motion` keeps
the flow readable.

- [ ] **Step 3: Review boundaries and commit**

Run:

```powershell
git diff --check origin/main...HEAD
git diff -- bot.py
rg -n "provider|fallback|cost_xu|retail_price_minor|price_vnd" copyfast_api.py static/portal/integration.js static/portal/portal.js
```

Commit only the files named in this plan with:

```powershell
git commit -m "feat: expose deferred route-engine boundary"
```
