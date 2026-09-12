"""Executable locale/UX contracts for the read-only Admin work queue."""

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


def _render(locale: str) -> dict[str, str]:
    host = ast.parse((ROOT / "tests/test_a09_admin_operations_locale_purity_contracts.py").read_text(encoding="utf-8"))
    function = next(node for node in host.body if isinstance(node, ast.FunctionDef) and node.name == "_render_admin_operations")
    assignment = next(node for node in function.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "script" for target in node.targets))
    script = ast.literal_eval(assignment.value).split("const api = context.__a09AdminOperations;")[0]
    script = script.replace("renderOperationsAdmin, localizedPageTitle", "renderOperationsDesk, renderOperationsAdmin, localizedPageTitle")
    script += r'''
const api=context.__a09AdminOperations;
const page={path:'/admin/work-queue',routePath:'/admin/work-queue',title:'Operations Desk',section:'Admin ERP',description:'Fallback',action:'none'};
const sources=['support_case','operations_incident','operations_approval','reliability_followup','content_handoff'].map((kind,index)=>({kind,availability:'available',count:index+1}));
const base={...api.normalizeBootstrap({session:{authenticated:true}}),session:{authenticated:true},capabilities:{'operations-desk-view':true},operationsDeskReadState:'ready',operationsDeskSummary:{sources,partial:false},operationsDeskFilter:{kind:'all',state:'all',severity:'all',view:'all'},operationsDeskItems:[{kind:'content_handoff',state:'review',severity:'normal',updated_at:'2026-09-11T00:00:00Z'}],operationsDeskListing:{pagination:{previous_offset:0,next_offset:30}}};
const empty={...base,operationsDeskItems:[],operationsDeskListing:{pagination:{previous_offset:null,next_offset:null}}};
const partialSources=sources.map((source)=>source.kind==='operations_approval'?{kind:source.kind,availability:'guarded',count:null}:source);
const partial={...base,operationsDeskReadState:'guarded',operationsDeskSummary:{sources:partialSources,partial:true}};
const guarded={...base,operationsDeskReadState:'failed',operationsDeskSummary:{},operationsDeskItems:[]};
const loading={...base,operationsDeskReadState:'loading',operationsDeskSummary:{},operationsDeskItems:[]};
process.stdout.write(JSON.stringify({ready:api.renderOperationsDesk(page,base),empty:api.renderOperationsDesk(page,empty),partial:api.renderOperationsDesk(page,partial),guarded:api.renderOperationsDesk(page,guarded),loading:api.renderOperationsDesk(page,loading),title:api.localizedPageTitle(page,base),description:api.localizedPageDescription(page)}));
'''
    result = subprocess.run([shutil.which("node"), "-e", script, str(ROOT / "static/portal/portal-i18n.js"), str(ROOT / "static/portal/portal.js"), locale], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _text(*values: str) -> str:
    parser = _Visible()
    for value in values:
        parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def test_admin_work_queue_is_task_first_and_locale_pure() -> None:
    expected = {
        "vi": ("Bàn điều hành", "Việc cần xử lý", "Chưa có việc phù hợp", "Chưa tải được hàng chờ", "Đang tải hàng chờ"),
        "en": ("Operations desk", "Items to handle", "No matching items", "Queue could not be loaded", "Loading queue"),
        "zh": ("运营工作台", "待处理事项", "没有符合条件的事项", "无法加载队列", "正在加载队列"),
    }
    for locale, anchors in expected.items():
        rendered = _render(locale)
        copy = _text(rendered["ready"], rendered["empty"], rendered["guarded"], rendered["loading"], rendered["title"], rendered["description"])
        assert all(anchor in copy for anchor in anchors), copy
        if locale in ("en", "zh"):
            assert not re.search(r"[ĂÂĐÊÔƠƯăâđêôơư\u1EA0-\u1EF9]", copy), copy
        else:
            for foreign in ("ADMIN ERP", "Operations Desk", "Read-only", "metadata", "available", "authority", "Server-side", "signed session", "staff", "redaction", "queue", "control plane", "write", "retry", "provider", "delivery", "deploy"):
                assert foreign not in copy, copy
        ready = rendered["ready"]
        assert ready.index('data-portal-action="operations-desk-filter"') < ready.index("portal-operations-metrics")
        assert ready.index("portal-operations-desk-work") < ready.index("portal-operations-desk-sources")
        assert 'data-portal-action="operations-desk-page"' in ready
        assert 'data-operations-desk-offset="30"' in ready
        assert 'href="/admin/content-handoffs"' in ready
        assert 'class="portal-operations-desk-guidance"' in ready
        assert '<details class="portal-operations-desk-guidance" open' not in ready
        assert ready.count('data-label=') >= 5


def test_admin_work_queue_error_states_have_no_data_rows() -> None:
    for locale in ("vi", "en", "zh"):
        rendered = _render(locale)
        for state in ("guarded", "loading"):
            assert "portal-data-table" not in rendered[state]


def _action_feedback(locale: str) -> dict[str, object]:
    integration = (ROOT / "static/portal/integration.js").read_text(encoding="utf-8")
    assert "function adminWorkQueueText(key, fallback, params)" in integration
    helper_start = integration.index("  function adminWorkQueueText(key, fallback, params)")
    helper_end = integration.index("\n  function ", helper_start + 2)
    helper = integration[helper_start:helper_end]
    action_start = integration.index('      if (action === "operations-desk-refresh")')
    action_end = integration.index('      if (action === "admin-automation-monitor-refresh")', action_start)
    actions = integration[action_start:action_end]
    script = r'''
const fs=require("fs"),vm=require("vm");
const locale=process.argv[2];
const context={console,Intl,navigator:{language:locale},document:{documentElement:{lang:locale,dir:"ltr",setAttribute(){},getAttribute(){return "";},removeAttribute(){}}},CustomEvent:function(){},addEventListener(){},removeEventListener(){},dispatchEvent(){return true;}};
context.window=context;context.globalThis=context;
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),context);
context.TOANAASI18n.setLocale(locale,{emit:false});
const window=context;
let state={operationsDeskReadState:"ready",capabilities:{"operations-desk-view":true,"operations-desk-filter":true,"operations-desk-page":true}};
let current=[];
function base(){return state;}
async function hydrateOperationsDesk(){return {};}
function toast(message,tone){current.push({message,tone:tone||""});}
function operationsDeskFilterPayload(fields){return fields;}
function operationsDeskOffset(value){return Number(value);}
''' + helper + r'''
async function dispatch(action,fields){
''' + actions + r'''
}
async function run(mode){
  const results={};
  for(const action of ["operations-desk-refresh","operations-desk-filter","operations-desk-filter-clear","operations-desk-page"]){
    current=[];
    state={operationsDeskReadState:mode,capabilities:mode==="denied"?{}:{"operations-desk-view":true,"operations-desk-filter":true,"operations-desk-page":true}};
    try{await dispatch(action,{kind:"all",state:"all",severity:"all",view:"all",__operationsDeskOffset:30});results[action]=current[0]||{};}
    catch(error){results[action]={error:String(error&&error.message||error)};}
  }
  return results;
}
(async()=>process.stdout.write(JSON.stringify({ready:await run("ready"),failed:await run("failed"),denied:await run("denied")})))().catch((error)=>{console.error(error);process.exit(1);});
'''
    result = subprocess.run(
        [shutil.which("node"), "-e", script, str(ROOT / "static/portal/portal-i18n.js"), locale],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_admin_work_queue_partial_copy_is_truthful_in_all_locales() -> None:
    expected = {
        "vi": ("Số lượng theo từng nhóm công việc từ máy chủ.", "Có nguồn chưa xác minh", "năm nhóm công việc đã kiểm tra"),
        "en": ("Counts by work type from the server.", "Some sources are not verified", "five verified work sources"),
        "zh": ("服务器按事项类型提供数量。", "部分来源尚未验证", "五个已检查的工作来源"),
    }
    for locale, (neutral, guarded, false_claim) in expected.items():
        copy = _text(_render(locale)["partial"])
        assert neutral in copy
        assert guarded in copy
        assert false_claim not in copy
        assert "—" in copy
    renderer = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
    start = renderer.index("function renderOperationsDesk(page, context)")
    end = renderer.index("function renderOperationsAdmin(page, context)", start)
    source = renderer[start:end]
    assert 'copy("sources.body", "Số lượng theo từng nhóm công việc từ máy chủ.")' in source
    assert "Số lượng được tổng hợp từ năm nhóm công việc đã kiểm tra." not in source


def test_admin_work_queue_action_feedback_is_locale_pure() -> None:
    expected = {
        "vi": {
            "ready": ["Đã làm mới hàng chờ.", "Đã áp dụng bộ lọc.", "Đã xóa bộ lọc.", "Đã tải trang danh sách."],
            "failed": ["Chưa thể làm mới hàng chờ.", "Chưa thể áp dụng bộ lọc.", "Chưa thể xóa bộ lọc.", "Chưa thể tải trang danh sách."],
            "denied": ["Bạn chưa có quyền xem hàng chờ.", "Bạn chưa có quyền lọc hàng chờ.", "Bạn chưa có quyền lọc hàng chờ.", "Bạn chưa có quyền chuyển trang danh sách."],
        },
        "en": {
            "ready": ["Queue refreshed.", "Filters applied.", "Filters cleared.", "Queue page loaded."],
            "failed": ["Queue could not be refreshed.", "Filters could not be applied.", "Filters could not be cleared.", "Queue page could not be loaded."],
            "denied": ["You do not have permission to view this queue.", "You do not have permission to filter this queue.", "You do not have permission to filter this queue.", "You do not have permission to change queue pages."],
        },
        "zh": {
            "ready": ["队列已刷新。", "筛选已应用。", "筛选已清除。", "队列页面已加载。"],
            "failed": ["无法刷新队列。", "无法应用筛选。", "无法清除筛选。", "无法加载队列页面。"],
            "denied": ["您无权查看此队列。", "您无权筛选此队列。", "您无权筛选此队列。", "您无权切换队列页面。"],
        },
    }
    actions = ["operations-desk-refresh", "operations-desk-filter", "operations-desk-filter-clear", "operations-desk-page"]
    for locale, states in expected.items():
        feedback = _action_feedback(locale)
        assert [feedback["ready"][action]["message"] for action in actions] == states["ready"]
        assert [feedback["failed"][action]["message"] for action in actions] == states["failed"]
        assert [feedback["denied"][action]["error"] for action in actions] == states["denied"]


def test_admin_work_queue_mobile_table_has_a_scoped_vertical_layout() -> None:
    css = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")
    marker = "/* A09 Admin Work Queue */"
    assert css.count(marker) == 1
    layer = css[css.index(marker):]
    for required in (
        ".portal-page.portal-operations-desk .portal-operations-desk-work {",
        ".portal-page.portal-operations-desk .portal-operations-desk-guidance {",
        "@media (max-width: 900px)",
        ".portal-page.portal-operations-desk .portal-operations-desk-table thead {",
        "display: none;",
        ".portal-page.portal-operations-desk .portal-data-table-scroll-hint {",
        ".portal-page.portal-operations-desk .portal-operations-desk-table tbody tr {",
        "grid-template-columns: minmax(0, 1fr);",
        ".portal-page.portal-operations-desk .portal-operations-desk-table td::before {",
        "content: attr(data-label);",
        "min-height: 44px;",
    ):
        assert required in layer
    clean = re.sub(r"/\*.*?\*/", "", layer, flags=re.DOTALL)
    assert "#" not in clean
    assert "rgba(" not in clean
