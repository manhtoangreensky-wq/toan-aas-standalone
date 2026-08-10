from __future__ import annotations

from copyfast_route_engine import (
    CatalogApproval,
    RouteCandidate,
    RouteCatalog,
    RouteRequest,
    RouteStatus,
    resolve_route,
    unconfigured_catalog,
)


def request() -> RouteRequest:
    return RouteRequest(
        capability_key="image_generate",
        model_key="flux-pro",
        currency="USD",
        billable_unit="image",
    )


def candidate(
    provider_key: str,
    cost_minor: int | None,
    *,
    adapter_key: str | None = None,
    capability_key: str = "image_generate",
    model_key: str = "flux-pro",
    currency: str = "USD",
    billable_unit: str = "image",
    approved: bool = True,
    fallback_eligible: bool = True,
) -> RouteCandidate:
    return RouteCandidate(
        provider_key=provider_key,
        adapter_key=adapter_key or f"{provider_key}-adapter",
        capability_key=capability_key,
        model_key=model_key,
        currency=currency,
        billable_unit=billable_unit,
        cost_minor=cost_minor,
        catalog_version="costs-2026-08-10",
        source_ref="owner-approved-catalog",
        approved=approved,
        fallback_eligible=fallback_eligible,
    )


def test_resolve_route_selects_cheapest_primary_orders_fallbacks_and_prices_highest_cost() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=(candidate("key4u", 25), candidate("shopai", 11), candidate("reserve", 18)),
    )

    decision = resolve_route(request(), catalog)

    assert decision.status is RouteStatus.READY
    assert decision.primary is not None
    assert decision.primary.provider_key == "shopai"
    assert [item.provider_key for item in decision.fallbacks] == ["reserve", "key4u"]
    assert decision.retail_price_minor == 75
    assert decision.currency == "USD"


def test_route_catalog_snapshots_list_candidates_at_construction() -> None:
    candidates = [candidate("shopai", 11)]
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=candidates,
    )
    candidates.clear()

    decision = resolve_route(request(), catalog)

    assert decision.primary is not None
    assert decision.primary.provider_key == "shopai"


def test_route_catalog_fails_closed_when_candidates_is_none() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=None,  # type: ignore[arg-type]
    )

    decision = resolve_route(request(), catalog)

    assert catalog.candidates == ()
    assert decision.status is RouteStatus.GUARDED
    assert decision.retail_price_minor is None


def test_route_catalog_fails_closed_when_candidates_is_not_a_container() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=object(),  # type: ignore[arg-type]
    )

    decision = resolve_route(request(), catalog)

    assert catalog.candidates == ()
    assert decision.status is RouteStatus.GUARDED
    assert decision.retail_price_minor is None


def test_resolve_route_guards_invalid_request_before_field_access() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=(candidate("primary", 11),),
    )

    decision = resolve_route(None, catalog)  # type: ignore[arg-type]

    assert decision.status is RouteStatus.GUARDED
    assert decision.catalog_version == "costs-2026-08-10"
    assert decision.primary is None
    assert decision.retail_price_minor is None
    assert decision.guard_reason == "ROUTE_INVALID_REQUEST"


def test_resolve_route_guards_invalid_catalog_before_field_access() -> None:
    decision = resolve_route(request(), None)  # type: ignore[arg-type]

    assert decision.status is RouteStatus.GUARDED
    assert decision.catalog_version == "unconfigured"
    assert decision.primary is None
    assert decision.retail_price_minor is None
    assert decision.guard_reason == "ROUTE_INVALID_CATALOG"


def test_resolve_route_guards_when_catalog_contains_malformed_candidate() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=(object(),),
    )

    decision = resolve_route(request(), catalog)

    assert decision.status is RouteStatus.GUARDED
    assert decision.primary is None
    assert decision.fallbacks == ()
    assert decision.retail_price_minor is None
    assert decision.guard_reason == "ROUTE_NO_VERIFIED_COST"


