"""Focused empirical verification test suite for Task V2-02: Admin Command Dashboard.

Task: TASK=P0.WEBAPP.V2-02.ADMIN.COMMAND.DASHBOARD
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Repository: manhtoangreensky-wq/toan-aas-standalone
Base Ref: feat/p0-webapp-v2-01-customer-dashboard-transformation
Branch: feat/p0-webapp-v2-02-admin-command-dashboard

Invariants:
1. ADMIN_12_KPIS_LIVE_TRUTH: Admin overview exposes 12 live operational KPIs when provided by canonical server state.
2. ZERO_REMAINS_ZERO: Numeric 0 is rendered as 0, never replaced by mock/synthetic data.
3. UNKNOWN_NOT_ZERO: Missing/unavailable metrics render as "Không khả dụng" / "Chưa xác định", not 0.
4. TOPUP_QUEUE_HERO_ALERT: Pending topup count is prominently displayed with primary CTA to /admin/topups.
5. OPERATIONAL_INCIDENT_ALERT: When failed_jobs > 0, an operational alert banner prompts investigation at /admin/jobs/failed.
6. HEALTHY_NO_INCIDENT_SPAM: When failed_jobs == 0, failure alert banner is cleanly suppressed.
7. QUICK_ACTIONS_INTEGRITY: Operational quick actions lead to valid admin routes (/admin/topups, /admin/customers, /admin/jobs, /admin/support).
8. CANONICAL_DB_METRICS_SOURCE: copyfast_db.get_admin_overview_metrics queries authoritative SQLite tables.
9. VIETNAMESE_COPY_PURITY: Zero forbidden English technical tokens (Job, Ticket, Studio, Server, Browser) in visible admin dashboard copy.
10. BLUE_VISUAL_SYSTEM_COMPLIANCE: Uses standard Blue design tokens (.portal-admin-grid, .portal-metric, .portal-card).
"""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from pathlib import Path

import pytest

import copyfast_db

ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"


def _run_node_admin_dashboard(body: str) -> dict:
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

function safeText(value) { return String(value == null ? "" : value); }
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
  "metrics.workerJobs": "Tác vụ xử lý",
  "metrics.workerJobsNote": "Hàng đợi tiến trình đã xác minh",
  "metrics.engineJobs": "Tác vụ hệ thống",
  "metrics.engineJobsNote": "Đọc từ hàng đợi đã xác minh",
  "metrics.revenueVnd": "Doanh thu nạp tiền",
  "metrics.revenueVndNote": "Doanh thu nạp tiền đã đối soát",
  "metrics.topupsCompleted": "Giao dịch nạp",
  "metrics.topupsCompletedNote": "Số đơn nạp đã hoàn tất",
  "metrics.xuConsumed": "Xu tiêu thụ",
  "metrics.xuConsumedNote": "Tổng Xu đã chi cho tác vụ",
  "metrics.activeSessions": "Phiên hoạt động",
  "metrics.activeSessionsNote": "Phiên đăng nhập đang hoạt động",
  "metrics.pendingApprovals": "Phê duyệt vận hành",
  "metrics.pendingApprovalsNote": "Yêu cầu vận hành chờ duyệt",
  "metrics.failureRate": "Tỷ lệ sự cố",
  "metrics.failureRateNote": "Tỷ lệ lỗi trên tổng tác vụ",
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

function adminErpNavigation(context) {
  return context.navigation || { canonicalAdmin: true, webLocalAdmin: false, supportRole: "none", groups: [], routes: new Set() };
}
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
# Test 1: Admin dashboard renders 12 KPIs when full ERP counts provided
# ---------------------------------------------------------------------------
def test_admin_dashboard_12_kpi_contract() -> None:
    res = _run_node_admin_dashboard(
        r'''
const counts = {
  action_required: 4,
  total_customers: 120,
  pending_topups: 2,
  open_support: 1,
  failed_jobs: 0,
  worker_jobs: 3,
  engine_jobs: 5,
  revenue_vnd: "15.000.000 đ",
  topups_completed: 18,
  xu_consumed: 45000,
  active_sessions: 24,
  pending_approvals: 1
};
const html = renderAdminOverview({}, {
  adminData: { counts, readiness: { auth: { public_ready: true }, jobs: { public_ready: true } } }
});
const matches = Array.from(html.matchAll(/class="portal-metric"[^>]*><span>([^<]*)<\/span><strong>([^<]*)<\/strong>/g))
  .map(m => [m[1].trim(), m[2].trim()]);
process.stdout.write(JSON.stringify({ matches, count: matches.length }));
'''
    )
    pairs = dict(res["matches"])
    assert "Cần xử lý ngay" in pairs
    assert pairs["Cần xử lý ngay"] == "4"
    assert "Tài khoản người dùng" in pairs
    assert pairs["Tài khoản người dùng"] == "120"
    assert "Nạp tiền chờ duyệt" in pairs
    assert pairs["Nạp tiền chờ duyệt"] == "2"
    assert "Phiếu hỗ trợ mở" in pairs
    assert pairs["Phiếu hỗ trợ mở"] == "1"
    assert "Tác vụ gặp sự cố" in pairs
    assert pairs["Tác vụ gặp sự cố"] == "0"
    assert "Tác vụ xử lý" in pairs
    assert pairs["Tác vụ xử lý"] == "3"
    assert "Tác vụ hệ thống" in pairs
    assert pairs["Tác vụ hệ thống"] == "5"
    assert "Doanh thu nạp tiền" in pairs
    assert pairs["Doanh thu nạp tiền"] == "15.000.000 đ"
    assert "Giao dịch nạp" in pairs
    assert pairs["Giao dịch nạp"] == "18"
    assert "Xu tiêu thụ" in pairs
    assert pairs["Xu tiêu thụ"] == "45000"
    assert "Phiên hoạt động" in pairs
    assert pairs["Phiên hoạt động"] == "24"
    assert "Phê duyệt vận hành" in pairs
    assert pairs["Phê duyệt vận hành"] == "1"
    assert "Mức sẵn sàng" in pairs
    assert pairs["Mức sẵn sàng"] == "2/2"


