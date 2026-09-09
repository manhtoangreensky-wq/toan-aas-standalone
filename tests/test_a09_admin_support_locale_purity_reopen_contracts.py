"""A09 live-reopen contracts for locale-pure Admin Support presentation.

These tests execute the real browser renderers.  They intentionally keep all
Support authority, records, routes and lifecycle values unchanged; only fixed
presentation copy may vary by locale.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "static" / "portal" / "portal-i18n.js"
PORTAL = ROOT / "static" / "portal" / "portal.js"

# Owner rule: Vietnamese fixed copy may retain English nouns and technical
# identifiers when translating them would make the product less clear. Keep
# this finite and reviewed; an omitted UI term must be translated or added here
# deliberately rather than disappearing from the forbidden-term scan.
VI_ALLOWED_ENGLISH_NOUNS = frozenset({
    "TOAN AAS", "Web", "Telegram", "PayOS", "Odoo", "Bot", "Email", "App",
})
VI_ALLOWED_TECHNICAL_IDENTIFIERS = frozenset({
    "ERP", "CSRF", "SLA", "API", "ID", "PDF", "QR", "OTP/CVV", "TXID",
    "URL", "PNG", "JPEG", "WebP", "TXT", "MB", "Xu",
})
VI_FORBIDDEN_FIXED_COPY = frozenset({
    "Admin ERP", "Support Desk", "Web-native", "Manager", "Operator", "Web-only",
    "case", "revision", "confirmation", "idempotency", "audit", "resolved", "closed",
    "public", "reply", "policy", "Customer Care", "Quality", "Escalation", "query",
    "browser", "external", "wallet", "refund", "ledger", "job", "provider",
    "file delivery", "staff", "lane", "notification", "Critical", "Assignee",
    "Activity", "Timeline", "Triage", "Internal", "server", "signed", "account",
    "redaction", "metadata", "Roster", "active", "write", "raw", "payload",
})
VI_FIXED_ASCII_TOKEN_SNAPSHOT = frozenset({
    "aas", "api", "app", "b", "bao", "bot", "cam", "cao", "che", "chi", "cho",
    "chung", "csrf", "cung", "danh", "do", "dung", "duy", "email", "erp", "ghi",
    "gian", "giao", "hay", "i", "id", "khai", "khi", "kho", "minh", "odoo",
    "otp/cvv", "payos", "pdf", "qr", "qua", "quay", "quy", "ra", "ranh", "sau",
    "sla", "suy", "telegram", "thanh", "thao", "thay", "theo", "thg", "tin",
    "toan", "tra", "trang", "trao", "trong", "trung", "txid", "url", "vai",
    "vi", "video", "web", "xem", "xong", "xu",
})


class _RenderedCopyParser(HTMLParser):
    """Collect user-visible text plus accessibility and form guidance copy."""

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


def _visible_copy(*markup: str) -> str:
    parser = _RenderedCopyParser()
    for value in markup:
        parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.values)).strip()


def _render_admin_support(locale: str) -> dict[str, object]:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the executable Admin Support locale contract")

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
  + `\nglobalThis.__a09AdminSupport = Object.freeze({\n`
  + `  renderSupportAdmin, renderSupportAdminCaseDetail,\n`
  + `  localizedPageTitle, localizedPageDescription, supportTicketHeroSection\n`
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
  location: { pathname: "/admin/support", search: "" },
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

const api = context.__a09AdminSupport;
if (!api) throw new Error("Admin Support renderer test API was not captured");
const caseId = "8a0d55e2-2287-4387-8bd1-3774a56f023f";
const listPage = {
  path: "/admin/support", routePath: "/admin/support", title: "Web Support Desk",
  section: "Admin ERP", description: "Fallback copy", action: "none", status: "processing"
};
const detailPage = {
  path: "/admin/support/:id", routePath: `/admin/support/${caseId}`,
  title: "Xử lý yêu cầu", section: "Web Support Desk", description: "Fallback copy",
  action: "none", status: "processing"
};
const summary = { operator_role: "manager", states: { new: 0 }, overdue: 0 };
const base = {
  session: { authenticated: true, csrfReady: true }, bridge: { available: true, csrfReady: true },
  capabilities: { "support-admin-case-write": true }, pageStates: {},
  supportAdminReadState: "ready", supportAdminSummary: summary,
  supportAdminCases: [], supportAdminCareQueues: [], supportAdminCareStaff: [], supportAdminCareHistory: [],
  supportAdminCaseListing: {
    filters: { state: "all", category: "", q: "", team_queue: "all", assignment: "all", sla_class: "all", escalation_state: "all" },
    pagination: { limit: 50, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null }
  }
};
const dynamicSubject = "TOAN AAS DYNAMIC SUBJECT 7429";
const detail = {
  ...base,
  supportAdminCaseDetail: {
    case: {
      id: caseId, category: "general_support", priority: "normal", state: "new", revision: 2,
      subject: dynamicSubject, excerpt: "", created_at: "2026-09-07T00:00:00Z",
      updated_at: "2026-09-07T00:00:00Z", last_public_message_at: "", resolved_at: "",
      customer: { display_name: "TOAN AAS", email_masked: "" }, care: {}
    },
    messages: [], events: [], attachments: []
  },
  supportAdminReplyReceipt: {
    case_id: caseId, revision: 2, state: "new", action: "operator_reply",
    visibility: "public", delivery: "web_view_only"
  }
};
const list = api.renderSupportAdmin(listPage, base);
const detailMarkup = api.renderSupportAdminCaseDetail(detailPage, detail);
const populated = {
  ...base,
  supportAdminCases: [{
    id: caseId, category: "general_support", priority: "urgent", state: "reviewing",
    subject: dynamicSubject, excerpt: "", created_at: "2026-09-07T00:00:00Z",
    updated_at: "2026-09-07T00:00:00Z", customer: { display_name: "TOAN AAS", email_masked: "" }
  }],
  supportAdminCareQueues: [{ team_queue: "technical", total: 1, unassigned: 0, critical: 1, escalated: 1 }],
  supportAdminResolutionFeedbackSummary: {
    delivery: "internal_metadata_only", window_days: 30, total_responses: 1,
    rating_counts: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 1 },
    average_rating: 5, comments_count: 1
  },
  supportAdminCaseListing: {
    ...base.supportAdminCaseListing,
    pagination: { limit: 50, offset: 0, returned: 1, has_more: true, next_offset: 50, previous_offset: null }
  }
};
const readyDetail = {
  ...detail,
  supportAdminCareStaff: [{ id: "staff-1", display_name: "TOAN AAS", role: "manager" }],
  supportAdminCareHistory: [
    { id: caseId, kind: "triage", action: "updated", created_at: "2026-09-07T00:00:00Z", actor_display_name: "TOAN AAS" },
    { id: caseId, kind: "escalation", action: "acknowledged", created_at: "2026-09-07T00:00:00Z", actor_display_name: "TOAN AAS" }
  ],
  supportAdminCaseDetail: {
    ...detail.supportAdminCaseDetail,
    case: {
      ...detail.supportAdminCaseDetail.case,
      care: {
        team_queue: "technical",
        assignee: { id: "staff-1", display_name: "TOAN AAS" },
        sla: { class: "critical", target_hours: 2, due_at: "2026-09-07T02:00:00Z", first_staff_touch_at: "", status: "pending" },
        escalation: { state: "requested", reason: "TOAN AAS", requested_at: "2026-09-07T00:00:00Z", acknowledged_at: "", resolved_at: "" }
      }
    },
    messages: [
      { author_role: "operator", visibility: "public", body: "TOAN AAS", created_at: "2026-09-07T00:00:00Z" },
      { author_role: "operator", visibility: "internal", body: "TOAN AAS", created_at: "2026-09-07T00:00:00Z" }
    ],
    events: [{ action: "operator_updated", state: "reviewing", created_at: "2026-09-07T00:00:00Z" }],
    attachments: [{ id: caseId, display_name: "TOAN AAS", content_type: "text/plain", byte_size: 64 }]
  }
};
const operatorDetail = {
  ...readyDetail,
  supportAdminSummary: { ...summary, operator_role: "operator" }
};
const guarded = { ...base, supportAdminReadState: "guarded", supportAdminSummary: {} };
const loading = { ...base, supportAdminReadState: "loading", supportAdminSummary: {} };
const guardedDetail = { ...base, supportAdminReadState: "guarded", supportAdminSummary: {}, supportAdminCaseDetail: {} };
const loadingDetail = { ...base, supportAdminReadState: "loading", supportAdminSummary: {}, supportAdminCaseDetail: {} };
const closedDetail = {
  ...detail,
  supportAdminCaseDetail: {
    ...detail.supportAdminCaseDetail,
    case: { ...detail.supportAdminCaseDetail.case, state: "closed" }
  },
  supportAdminReplyReceipt: null
};
process.stdout.write(JSON.stringify({
  list,
  detail: detailMarkup,
  untitledDetail: api.renderSupportAdminCaseDetail(detailPage, {
    ...detail,
    supportAdminCaseDetail: { ...detail.supportAdminCaseDetail,
      case: { ...detail.supportAdminCaseDetail.case, subject: "" } }
  }),
  populatedList: api.renderSupportAdmin(listPage, populated),
  readyDetail: api.renderSupportAdminCaseDetail(detailPage, readyDetail),
  operatorDetail: api.renderSupportAdminCaseDetail(detailPage, operatorDetail),
  guardedList: api.renderSupportAdmin(listPage, guarded),
  loadingList: api.renderSupportAdmin(listPage, loading),
  guardedDetail: api.renderSupportAdminCaseDetail(detailPage, guardedDetail),
  loadingDetail: api.renderSupportAdminCaseDetail(detailPage, loadingDetail),
  closedDetail: api.renderSupportAdminCaseDetail(detailPage, closedDetail),
  listTitle: api.localizedPageTitle(listPage, base),
  listDescription: api.localizedPageDescription(listPage),
  listSection: api.supportTicketHeroSection(listPage),
  detailTitle: api.localizedPageTitle(detailPage, detail),
  detailDescription: api.localizedPageDescription(detailPage),
  detailSection: api.supportTicketHeroSection(detailPage),
  dynamicSubject,
  dynamicCaseId: caseId,
  dynamicContentType: "text/plain",
  adminKeys: Object.keys(context.TOANAASI18n.messages[locale]).filter((key) => key.startsWith("adminSupport.")).sort()
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


def _admin_support_vi_fixed_copy(rendered: dict[str, object]) -> str:
    copy = _visible_copy(
        rendered["list"],
        rendered["detail"],
        rendered["populatedList"],
        rendered["readyDetail"],
        rendered["operatorDetail"],
        rendered["guardedList"],
        rendered["loadingList"],
        rendered["guardedDetail"],
        rendered["loadingDetail"],
        rendered["closedDetail"],
        rendered["listTitle"],
        rendered["listDescription"],
        rendered["listSection"],
        rendered["detailTitle"],
        rendered["detailDescription"],
        rendered["detailSection"],
    )
    return (
        copy
        .replace(str(rendered["dynamicSubject"]), " ")
        .replace(str(rendered["dynamicCaseId"])[:8], " ")
        .replace(str(rendered["dynamicContentType"]), " ")
    )


def _ascii_tokens(copy: str) -> frozenset[str]:
    return frozenset(
        token.casefold()
        for token in re.findall(r"(?<!\w)[A-Za-z][A-Za-z0-9]*(?:/[A-Za-z0-9]+)?(?!\w)", copy)
    )


def test_admin_support_vi_fixed_copy_is_vietnamese_except_finite_terms() -> None:
    rendered = _render_admin_support("vi")
    assert str(rendered["dynamicSubject"]) in str(rendered["detail"])
    assert str(rendered["dynamicSubject"]) in str(rendered["populatedList"])
    copy = _admin_support_vi_fixed_copy(rendered)
    reviewed_terms = VI_ALLOWED_ENGLISH_NOUNS | VI_ALLOWED_TECHNICAL_IDENTIFIERS | VI_FORBIDDEN_FIXED_COPY
    present_terms = {
        term for term in reviewed_terms
        if re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", copy, re.IGNORECASE)
    }
    violations = sorted(present_terms & VI_FORBIDDEN_FIXED_COPY, key=str.casefold)
    assert violations == [], f"Vietnamese Admin Support contains foreign fixed copy: {violations}\n{copy}"
    expected_reviewed_exceptions = {
        "TOAN AAS", "Web", "Telegram", "PayOS", "Odoo", "Bot", "Email", "App",
        "ERP", "CSRF", "SLA", "API", "ID", "PDF", "QR", "OTP/CVV", "TXID", "URL", "Xu",
    }
    assert expected_reviewed_exceptions <= present_terms
    assert expected_reviewed_exceptions <= (VI_ALLOWED_ENGLISH_NOUNS | VI_ALLOWED_TECHNICAL_IDENTIFIERS)
    assert not re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", copy), (
        f"Vietnamese timestamps must use the active Vietnamese locale: {copy}"
    )
    assert "thg" in copy.lower(), "The Vietnamese timestamp fixture must exercise localized month output"
    assert _ascii_tokens(copy) == VI_FIXED_ASCII_TOKEN_SNAPSHOT
    assert _ascii_tokens(copy + " Dashboard") != VI_FIXED_ASCII_TOKEN_SNAPSHOT
    assert not {"dynamic", "subject", "text", "plain", "a0d55e2"} & _ascii_tokens(copy)


def test_admin_support_en_fixed_copy_contains_no_vietnamese() -> None:
    rendered = _render_admin_support("en")
    copy = _visible_copy(
        rendered["list"],
        rendered["detail"],
        rendered["populatedList"],
        rendered["readyDetail"],
        rendered["operatorDetail"],
        rendered["guardedList"],
        rendered["loadingList"],
        rendered["guardedDetail"],
        rendered["loadingDetail"],
        rendered["closedDetail"],
        rendered["listTitle"],
        rendered["listDescription"],
        rendered["listSection"],
        rendered["detailTitle"],
        rendered["detailDescription"],
        rendered["detailSection"],
    )

    assert rendered["dynamicSubject"] in copy, "Server/user record text must remain unchanged"
    vietnamese_letters = re.findall(r"[ĂÂĐÊÔƠƯăâđêôơư\u1EA0-\u1EF9]", copy)
    vietnamese_words = re.findall(
        r"\b(?:Khach|Khong|May chu|Trang thai|Hang doi|Phan cong|Ghi chu|Lam moi|Xoa loc|Quay lai|Yeu cau)\b",
        copy,
        re.IGNORECASE,
    )
    assert vietnamese_letters == [] and vietnamese_words == [], (
        f"English Admin Support contains Vietnamese fixed copy: letters={vietnamese_letters}, "
        f"words={vietnamese_words}\n{copy}"
    )
    assert " thg " not in copy.lower(), "English timestamps must not use Vietnamese month output"


@pytest.mark.parametrize("locale, expected", [("vi", "Yêu cầu Web"), ("en", "Web request"), ("zh", "Web 请求")])
def test_existing_request_without_subject_is_not_described_as_empty_queue(locale, expected):
    rendered = _render_admin_support(locale)
    assert f"<h2>{expected}</h2>" in rendered["untitledDetail"]


@pytest.mark.parametrize(
    "locale, guarded_title, loading_title",
    [
        ("vi", "Yêu cầu không khả dụng", "Đang nạp yêu cầu vận hành"),
        ("en", "Request unavailable", "Loading operational request"),
        ("zh", "请求不可用", "正在加载运营请求"),
    ],
)
def test_admin_support_detail_guarded_and_loading_states_are_localized(locale, guarded_title, loading_title):
    rendered = _render_admin_support(locale)
    assert f"<h2>{guarded_title}</h2>" in rendered["guardedDetail"]
    assert f"<h2>{loading_title}</h2>" in rendered["loadingDetail"]


def test_admin_support_catalogue_has_symmetric_keys_and_locale_specific_anchors() -> None:
    rendered = {locale: _render_admin_support(locale) for locale in ("vi", "en", "zh")}

    assert rendered["vi"]["listTitle"] == "Trung tâm hỗ trợ khách hàng Web"
    assert rendered["en"]["listTitle"] == "Web Customer Support Center"
    assert rendered["zh"]["listTitle"] == "Web 客户支持中心"
    assert rendered["vi"]["detailTitle"] == "Xử lý yêu cầu hỗ trợ"
    assert rendered["en"]["detailTitle"] == "Handle support request"
    assert rendered["zh"]["detailTitle"] == "处理支持请求"

    assert rendered["vi"]["adminKeys"] == rendered["en"]["adminKeys"] == rendered["zh"]["adminKeys"]
    assert len(rendered["vi"]["adminKeys"]) >= 80, (
        "Route-family catalogue must cover list, detail and care controls"
    )


def test_admin_support_renderers_use_the_dedicated_catalogue_not_literal_fixed_copy() -> None:
    source = PORTAL.read_text(encoding="utf-8")
    assert "function adminSupportText" in source
    start = source.index("function renderSupportAdminSummary")
    end = source.index("function renderAccountSettingsNav", start)
    renderers = source[start:end]
    for forbidden in (
        ">Customer Care Board<",
        ">Web-native operations<",
        ">Escalation<",
        ">Tìm case<",
        ">Thread case<",
        ">Timeline hệ thống<",
        '"Manager" : "Operator"',
    ):
        assert forbidden not in renderers
