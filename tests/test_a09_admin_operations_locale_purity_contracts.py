"""Executable locale contracts for the Admin Operations route family.

These tests render the real portal functions in Node. They cover fixed UI
copy only; server records, identifiers and machine codes remain canonical.
"""

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).parents[1]
PORTAL = ROOT / "static" / "portal" / "portal.js"
I18N = ROOT / "static" / "portal" / "portal-i18n.js"
THEME = ROOT / "static" / "portal" / "portal-theme.css"

FIXED_ASCII_TOKEN_SNAPSHOTS = {
    "vi": frozenset({
        "an", "bot", "cao", "coi", "csrf", "cung", "do", "dung", "erp", "ghi",
        "giao", "i", "id", "khai", "khi", "minh", "payos", "quan", "quy", "ranh",
        "ro", "sau", "sla", "suy", "telegram", "tham", "thanh", "thao", "thay",
        "theo", "thg", "thi", "tin", "tra", "trang", "trong", "url", "vai", "vi",
        "web", "xem", "xu",
    }),
    "en": frozenset({
        "a", "access", "account", "accountable", "action", "actions", "admin",
        "administration", "administrator", "administrators", "after", "am", "an", "and",
        "app", "approval", "are", "as", "audit", "authority", "automated", "automatic",
        "automatically", "automation", "autopilot", "available", "awaiting", "baseline",
        "been", "beyond", "board", "bot", "boundary", "breach", "breached", "browser",
        "but", "by", "call", "cannot", "card", "change", "checking", "cleared", "completed",
        "configuration", "configured", "confirm", "confirmation", "contain", "controlled",
        "controls", "correct", "created", "creates", "credentials", "critical", "csrf",
        "current", "customer", "data", "decision", "decisions", "delay", "delivery",
        "deployments", "detected", "did", "disabled", "do", "does", "empty", "enough",
        "erp", "establishing", "evaluate", "evaluating", "evaluation", "evidence", "executed",
        "executes", "executor", "exposes", "external", "financial", "follow", "for", "grant",
        "granted", "guarded", "has", "have", "health", "heartbeat", "high", "hmac", "i",
        "id", "idempotency", "ids", "incident", "incidents", "infer", "infrastructure",
        "intentional", "internal", "interpret", "interval", "investigate", "investigating",
        "investigation", "invoke", "is", "it", "itself", "job", "jobs", "lacks", "levels",
        "local", "logs", "manager", "managers", "may", "member", "money", "monitor", "more",
        "must", "near", "never", "next", "no", "nonce", "not", "observations", "occurs",
        "one", "only", "open", "operations", "operator", "operators", "or", "outside",
        "oversight", "overview", "owner", "ownership", "page", "pagination", "parameters",
        "payload", "payloads", "payments", "payos", "permission", "permissions", "personal",
        "policy", "portal", "present", "previous", "process", "processing", "proposal",
        "proposals", "provider", "providers", "queue", "raw", "reached", "read", "ready",
        "receipt", "receipts", "receive", "recent", "record", "recording", "records", "refresh",
        "refund", "reject", "rejection", "release", "reliability", "remains", "repair",
        "replaced", "replies", "request", "requests", "require", "required", "restart", "retry",
        "return", "returned", "review", "reviewing", "revision", "risk", "role", "roles", "run",
        "runs", "safe", "same", "sanitized", "schedule", "scheduler", "scope", "scoped", "secrets",
        "section", "sensitive", "sep", "server", "session", "severity", "showing", "shows", "signed",
        "sla", "some", "source", "staff", "stale", "still", "storage", "subqueues", "suitable",
        "summary", "support", "system", "telegram", "that", "the", "this", "through", "tick", "to",
        "totals", "triaged", "unable", "under", "unverified", "up", "updated", "ups", "url", "use",
        "valid", "verified", "verifies", "view", "wallet", "web", "when", "wide", "will", "window",
        "with", "within", "workflow", "xu", "yet", "you", "zero",
    }),
    "zh": frozenset({"bot", "csrf", "erp", "hmac", "i", "id", "payos", "sla", "telegram", "url", "web", "xu"}),
}


