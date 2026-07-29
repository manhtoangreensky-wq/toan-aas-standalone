"""Focused boundaries for the finite Admin Finance Compliance readiness handoff."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "migration" / "audit_bot_to_web.py"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_bot_to_web_finance_compliance", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finance_compliance_is_one_exact_readiness_handoff_and_not_a_finance_adapter() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {"menu|finance_compliance"}

    assert set(audit.FINANCE_COMPLIANCE_READINESS_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS) == expected
    descriptor = audit.FINANCE_COMPLIANCE_READINESS_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS["menu|finance_compliance"]
    mapped = audit._map_callback("menu|finance_compliance", "callback_data", {"file": "bot.py", "line": 1}, routes)

    assert mapped["target"] == "/admin/finance/tax-readiness"
    assert mapped["classification"] == "admin"
    assert mapped["status"] == "NAVIGATION_ONLY"
    assert mapped["resolution"] == "reviewed_finance_compliance_readiness_fresh_web_navigation"
    assert mapped["source_dispositions"] == descriptor["source_dispositions"]
    assert mapped["finance_compliance_readiness_feature_key"] == "admin_tax_readiness"
    assert mapped["finance_compliance_readiness_authority"] == "SIGNED_CANONICAL_ADMIN_READ"
    assert mapped["finance_compliance_readiness_launch_mode"] == "WEB_NAVIGATION"
    for disposition in (
        "BOT_ADMIN_ONLY",
        "BOT_FINANCE_COMPLIANCE_STATUS_NOT_REPLAYED",
        "BOT_FINANCE_COMPLIANCE_NOTES_NOT_REPLAYED",
        "NO_CANONICAL_FINANCE_DATA_TRANSFER",
        "NO_TAX_ESTIMATE_OR_FINANCIAL_CALCULATION",
        "NO_REPORT_EXPORT_OR_FILE_DELIVERY",
        "NO_TAX_PROFILE_OR_COMPLIANCE_MUTATION",
        "NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
        "NO_RUNTIME_CLAIM",
    ):
        assert disposition in mapped["source_dispositions"]


def test_finance_compliance_variants_and_update_never_inherit_the_guidance_route() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    for token in (
        "MENU|FINANCE_COMPLIANCE",
        "menu|finance_compliance_update",
        "menu|finance_compliance_future",
        "menu|finance_compliance|future",
        "menu|finance_compliance_*",
        "menu|tax_config",
        "menu|finance_overview",
    ):
        mapped = audit._map_callback(token, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] != "/admin/finance/tax-readiness" or token == "menu|finance_overview"
        assert mapped["resolution"] != "reviewed_finance_compliance_readiness_fresh_web_navigation"

    update = audit._map_callback("menu|finance_compliance_update", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert update["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert update["classification"] == "admin"
    assert "FINANCE_COMPLIANCE" in update["target"]


def test_finance_compliance_contract_is_private_to_the_auditor_and_documents_no_transfer() -> None:
    audit_source = _read("scripts/migration/audit_bot_to_web.py")
    contract = _read("docs/migration/FINANCE_COMPLIANCE_READINESS_CALLBACK_CONTRACT.md")
    catalog = _read("docs/migration/NON_VIDEO_MENU_NAVIGATION_CATALOG.md")

    for declaration in (
        "FINANCE_COMPLIANCE_READINESS_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS",
        '"FINANCE_COMPLIANCE_READINESS_CALLBACK_CONTRACT.md"',
        "reviewed_finance_compliance_readiness_fresh_web_navigation",
        "BOT_FINANCE_COMPLIANCE_STATUS_NOT_REPLAYED",
        "BOT_FINANCE_COMPLIANCE_NOTES_NOT_REPLAYED",
        "NO_TAX_PROFILE_OR_COMPLIANCE_MUTATION",
    ):
        assert declaration in audit_source

    registry = audit_source[
        audit_source.index("FINANCE_COMPLIANCE_READINESS_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS"):
        audit_source.index("FINANCE_COMPLIANCE_CANONICAL_SOURCE_REVIEW_BASE_DISPOSITIONS")
    ]
    assert '"menu|finance_compliance": {' in registry
    for excluded in (
        "menu|finance_compliance_update",
        "menu|finance_compliance_future",
        "menu|finance_compliance_*",
    ):
        assert f'"{excluded}":' not in registry

    assert "does not read the Bot compliance status" in contract
    assert "does not create, update, or mutate a compliance note" in contract
    assert "Case variants, suffixes, and `menu|finance_compliance_update`" in contract
    assert "`menu|finance_compliance`" in catalog
    assert "| `menu|finance_compliance_update` |" not in catalog

    from copyfast_registry import menu_capability_catalog

    serialized_catalog = json.dumps(menu_capability_catalog(), ensure_ascii=False)
    assert "menu|finance_compliance" not in serialized_catalog


def test_non_video_catalog_exempts_only_the_exact_finance_compliance_literal() -> None:
    catalog = _read("docs/migration/NON_VIDEO_MENU_NAVIGATION_CATALOG.md")
    normalized_catalog = " ".join(catalog.split())

    assert "the exact `menu|finance_compliance` literal has its dedicated Finance Compliance readiness contract" in normalized_catalog
    assert "`finance_compliance*`" not in catalog


def test_sql_database_extraction_excludes_finance_compliance_prose_but_keeps_real_tables(tmp_path: Path) -> None:
    audit = _load_audit_module()
    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE compliance_audit_events (id INTEGER);", encoding="utf-8")

    fixture_tables = {record["table"] for record in audit._extract_database_references(tmp_path, [schema])}
    source_tables = {
        record["table"]
        for record in audit._extract_database_references(ROOT, [SCRIPT_PATH])
    }

    assert fixture_tables == {"compliance_audit_events"}
    assert source_tables.isdisjoint({"literal", "branch", "mutation"})


def test_static_audit_generates_the_finite_finance_compliance_contract(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    report_dir = tmp_path / "reports"
    docs_dir = tmp_path / "docs"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '\n'.join(
            (
                'InlineKeyboardButton("Compliance", callback_data="menu|finance_compliance")',
                'InlineKeyboardButton("Update", callback_data="menu|finance_compliance_update")',
            )
        ),
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        """
app = FastAPI()
@app.get('/admin/finance/tax-readiness')
async def readiness():
    return {}
""",
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", report_dir, docs_dir)
    mappings = {item["source"]: item for item in result["parity_gap"]["callback_mappings"]}
    assert mappings["menu|finance_compliance"]["status"] == "NAVIGATION_ONLY"
    assert mappings["menu|finance_compliance"]["target"] == "/admin/finance/tax-readiness"
    assert mappings["menu|finance_compliance_update"]["target"] == "CANONICAL_FINANCE_COMPLIANCE_SOURCE_REVIEW_REQUIRED"
    assert mappings["menu|finance_compliance_update"]["status"] == "NEEDS_FEATURE_DISPOSITION"

    generated_contract = (docs_dir / "FINANCE_COMPLIANCE_READINESS_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "menu|finance_compliance" in generated_contract
    assert "CANONICAL_FINANCE_COMPLIANCE_SOURCE_REVIEW_REQUIRED" in generated_contract
