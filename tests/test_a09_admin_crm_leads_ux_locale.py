"""Executable locale/UX contracts for the read-only Admin CRM directory."""

import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


class _Visible(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _text(*values: str) -> str:
    parser = _Visible()
    for value in values:
        parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _render(locale: str) -> dict[str, str]:
    host = ast.parse((ROOT / "tests/test_a09_admin_operations_locale_purity_contracts.py").read_text(encoding="utf-8"))
    function = next(node for node in host.body if isinstance(node, ast.FunctionDef) and node.name == "_render_admin_operations")
    assignment = next(node for node in function.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "script" for target in node.targets))
    script = ast.literal_eval(assignment.value).split("const api = context.__a09AdminOperations;")[0]
    script = script.replace("renderOperationsAdmin, localizedPageTitle", "renderPartnerCrmManager, renderOperationsAdmin, localizedPageTitle")
    script += r'''
const api=context.__a09AdminOperations;
const page={path:'/admin/crm/leads',routePath:'/admin/crm/leads',title:'CRM Manager Directory',section:'CRM',description:'Fallback',action:'none'};
const row={lead_kind:'partner',stage:'review',consent_status:'documented',revision:2,updated_at:'2026-09-12T00:00:00Z'};
const base={...api.normalizeBootstrap({session:{authenticated:true}}),session:{authenticated:true},capabilities:{'partner-crm-view':true},partnerCrmReadState:'ready',pageStates:{'/admin/crm/leads':'read_only'},partnerCrmManagerDirectory:[row],partnerCrmManagerListing:{filters:{stage:'all'},pagination:{limit:50,offset:50,returned:1,has_more:true,previous_offset:0,next_offset:100}}};
const empty={...base,partnerCrmManagerDirectory:[],partnerCrmManagerListing:{filters:{stage:'all'},pagination:{limit:50,offset:0,returned:0,has_more:false,previous_offset:null,next_offset:null}}};
const guarded={...base,partnerCrmReadState:'guarded',pageStates:{'/admin/crm/leads':'guarded'},partnerCrmManagerDirectory:[]};
const loading={...base,partnerCrmReadState:'loading',pageStates:{'/admin/crm/leads':'processing'},partnerCrmManagerDirectory:[]};
process.stdout.write(JSON.stringify({ready:api.renderPartnerCrmManager(page,base),empty:api.renderPartnerCrmManager(page,empty),guarded:api.renderPartnerCrmManager(page,guarded),loading:api.renderPartnerCrmManager(page,loading),title:api.localizedPageTitle(page,base),description:api.localizedPageDescription(page)}));
'''
    result = subprocess.run(
        [shutil.which("node"), "-e", script, str(ROOT / "static/portal/portal-i18n.js"), str(ROOT / "static/portal/portal.js"), locale],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_admin_crm_directory_is_task_first_anonymous_and_locale_pure() -> None:
    expected = {
        "vi": ("Theo dõi khách hàng tiềm năng", "Danh sách cần theo dõi", "Chưa có mục phù hợp", "Chưa tải được danh sách", "Đang tải danh sách"),
        "en": ("Lead monitoring", "Leads to monitor", "No matching leads", "Lead directory could not be loaded", "Loading lead directory"),
        "zh": ("潜在客户跟进", "待跟进名单", "没有符合条件的潜在客户", "无法加载潜在客户目录", "正在加载潜在客户目录"),
    }
    for locale, anchors in expected.items():
        rendered = _render(locale)
        copy = _text(rendered["ready"], rendered["empty"], rendered["guarded"], rendered["loading"], rendered["title"], rendered["description"])
        assert all(anchor in copy for anchor in anchors), copy
        if locale in ("en", "zh"):
            assert not re.search(r"[ĂÂĐÊÔƠƯăâđêôơư\u1EA0-\u1EF9]", copy), copy
        else:
            for foreign in ("CRM Manager Directory", "Server-redacted", "read only", "stage", "lead", "metadata", "pipeline", "redact", "owner", "opportunity", "notes", "control", "cross-account", "Directory", "Consent"):
                assert not re.search(rf"(?<![\w-]){re.escape(foreign)}(?![\w-])", copy, re.IGNORECASE), copy
        ready = rendered["ready"]
        assert ready.index('data-portal-action="partner-crm-manager-filter"') < ready.index("portal-admin-crm-directory-results")
        assert 'data-portal-action="partner-crm-manager-page"' in ready
        assert 'data-partner-crm-manager-offset="100"' in ready
        assert 'class="portal-admin-crm-guidance"' in ready
        assert '<details class="portal-admin-crm-guidance" open' not in ready
        assert ready.count("data-label=") >= 4
        for private in ("lead_id", "owner_account_id", "owner_display_name", "contact_email", "opportunity_summary", "tags", "notes"):
            assert private not in ready


def test_admin_crm_guarded_and_empty_never_render_stale_rows() -> None:
    for locale in ("vi", "en", "zh"):
        rendered = _render(locale)
        assert "portal-data-table" not in rendered["guarded"]
        assert "portal-data-table" not in rendered["loading"]
        assert "portal-data-table" not in rendered["empty"]
        assert 'aria-busy="true"' in rendered["loading"]


def _action_feedback(locale: str) -> dict[str, object]:
    integration = (ROOT / "static/portal/integration.js").read_text(encoding="utf-8")
    assert "function adminCrmManagerText(key, fallback, params)" in integration
    helper_start = integration.index("  function adminCrmManagerText(key, fallback, params)")
    helper_end = integration.index("\n  function ", helper_start + 2)
    helper = integration[helper_start:helper_end]
    action_start = integration.index('      if (action === "partner-crm-refresh")')
    action_end = integration.index('      if (action === "partner-crm-create")', action_start)
    actions = integration[action_start:action_end]
    script = r'''
const fs=require("fs"),vm=require("vm");
const locale=process.argv[2];
const context={console,Intl,navigator:{language:locale},document:{documentElement:{lang:locale,dir:"ltr",setAttribute(){},getAttribute(){return "";},removeAttribute(){}}},CustomEvent:function(){},addEventListener(){},removeEventListener(){},dispatchEvent(){return true;}};
context.window=context;context.globalThis=context;
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),context);
context.TOANAASI18n.setLocale(locale,{emit:false});
const window=context;
let state={partnerCrmReadState:"ready",capabilities:{"partner-crm-view":true}};
let current=[];
function base(){return state;}
function partnerCrmLeadIdFromPath(){return "";}
async function hydratePartnerCrmLead(){}
async function hydratePartnerCrm(){}
async function hydratePartnerCrmManagerDirectory(){}
function partnerCrmManagerStage(value){return ["all","review"].includes(String(value))?String(value):"all";}
function partnerCrmListOffset(value){return Number(value)||0;}
function toast(message,tone){current.push({message,tone:tone||""});}
''' + helper + r'''
async function dispatch(action,fields){const route="/admin/crm/leads";const detail={};
''' + actions + r'''
}
async function one(mode,action,fields){current=[];state={partnerCrmReadState:mode,capabilities:mode==="denied"?{}:{"partner-crm-view":true}};try{await dispatch(action,fields||{});return current[0]||{};}catch(error){return {error:String(error&&error.message||error)};}}
(async()=>process.stdout.write(JSON.stringify({
  ready:[await one("ready","partner-crm-refresh"),await one("ready","partner-crm-manager-filter",{stage:"all"}),await one("ready","partner-crm-manager-filter",{stage:"review"}),await one("ready","partner-crm-manager-page",{__partnerCrmManagerStage:"all",__partnerCrmManagerOffset:50})],
  guarded:[await one("guarded","partner-crm-refresh"),await one("guarded","partner-crm-manager-filter",{stage:"all"}),await one("guarded","partner-crm-manager-page",{__partnerCrmManagerStage:"all",__partnerCrmManagerOffset:50})],
  denied:[await one("denied","partner-crm-refresh"),await one("denied","partner-crm-manager-filter",{stage:"all"}),await one("denied","partner-crm-manager-page",{__partnerCrmManagerStage:"all",__partnerCrmManagerOffset:50})]
})))().catch((error)=>{console.error(error);process.exit(1);});
'''
    result = subprocess.run(
        [shutil.which("node"), "-e", script, str(ROOT / "static/portal/portal-i18n.js"), locale],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_admin_crm_action_feedback_is_locale_pure() -> None:
    expected = {
        "vi": {
            "ready": ["Đã làm mới danh sách.", "Đã hiển thị tất cả giai đoạn.", "Đã lọc theo giai đoạn.", "Đã tải trang danh sách."],
            "guarded": ["Chưa thể làm mới danh sách.", "Chưa thể áp dụng bộ lọc.", "Chưa thể tải trang danh sách."],
            "denied": ["Bạn chưa có quyền xem danh sách.", "Bạn chưa có quyền lọc danh sách.", "Bạn chưa có quyền chuyển trang danh sách."],
        },
        "en": {
            "ready": ["Lead directory refreshed.", "All stages are shown.", "Directory filtered by stage.", "Lead directory page loaded."],
            "guarded": ["Lead directory could not be refreshed.", "Filters could not be applied.", "Lead directory page could not be loaded."],
            "denied": ["You do not have permission to view this directory.", "You do not have permission to filter this directory.", "You do not have permission to change directory pages."],
        },
        "zh": {
            "ready": ["潜在客户目录已刷新。", "已显示所有阶段。", "已按阶段筛选目录。", "潜在客户目录页面已加载。"],
            "guarded": ["无法刷新潜在客户目录。", "无法应用筛选。", "无法加载潜在客户目录页面。"],
            "denied": ["您无权查看此目录。", "您无权筛选此目录。", "您无权切换目录页面。"],
        },
    }
    for locale, states in expected.items():
        feedback = _action_feedback(locale)
        assert [item["message"] for item in feedback["ready"]] == states["ready"]
        assert [item["message"] for item in feedback["guarded"]] == states["guarded"]
        assert [item["error"] for item in feedback["denied"]] == states["denied"]


def test_admin_crm_mobile_directory_has_a_scoped_vertical_layout() -> None:
    css = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")
    marker = "/* A09 Admin CRM Leads */"
    assert css.count(marker) == 1
    layer = css[css.index(marker):]
    for required in (
        ".portal-page.portal-admin-crm-manager {",
        ".portal-page.portal-admin-crm-manager .portal-admin-crm-work {",
        ".portal-page.portal-admin-crm-manager .portal-admin-crm-filter .portal-field > span {",
        "color: var(--portal-ink);",
        ".portal-page.portal-admin-crm-manager .portal-admin-crm-filter .portal-form-note {",
        "color: var(--portal-muted);",
        ".portal-page.portal-admin-crm-manager .portal-admin-crm-guidance {",
        "@media (max-width: 900px)",
        ".portal-page.portal-admin-crm-manager .portal-admin-crm-table thead {",
        "display: none;",
        ".portal-page.portal-admin-crm-manager .portal-admin-crm-table tbody tr {",
        "grid-template-columns: minmax(0, 1fr);",
        ".portal-page.portal-admin-crm-manager .portal-admin-crm-table td::before {",
        "content: attr(data-label);",
        "min-height: 44px;",
    ):
        assert required in layer
    clean = re.sub(r"/\*.*?\*/", "", layer, flags=re.DOTALL)
    assert "#" not in clean
    assert "rgba(" not in clean
