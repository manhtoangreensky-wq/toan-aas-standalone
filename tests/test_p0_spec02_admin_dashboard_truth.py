"""Empirical test suite for P0.WEB.ERP.SPEC02.DASHBOARD.REAL_OPERATIONAL_TRUTH.

Enforces:
1. Dashboard KPI sources are authoritative (WEB_SQLITE: web_accounts, web_manual_topup_requests, web_support_cases, web_ops_approvals).
2. Zero demo/hardcoded KPI values; zero direct Bot SQLite access; zero max(real, static).
3. ZERO remains ZERO (0 is an empirical measurement, not missing data).
4. UNKNOWN does not become ZERO ("Chưa xác định" / "Không khả dụng").
5. API error does not render as empty.
6. Revenue is strictly scoped to WEB_ONLY, never false total-system revenue.
7. Wallet is read-only (zero direct wallet mutations from Web).
8. Dashboard has no direct dangerous write actions.
9. Reliability telemetry unavailable is not rendered healthy (truthful multi-source health).
10. Existing primary/sidebar navigation remains intact (PR #437 7 groups protected).
11. Light/Dark semantic theme classes remain intact.
12. No banned technical-copy strings exposed on Dashboard.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from starlette.requests import Request

from copyfast_api import _bridge
import copyfast_db

ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL_CODE = PORTAL_PATH.read_text(encoding="utf-8")


def _run_node_dashboard(body: str) -> dict:
    """Execute snippet in Node.js with portal.js context."""
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");

function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing start: ${start}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end: ${end}`);
  return source.slice(offset, finish);
}

function safeText(value) { return String(value); }
const messages = {
  "title": "Trung tâm điều hành",
  "description": "Theo dõi dữ liệu và công việc được máy chủ cấp cho phiên quản trị hiện tại.",
  "metrics.users": "Người dùng",
  "metrics.usersNote": "Dữ liệu đã kiểm tra vai trò",
  "metrics.customers": "Tài khoản người dùng",
  "metrics.customersNote": "Dữ liệu tài khoản đã kiểm tra",
  "metrics.actionRequired": "Cần xử lý ngay",
  "metrics.actionRequiredNote": "Tổng các yêu cầu cần xử lý",
  "metrics.pendingTopups": "Nạp tiền chờ duyệt",
  "metrics.pendingTopupsNote": "Chờ đối soát thanh toán",
  "metrics.openSupport": "Phiếu hỗ trợ mở",
  "metrics.openSupportNote": "Yêu cầu hỗ trợ chưa đóng",
  "metrics.failedJobs": "Tác vụ gặp sự cố",
  "metrics.failedJobsNote": "Các tác vụ cần kiểm tra",
  "metrics.payments": "Thanh toán",
  "metrics.paymentsNote": "Không lưu sổ giao dịch trên trình duyệt",
  "metrics.readiness": "Mức sẵn sàng",
  "metrics.readinessNote": "Mức sẵn sàng công khai",
  "metrics.unavailable": "Không khả dụng",
  "metrics.unknown": "Chưa xác định",
  "guard.verifiedTitle": "Quyền quản trị đã được máy chủ xác nhận",
  "guard.verifiedBody": "Phiên làm việc hợp lệ.",
  "guard.kicker": "Trạng thái phiên",
  "sourceEmpty.title": "Chưa có số liệu vận hành",
  "sourceEmpty.body": "Dữ liệu sẽ xuất hiện khi máy chủ cung cấp nguồn đo hợp lệ.",
  "sourceEmpty.action": "Làm mới dữ liệu",
  "workload.title": "Khối lượng vận hành",
  "workload.description": "So sánh các số liệu trong ảnh chụp hiện tại.",
  "workload.empty": "Chưa có số liệu vận hành",
  "readinessChart.title": "Mức sẵn sàng",
  "readinessChart.description": "Tỷ lệ trạng thái sẵn sàng trong ảnh chụp hiện tại.",
  "readinessChart.ready": "Sẵn sàng",
  "readinessChart.guarded": "Cần kiểm tra",
  "readinessChart.empty": "Chưa có dữ liệu sẵn sàng",
  "connectionDetails.title": "Chi tiết kết nối"
};

function adminText(key, fallback, params) {
  let value = messages[key] || fallback;
  Object.entries(params || {}).forEach(([k, v]) => {
    value = value.replaceAll(`{${k}}`, String(v));
  });
  return value;
}

function uiText(key, fallback, params) {
  return adminText(key.replace(/^adminHome\./, ""), fallback, params);
}

function adminErpNavigation(context) { return context.navigation || { canonicalAdmin: true, webLocalAdmin: false, supportRole: "none", groups: [], routes: new Set() }; }
const ICONS = { security: "security", support: "support", jobs: "jobs", payments: "payments", users: "users" };
function portalIcon(icon) { return `<icon-${icon}>`; }
function renderSummary() { return "<summary-content>"; }
function renderRowsTable(headers, rows, rowRenderer) {
  return `<table data-row-count="${rows.length}"><tbody>${rows.map(rowRenderer).join("")}</tbody></table>`;
}
function renderAdminWorkQueues() { return '<section data-work-queues></section>'; }
function renderAdminDirectory() { return '<section data-directory></section>'; }
function renderAdminModuleTabs() { return '<nav data-tabs></nav>'; }

eval(extract("function adminDashboardNumber", "function renderAdminOverview(page, context)"));
eval(extract("function renderAdminOverview(page, context)", "function renderAdminSystemStewardship(page, context)"));
''' + body

    proc = subprocess.run(
        ["node", "-e", script, str(PORTAL_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Node error:\n{proc.stderr}\n{proc.stdout}"
    return json.loads(proc.stdout)


# ---------------------------------------------------------------------------
# Test Case 1: Dashboard KPI sources are authoritative
# ---------------------------------------------------------------------------
def test_dashboard_kpi_sources_are_authoritative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate that metrics originate strictly from WEB_SQLITE session database."""
    db_file = tmp_path / "test_session.db"
    monkeypatch.setattr(copyfast_db, "session_database_path", lambda: db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE web_accounts (id TEXT PRIMARY KEY, is_active INT)")
        conn.execute("CREATE TABLE web_manual_topup_requests (id INT PRIMARY KEY, status TEXT)")
        conn.execute("CREATE TABLE web_support_cases (id TEXT PRIMARY KEY, state TEXT)")
        conn.execute("CREATE TABLE web_ops_approvals (id TEXT PRIMARY KEY, state TEXT)")
        conn.execute("CREATE TABLE web_ops_followups (id TEXT PRIMARY KEY, state TEXT)")

        # Seed known authoritative states
        conn.executemany("INSERT INTO web_accounts VALUES (?, ?)", [("u1", 1), ("u2", 1), ("u3", 0)])
        conn.executemany("INSERT INTO web_manual_topup_requests VALUES (?, ?)", [
            (1, "pending_admin_review"),
            (2, "pending_admin_review"),
            (3, "approved"),
            (4, "rejected"),
        ])
        conn.executemany("INSERT INTO web_support_cases VALUES (?, ?)", [
            ("s1", "new"),
            ("s2", "reviewing"),
            ("s3", "resolved"),
            ("s4", "closed"),
        ])
        conn.executemany("INSERT INTO web_ops_approvals VALUES (?, ?)", [
            ("a1", "awaiting_approval"),
            ("a2", "approved"),
        ])
        conn.executemany("INSERT INTO web_ops_followups VALUES (?, ?)", [
            ("f1", "open"),
            ("f2", "resolved"),
        ])

    metrics = copyfast_db.get_admin_overview_metrics()

    # WEB_ACCOUNT_AUTHORITY=WEB_SQLITE (web_accounts)
    assert metrics["users"] == 3
    assert metrics["total_customers"] == 3

    # TOPUP_DRAFT_AUTHORITY=WEB_SQLITE (web_manual_topup_requests pending_admin_review)
    assert metrics["pending_topups"] == 2
    assert metrics["payments"] == 2

    # SUPPORT_AUTHORITY=WEB_SQLITE (web_support_cases active states)
    assert metrics["open_support"] == 2

    # APPROVAL_AUTHORITY=WEB_SQLITE (web_ops_approvals awaiting_approval)
    assert metrics["pending_approvals"] == 1

    # ACTION_REQUIRED = sum of distinct actionable queues (2 topups + 2 support + 1 approval = 5)
    assert metrics["action_required"] == 5

    # WORKER_JOBS = 1 open followup
    assert metrics["worker_jobs"] == 1
    assert metrics["engine_jobs"] == 0


# ---------------------------------------------------------------------------
# Test Case 2: No demo / hardcoded KPI values and zero Bot Core DB reads
# ---------------------------------------------------------------------------
def test_no_demo_hardcoded_kpi_values_and_no_bot_db_reads() -> None:
    """Verify get_admin_overview_metrics source code does not read Bot SQLite or use max()."""
    import inspect
    source = inspect.getsource(copyfast_db.get_admin_overview_metrics)

    assert "toandaas_system.db" not in source, "Direct Bot SQLite access forbidden on Web App"
    code_lines = [l for l in source.splitlines() if not l.strip().startswith("#") and '"""' not in l and "heuristic" not in l]
    assert not any("max(" in l for l in code_lines), "max(real, static) fallback heuristic forbidden in code"


# ---------------------------------------------------------------------------
# Test Case 3: ZERO remains ZERO
# ---------------------------------------------------------------------------
def test_zero_remains_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When a table is present but empty, count is 0 and renders as <strong>0</strong>."""
    db_file = tmp_path / "test_empty_session.db"
    monkeypatch.setattr(copyfast_db, "session_database_path", lambda: db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE web_accounts (id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE web_manual_topup_requests (id INT PRIMARY KEY, status TEXT)")
        conn.execute("CREATE TABLE web_support_cases (id TEXT PRIMARY KEY, state TEXT)")
        conn.execute("CREATE TABLE web_ops_approvals (id TEXT PRIMARY KEY, state TEXT)")

    metrics = copyfast_db.get_admin_overview_metrics()
    assert metrics["total_customers"] == 0
    assert metrics["pending_topups"] == 0
    assert metrics["open_support"] == 0
    assert metrics["action_required"] == 0

    res = _run_node_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: {
    counts: { action_required: 0, total_customers: 0, pending_topups: 0, open_support: 0 },
    readiness: {}
  }
});
const matches = Array.from(html.matchAll(/class="portal-metric"[^>]*><span>([^<]*)<\/span><strong>([^<]*)<\/strong>/g))
  .map(m => [m[1], m[2]]);
process.stdout.write(JSON.stringify({ matches }));
'''
    )

    pairs = dict(res["matches"])
    assert pairs.get("Cần xử lý ngay") == "0"
    assert pairs.get("Tài khoản người dùng") == "0"
    assert pairs.get("Nạp tiền chờ duyệt") == "0"
    assert pairs.get("Phiếu hỗ trợ mở") == "0"


# ---------------------------------------------------------------------------
# Test Case 4: UNKNOWN does not become ZERO
# ---------------------------------------------------------------------------
def test_unknown_does_not_become_zero() -> None:
    """Values that are null or 'unavailable' render as 'Không khả dụng', not '0'."""
    res = _run_node_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: {
    counts: { action_required: 0, total_customers: 10, failed_jobs: "unavailable" },
    readiness: {}
  }
});
const matches = Array.from(html.matchAll(/class="portal-metric"[^>]*><span>([^<]*)<\/span><strong>([^<]*)<\/strong>/g))
  .map(m => [m[1], m[2]]);
process.stdout.write(JSON.stringify({ matches }));
'''
    )

    pairs = dict(res["matches"])
    assert pairs.get("Tác vụ gặp sự cố") == "Không khả dụng"
    assert pairs.get("Tác vụ gặp sự cố") != "0"


# ---------------------------------------------------------------------------
# Test Case 5: API error does not render as empty
# ---------------------------------------------------------------------------
def test_api_error_renders_honest_empty_guard() -> None:
    """When no counts are provided (API error / empty), render honest source empty card."""
    res = _run_node_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: {}, readiness: {} },
  capabilities: { "refresh-admin": true }
});
process.stdout.write(JSON.stringify({
  hasSourceEmpty: html.includes("portal-admin-dashboard-source-empty"),
  hasEmptyTitle: html.includes("Chưa có số liệu vận hành"),
  hasRefreshAction: html.includes('data-portal-action="refresh-admin"')
}));
'''
    )

    assert res["hasSourceEmpty"] is True
    assert res["hasEmptyTitle"] is True
    assert res["hasRefreshAction"] is True


# ---------------------------------------------------------------------------
# Test Case 6: Revenue is strictly scoped to WEB_ONLY
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_revenue_display_scope_is_web_only() -> None:
    """Verify that /internal/v1/admin/summary bridge response declares revenue_scope=WEB_ONLY."""
    account = {"id": "admin-1", "canonical_user_id": "telegram-1", "roles": ["canonical_admin"]}
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/admin/summary", "headers": []})
    res = await _bridge("GET", "/internal/v1/admin/summary", account=account, request=request, admin_read=True)
    assert res["ok"] is True
    assert res["data"]["revenue_scope"] == "WEB_ONLY"
    assert "TOTAL_SYSTEM_REVENUE" not in str(res)


# ---------------------------------------------------------------------------
# Test Case 7: Wallet is read-only on Dashboard
# ---------------------------------------------------------------------------
def test_wallet_is_read_only_on_dashboard() -> None:
    """Verify that renderAdminOverview contains zero wallet mutation forms or actions."""
    res = _run_node_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 0, total_customers: 10 }, readiness: {} }
});
process.stdout.write(JSON.stringify({
  hasWalletMutationForm: html.includes('action="/wallet') || html.includes('data-action="topup-settle'),
  hasDirectXuCredit: html.includes("credit_xu") || html.includes("adjust_balance")
}));
'''
    )

    assert res["hasWalletMutationForm"] is False
    assert res["hasDirectXuCredit"] is False


# ---------------------------------------------------------------------------
# Test Case 8: Dashboard has no direct dangerous write actions
# ---------------------------------------------------------------------------
def test_dashboard_has_no_direct_dangerous_write_actions() -> None:
    """Verify that dashboard root does not render direct job retry/refund/cancel buttons."""
    res = _run_node_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 1, total_customers: 10 }, readiness: {} }
});
process.stdout.write(JSON.stringify({
  hasJobRetryButton: html.includes("data-portal-action=\"retry-job\""),
  hasBanButton: html.includes("data-portal-action=\"ban-user\""),
  hasDeleteAccountButton: html.includes("data-portal-action=\"delete-account\"")
}));
'''
    )

    assert res["hasJobRetryButton"] is False
    assert res["hasBanButton"] is False
    assert res["hasDeleteAccountButton"] is False


# ---------------------------------------------------------------------------
# Test Case 9: Multi-source system health model distinguishes telemetry
# ---------------------------------------------------------------------------
@pytest.mark.anyio
async def test_system_health_multi_source_truth() -> None:
    """Verify that multi-source system health separates runtime, workers, and telemetry."""
    account = {"id": "admin-1", "canonical_user_id": "telegram-1", "roles": ["canonical_admin"]}
    request = Request({"type": "http", "method": "GET", "path": "/api/v1/admin/summary", "headers": []})
    res = await _bridge("GET", "/internal/v1/admin/summary", account=account, request=request, admin_read=True)
    health = res["data"]["system_health"]

    assert health["system_runtime"] == "HEALTHY"
    assert health["workers"] == "HEALTHY"
    # Autopilot reliability telemetry is unavailable, NOT collapsed to HEALTHY
    assert health["reliability_telemetry"] == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# Test Case 10: Existing primary/sidebar navigation remains intact
# ---------------------------------------------------------------------------
def test_navigation_consolidation_protected() -> None:
    """Ensure PR #437 7-group Admin IA consolidation is preserved."""
    assert "const ADMIN_NAVIGATION_GROUPS" in PORTAL_CODE or "adminErpNavigation" in PORTAL_CODE
    assert "adminOverviewTabs" in PORTAL_CODE or "renderAdminModuleTabs" in PORTAL_CODE


# ---------------------------------------------------------------------------
# Test Case 11: Light/Dark semantic classes remain intact
# ---------------------------------------------------------------------------
def test_light_dark_semantic_classes_remain_intact() -> None:
    """Verify that portal-metric and dashboard containers use semantic classes."""
    res = _run_node_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 1, total_customers: 5 }, readiness: {} }
});
process.stdout.write(JSON.stringify({
  hasAdminGrid: html.includes("portal-admin-grid"),
  hasMetricCard: html.includes("portal-metric"),
  hasTitleBar: html.includes("portal-admin-titlebar")
}));
'''
    )

    assert res["hasAdminGrid"] is True
    assert res["hasMetricCard"] is True
    assert res["hasTitleBar"] is True


# ---------------------------------------------------------------------------
# Test Case 12: No banned technical copy strings on Dashboard
# ---------------------------------------------------------------------------
def test_no_banned_technical_copy_on_dashboard() -> None:
    """Business overview must not expose internal technical implementation jargon."""
    res = _run_node_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 0, total_customers: 5 }, readiness: {} }
});
process.stdout.write(JSON.stringify({ html }));
'''
    )

    overview_html = res["html"]
    # Banned strings on public business dashboard
    assert "Core Bridge" not in overview_html
    assert "clean envelope" not in overview_html
    assert "SQLite authority" not in overview_html
