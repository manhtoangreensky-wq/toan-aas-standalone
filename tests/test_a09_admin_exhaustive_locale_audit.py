"""Executable integrity contracts for the exhaustive A09 Admin audit ledger."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
REPORT = ROOT / "reports" / "audit" / "A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.json"


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _source_route_sets() -> tuple[set[str], set[str], set[str]]:
    registry_source = _between(PORTAL, "const ADMIN_ERP_ROUTE_I18N", "function adminErpGroupText")
    registry = set(re.findall(r'"(/admin[^"]*)":\s*"adminErpNavigation\.route\.', registry_source))
    page_routes = set(re.findall(r'adminPage\("(/admin[^"]*)"', PORTAL))
    special_routes = {"/admin/content-handoffs", "/admin/crm/leads"}
    return registry, page_routes, registry | page_routes | special_routes


def test_audit_report_covers_exact_page_server_route_universe() -> None:
    registry, page_routes, universe = _source_route_sets()
    assert len(registry) in {49, 50}
    assert len(page_routes) == 48
    assert page_routes - registry in ({"/admin/export"}, set())
    assert len(universe) == 50

    assert REPORT.is_file(), "The deterministic A09 Admin audit report has not been created"
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    rows = data["routes"]
    assert len(rows) == 50
    assert {row["route"] for row in rows} == universe
    assert len({row["route"] for row in rows}) == len(rows)
    for row in rows:
        assert row["authority"] in {"support_staff", "local_web_admin", "canonical_admin"}
        assert row["layout"]
        assert row["renderer_family"]
        assert isinstance(row["aliases"], list)


def test_audit_ledger_coverage_and_direct_locale_ownership() -> None:
    assert REPORT.is_file(), "The deterministic A09 Admin audit report has not been created"
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    rows = data["routes"]
    summary = data["summary"]

    coverage_counts = summary["coverage_counts"]
    assert sum(coverage_counts.values()) == 50

    meta_ownership = summary["metadata_ownership"]
    assert meta_ownership["both_owned"] + meta_ownership["gap_count"] == 50
    assert meta_ownership["both_owned"] == 26
    assert meta_ownership["gap_count"] == 24

    for row in rows:
        assert row["coverage"] in {"FULL", "PARTIAL", "NONE"}
        assert isinstance(row["title_owned"], bool)
        assert isinstance(row["description_owned"], bool)
        if row["coverage"] in {"FULL", "PARTIAL"}:
            assert len(row["tests"]) > 0, f"Route {row['route']} marked {row['coverage']} but has no test evidence"
            for test_ref in row["tests"]:
                file_part = test_ref.split("::")[0]
                assert (ROOT / file_part).is_file(), f"Test file {file_part} must exist"


def test_audit_report_consistency_and_next_spec() -> None:
    md_file = ROOT / "reports" / "audit" / "A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.md"
    assert md_file.is_file(), "A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.md must exist"
    md_text = md_file.read_text(encoding="utf-8")

    data = json.loads(REPORT.read_text(encoding="utf-8"))
    summary = data["summary"]

    assert f"Tổng số route Admin chính thức**: `{data['total_routes']}`" in md_text
    assert f"`{summary['metadata_ownership']['both_owned']}/50`" in md_text
    assert f"`{summary['metadata_ownership']['gap_count']}/50`" in md_text

    next_spec = data.get("next_spec")
    assert next_spec is not None
    assert next_spec["spec_id"] == "A09-ADMIN-LOCALE-GAP-24-COMPLETION-001"
    assert next_spec["gap_route_count"] == 24
    assert next_spec["spec_id"] in md_text


