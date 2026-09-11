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
const guarded={...base,operationsDeskReadState:'failed',operationsDeskSummary:{},operationsDeskItems:[]};
const loading={...base,operationsDeskReadState:'loading',operationsDeskSummary:{},operationsDeskItems:[]};
process.stdout.write(JSON.stringify({ready:api.renderOperationsDesk(page,base),empty:api.renderOperationsDesk(page,empty),guarded:api.renderOperationsDesk(page,guarded),loading:api.renderOperationsDesk(page,loading),title:api.localizedPageTitle(page,base),description:api.localizedPageDescription(page)}));
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