class _RenderedCopyParser(HTMLParser):
    COPY_ATTRIBUTES = {"aria-label", "title", "placeholder", "data-portal-confirm"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.values.append(data)

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in self.COPY_ATTRIBUTES and value:
                self.values.append(value)


def _visible_copy(*markup: object) -> str:
    parser = _RenderedCopyParser()
    for value in markup:
        parser.feed(str(value))
    return re.sub(r"\s+", " ", " ".join(parser.values)).strip()


def _render_admin_operations(locale: str) -> dict[str, object]:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the Admin Operations renderer contract")

    script = r'''
const fs = require("fs");
const vm = require("vm");
const i18nPath = process.argv[1];
const portalPath = process.argv[2];
const locale = process.argv[3];
const i18nSource = fs.readFileSync(i18nPath, "utf8");
let portalSource = fs.readFileSync(portalPath, "utf8");
const closing = "}());";
const closingOffset = portalSource.lastIndexOf(closing);
if (closingOffset < 0) throw new Error("Portal closure was not found");
portalSource = portalSource.slice(0, closingOffset)
  + `\nglobalThis.__a09AdminOperations = Object.freeze({\n`
  + `  renderOperationsAdmin, localizedPageTitle, localizedPageDescription\n`
  + `});\n`
  + portalSource.slice(closingOffset);

function classList() {
  return { add() {}, remove() {}, contains() { return false; }, toggle() { return false; } };
}
function element() {
  const attributes = {};
  return {
    hidden: false, innerHTML: "", textContent: "", dataset: {}, classList: classList(),
    setAttribute(name, value) { attributes[name] = String(value); },
    getAttribute(name) { return attributes[name] || ""; },
    removeAttribute(name) { delete attributes[name]; },
    hasAttribute(name) { return Object.prototype.hasOwnProperty.call(attributes, name); },
    querySelector() { return null; }, querySelectorAll() { return []; },
    appendChild(child) { return child; }, remove() {},
    addEventListener() {}, removeEventListener() {}, matches() { return false; },
    closest() { return null; }, focus() {}
  };
}
const documentElement = {
  lang: locale, dir: "ltr", attributes: {}, style: {},
  setAttribute(name, value) { this.attributes[name] = String(value); },
  getAttribute(name) { return this.attributes[name] || ""; },
  removeAttribute(name) { delete this.attributes[name]; }
};
const document = {
  documentElement, body: element(), title: "TOAN AAS", readyState: "loading", activeElement: null,
  getElementById() { return null; }, querySelector() { return null; }, querySelectorAll() { return []; },
  addEventListener() {}, removeEventListener() {}, createElement() { return element(); }
};
const context = {
  console, JSON, URL, URLSearchParams, Intl, document,
  location: { pathname: "/admin/operations", search: "" },
  history: { pushState() {}, replaceState() {} },
  navigator: { language: locale },
  CustomEvent: function CustomEvent(type, init) { this.type = type; this.detail = init && init.detail; },
  HTMLElement: function HTMLElement() {},
  addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
  matchMedia() { return { matches: false, addEventListener() {}, removeEventListener() {} }; },
  requestAnimationFrame(callback) { if (typeof callback === "function") callback(); return 0; },
  cancelAnimationFrame() {}, setTimeout() { return 0; }, clearTimeout() {},
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} }
};
context.window = context;
context.globalThis = context;
vm.createContext(context);
vm.runInContext(i18nSource, context, { filename: i18nPath });
context.TOANAASI18n.setLocale(locale, { emit: false });
vm.runInContext(portalSource, context, { filename: portalPath });

const api = context.__a09AdminOperations;
if (!api) throw new Error("Admin Operations renderer API was not captured");
const page = {
  path: "/admin/operations", routePath: "/admin/operations",
  title: "Operations Autopilot", section: "Admin ERP",
  description: "Fallback description", action: "none", status: "processing"
};
const supportId = "8a0d55e2-2287-4387-8bd1-3774a56f023f";
const dynamicAction = "dynamic_action_7429";
const dynamicKind = "dynamic_kind_7429";
const dynamicCode = "OPS_DYNAMIC_7429";
const pagination = {
  limit: 50, offset: 0, returned: 1, has_more: true,
  next_offset: 50, previous_offset: null
};
const summary = {
  operator_role: "manager", approvals_access: "full", scheduler_preflight: "ready",
  open_incidents: 2, pending_approvals: 1,
  sla: { at_risk: 1, breached: 1 },
  last_run: { state: "completed", finished_at: "2026-09-10T00:00:00Z" },
  scheduler_heartbeat: {
    state: "late", previous_tick_seen: true, late: true, code: "", open_followups: 2
  }
};
const base = {
  session: { authenticated: true, csrfReady: true },
  bridge: { available: true, csrfReady: true },
  pageStates: {},
  capabilities: {
    "operations-approval-approve": true,
    "operations-approval-reject": true
  },
  operationsAdminReadState: "ready",
  operationsAdminSummary: summary,
  operationsAdminQueueStates: { runs: "ready", incidents: "ready", approvals: "ready" },
  operationsAdminRuns: [], operationsAdminIncidents: [], operationsApprovals: [],
  operationsAdminRunListing: { pagination },
  operationsAdminIncidentListing: { pagination },
  operationsApprovalListing: { pagination }
};
const populated = {
  ...base,
  operationsAdminRuns: [{
    id: supportId, state: "completed", finished_at: "2026-09-10T00:00:00Z",
    triaged_case_count: 4, incident_count: 1, error_code: dynamicCode
  }],
  operationsAdminIncidents: [{
    id: supportId, kind: dynamicKind, state: "investigating", severity: "critical",
    support_case_id: supportId, observation_count: 3,
    last_observed_at: "2026-09-10T00:00:00Z", revision: 2
  }],
  operationsApprovals: [{
    id: supportId, support_case_id: supportId, state: "awaiting_approval",
    action_type: dynamicAction, risk: "high", proposed_at: "2026-09-10T00:00:00Z", revision: 2
  }]
};
const operator = {
  ...base,
  operationsAdminSummary: { ...summary, operator_role: "operator", approvals_access: "none" }
};
const partial = {
  ...base,
  operationsAdminQueueStates: { runs: "ready", incidents: "guarded", approvals: "guarded" }
};
const loading = { ...base, operationsAdminReadState: "loading", operationsAdminSummary: {} };
const guarded = { ...base, operationsAdminReadState: "guarded", operationsAdminSummary: {} };
const heartbeatStates = Object.fromEntries([
  ["disabled", { state: "disabled", previous_tick_seen: false, late: false, code: "", open_followups: 0 }],
  ["baseline_pending", { state: "baseline_pending", previous_tick_seen: false, late: false, code: "", open_followups: 0 }],
  ["within_window", { state: "within_window", previous_tick_seen: true, late: false, code: "", open_followups: 0 }],
  ["late", { state: "late", previous_tick_seen: true, late: true, code: "", open_followups: 2 }],
  ["guarded", { state: "guarded", previous_tick_seen: false, late: false, code: "OPS_HEARTBEAT_CONFIG_UNVERIFIED", open_followups: 0 }]
].map(([state, scheduler_heartbeat]) => [state, api.renderOperationsAdmin(page, {
  ...base,
  operationsAdminSummary: { ...summary, scheduler_heartbeat }
})]));
const invalidAction = api.renderOperationsAdmin(page, {
  ...populated,
  operationsApprovals: [{ ...populated.operationsApprovals[0], action_type: "Bad<script>7429" }]
});

process.stdout.write(JSON.stringify({
  emptyManager: api.renderOperationsAdmin(page, base),
  populatedManager: api.renderOperationsAdmin(page, populated),
  operator: api.renderOperationsAdmin(page, operator),
  partial: api.renderOperationsAdmin(page, partial),
  loading: api.renderOperationsAdmin(page, loading),
  guarded: api.renderOperationsAdmin(page, guarded),
  heartbeatStates,
  invalidAction,
  title: api.localizedPageTitle(page, base),
  description: api.localizedPageDescription(page),
  adminKeys: Object.keys(context.TOANAASI18n.messages[locale]).filter((key) => key.startsWith("adminOperations.")).sort(),
  dynamicValues: [dynamicAction, dynamicKind, dynamicCode, supportId.slice(0, 8), "approval_record_only", "ready", "OPS_HEARTBEAT_CONFIG_UNVERIFIED"]
}));
'''
    result = subprocess.run(
        [node, "-e", script, str(I18N), str(PORTAL), locale],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def _fixed_copy(rendered: dict[str, object]) -> str:
    copy = _visible_copy(
        rendered["emptyManager"], rendered["populatedManager"], rendered["operator"],
        rendered["partial"], rendered["loading"], rendered["guarded"],
        *rendered["heartbeatStates"].values(),
        rendered["title"], rendered["description"],
    )
    for value in rendered["dynamicValues"]:
        copy = copy.replace(str(value), " ")
    return re.sub(r"\s+", " ", copy).strip()


def _ascii_tokens(copy: str) -> frozenset[str]:
    return frozenset(
        token.casefold()
        for token in re.findall(r"(?<!\w)[A-Za-z][A-Za-z0-9]*(?:/[A-Za-z0-9]+)?(?!\w)", copy)
    )


def test_admin_operations_vi_fixed_copy_has_no_unreviewed_english() -> None:
    rendered = _render_admin_operations("vi")
    copy = _fixed_copy(rendered)
    forbidden = (
        "Manager", "Operator", "Support Desk", "signed", "role", "boundary", "Browser",
        "localStorage", "query string", "Summary", "queue", "Approval", "record", "risk",
        "proposal", "audit", "confirmation", "Approve", "payment", "provider", "job",
        "deploy", "external", "workflow", "receipt", "Scheduler", "triage", "incident",
        "follow-up", "heartbeat", "policy", "baseline", "Controlled operations", "metadata",
        "sanitize", "credential", "payload", "PII", "wallet", "control", "Server-side",
        "read only", "revision", "idempotency", "executor", "retry", "delivery", "HMAC",
    )
    violations = sorted(
        term for term in forbidden
        if re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", copy, re.IGNORECASE)
    )
    assert violations == [], f"Vietnamese Admin Operations contains foreign fixed copy: {violations}\n{copy}"
    assert "Điều hành có kiểm soát" in copy
    assert "Vai trò do máy chủ xác minh" in copy
    assert "thg" in copy.lower(), "The fixture must exercise Vietnamese timestamp formatting"
    assert _ascii_tokens(copy) == FIXED_ASCII_TOKEN_SNAPSHOTS["vi"]
    assert _ascii_tokens(copy + " Dashboard") != FIXED_ASCII_TOKEN_SNAPSHOTS["vi"]


@pytest.mark.parametrize("locale", ["en", "zh"])
def test_admin_operations_non_vietnamese_fixed_copy_contains_no_vietnamese(locale: str) -> None:
    rendered = _render_admin_operations(locale)
    copy = _fixed_copy(rendered)
    vietnamese_letters = re.findall(r"[ĂÂĐÊÔƠƯăâđêôơư\u1EA0-\u1EF9]", copy)
    vietnamese_words = re.findall(
        r"\b(?:Khong|May chu|Quyen|Dang|Hang doi|Phan trang|Trang truoc|Trang sau|"
        r"Lam moi|Mo yeu cau|Da ghi nhan|Ranh gioi|Gan qua|Chua co)\b",
        copy,
        re.IGNORECASE,
    )
    assert vietnamese_letters == [] and vietnamese_words == [], (
        f"{locale} Admin Operations contains Vietnamese fixed copy: "
        f"letters={vietnamese_letters}, words={vietnamese_words}\n{copy}"
    )
    assert _ascii_tokens(copy) == FIXED_ASCII_TOKEN_SNAPSHOTS[locale]
    assert _ascii_tokens(copy + " ChuaHoanTat") != FIXED_ASCII_TOKEN_SNAPSHOTS[locale]


def test_admin_operations_catalogue_is_symmetric_and_covers_all_render_states() -> None:
    rendered = {locale: _render_admin_operations(locale) for locale in ("vi", "en", "zh")}
    assert rendered["vi"]["adminKeys"] == rendered["en"]["adminKeys"] == rendered["zh"]["adminKeys"]
    assert len(rendered["vi"]["adminKeys"]) >= 65

    assert "Điều hành có kiểm soát" in rendered["vi"]["populatedManager"]
    assert "Controlled operations" in rendered["en"]["populatedManager"]
    assert "受控运营" in rendered["zh"]["populatedManager"]
    assert "Quyền điều hành chưa được cấp" in rendered["vi"]["guarded"]
    assert "Operations permission has not been granted" in rendered["en"]["guarded"]
    assert "尚未授予运营权限" in rendered["zh"]["guarded"]
    assert "Chỉ người quản lý hỗ trợ" in rendered["vi"]["operator"]
    assert "Support managers only" in rendered["en"]["operator"]
    assert "仅限支持经理" in rendered["zh"]["operator"]
    assert "Trang sau" in rendered["vi"]["populatedManager"]
    assert "Next page" in rendered["en"]["populatedManager"]
    assert "下一页" in rendered["zh"]["populatedManager"]
    assert "Đã hoàn tất" in rendered["vi"]["populatedManager"]
    assert "Completed" in rendered["en"]["populatedManager"]
    assert "已完成" in rendered["zh"]["populatedManager"]
    expected_heartbeat_labels = {
        "vi": ["Chưa bật theo dõi tiếp", "Đang tạo mốc", "Nhịp chạy đúng thời hạn", "Cần tra xét", "Đang bảo vệ"],
        "en": ["Follow-up disabled", "Establishing baseline", "Heartbeat within window", "Investigation required", "Guarded"],
        "zh": ["后续跟踪未启用", "正在建立基线", "心跳在时间窗内", "需要调查", "受保护"],
    }
    for locale, labels in expected_heartbeat_labels.items():
        heartbeat_markup = " ".join(rendered[locale]["heartbeatStates"].values())
        assert all(label in heartbeat_markup for label in labels)


def test_admin_operations_preserves_dynamic_values_and_record_only_actions() -> None:
    for locale in ("vi", "en", "zh"):
        rendered = _render_admin_operations(locale)
        populated = str(rendered["populatedManager"])
        for dynamic in rendered["dynamicValues"][:4]:
            assert str(dynamic) in populated
        for action in ("operations-approval-approve", "operations-approval-reject"):
            assert f'data-portal-action="{action}"' in populated
        assert 'data-portal-route="/admin/operations"' in populated
        assert 'name="expected_revision" value="2"' in populated
        assert 'name="decision_code" value="manager_approved"' in populated
        assert 'name="decision_code" value="manager_rejected"' in populated
        assert "Bad&lt;script&gt;7429" not in str(rendered["invalidAction"])
        assert "<strong>review</strong>" in str(rendered["invalidAction"])


def test_admin_operations_renderer_uses_dedicated_catalogue_for_fixed_copy() -> None:
    source = PORTAL.read_text(encoding="utf-8")
    assert "function adminOperationsText" in source
    start = source.index("function renderOperationsAdmin(page, context)")
    end = source.index("function automationMonitorStateLabel", start)
    renderer = source[start:end]
    assert "const copy = (key, fallback, params) => adminOperationsText(key, fallback, params);" in renderer
    assert renderer.count("copy(") >= 55
    for forbidden in (
        ">Approval queue<", ">Scheduler heartbeat<", ">Làm mới<", ">Mở case<",
        ">Ghi nhận duyệt<", ">Từ chối<", ">Controlled operations<",
    ):
        assert forbidden not in renderer


def test_admin_operations_uses_professional_semantic_responsive_surface() -> None:
    css = THEME.read_text(encoding="utf-8")
    marker = "/* A09 Admin Operations */"
    assert css.count(marker) == 1
    layer = css[css.index(marker):]
    for required in (
        ".portal-page.portal-operations-admin {",
        "background: var(--portal-surface-light);",
        ".portal-page.portal-operations-admin .portal-operations-admin-intro {",
        "box-shadow: var(--portal-elevation-1);",
        "grid-template-columns: minmax(0, 1.18fr) minmax(280px, .82fr);",
        ".portal-page.portal-operations-admin .portal-operations-metrics {",
        "grid-template-columns: repeat(4, minmax(0, 1fr));",
        ".portal-page.portal-operations-admin .portal-operations-approval-actions .portal-button {",
        "min-height: 44px;",
        ".portal-page.portal-operations-admin .portal-empty {",
        "border: 1px dashed var(--portal-border-strong);",
        "white-space: nowrap;",
        "@media (max-width: 980px)",
        "grid-template-columns: repeat(2, minmax(0, 1fr));",
        "@media (max-width: 700px)",
        "grid-template-columns: minmax(0, 1fr);",
    ):
        assert required in layer
    clean = re.sub(r"/\*.*?\*/", "", layer, flags=re.DOTALL)
    assert "#" not in clean
    assert "rgba(" not in clean
    assert "transition:" not in clean
    assert "transform:" not in clean
