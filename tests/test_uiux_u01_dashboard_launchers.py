"""Execute the bounded dashboard launcher renderer; no API or account fixture."""
import json
import html as html_parser
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def render_launchers(locale):
    source = (ROOT / 'static/portal/portal.js').read_text(encoding='utf-8')
    start = source.index('    function renderDashboardProductHero(ctx) {')
    end = source.index('    function renderDashboardAccountSummary(ctx)', start)
    script = """
const vm=require('vm');
const source=JSON.parse(process.argv[1]);
const locale=process.argv[2];
const context={interfaceLocaleFor:ctx=>ctx.locale,
  safeText:x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'),
  portalIcon:()=>'<svg aria-hidden="true"></svg>',
  ICONS:{video:'v',image:'i',voice:'v',subtitle:'s',prompt:'p',music:'m'}};
console.log(vm.runInNewContext(source+';renderDashboardProductHero({locale:'+JSON.stringify(locale)+'})',context));
"""
    return subprocess.run(['node', '-e', script, json.dumps(source[start:end]), locale],
                          check=True, capture_output=True, text=True, encoding='utf-8', timeout=20).stdout


def test_six_destinations_preserved_without_inline_card_layout():
    html = render_launchers('vi')
    assert re.findall(r'href="([^"]+)"', html) == ['/studio', '/tools/image', '/voice', '/subdub', '/content', '/music']
    assert html.count('portal-product-launcher-card"') == 6
    assert 'style=' not in html
    for claim in ['4K', 'Bản quyền thương mại', 'Khớp nhịp audio', 'copywriting']:
        assert claim not in html


def test_launcher_copy_follows_interface_locale():
    vi, en, zh = (html_parser.unescape(render_launchers(locale)) for locale in ('vi', 'en', 'zh'))
    assert 'Bạn muốn tạo gì hôm nay?' in vi
    assert 'What would you like to create?' in en
    assert '今天想创作什么？' in zh
    for html in (en, zh):
        assert 'Bạn muốn' not in html
        assert 'Tạo Giọng' not in html
    assert 'Subtitles & dubbing' in en
    assert 'Phụ đề & lồng tiếng' in vi


def test_dashboard_launcher_layout_is_scoped_and_motion_safe():
    css = (ROOT / 'static/portal/portal-theme.css').read_text(encoding='utf-8')
    assert '.portal-dashboard-product-hero .portal-dashboard-launchers-grid' in css
    assert 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' in css
    assert '.portal-dashboard-product-hero .portal-product-launcher-card:focus-visible' in css
    assert '@media (prefers-reduced-motion: no-preference)' in css
    assert '.portal-shell[data-portal-app-kind="customer"] .portal-sidebar.is-open { transform: translateX(0); }' in css
    assert '.portal-shell[data-portal-app-kind="customer"] .portal-workspace { width: 100%; min-width: 0; }' in css


def test_mobile_resize_preserves_open_drawer_accessibility_state():
    source = (ROOT / 'static/portal/portal.js').read_text(encoding='utf-8')
    start = source.index('  function closeSidebarAboveMobileBreakpoint() {')
    end = source.index('\n  function commandPaletteFocusables', start)
    resize_handler = source[start:end]
    script = r"""
const vm = require('vm');
const handler = JSON.parse(process.argv[1]);
function run(mobile, isOpen) {
  const calls = [];
  const sidebar = { classList: { contains: name => name === 'is-open' && isOpen } };
  const context = {
    desktopNavigationFocusEnabled: true,
    desktopFocusNavigationSupported: () => !mobile,
    document: { querySelector: selector => selector === '[data-portal-sidebar]' ? sidebar : null },
    syncDesktopFocusNavigation: () => calls.push(['sync']),
    setSidebarAccessibilityState: opened => calls.push(['accessibility', opened]),
    closeSidebar: options => calls.push(['close', options]),
  };
  vm.runInNewContext(`${handler}; closeSidebarAboveMobileBreakpoint();`, context);
  return { enabled: context.desktopNavigationFocusEnabled, calls };
}
console.log(JSON.stringify([run(true, true), run(true, false), run(false, true), run(false, false)]));
"""
    result = subprocess.run(
        ['node', '-e', script, json.dumps(resize_handler)],
        check=True, capture_output=True, text=True, encoding='utf-8', timeout=20,
    )
    mobile_open, mobile_closed, desktop_open, desktop_closed = json.loads(result.stdout)
    assert mobile_open['calls'] == [['sync'], ['accessibility', True]]
    assert mobile_closed['calls'] == [['sync'], ['accessibility', False]]
    assert desktop_open['calls'] == [['close', {'restoreFocus': False}]]
    assert desktop_closed['calls'] == [['accessibility', False]]
