"""Executable locale/UX contracts for the staff Content Handoff queue."""

import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def _render(locale: str) -> dict[str, object]:
    host = ast.parse(
        (ROOT / "tests/test_a09_admin_operations_locale_purity_contracts.py").read_text(encoding="utf-8")
    )
    function = next(
        node for node in host.body
        if isinstance(node, ast.FunctionDef) and node.name == "_render_admin_operations"
    )
    assignment = next(
        node for node in function.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "script" for target in node.targets)
    )
    script = ast.literal_eval(assignment.value).split("const api = context.__a09AdminOperations;")[0]
    script = script.replace(
        "renderOperationsAdmin, localizedPageTitle",
        "renderContentHandoffAdmin, renderOperationsAdmin, localizedPageTitle",
    )
    script += r'''
const api=context.__a09AdminOperations;
const page={path:'/admin/content-handoffs',routePath:'/admin/content-handoffs',title:'Content Handoff Queue',section:'Admin ERP',description:'Fallback',action:'none'};
const record={
  id:'8a0d55e2-2287-4387-8bd1-3774a56f023f',revision:2,
  handoff_status:'review',record_state:'active',references:{},
  title:'QA 7429',purpose:'Purpose 7429',staff_note:''
};
const normalized=api.normalizeBootstrap({session:{authenticated:true}});
const populated={...normalized,session:{authenticated:true},pageStates:{'/admin/content-handoffs':'read_only'},contentHandoffStaffRole:'manager',contentHandoffStaffQueue:[record],contentHandoffStaffListing:{filters:{status:'all'},pagination:{offset:10,returned:1,previous_offset:0,has_more:true,next_offset:20}}};
const empty={...populated,contentHandoffStaffRole:'operator',contentHandoffStaffQueue:[],contentHandoffStaffListing:{filters:{status:'all'},pagination:{offset:0,returned:0,previous_offset:null,has_more:false,next_offset:null}}};
const guarded={...normalized,session:{authenticated:true},pageStates:{'/admin/content-handoffs':'guarded'},contentHandoffStaffRole:'none',contentHandoffStaffQueue:[]};
process.stdout.write(JSON.stringify({
  populated:api.renderContentHandoffAdmin(page,populated),
  empty:api.renderContentHandoffAdmin(page,empty),
  guarded:api.renderContentHandoffAdmin(page,guarded),
  title:api.localizedPageTitle(page,populated),
  description:api.localizedPageDescription(page)
}));
'''
    result = subprocess.run(
        [shutil.which("node"), "-e", script, str(ROOT / "static/portal/portal-i18n.js"), str(ROOT / "static/portal/portal.js"), locale],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _text(*markup: object) -> str:
    parser = _VisibleText()
    for value in markup:
        parser.feed(str(value))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def test_staff_handoff_queue_is_locale_pure_and_task_first() -> None:
    rendered = {locale: _render(locale) for locale in ("vi", "en", "zh")}
    expected = {
        "vi": ("Hàng chờ bàn giao nội dung", "Việc cần duyệt", "Chưa có nội dung chờ duyệt", "Chưa tải được hàng chờ"),
        "en": ("Content handoff queue", "Items to review", "No content awaiting review", "Queue could not be loaded"),
        "zh": ("内容交接队列", "待审核事项", "暂无待审核内容", "无法加载队列"),
    }
    for locale, anchors in expected.items():
        copy = _text(
            rendered[locale]["populated"], rendered[locale]["empty"], rendered[locale]["guarded"],
            rendered[locale]["title"], rendered[locale]["description"],
        ).replace("QA 7429", " ").replace("Purpose 7429", " ")
        assert all(anchor in copy for anchor in anchors), copy
        if locale in ("en", "zh"):
            assert not re.search(r"[ĂÂĐÊÔƠƯăâđêôơư\u1EA0-\u1EF9]", copy), copy
        else:
            for foreign in (
                "ADMIN ERP", "Customer Care", "Content Handoff", "server-authorized", "Role",
                "Manager", "Operator", "write", "decision", "publish", "delivery", "provider",
                "payment", "external", "recipient", "path",
            ):
                assert foreign not in copy, copy
        html = str(rendered[locale]["populated"])
        assert html.index("content-handoff-staff-filter") < html.index("portal-coordination-card-list")
        assert 'name="record_id" value="8a0d55e2-2287-4387-8bd1-3774a56f023f"' in html
        assert 'name="expected_revision" value="2"' in html
        assert 'option value="approved_for_handoff"' in html
        assert 'option value="blocked"' in html
        assert 'data-content-handoff-staff-offset="20"' in html


def test_staff_handoff_guard_and_empty_never_expose_review_action() -> None:
    for locale in ("vi", "en", "zh"):
        rendered = _render(locale)
        for state in ("guarded", "empty"):
            assert 'data-portal-action="content-handoff-staff-review"' not in str(rendered[state])
