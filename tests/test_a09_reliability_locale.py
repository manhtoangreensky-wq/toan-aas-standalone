"""Render actual Reliability states; fixed English must not leak into VI."""
import json
from pathlib import Path
import subprocess
import shutil
import ast
import re
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]


def test_complete_reliability_renderer_uses_real_helpers_in_all_locales():
    # Reuse the established minimal DOM host, not mocked renderer helpers.
    host = ast.parse((ROOT / 'tests/test_a09_admin_operations_locale_purity_contracts.py').read_text(encoding='utf-8'))
    function = next(node for node in host.body if isinstance(node, ast.FunctionDef) and node.name == '_render_admin_operations')
    assignment = next(node for node in function.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'script' for t in node.targets))
    script = ast.literal_eval(assignment.value).split('const api = context.__a09AdminOperations;')[0]
    script = script.replace('renderOperationsAdmin, localizedPageTitle', 'renderReliabilityAdmin, renderOperationsAdmin, localizedPageTitle')
    script += """
const api=context.__a09AdminOperations;
const page={path:'/admin/reliability',routePath:'/admin/reliability',title:'Reliability Follow-up',section:'Admin ERP',description:'Fallback',action:'none'};
const pagination={offset:10,returned:1,previous_offset:0,has_more:true,next_offset:20};
const base={...api.normalizeBootstrap({session:{authenticated:true}}),session:{authenticated:true},reliabilityReadState:'ready',reliabilitySummary:{operator_role:'manager',counts:{open:1,acknowledged:0},signal_groups:1,
recent_signals:[{route_family:'qa_module',count:7,last_seen_at:'2026-09-11T00:00:00Z'}]},
reliabilityFollowupListing:{pagination},reliabilityFollowupFilter:{state:'all',severity:'all'},
capabilities:{'reliability-followup-resolve':true,'reliability-followup-handoff':true},
reliabilityFollowups:[{id:'qa-record',revision:2,state:'open',source_kind:'support_triage',severity:'high',required_role:'manager',updated_at:'2026-09-11T00:00:00Z'}]};
const matrix={};
for(const state of ['open','acknowledged','resolved','superseded']) {
  for(const granted of [false,true]) {
    matrix[state+'-'+granted]=api.renderReliabilityAdmin(page,{
      ...base, capabilities:granted?{'reliability-followup-acknowledge':true,'reliability-followup-resolve':true,'reliability-followup-reopen':true,'reliability-followup-handoff':true}:{},
      reliabilityFollowups:[{...base.reliabilityFollowups[0],state}]
    });
  }
}
const injected=api.renderReliabilityAdmin(page,{
 ...base,
 reliabilitySummary:{...base.reliabilitySummary,recent_signals:[{route_family:'<img src=x onerror=alert(1)>',count:7}]},
 reliabilityFollowups:[{...base.reliabilityFollowups[0],id:'"><script>alert(1)</script>',required_role:'<img src=x>',state:'<script>alert(1)</script>'}]
});
process.stdout.write(JSON.stringify({html:api.renderReliabilityAdmin(page,base),matrix,injected,title:api.localizedPageTitle(page,base),description:api.localizedPageDescription(page)}));
"""
    class Visible(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []
        def handle_data(self, data):
            self.parts.append(data)
    for locale in ('vi', 'en', 'zh'):
        result = subprocess.run([shutil.which('node'), '-e', script, str(ROOT/'static/portal/portal-i18n.js'), str(ROOT/'static/portal/portal.js'), locale], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        rendered = json.loads(result.stdout)
        parser = Visible()
        parser.feed(rendered['html'])
        text = ' '.join(parser.parts) + rendered['title'] + rendered['description']
        if locale in ('en', 'zh'):
            assert not re.search(r'[ĂÂĐÊÔƠƯăâđêôơư\u1EA0-\u1EF9]', text), text
        else:
            for foreign in ('Manager', 'Operator', 'runtime', 'follow-up', 'Railway', 'Support Desk'):
                assert foreign not in text, text
        assert 'name="expected_revision" value="2"' in rendered['html']
        assert 'data-reliability-followup-offset="20"' in rendered['html']
        assert 'qa module' in text and '7' in text
        assert '<script>' not in rendered['injected']
        assert '<img src=x' not in rendered['injected']
        assert '&lt;img src=x' in rendered['injected']
        assert not re.search(r'data-portal-action="reliability-followup-(resolve|acknowledge|reopen|handoff)"', rendered['injected'])
        allowed = {
            'open': {'acknowledge', 'resolve', 'handoff'},
            'acknowledged': {'resolve', 'handoff'},
            'resolved': {'reopen'},
            'superseded': set(),
        }
        for state, expected in allowed.items():
            for granted in (False, True):
                markup = rendered['matrix'][f'{state}-{str(granted).lower()}']
                actions = set(re.findall(r'data-portal-action="reliability-followup-(acknowledge|resolve|reopen|handoff)"', markup))
                assert actions == (expected if granted else set())


def test_reliability_pagination_translates_and_preserves_disabled_cursor():
    source = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
    start = source.index("function renderOperationsPagination(")
    end = source.index("function operationsIncidentCards(", start)
    script = """
const fs=require('fs'),vm=require('vm'),window={};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,console});
let locale='vi'; const safeText=x=>String(x);
const uiText=(key,fallback,params={})=>Object.entries(params).reduce(
 (text,[key,value])=>text.replaceAll('{'+key+'}',value),window.TOANAASI18n.messages[locale][key]||fallback);
const adminOperationsText=(key,fallback,params)=>uiText('adminOperations.'+key,fallback,params);
""" + source[start:end] + """
const result={};
for(locale of ['vi','en','zh']) result[locale]=renderReliabilityFollowupPagination({pagination:{
offset:10,returned:10,previous_offset:0,has_more:true,next_offset:20}},false);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([shutil.which("node"), "-e", script, str(ROOT / "static/portal/portal-i18n.js")],
                            capture_output=True, text=True, check=True, timeout=30)
    markup = json.loads(result.stdout)
    for locale, labels in {"vi": ("Trang trước", "Trang sau", "mục theo dõi"),
                           "en": ("Previous page", "Next page", "follow-ups"),
                           "zh": ("上一页", "下一页", "跟进项")}.items():
        assert all(label in markup[locale] for label in labels)
        assert 'data-reliability-followup-offset="20" disabled' in markup[locale]
        assert 'data-reliability-followup-offset="0" disabled' in markup[locale]
        assert markup[locale].count('data-portal-route="/admin/reliability"') == 2


def test_reliability_guarded_copy_does_not_mix_english_or_assert_permission():
    source = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
    start = source.index("function renderReliabilityAdmin(page, context)")
    end = source.index("function renderTickets(page, context)", start)
    script = "const renderHero=()=>''; const safeText=x=>x; const uiText=(key,fallback)=>fallback;\n" + source[start:end] + """
process.stdout.write(JSON.stringify(renderReliabilityAdmin({}, {
  reliabilityReadState: 'guarded', reliabilitySummary: {}
})));
"""
    result = subprocess.run([shutil.which("node"), "-e", script],
                            capture_output=True, text=True, check=True, timeout=30)
    markup = json.loads(result.stdout)
    for foreign in ("Reliability", "Support staff", "Browser", "role", "Follow-up"):
        assert foreign not in markup, f"Mixed fixed Vietnamese copy: {foreign}"
    assert "chưa được cấp" not in markup, "Unknown data does not prove permission denial"


def test_reliability_guarded_and_loading_use_actual_locale_catalogue():
    source = (ROOT / "static/portal/portal.js").read_text(encoding="utf-8")
    start = source.index("function renderReliabilityAdmin(page, context)")
    end = source.index("function renderTickets(page, context)", start)
    script = """
const fs=require('fs'), vm=require('vm');
const window={};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), {window, console});
let locale='vi';
const renderHero=()=>'', safeText=x=>x;
const renderEmpty=(title,body)=>'<h3>'+title+'</h3><p>'+body+'</p>', supportCaseTimestamp=()=>'', badge=()=>'', operationsCount=x=>x||0, operationsCode=x=>x;
const reliabilityFollowupFilter=()=>({}), reliabilityFollowupListing=()=>({});
const reliabilityFollowupFilterOptions=()=>'', renderReliabilityFollowupPagination=()=>'';
const RELIABILITY_FOLLOWUP_STATE_FILTERS=[], RELIABILITY_FOLLOWUP_SEVERITY_FILTERS=[];
const uiText=(key,fallback)=>window.TOANAASI18n.messages[locale][key] || fallback;
""" + source[start:end] + """
const result={};
for (locale of ['vi','en','zh']) {
  result[locale]=['guarded','loading'].map(reliabilityReadState =>
    renderReliabilityAdmin({}, {reliabilityReadState, reliabilitySummary:{}}));
  result[locale].push(renderReliabilityAdmin({}, {
    reliabilityReadState:'ready', reliabilitySummary:{operator_role:'manager'},
    capabilities:{'reliability-followup-resolve':true},
    reliabilityFollowups:[{id:'fixture-1',revision:2,state:'open',source_kind:'runtime_signal'}]
  }));
  result[locale].push(renderReliabilityAdmin({}, {reliabilityReadState:'ready',reliabilitySummary:{operator_role:'operator'}}));
}
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([shutil.which("node"), "-e", script,
                             str(ROOT / "static/portal/portal-i18n.js")],
                            capture_output=True, text=True, check=True, timeout=30)
    rendered = json.loads(result.stdout)
    for locale, titles in {
        "vi": ("Chưa xác minh được dữ liệu theo dõi", "Đang xác minh dữ liệu theo dõi"),
        "en": ("Monitoring data is not verified", "Verifying monitoring data"),
        "zh": ("监测数据尚未验证", "正在验证监测数据"),
    }.items():
        for markup, title in zip(rendered[locale], titles):
            assert title in markup
            assert 'data-portal-action=' not in markup
    assert 'Đánh dấu mục theo dõi đã xử lý?' in rendered['vi'][2]
    assert 'Mark this follow-up as resolved?' in rendered['en'][2]
    assert '将此跟进项标记为已处理？' in rendered['zh'][2]
    for locale, label in {'vi':'Tín hiệu vận hành đã tổng hợp', 'en':'Aggregated runtime signals', 'zh':'汇总运行信号'}.items():
        assert label in rendered[locale][2]
    for locale, label in {'vi':'Đã xử lý', 'en':'Resolve', 'zh':'标记已处理'}.items():
        assert f'>{label}</button>' in rendered[locale][2]
    assert '>Clear filters</button>' in rendered['en'][2]
    assert '>清除筛选</button>' in rendered['zh'][2]
    assert 'aria-label="Reliability overview"' in rendered['en'][2]
    assert 'aria-label="稳定性概览"' in rendered['zh'][2]
    assert 'Track issues without automatic repairs' in rendered['en'][2]
    assert '跟踪问题，不自动修复' in rendered['zh'][2]
    assert 'Investigation queue' in rendered['en'][2]
    assert '调查队列' in rendered['zh'][2]
    assert 'Railway' not in rendered['vi'][2]
    assert 'Signals guide investigation; they do not confirm a cause or a repair.' in rendered['en'][2]
    for locale in ('vi', 'en', 'zh'):
        assert 'name="expected_revision" value="2"' in rendered[locale][2]
        assert 'reliability-followup-resolve' in rendered[locale][2]
    for locale, labels in {
        'vi': ('Chưa có mục theo dõi', 'Chưa có tín hiệu vận hành'),
        'en': ('No follow-ups yet', 'No runtime signals yet'),
        'zh': ('暂无跟进项', '暂无运行信号'),
    }.items():
        assert all(label in rendered[locale][3] for label in labels)
        assert 'reliability-followup-resolve' not in rendered[locale][3]
