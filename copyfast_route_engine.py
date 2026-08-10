"""Pure, fail-closed selection of approved provider routes.

This module deliberately owns no catalog data and performs no I/O.  Trusted
server code may provide a canonical catalog when an executor is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class CatalogApproval(str, Enum):
    CANONICAL_APPROVED = "canonical_approved"
    DRAFT = "draft"
    UNCONFIGURED = "unconfigured"


class RouteStatus(str, Enum):
    READY = "ready"
    GUARDED = "guarded"


@dataclass(frozen=True)
class RouteRequest:
    capability_key: str
    model_key: str
    currency: str
    billable_unit: str


@dataclass(frozen=True)
class RouteCandidate:
    provider_key: str
    adapter_key: str
    capability_key: str
    model_key: str
    currency: str
    billable_unit: str
    cost_minor: int | None
    catalog_version: str
    source_ref: str
    approved: bool
    fallback_eligible: bool


@dataclass(frozen=True)
class RouteCatalog:
    version: str
    approval_status: CatalogApproval
    candidates: tuple[RouteCandidate, ...]

    def __post_init__(self) -> None:
        approval_status = self.approval_status
        if type(approval_status) is str:
            try:
                approval_status = CatalogApproval(approval_status)
            except ValueError:
                approval_status = CatalogApproval.UNCONFIGURED
        elif not isinstance(approval_status, CatalogApproval):
            approval_status = CatalogApproval.UNCONFIGURED

        object.__setattr__(self, "approval_status", approval_status)
        candidates = self.candidates if type(self.candidates) in (tuple, list) else ()
        object.__setattr__(self, "candidates", tuple(candidates))


@dataclass(frozen=True)
class RouteDecision:
    status: RouteStatus
    catalog_version: str
    primary: RouteCandidate | None
    fallbacks: tuple[RouteCandidate, ...]
    retail_price_minor: int | None
    currency: str | None
    guard_reason: str | None

    @classmethod
    def guarded(cls, catalog_version: str, reason: str) -> RouteDecision:
        return cls(RouteStatus.GUARDED, catalog_version, None, (), None, None, reason)

    @classmethod
    def ready(
        cls,
        catalog_version: str,
        primary: RouteCandidate,
        fallbacks: tuple[RouteCandidate, ...],
        retail_price_minor: int,
    ) -> RouteDecision:
        return cls(RouteStatus.READY, catalog_version, primary, fallbacks, retail_price_minor, primary.currency, None)


def unconfigured_catalog() -> RouteCatalog:
    """Return the intentionally empty default catalog until costs are approved."""
    return RouteCatalog("unconfigured", CatalogApproval.UNCONFIGURED, ())


def resolve_route(request: RouteRequest, catalog: RouteCatalog) -> RouteDecision:
    """Select the cheapest exact approved route, or fail closed without a quote."""
    if catalog.approval_status is not CatalogApproval.CANONICAL_APPROVED:
        return RouteDecision.guarded(catalog.version, "ROUTE_CATALOG_NOT_APPROVED")
    if not _has_nonempty_strings(
        request.capability_key,
        request.model_key,
        request.currency,
        request.billable_unit,
        catalog.version,
    ):
        return RouteDecision.guarded(catalog.version, "ROUTE_NO_VERIFIED_COST")

    eligible = sorted(
        (
            candidate
            for candidate in catalog.candidates
            if _is_eligible(candidate, request, catalog.version)
        ),
        key=lambda candidate: (candidate.cost_minor, candidate.provider_key, candidate.adapter_key),
    )
    if not eligible:
        return RouteDecision.guarded(catalog.version, "ROUTE_NO_VERIFIED_COST")

    primary = eligible[0]
    fallbacks = tuple(candidate for candidate in eligible[1:] if candidate.fallback_eligible is True)
    selectable = (primary, *fallbacks)
    retail_price_minor = math.ceil(max(candidate.cost_minor for candidate in selectable) * 3)
    return RouteDecision.ready(catalog.version, primary, fallbacks, retail_price_minor)


def _is_eligible(candidate: RouteCandidate, request: RouteRequest, catalog_version: str) -> bool:
    return (
        type(candidate) is RouteCandidate
        and candidate.approved is True
        and candidate.cost_minor is not None
        and type(candidate.cost_minor) is int
        and candidate.cost_minor > 0
        and candidate.catalog_version == catalog_version
        and _has_nonempty_strings(
            candidate.provider_key,
            candidate.adapter_key,
            candidate.capability_key,
            candidate.model_key,
            candidate.currency,
            candidate.billable_unit,
            candidate.catalog_version,
            candidate.source_ref,
        )
        and candidate.capability_key == request.capability_key
        and candidate.model_key == request.model_key
        and candidate.currency == request.currency
        and candidate.billable_unit == request.billable_unit
    )


def _has_nonempty_strings(*values: str) -> bool:
    return all(type(value) is str and bool(value.strip()) for value in values)
