# Route Engine Pricing Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pure, fail-closed route selector that chooses an approved lowest-cost provider route and computes the required `ceil(max × 3)` quote without executing a provider.

**Architecture:** `copyfast_route_engine.py` defines immutable request, candidate, catalog, and decision types plus one pure resolver. It receives a trusted in-memory catalog, never reads configuration or invokes a service, and returns `guarded` instead of inventing cost data. Tests treat the module as an internal server-side primitive, not a browser API.

**Tech Stack:** Python 3.12 standard library, pytest.

---

### Task 1: Pure route selector and contract tests

**Files:**

- Create: `copyfast_route_engine.py`
- Create: `tests/test_route_engine.py`
- Create: `tests/test_route_engine_contracts.py`

- [ ] **Step 1: Write failing behavior tests**

```python
def test_resolve_route_selects_cheapest_primary_orders_fallbacks_and_prices_highest_cost() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=(candidate("key4u", 25), candidate("shopai", 11), candidate("reserve", 18)),
    )
    decision = resolve_route(request(), catalog)
    assert decision.status is RouteStatus.READY
    assert decision.primary.provider_key == "shopai"
    assert [item.provider_key for item in decision.fallbacks] == ["reserve", "key4u"]
    assert decision.retail_price_minor == 75

def test_resolve_route_returns_guarded_without_exact_approved_cost() -> None:
    catalog = RouteCatalog("draft", CatalogApproval.DRAFT, (candidate("shopai", None),))
    decision = resolve_route(request(), catalog)
    assert decision.status is RouteStatus.GUARDED
    assert decision.retail_price_minor is None
```

- [ ] **Step 2: Run the tests and observe RED**

Run:

```powershell
python -m pytest -q tests/test_route_engine.py tests/test_route_engine_contracts.py
```

Expected: collection fails because `copyfast_route_engine` does not yet exist.

- [ ] **Step 3: Add the minimal pure implementation**

```python
class RouteStatus(str, Enum):
    READY = "ready"
    GUARDED = "guarded"

def resolve_route(request: RouteRequest, catalog: RouteCatalog) -> RouteDecision:
    if catalog.approval_status is not CatalogApproval.CANONICAL_APPROVED:
        return RouteDecision.guarded(catalog.version, "ROUTE_CATALOG_NOT_APPROVED")
    eligible = sorted(
        (candidate for candidate in catalog.candidates if candidate.matches(request)),
        key=lambda candidate: (candidate.cost_minor, candidate.provider_key, candidate.adapter_key),
    )
    if not eligible:
        return RouteDecision.guarded(catalog.version, "ROUTE_NO_VERIFIED_COST")
    primary = eligible[0]
    fallbacks = tuple(candidate for candidate in eligible[1:] if candidate.fallback_eligible)
    selectable = (primary, *fallbacks)
    price = math.ceil(max(candidate.cost_minor for candidate in selectable) * 3)
    return RouteDecision.ready(catalog.version, primary, fallbacks, price)
```

The full implementation must validate keys, require a positive integer cost, and preserve no mutable global catalog.

- [ ] **Step 4: Add import and boundary contract**

```python
FORBIDDEN_IMPORT_ROOTS = {
    "bot", "copyfast_bridge", "copyfast_db", "copyfast_api", "httpx",
    "requests", "subprocess", "os", "sqlite3", "payos",
}

def test_route_engine_has_no_provider_or_payment_runtime_dependency() -> None:
    tree = ast.parse(Path("copyfast_route_engine.py").read_text(encoding="utf-8"))
    imported = imported_roots(tree)
    assert not imported.intersection(FORBIDDEN_IMPORT_ROOTS)
```

- [ ] **Step 5: Run targeted tests and static syntax check**

Run:

```powershell
python -m pytest -q tests/test_route_engine.py tests/test_route_engine_contracts.py
python -m py_compile copyfast_route_engine.py
git diff --check
```

Expected: all new tests pass, module compiles, and diff check exits zero.

- [ ] **Step 6: Commit**

```powershell
git add copyfast_route_engine.py tests/test_route_engine.py tests/test_route_engine_contracts.py docs/superpowers/specs/2026-08-10-route-engine-pricing-foundation-design.md docs/superpowers/plans/2026-08-10-route-engine-pricing-foundation.md
git commit -m "feat: add fail-closed provider route selector"
```

### Task 2: Scope review and handoff

**Files:**

- Review: `copyfast_route_engine.py`
- Review: `tests/test_route_engine.py`
- Review: `tests/test_route_engine_contracts.py`

- [ ] **Step 1: Inspect full diff**

Run:

```powershell
git diff --check origin/main...HEAD
git diff --name-only origin/main...HEAD
git diff origin/main...HEAD -- bot.py
```

Expected: no whitespace error, only route-engine docs/module/tests, and no `bot.py` change.

- [ ] **Step 2: Verify protected boundaries**

Run:

```powershell
rg -n "ShopAIKey|Key4U|httpx|requests|subprocess|copyfast_bridge|copyfast_db|PayOS|wallet" copyfast_route_engine.py
```

Expected: no provider endpoint, credential, bridge, payment, database or network runtime dependency.

- [ ] **Step 3: Push and create a PR (requires explicit, current Owner authority)**

Run:

```powershell
git push -u origin feature/p0-webapp-route-engine-pricing
gh pr create --base main --title "feat: add fail-closed provider route selector"
```

Only perform this step with explicit, current Owner authority. The PR must
explicitly state that the catalog remains unconfigured until an exact approved
provider cost table exists. Public/provisional ShopAIKey/Key4U UI quote data
is not canonical cost and must not be imported. Do not deploy, call a
provider, change ENV, or mutate wallet/PayOS.