def test_resolve_route_excludes_non_boolean_fallback_eligibility() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=(
            candidate("primary", 11),
            candidate("string-fallback", 18, fallback_eligible="false"),  # type: ignore[arg-type]
        ),
    )

    decision = resolve_route(request(), catalog)

    assert decision.status is RouteStatus.READY
    assert decision.primary is not None
    assert decision.primary.provider_key == "primary"
    assert decision.fallbacks == ()
    assert decision.retail_price_minor == 33


def test_route_catalog_normalizes_canonical_approval_string_and_guards_untrusted_values() -> None:
    canonical_catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status="canonical_approved",  # type: ignore[arg-type]
        candidates=(candidate("primary", 11),),
    )
    invalid_catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=object(),  # type: ignore[arg-type]
        candidates=(candidate("primary", 11),),
    )
    provisional_catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status="PROVISIONAL_PUBLIC_CATALOG",  # type: ignore[arg-type]
        candidates=(candidate("primary", 11),),
    )

    canonical_decision = resolve_route(request(), canonical_catalog)
    invalid_decision = resolve_route(request(), invalid_catalog)
    provisional_decision = resolve_route(request(), provisional_catalog)

    assert canonical_catalog.approval_status is CatalogApproval.CANONICAL_APPROVED
    assert canonical_decision.status is RouteStatus.READY
    assert invalid_catalog.approval_status is CatalogApproval.UNCONFIGURED
    assert invalid_decision.status is RouteStatus.GUARDED
    assert invalid_decision.guard_reason == "ROUTE_CATALOG_NOT_APPROVED"
    assert provisional_catalog.approval_status is CatalogApproval.UNCONFIGURED
    assert provisional_decision.status is RouteStatus.GUARDED
    assert provisional_decision.primary is None
    assert provisional_decision.retail_price_minor is None


def test_resolve_route_only_uses_fallback_eligible_candidates_in_quote() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=(
            candidate("primary", 11),
            candidate("not-selectable", 99, fallback_eligible=False),
            candidate("fallback", 18),
        ),
    )

    decision = resolve_route(request(), catalog)

    assert [item.provider_key for item in decision.fallbacks] == ["fallback"]
    assert decision.retail_price_minor == 54


def test_resolve_route_breaks_equal_cost_ties_by_provider_then_adapter() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=(
            candidate("zeta", 11, adapter_key="a"),
            candidate("alpha", 11, adapter_key="z"),
            candidate("alpha", 11, adapter_key="a"),
        ),
    )

    decision = resolve_route(request(), catalog)

    assert decision.primary is not None
    assert decision.primary.adapter_key == "a"
    assert [(item.provider_key, item.adapter_key) for item in decision.fallbacks] == [
        ("alpha", "z"),
        ("zeta", "a"),
    ]


def test_resolve_route_returns_guarded_without_exact_approved_cost() -> None:
    catalog = RouteCatalog(
        version="draft",
        approval_status=CatalogApproval.DRAFT,
        candidates=(candidate("shopai", None),),
    )

    decision = resolve_route(request(), catalog)

    assert decision.status is RouteStatus.GUARDED
    assert decision.primary is None
    assert decision.fallbacks == ()
    assert decision.retail_price_minor is None
    assert decision.currency is None
    assert decision.guard_reason == "ROUTE_CATALOG_NOT_APPROVED"


def test_resolve_route_guards_when_all_candidates_are_invalid_or_mismatched() -> None:
    catalog = RouteCatalog(
        version="costs-2026-08-10",
        approval_status=CatalogApproval.CANONICAL_APPROVED,
        candidates=(
            candidate("missing", None),
            candidate("zero", 0),
            candidate("unapproved", 10, approved=False),
            candidate("wrong-model", 10, model_key="other-model"),
        ),
    )

    decision = resolve_route(request(), catalog)

    assert decision.status is RouteStatus.GUARDED
    assert decision.primary is None
    assert decision.fallbacks == ()
    assert decision.retail_price_minor is None
    assert decision.guard_reason == "ROUTE_NO_VERIFIED_COST"


def test_unconfigured_catalog_is_empty_and_fails_closed() -> None:
    catalog = unconfigured_catalog()

    decision = resolve_route(request(), catalog)

    assert catalog.approval_status is CatalogApproval.UNCONFIGURED
    assert catalog.candidates == ()
    assert decision.status is RouteStatus.GUARDED
