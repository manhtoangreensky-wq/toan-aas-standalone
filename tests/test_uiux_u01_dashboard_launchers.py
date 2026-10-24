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
    i18n_path = ROOT / 'static/portal/portal-i18n.js'
    script = """
const vm=require('vm');
const fs=require('fs');
const source=JSON.parse(process.argv[1]);
const locale=process.argv[2];
const i18nSource=fs.readFileSync(process.argv[3],'utf8');
const context={
  interfaceLocaleFor:ctx=>ctx.locale,
  safeText:x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'),
  portalIcon:()=>'<svg aria-hidden="true"></svg>',
  ICONS:{video:'v',image:'i',voice:'v',subtitle:'s',prompt:'p',music:'m'},
  dashboardText:(key,params)=>context.safeText(context.TOANAASI18n.t('dashboard.'+key,params||{},locale)),
  uiText:(key,fallback,params)=>context.TOANAASI18n.t(key,params||{},locale)||fallback
};
context.window=context;
context.globalThis=context;
vm.runInNewContext(i18nSource,context);
if(context.TOANAASI18n&&context.TOANAASI18n.setLocale){context.TOANAASI18n.setLocale(locale,{emit:false});}
console.log(vm.runInNewContext(source+';renderDashboardProductHero({locale:'+JSON.stringify(locale)+'})',context));
"""
    return subprocess.run(['node', '-e', script, json.dumps(source[start:end]), locale, str(i18n_path)],
                          check=True, capture_output=True, text=True, encoding='utf-8', timeout=20).stdout


def render_account_summary(locale, wallet=None):
    source = (ROOT / 'static/portal/portal.js').read_text(encoding='utf-8')
    start = source.index('    function renderDashboardAccountSummary(ctx) {')
    end = source.index('\n    return `<article class="portal-page portal-dashboard-app', start)
    i18n_path = ROOT / 'static/portal/portal-i18n.js'
    script = r"""
const vm = require('vm');
const fs = require('fs');
const source = JSON.parse(process.argv[1]);
const locale = process.argv[2];
const wallet = JSON.parse(process.argv[3]);
const i18nSource = fs.readFileSync(process.argv[4], 'utf8');
const context = {
  canonicalWalletProjection: w => w,
  localizedNumber: value => String(value),
  locale,
  wallet,
  interfaceLocaleFor: ctx => ctx.locale,
  safeText: value => String(value),
  portalIcon: () => '<svg aria-hidden="true"></svg>',
  ICONS: { payments: 'payments' },
  dashboardText: (key, params) => context.safeText(context.TOANAASI18n.t('dashboard.' + key, params || {}, locale)),
  uiText: (key, fallback, params) => context.TOANAASI18n.t(key, params || {}, locale) || fallback
};
context.window = context;
context.globalThis = context;
vm.runInNewContext(i18nSource, context);
if (context.TOANAASI18n && context.TOANAASI18n.setLocale) { context.TOANAASI18n.setLocale(locale, { emit: false }); }
console.log(vm.runInNewContext(source + '; renderDashboardAccountSummary({ locale, wallet })', context));
"""
    return subprocess.run(['node', '-e', script, json.dumps(source[start:end]), locale, json.dumps(wallet), str(i18n_path)],
                          check=True, capture_output=True, text=True, encoding='utf-8', timeout=20).stdout


def test_six_destinations_preserved_without_inline_card_layout():
    html = render_launchers('vi')
    assert re.findall(r'href="([^"]+)"', html) == ['/studio', '/tools/image', '/voice', '/subdub', '/content', '/music']
    assert html.count('portal-product-launcher-card"') == 6
    assert html.count('<h1 id="dashboard-product-title">') == 1
    assert html.count('<h3') == 6
    assert 'style=' not in html
    for claim in ['4K', 'Bản quyền thương mại', 'Khớp nhịp audio', 'copywriting']:
        assert claim not in html


def test_launcher_copy_follows_interface_locale():
    vi, en, zh = (html_parser.unescape(render_launchers(locale)) for locale in ('vi', 'en', 'zh'))
    assert 'Bạn muốn làm gì hôm nay?' in vi
    assert 'What would you like to make today?' in en
    assert '今天想创作什么？' in zh
    for html in (en, zh):
        assert 'Bạn muốn' not in html
        assert 'Tạo Giọng' not in html
    assert 'subtitles' in en.lower()
    assert 'phụ đề' in vi.lower()


def test_dashboard_account_summary_uses_complete_interface_locale():
    vi, en, zh = (render_account_summary(locale) for locale in ('vi', 'en', 'zh'))
    assert '<h2 id="dashboard-account-summary-title"' in vi
    assert 'Xu khả dụng' in vi
    assert 'Gói tài khoản' in vi
    assert 'Nạp Xu' in vi
    assert 'Thành viên' in vi
    assert 'Available Xu' in en
    assert 'Account plan' in en
    assert 'Top up Xu' in en
    assert 'Member' in en
    assert '可用 Xu' in zh
    assert '账户套餐' in zh
    assert '充值 Xu' in zh
    assert '会员' in zh
    for html in (en, zh):
        for vi_label in (
            'Xu khả dụng', 'Gói tài khoản', 'Lũy kế đã dùng', 'Nạp Xu',
            'Ví Xu & Lịch sử', 'Bảng giá & Gói', 'Thành viên',
        ):
            assert vi_label not in html


def test_dashboard_account_summary_vip_fallback_without_invented_package():
    wallet_vip = {'balance_xu': 100, 'total_spent_xu': 20, 'is_vip': True, 'plan': None}
    vi_vip = render_account_summary('vi', wallet=wallet_vip)
    en_vip = render_account_summary('en', wallet=wallet_vip)
    zh_vip = render_account_summary('zh', wallet=wallet_vip)
    assert 'Thành viên VIP' in vi_vip
    assert 'VIP Doanh nghiệp' not in vi_vip
    assert 'VIP member' in en_vip
    assert 'Business VIP' not in en_vip
    assert 'VIP 会员' in zh_vip
    assert '企业 VIP' not in zh_vip


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