# ---------------------------------------------------------------------------
# Test 2: Zero remains zero and unavailable is not zero
# ---------------------------------------------------------------------------
def test_admin_dashboard_zero_remains_zero_and_unknown_is_not_zero() -> None:
    res = _run_node_admin_dashboard(
        r'''
const counts = {
  action_required: 0,
  total_customers: 0,
  pending_topups: 0,
  open_support: 0,
  failed_jobs: 0,
  revenue_vnd: 0,
  topups_completed: 0,
  xu_consumed: 0,
  active_sessions: "unavailable"
};
const html = renderAdminOverview({}, {
  adminData: { counts, readiness: {} }
});
const matches = Array.from(html.matchAll(/class="portal-metric"[^>]*><span>([^<]*)<\/span><strong>([^<]*)<\/strong>/g))
  .map(m => [m[1].trim(), m[2].trim()]);
process.stdout.write(JSON.stringify({ matches }));
'''
    )
    pairs = dict(res["matches"])
    assert pairs["Cần xử lý ngay"] == "0"
    assert pairs["Tài khoản người dùng"] == "0"
    assert pairs["Tác vụ gặp sự cố"] == "0"
    assert pairs["Phiên hoạt động"] == "Không khả dụng"
    assert pairs["Phiên hoạt động"] != "0"


# ---------------------------------------------------------------------------
# Test 3: Topup queue hero alert displays pending count & link
# ---------------------------------------------------------------------------
def test_admin_dashboard_pending_topups_hero_alert() -> None:
    res = _run_node_admin_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 5, total_customers: 10, pending_topups: 5 } }
});
process.stdout.write(JSON.stringify({
  hasTopupHero: html.includes("portal-admin-topup-hero"),
  hasTopupLink: html.includes('href="/admin/topups"'),
  hasTopupCount: html.includes("5</strong>") || html.includes(">5<")
}));
'''
    )
    assert res["hasTopupHero"] is True
    assert res["hasTopupLink"] is True
    assert res["hasTopupCount"] is True


# ---------------------------------------------------------------------------
# Test 4: Operational incident alert banner triggers when failed_jobs > 0
# ---------------------------------------------------------------------------
def test_admin_dashboard_incident_alert_when_failures_present() -> None:
    res = _run_node_admin_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 2, total_customers: 10, failed_jobs: 3 } }
});
process.stdout.write(JSON.stringify({
  hasIncidentBanner: html.includes("portal-admin-incident-alert") || html.includes("portal-admin-incident-hero"),
  hasFailedJobLink: html.includes('href="/admin/jobs/failed"') || html.includes('href="/admin/jobs"'),
  hasFailedCount: html.includes("3</strong>") || html.includes(">3<")
}));
'''
    )
    assert res["hasIncidentBanner"] is True
    assert res["hasFailedJobLink"] is True
    assert res["hasFailedCount"] is True


# ---------------------------------------------------------------------------
# Test 5: Operational incident alert hidden when healthy (failed_jobs == 0)
# ---------------------------------------------------------------------------
def test_admin_dashboard_incident_alert_hidden_when_healthy() -> None:
    res = _run_node_admin_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 0, total_customers: 10, failed_jobs: 0 } }
});
process.stdout.write(JSON.stringify({
  hasIncidentBanner: html.includes("portal-admin-incident-alert") || html.includes("portal-admin-incident-hero")
}));
'''
    )
    assert res["hasIncidentBanner"] is False


# ---------------------------------------------------------------------------
# Test 6: Operational quick actions lead to valid admin routes
# ---------------------------------------------------------------------------
def test_admin_dashboard_quick_action_bar_truth() -> None:
    res = _run_node_admin_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 1, total_customers: 10 } }
});
process.stdout.write(JSON.stringify({
  hasTopupAction: html.includes('href="/admin/topups"'),
  hasUsersAction: html.includes('href="/admin/customers"') || html.includes('href="/admin/users"'),
  hasJobsAction: html.includes('href="/admin/jobs"'),
  hasCustomerRouteLeak: html.includes('href="/dashboard"') || html.includes('href="/workspace"')
}));
'''
    )
    assert res["hasTopupAction"] is True
    assert res["hasUsersAction"] is True
    assert res["hasJobsAction"] is True
    assert res["hasCustomerRouteLeak"] is False


