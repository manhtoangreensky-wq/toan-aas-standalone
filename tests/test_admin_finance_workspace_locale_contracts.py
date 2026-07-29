"""Contracts for fixed, signed Admin Finance workspace locale chrome.

The locale preference applies only to Portal-owned wording. It must not turn
server data or a Finance navigation page into a browser-owned financial model.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end():])
    return source[match.start():match.end() + following.start() if following else len(source)]


def test_admin_finance_workspace_fixed_copy_uses_reviewed_locale_catalogue() -> None:
    i18n = _read("static/portal/portal-i18n.js")
    portal = _read("static/portal/portal.js")

    assert "const ADMIN_FINANCE_WORKSPACE_MESSAGES" in i18n
    for key in (
        "adminFinance.hub.kicker",
        "adminFinance.stream.payments.title",
        "adminFinance.tax.checkpoint.source.title",
        "adminFinance.tax.boundary.noLedger.title",
    ):
        assert f'"{key}"' in i18n

    assert "function adminFinanceText(key, fallback, params)" in portal
    assert "uiText(`adminFinance.${key}`, fallback, params)" in portal
    assert "function adminFinanceDomain()" in portal

    finance_domain = _function_source(portal, "adminFinanceDomain")
    tax_readiness = _function_source(portal, "renderAdminTaxReadiness")
    admin_domain = _function_source(portal, "renderAdminDomain")

    assert "adminFinanceText(" in finance_domain
    assert "adminFinanceText(" in tax_readiness
    assert "adminFinanceDomain()" in admin_domain

    # The static translation surface must not become a network client, a
    # bridge, browser persistence or a second financial action path.
    for source in (finance_domain, tax_readiness):
        for forbidden in ("fetch(", "/internal/", "localStorage", "sessionStorage", "translate("):
            assert forbidden not in source
    assert "safeText(data.message)" in admin_domain
    assert "serverAuthorizesAdminRoute(context, stream.route)" in admin_domain
    assert "renderNotes(page)" in tax_readiness

