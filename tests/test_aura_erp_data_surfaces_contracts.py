from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    return source[start_index : source.index(end, start_index + len(start))]


def _run_admin_number_harness() -> dict[str, str]:
    node = shutil.which("node")
    assert node, "Node.js is required for the portal behavior harness"
    script = r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");
const xuStart = source.indexOf("function canonicalXu");
const xuEnd = source.indexOf("function jobCost", xuStart);
const start = source.indexOf("function adminNumericValue");
const end = source.indexOf("function adminJobActions", start);
if (xuStart < 0 || xuEnd < 0 || start < 0 || end < 0) throw new Error("Numeric helper boundary missing");
const context = {};
vm.createContext(context);
vm.runInContext("function localizedNumber(value) { return String(value); }\n" + source.slice(xuStart, xuEnd) + source.slice(start, end), context);
if (typeof context.adminNumber !== "function" || typeof context.canonicalXu !== "function") throw new Error("Numeric formatter is not exposed in harness");
process.stdout.write(JSON.stringify({
  zero: context.adminNumber(0, " đ"),
  null: context.adminNumber(null, " đ"),
  blank: context.adminNumber("   ", " đ"),
  text: context.adminNumber("not-a-number", " đ"),
  canonicalZero: context.canonicalXu(0),
  canonicalNull: context.canonicalXu(null),
  canonicalBlank: context.canonicalXu("   "),
  canonicalText: context.canonicalXu("not-a-number")
}));
"""
    result = subprocess.run(
        [node, "-e", script, str(ROOT / "static" / "portal" / "portal.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_admin_erp_surface_exposes_truthful_source_backed_toolbar() -> None:
    assert "function renderAdminDataSurface(module, data, content)" in PORTAL
    surface = _section(PORTAL, "function renderAdminDataSurface", "function adminJobActions")
    for marker in (
        'data-portal-admin-data-surface',
        'data-portal-admin-data-count',
        'data-portal-admin-data-scope',
        'class="portal-admin-data-toolbar"',
        "source.compatibility_guarded !== true && Array.isArray(source.items)",
        "source.items.length",
        "source.compatibility_guarded === true",
    ):
        assert marker in surface
    for forbidden in ("api(", "fetch(", "dispatchAction(", "merge(", "localStorage", "sessionStorage", "URLSearchParams"):
        assert forbidden not in surface
    assert "data-portal-admin-table-filter" not in surface
    assert "data-portal-action" not in surface

    renderer = _section(PORTAL, "function renderAdminDataTable", "// These are first-class navigation centers")
    assert 'if (module === "audit" && context.adminAudit' in renderer
    assert "const surface = (content) => renderAdminDataSurface(module, data, content);" in renderer
    assert renderer.count("surface(") >= 6
    assert "ticketStatusCell(item)" in renderer
    assert "const incidentCount = data.compatibility_guarded !== true && Array.isArray(data.items)" in renderer
    assert "const rows = data.compatibility_guarded !== true && Array.isArray(data.items) ? data.items : [];" in renderer


def test_admin_erp_number_formatter_preserves_zero_and_rejects_missing_values() -> None:
    assert "function adminNumericValue(value)" in PORTAL
    assert _run_admin_number_harness() == {
        "zero": "0 đ",
        "null": "— đ",
        "blank": "— đ",
        "text": "— đ",
        "canonicalZero": "0 Xu",
        "canonicalNull": "—",
        "canonicalBlank": "—",
        "canonicalText": "—",
    }


def test_admin_erp_surface_fixed_chrome_is_localized_in_all_supported_locales() -> None:
    for key in (
        "adminDataSurface.kicker",
        "adminDataSurface.recordCount",
        "adminDataSurface.serverScope",
        "adminDataSurface.guardedScope",
        "adminDataSurface.unavailableCount",
        "adminDataSurface.unavailableScope",
    ):
        assert I18N.count(f'"{key}"') == 3
    state_i18n = _section(PORTAL, "const STATE_I18N_KEYS", "function stateLabel")
    assert 'unavailable: "states.unavailable"' in state_i18n
    assert I18N.count('"states.unavailable"') == 3


def test_generic_admin_erp_chrome_uses_closed_reviewed_locale_copy() -> None:
    """Generic Admin data screens translate fixed chrome, never server data."""

    generic_keys = sorted(set(re.findall(r'adminGenericText\("([^"]+)"', PORTAL)))
    assert len(generic_keys) >= 100
    for key in generic_keys:
        assert I18N.count(f'"adminGeneric.{key}"') == 3

    assert "function adminGenericText(key, fallback, params)" in PORTAL
    assert "uiText(`adminGeneric.${key}`, fallback, params)" in PORTAL
    assert "function adminGenericModuleLabel(module)" in PORTAL

    actions = _section(PORTAL, "function adminJobActions", "function renderAdminFreezeControls")
    maintenance = _section(PORTAL, "function renderAdminFreezeControls", "function adminAuditListing")
    audit_pagination = _section(PORTAL, "function renderAdminAuditPagination", "function renderAdminAuditExplorer")
    audit = _section(PORTAL, "function renderAdminAuditExplorer", "function renderAdminDataTable")
    tables = _section(PORTAL, "function renderAdminDataTable", "// These are first-class navigation centers")
    admin = _section(PORTAL, "function renderAdmin(page, context)", "const BOT_COMPANION_COMMAND_PATTERN")
    for source in (actions, maintenance, audit_pagination, audit, tables, admin):
        assert "adminGenericText(" in source
        for forbidden in ("fetch(", "localStorage", "sessionStorage", "XMLHttpRequest"):
            assert forbidden.lower() not in source.lower()

    assert "safeText(data.message)" in admin
    assert "recordId: String(page.recordId)" in admin
    assert 'safeText(adminGenericText("record.body"' in admin
    assert "safeText(item.user_id" in tables
    assert "safeText(item.username" in tables
    assert "adminNumber(item.amount_vnd" in tables
    assert "safeText(event.created_at" in audit


def test_generic_admin_erp_audit_filters_and_module_headings_stay_localized() -> None:
    """Dynamic label lookup must not leave reviewed Admin chrome in Vietnamese."""

    audit_options = _section(PORTAL, "const ADMIN_AUDIT_CATEGORY_OPTIONS", "const ADMIN_AUDIT_CATEGORY_KEYS")
    for value, key in (
        ("all", "audit.filter.option.all"),
        ("auth", "audit.filter.option.auth"),
        ("support", "audit.filter.option.support"),
        ("operations", "audit.filter.option.operations"),
        ("workspace", "audit.filter.option.workspace"),
        ("content", "audit.filter.option.content"),
        ("asset", "audit.filter.option.asset"),
        ("admin", "audit.filter.option.admin"),
        ("security", "audit.filter.option.security"),
    ):
        assert f'["{value}", "{key}"]' in audit_options
        assert I18N.count(f'"adminGeneric.{key}"') == 3

    audit_normalizer = _section(PORTAL, "function normalizeAdminAuditProjection", "function normalizeAdminAuditListing")
    for vietnamese_default in ("Sự kiện Web", "Sự kiện đã redaction", "Đã ghi nhận trạng thái"):
        assert vietnamese_default not in audit_normalizer

    audit = _section(PORTAL, "function renderAdminAuditExplorer", "function renderAdminDataTable")
    assert "ADMIN_AUDIT_CATEGORY_OPTIONS.map(([value, labelKey])" in audit
    assert "adminGenericText(labelKey, value)" in audit

    module_labels = _section(PORTAL, "const ADMIN_GENERIC_MODULE_LABEL_KEYS", "function adminGenericModuleLabel")
    for module, key in (
        ("overview", "module.overview"),
        ("packages", "module.packages"),
        ("campaigns", "module.campaigns"),
        ("calendar", "module.calendar"),
        ("approvals", "module.approvals"),
        ("analytics", "module.analytics"),
        ("reports", "module.reports"),
        ("export", "module.export"),
        ("system", "module.system"),
        ("backups", "module.backups"),
    ):
        assert f'{module}: "{key}"' in module_labels or f'"{module}": "{key}"' in module_labels
        assert I18N.count(f'"adminGeneric.{key}"') == 3


def test_admin_erp_surface_uses_aura_tokens_and_shared_failure_semantics() -> None:
    marker = "/* Aura ERP data surfaces — truthful table read model. */"
    assert marker in THEME
    harmony = THEME[THEME.index(marker) :]
    for selector in (
        ".portal-page .portal-admin-data-surface {",
        ".portal-page .portal-admin-data-toolbar {",
        ".portal-page .portal-admin-data-toolbar strong {",
        ".portal-page .portal-admin-data-surface .portal-data-table-wrap {",
        ".portal-page .portal-admin-data-surface .portal-badge[data-status=\"failed_no_charge\"] {",
        "@media (min-width: 921px)",
    ):
        assert selector in harmony
    for token in (
        "var(--portal-space-3)",
        "var(--portal-radius-md)",
        "var(--portal-elevation-1)",
        "var(--portal-surface-strong)",
        "var(--portal-surface-light)",
        "var(--portal-border)",
        "var(--portal-ink)",
        "var(--portal-muted)",
        "var(--portal-context)",
        "var(--portal-danger)",
    ):
        assert token in harmony
    assert "overflow-x: auto;" in harmony
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", harmony)
    assert "linear-gradient" not in harmony


def test_admin_erp_surface_keeps_mobile_sticky_identifiers_readable() -> None:
    """The generic mobile sticky-cell rule must not reduce IDs to one glyph per line."""
    marker = "/* Aura ERP data surfaces — truthful table read model. */"
    harmony = THEME[THEME.index(marker) :]
    mobile_selector = (
        ".portal-page .portal-admin-data-surface .portal-data-table th:first-child,\n"
        "  .portal-page .portal-admin-data-surface .portal-data-table tbody td:first-child:not(.portal-empty-cell) {"
    )
    assert mobile_selector in harmony
    mobile_rule = harmony[harmony.index(mobile_selector) :]
    mobile_rule = mobile_rule[: mobile_rule.index("}\n") + 1]
    assert "min-width: 10rem;" in mobile_rule
    assert "overflow-wrap: break-word;" in mobile_rule