# ---------------------------------------------------------------------------
# Test 7: copyfast_db.get_admin_overview_metrics queries authoritative SQLite
# ---------------------------------------------------------------------------
def test_admin_overview_metrics_authoritative_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "test_session_v2_02.db"
    monkeypatch.setattr(copyfast_db, "session_database_path", lambda: db_file)

    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE web_accounts (id TEXT PRIMARY KEY, is_active INT)")
        conn.execute("CREATE TABLE web_manual_topup_requests (id INT PRIMARY KEY, status TEXT, amount_vnd INT)")
        conn.execute("CREATE TABLE web_support_cases (id TEXT PRIMARY KEY, state TEXT)")
        conn.execute("CREATE TABLE web_ops_approvals (id TEXT PRIMARY KEY, state TEXT)")
        conn.execute("CREATE TABLE web_ops_followups (id TEXT PRIMARY KEY, state TEXT)")
        conn.execute("CREATE TABLE web_sessions (id TEXT PRIMARY KEY, is_revoked INT)")

        conn.executemany("INSERT INTO web_accounts VALUES (?, ?)", [("u1", 1), ("u2", 1), ("u3", 0)])
        conn.executemany("INSERT INTO web_manual_topup_requests VALUES (?, ?, ?)", [
            (1, "pending_admin_review", 100000),
            (2, "pending_admin_review", 200000),
            (3, "approved", 500000),
            (4, "approved", 1000000),
            (5, "rejected", 50000),
        ])
        conn.executemany("INSERT INTO web_support_cases VALUES (?, ?)", [
            ("s1", "new"),
            ("s2", "closed"),
        ])
        conn.executemany("INSERT INTO web_ops_approvals VALUES (?, ?)", [
            ("a1", "awaiting_approval"),
        ])
        conn.executemany("INSERT INTO web_sessions VALUES (?, ?)", [
            ("sess1", 0),
            ("sess2", 0),
            ("sess3", 1),
        ])

    metrics = copyfast_db.get_admin_overview_metrics()

    # Pre-existing invariants preserved
    assert metrics["users"] == 3
    assert metrics["total_customers"] == 3
    assert metrics["pending_topups"] == 2
    assert metrics["payments"] == 2
    assert metrics["open_support"] == 1
    assert metrics["pending_approvals"] == 1
    assert metrics["action_required"] == 4  # 2 topups + 1 support + 1 approval

    # V2-02 Enhanced Authoritative KPIs
    assert metrics.get("topups_completed") == 2
    assert metrics.get("revenue_vnd") == 1500000
    assert metrics.get("active_sessions") == 2


# ---------------------------------------------------------------------------
# Test 8: Vietnamese copy purity in Admin Overview
# ---------------------------------------------------------------------------
def test_admin_dashboard_vietnamese_copy_purity() -> None:
    res = _run_node_admin_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: {
    counts: { action_required: 1, total_customers: 10, failed_jobs: 1, pending_topups: 2 },
    readiness: { auth: { public_ready: true } }
  }
});
process.stdout.write(JSON.stringify({ html }));
'''
    )
    clean_text = re.sub(r"<[^>]+>", " ", res["html"])
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # Forbidden English technical terms
    for token in ("Job", "Ticket", "Studio", "Server", "Browser", "Workspace"):
        assert not re.search(rf"\b{re.escape(token)}\b", clean_text, re.IGNORECASE), f"Found forbidden token: {token}"


# ---------------------------------------------------------------------------
# Test 9: Visual system tokens compliance
# ---------------------------------------------------------------------------
def test_admin_dashboard_visual_system_tokens() -> None:
    res = _run_node_admin_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 1, total_customers: 10 } }
});
process.stdout.write(JSON.stringify({
  hasAdminHome: html.includes("portal-admin-home"),
  hasAdminGrid: html.includes("portal-admin-grid"),
  hasMetricCard: html.includes("portal-metric"),
  hasCardPad: html.includes("portal-card-pad")
}));
'''
    )
    assert res["hasAdminHome"] is True
    assert res["hasAdminGrid"] is True
    assert res["hasMetricCard"] is True
    assert res["hasCardPad"] is True


# ---------------------------------------------------------------------------
# Test 10: Zero dangerous unconfirmed mutations
# ---------------------------------------------------------------------------
def test_admin_dashboard_no_dangerous_mutations() -> None:
    res = _run_node_admin_dashboard(
        r'''
const html = renderAdminOverview({}, {
  adminData: { counts: { action_required: 1, total_customers: 10 } }
});
process.stdout.write(JSON.stringify({
  hasDeleteForm: html.includes('action="/delete') || html.includes('data-action="delete'),
  hasDropForm: html.includes('drop table'),
  hasDirectCredit: html.includes('adjust_balance') || html.includes('mutate_wallet')
}));
'''
    )
    assert res["hasDeleteForm"] is False
    assert res["hasDropForm"] is False
    assert res["hasDirectCredit"] is False
