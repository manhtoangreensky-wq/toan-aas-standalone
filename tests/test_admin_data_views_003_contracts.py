"""Contracts for read-only Admin data views over rendered table text."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL = PORTAL_PATH.read_text(encoding="utf-8")
I18N = (ROOT / "static/portal/portal-i18n.js").read_text(encoding="utf-8")
THEME = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _run_node(body: str) -> dict[str, object]:
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing ${start}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end ${end}`);
  return source.slice(offset, finish);
}
function safeText(value) { return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;"); }
function uiText(key, fallback, params) {
  let value = fallback;
  Object.entries(params || {}).forEach(([name, replacement]) => value = value.replaceAll(`{${name}}`, String(replacement)));
  return value;
}
function adminDataViewText(key, fallback, params) { return uiText(`adminDataView.${key}`, fallback, params); }
const ALLOWED_STATES = new Set(["ready", "guarded", "failed", "read_only"]);
function badge(state) { return ["ready", "guarded", "read_only"].includes(state) ? "" : `<span data-status="${state}">STATE:${state}</span>`; }
function stateLabel(state) { return `STATE:${state}`; }
eval(extract("function adminDataStatusCell", "function adminJobActions"));
''' + body
    result = subprocess.run(
        ["node", "-e", script, str(PORTAL_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_controls_and_inspector_render_only_for_server_granted_item_arrays() -> None:
    result = _run_node(
        r'''
const table = '<div class="portal-data-table-wrap"><table><tbody><tr><td>U-1</td></tr></tbody></table></div>';
const granted = renderAdminDataSurface("users", { items: [{ user_id: "U-1" }] }, table);
const emptyGranted = renderAdminDataSurface("users", { items: [] }, table);
const guarded = renderAdminDataSurface("users", { compatibility_guarded: true }, table);
const unavailable = renderAdminDataSurface("users", {}, table);
const inspect = (html) => ({
  controls: html.includes("data-admin-data-view-controls"),
  layout: html.includes('class="portal-admin-data-layout"'),
  list: html.includes("data-admin-data-list"),
  inspector: html.includes("data-admin-data-inspector") && html.includes("data-admin-data-inspector-body"),
  noResults: html.includes("data-admin-data-no-results"),
  contentOnce: html.split("U-1").length - 1
});
process.stdout.write(JSON.stringify({
  granted: inspect(granted),
  emptyGranted: inspect(emptyGranted),
  guarded: inspect(guarded),
  unavailable: inspect(unavailable),
  controlsBeforeLayout: granted.indexOf("data-admin-data-view-controls") < granted.indexOf("portal-admin-data-layout")
}));
'''
    )

    full = {"controls": True, "layout": True, "list": True, "inspector": True, "noResults": True, "contentOnce": 1}
    none = {"controls": False, "layout": False, "list": False, "inspector": False, "noResults": False, "contentOnce": 1}
    assert result == {
        "granted": full,
        "emptyGranted": full,
        "guarded": none,
        "unavailable": none,
        "controlsBeforeLayout": True,
    }


def test_dom_filtering_matches_accents_status_counts_and_no_results() -> None:
    result = _run_node(
        r'''
function row(text, status) {
  return {
    innerText: text, hidden: false,
    querySelector(selector) { return selector === "[data-status]" ? { getAttribute() { return status; } } : null; },
    getAttribute(name) { return name === "aria-selected" ? "false" : null; }
  };
}
const rows = [row("P-1 Thanh toán Hoàn tất", "completed"), row("J-2 Dựng video Đang xử lý", "processing"), row("U-3 Người dùng", "queued")];
const search = { value: "" }, status = { value: "all" }, clear = { disabled: false }, count = { textContent: "" }, noResults = { hidden: true };
const surface = {
  querySelector(selector) { return ({ "[data-admin-data-search]": search, "[data-admin-data-status]": status, "[data-admin-data-clear]": clear, "[data-admin-data-filter-count]": count, "[data-admin-data-no-results]": noResults })[selector] || null; },
  querySelectorAll(selector) { return selector === "[data-admin-data-row]" ? rows : []; }
};
const snapshot = () => ({ visible: rows.filter((item) => !item.hidden).map((item) => item.innerText), count: count.textContent, clearDisabled: clear.disabled, noResultsHidden: noResults.hidden });
applyAdminDataViewFilters(surface);
const initial = snapshot();
search.value = "thanh toan";
applyAdminDataViewFilters(surface);
const accent = snapshot();
status.value = "processing";
applyAdminDataViewFilters(surface);
const mismatch = snapshot();
search.value = "";
applyAdminDataViewFilters(surface);
const statusOnly = snapshot();
search.value = "khong ton tai";
status.value = "all";
applyAdminDataViewFilters(surface);
const none = snapshot();
search.value = "";
status.value = "all";
applyAdminDataViewFilters(surface);
const cleared = snapshot();
process.stdout.write(JSON.stringify({ initial, accent, mismatch, statusOnly, none, cleared }));
'''
    )

    assert result == {
        "initial": {"visible": ["P-1 Thanh toán Hoàn tất", "J-2 Dựng video Đang xử lý", "U-3 Người dùng"], "count": "3/3 bản ghi", "clearDisabled": True, "noResultsHidden": True},
        "accent": {"visible": ["P-1 Thanh toán Hoàn tất"], "count": "1/3 bản ghi", "clearDisabled": False, "noResultsHidden": True},
        "mismatch": {"visible": [], "count": "0/3 bản ghi", "clearDisabled": False, "noResultsHidden": False},
        "statusOnly": {"visible": ["J-2 Dựng video Đang xử lý"], "count": "1/3 bản ghi", "clearDisabled": False, "noResultsHidden": True},
        "none": {"visible": [], "count": "0/3 bản ghi", "clearDisabled": False, "noResultsHidden": False},
        "cleared": {"visible": ["P-1 Thanh toán Hoàn tất", "J-2 Dựng video Đang xử lý", "U-3 Người dùng"], "count": "3/3 bản ghi", "clearDisabled": True, "noResultsHidden": True},
    }


def test_selection_projects_visible_cells_as_text_and_skips_action_only_cells() -> None:
    result = _run_node(
        r'''
class FakeNode {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.textContent = ""; this.attributes = {}; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = [...nodes]; this.textContent = ""; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] || null; }
}
global.document = { createElement(tag) { return new FakeNode(tag); } };
const headers = ["Mã", "Tên", "Trạng thái", "Thao tác"] .map((text) => ({ innerText: text }));
function cell(text, actionOnly) {
  return {
    innerText: text,
    querySelector(selector) { return actionOnly && selector.includes("button") ? {} : null; },
    cloneNode() { const clone = { innerText: actionOnly ? "" : text, querySelectorAll() { return actionOnly ? [{ remove() { clone.innerText = ""; } }] : []; } }; return clone; }
  };
}
const table = { querySelectorAll(selector) { return selector === "thead th" ? headers : []; } };
const body = new FakeNode("div"), announcement = new FakeNode("p");
const inspector = { getAttribute(name) { return name === "data-admin-data-inspector-prompt" ? "Chọn một dòng" : null; } };
const classes = new Set();
const row = {
  hidden: false, attributes: { "aria-selected": "false" },
  classList: { add(value) { classes.add(value); }, remove(value) { classes.delete(value); } },
  setAttribute(name, value) { this.attributes[name] = String(value); }, getAttribute(name) { return this.attributes[name]; },
  querySelectorAll(selector) { return selector === "td" ? [cell("U-1", false), cell("<img onerror=global.xss=1>", false), cell("Hoàn tất", false), cell("Xóa", true)] : []; },
  closest(selector) { return selector === "table" ? table : (selector.includes("portal-admin-data-surface") ? surface : null); }
};
const other = { attributes: { "aria-selected": "true" }, classList: { remove() {} }, setAttribute(name, value) { this.attributes[name] = String(value); } };
const surface = {
  querySelector(selector) { return ({ "[data-admin-data-inspector]": inspector, "[data-admin-data-inspector-body]": body, "[data-admin-data-selection-announcement]": announcement })[selector] || null; },
  querySelectorAll(selector) { return selector === "[data-admin-data-row]" ? [row, other] : []; }
};
global.xss = 0;
selectAdminDataViewRow(row);
const dl = body.children[0];
const fields = dl.children.map((node) => [node.tagName, node.textContent]);
const selected = { row: row.attributes["aria-selected"], other: other.attributes["aria-selected"], classSelected: classes.has("is-selected"), announcement: announcement.textContent, fields, xss: global.xss };
clearAdminDataViewSelection(surface);
process.stdout.write(JSON.stringify({ selected, cleared: { aria: row.attributes["aria-selected"], body: body.textContent, childCount: body.children.length } }));
'''
    )

    assert result == {
        "selected": {
            "row": "true", "other": "false", "classSelected": True, "announcement": "Đã chọn bản ghi",
            "fields": [["DT", "Mã"], ["DD", "U-1"], ["DT", "Tên"], ["DD", "<img onerror=global.xss=1>"], ["DT", "Trạng thái"], ["DD", "Hoàn tất"]],
            "xss": 0,
        },
        "cleared": {"aria": "false", "body": "Chọn một dòng", "childCount": 0},
    }

    interactions = _between(PORTAL, "function bindInteractions()", "function bindVideoPreviewPlayer")
    assert 'closest("[data-admin-data-row]")' in interactions
    assert 'closest("a,button,input,select,textarea,summary")' in interactions
    assert 'event.key === "Enter" || event.key === " "' in interactions
    assert "selectAdminDataViewRow" in interactions


def test_locale_ticket_copy_and_scoped_responsive_css_are_complete() -> None:
    keys = (
        "searchLabel", "searchPlaceholder", "statusLabel", "allStatuses", "clearFilters", "resultCount",
        "noResultsTitle", "noResultsBody", "inspectorTitle", "inspectorPrompt", "selectedAnnouncement", "detailsColumn",
        "ticketColumn.ticket", "ticketColumn.type", "ticketColumn.priority", "ticketColumn.status",
        "ticketColumn.attachment", "ticketColumn.updatedAt", "yes", "no",
    )
    exact = {
        "searchLabel": ("Tìm trong bảng", "Search table"),
        "searchPlaceholder": ("Tìm theo nội dung đang hiển thị", "Search visible content"),
        "statusLabel": ("Trạng thái", "Status"),
        "allStatuses": ("Tất cả trạng thái", "All statuses"),
        "clearFilters": ("Xóa bộ lọc", "Clear filters"),
        "resultCount": ("{visible}/{total} bản ghi", "{visible}/{total} records"),
        "noResultsTitle": ("Không có kết quả phù hợp", "No matching results"),
        "noResultsBody": ("Thử đổi từ khóa hoặc trạng thái.", "Try another keyword or status."),
        "inspectorTitle": ("Chi tiết bản ghi", "Record details"),
        "inspectorPrompt": ("Chọn một dòng để xem các trường đã được máy chủ cấp.", "Select a row to review the server-granted fields."),
        "selectedAnnouncement": ("Đã chọn bản ghi", "Record selected"),
        "yes": ("Có", "Yes"), "no": ("Không", "No"),
    }
    for key in keys:
        assert I18N.count(f'"adminDataView.{key}"') == 3
    for key, (vi, en) in exact.items():
        assert f'"adminDataView.{key}": "{vi}"' in I18N
        assert f'"adminDataView.{key}": "{en}"' in I18N

    ticket = _between(PORTAL, 'if (["tickets", "support"].includes(module))', 'if (module === "audit")')
    for key in ("ticketColumn.ticket", "ticketColumn.type", "ticketColumn.priority", "ticketColumn.status", "ticketColumn.attachment", "ticketColumn.updatedAt", "yes", "no"):
        assert f'adminDataViewText("{key}"' in ticket
    assert '["Ticket", "Loại", "Ưu tiên", "Trạng thái", "Đính kèm", "Cập nhật"]' not in ticket
    assert '? "Có" : "Không"' not in ticket

    marker = "/* Admin Data Views 003 ---------------------------------------------- */"
    css = THEME[THEME.index(marker) :]
    root = '.portal-shell[data-portal-app-kind="admin"] .portal-admin-data-layout'
    for contract in (
        f"{root} {{", "grid-template-columns: minmax(560px, 1fr) minmax(280px, 340px);",
        "position: sticky;", "min-height: 44px;", "outline: 3px solid var(--portal-focus);",
        "@media (max-width: 1100px)", "grid-template-columns: minmax(0, 1fr);", "position: static;",
        "@media (max-width: 700px)", "font-size: 16px;", "overflow-x: auto;",
    ):
        assert contract in css
    assert not re.search(r"#[0-9a-fA-F]{3,8}|rgba?\(|gradient|glow|!important|@keyframes|animation:|transition:", css)


def test_desktop_data_page_owns_full_outer_width_and_primary_list_track() -> None:
    renderer = _between(PORTAL, "function renderAdmin(page, context)", "const BOT_COMPANION_COMMAND_PATTERN")
    assert 'const pageClass = " portal-admin-data-page"' in renderer
    assert 'portal-admin-audit' in renderer and 'portal-admin-runtime' in renderer
    marker = "/* Admin Data Views 003 ---------------------------------------------- */"
    css = THEME[THEME.index(marker) :]
    assert '.portal-shell[data-portal-app-kind="admin"] .portal-page.portal-admin-data-page > .portal-work-grid {' in css
    assert "grid-template-columns: minmax(0, 1fr);" in css
    layout = re.search(re.escape('.portal-shell[data-portal-app-kind="admin"] .portal-admin-data-layout') + r"\s*\{([^{}]*)\}", css)
    assert layout and "grid-template-columns: minmax(560px, 1fr) minmax(280px, 340px);" in layout.group(1)


def test_ticket_lifecycle_labels_are_locale_owned_for_vi_en_zh() -> None:
    statuses = ("new", "reviewing", "waitingUser", "waitingProvider", "refundPending", "resolved", "closed", "unknown")
    for status in statuses:
        assert I18N.count(f'"adminDataView.ticketStatus.{status}"') == 3
    labels = _between(PORTAL, "function ticketStatusLabel(item)", "function ticketCategoryLabel(item)")
    assert "adminDataViewText" in labels
    assert "TICKET_STATUS_LABELS[canonical]" not in labels
    for canonical, key in (("new", "new"), ("reviewing", "reviewing"), ("closed", "closed")):
        assert f'{canonical}: "{key}"' in labels
    assert '"adminDataView.ticketStatus.new": "Mới"' in I18N
    assert '"adminDataView.ticketStatus.new": "New"' in I18N
    assert '"adminDataView.ticketStatus.reviewing": "Under review"' in I18N
    assert '"adminDataView.ticketStatus.closed": "Closed"' in I18N


def test_provider_status_cells_keep_ready_guarded_failed_visible_for_filters() -> None:
    result = _run_node(r'''
const html = ["ready", "guarded", "failed"].map(adminDataStatusCell).join("");
const statuses = Array.from(html.matchAll(/data-status="([^"]+)"/g), match => match[1]);
global.document = { createElement() { return { value: "", textContent: "" }; } };
const rows = statuses.map(status => ({ innerText: status, hidden: false, attributes: {}, classList: { remove() {} }, setAttribute(name, value) { this.attributes[name] = String(value); }, getAttribute(name) { return this.attributes[name] || null; }, querySelector(selector) { return selector === ".portal-empty-cell" ? null : (selector === "[data-status]" ? { getAttribute() { return status; } } : null); } }));
const select = { value: "all", children: [], getAttribute() { return "ALL"; }, replaceChildren(...items) { this.children = items; }, append(item) { this.children.push(item); } }, search = { value: "" }, clear = {}, output = {}, noResults = {};
const surface = { querySelector(selector) { return ({ "[data-admin-data-status]": select, "[data-admin-data-search]": search, "[data-admin-data-clear]": clear, "[data-admin-data-filter-count]": output, "[data-admin-data-no-results]": noResults })[selector] || null; }, querySelectorAll(selector) { return selector === "tbody tr" || selector === "[data-admin-data-row]" ? rows : []; } };
syncAdminDataViewRows({ querySelectorAll() { return [surface]; } });
process.stdout.write(JSON.stringify({ statuses, options: select.children.map(item => item.value), labels: ["STATE:ready", "STATE:guarded", "STATE:failed"].every(label => html.includes(label)) }));
''')
    assert result == {"statuses": ["ready", "guarded", "failed"], "options": ["all", "ready", "guarded", "failed"], "labels": True}
    provider = _between(PORTAL, 'if (["providers", "provider-cost", "features", "freezes", "pricing", "promos"].includes(module))', 'if (["tickets", "support"].includes(module))')
    assert 'adminDataStatusCell(jobStatus(item))' in provider
