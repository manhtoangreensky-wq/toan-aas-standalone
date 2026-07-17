"""Static boundary checks for the Admin domain navigation centers."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_admin_registry_and_portal_expose_the_first_class_domain_centers() -> None:
    registry = (ROOT / "copyfast_registry.py").read_text(encoding="utf-8")
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")

    for key, route in (
        ("admin_growth", "/admin/growth"),
        ("admin_finance", "/admin/finance"),
        ("admin_trends", "/admin/trends"),
    ):
        assert f'WebFeature("{key}"' in registry
        assert route in registry
        assert f'adminPage("{route}"' in portal
    assert "const ADMIN_DOMAIN_CENTERS = Object.freeze" in portal
    assert "function renderAdminDomain(page, context)" in portal
    assert 'case "admin-domain": return renderAdminDomain(page, context);' in portal
    assert ".portal-admin-domain-grid" in css


def test_domain_centers_remain_navigation_only_and_do_not_add_a_bridge_adapter() -> None:
    api = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
    integration = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
    portal = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "migration" / "ADMIN_DOMAIN_CENTERS_CONTRACT.md").read_text(encoding="utf-8")

    for module in ("growth", "finance", "trends", "publishing"):
        assert f'"{module}"' not in api[api.index("ADMIN_BRIDGE_MODULES"):api.index("ADMIN_BRIDGE_MODULE_ALIASES")]
        assert f'"{module}"' not in integration[integration.index("const ADMIN_CANONICAL_READ_MODULES"):integration.index("const ADMIN_MODULE_NAME_PATTERN")]
    center = portal[portal.index("const ADMIN_DOMAIN_CENTERS"):portal.index("function renderAdmin(page, context)")]
    assert "fetch(" not in center
    assert "api(" not in center
    assert "data-portal-action" not in center
    assert "provider" in center.lower()
    assert "do not call providers, channel APIs, scrapers, PayOS" in contract
    assert "do not claim" in contract
