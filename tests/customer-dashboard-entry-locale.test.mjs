import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Catch hard-coded copy at the real Dashboard renderer, without booting APIs.
const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const messages = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const theme = fs.readFileSync('static/portal/portal-theme.css', 'utf8');
const dashboardTypeTitleKeys = [
  'drafts.title', 'projects.title', 'canonical.jobs.title', 'canonical.assets.title'
];
const noop = () => {};
function render(locale, wallet = {}, dashboardReadState = 'guarded') {
  const document = { readyState: 'loading', title: '', addEventListener: noop,
    querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
    documentElement: { lang: locale, setAttribute: noop, getAttribute: () => null, classList: { add: noop, remove: noop } },
    body: { classList: { add: noop, remove: noop, toggle: noop }, setAttribute: noop } };
  const window = { document, navigator: { language: locale, userAgent: 'QA' },
    location: { pathname: '/dashboard', search: '', href: 'http://127.0.0.1:4178/dashboard' },
    addEventListener: noop, dispatchEvent: noop, CustomEvent: function () {},
    matchMedia: () => ({ matches: false, addEventListener: noop }), localStorage: { getItem: () => null } };
  const sandbox = vm.createContext({ window, document, navigator: window.navigator, URL, URLSearchParams, Intl, console, setTimeout, clearTimeout });
  vm.runInContext(messages, sandbox);
  vm.runInContext(source.replace('  window.TOANAASPortal = Object.freeze({',
    '  window.__DashboardTest = { renderDashboard, normalizeBootstrap };\n  window.TOANAASPortal = Object.freeze({'), sandbox);
  window.TOANAASI18n.setLocale(locale, { emit: false });
  const state = window.__DashboardTest.normalizeBootstrap({ path: '/dashboard', profile: { locale },
    session: { authenticated: true, csrfToken: 'qa' }, wallet, dashboardReadState });
  const html = window.__DashboardTest.renderDashboard(window.TOANAASPortal.resolvePage('/dashboard'), state);
  return {
    html,
    dashboardTypeTitles: dashboardTypeTitleKeys.map((key) => window.TOANAASI18n.t(`dashboard.${key}`, locale)),
    hero: html.match(/<section class="[^"]*portal-dashboard-product-hero[^"]*"[\s\S]*?<\/section>/)?.[0] || '',
    account: html.match(/<section class="[^"]*portal-dashboard-account-summary-strip[^"]*"[\s\S]*?<\/section>/)?.[0] || ''
  };
}
const visible = (html) => html.replace(/<[^>]+>/g, ' ').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();
const expected = {
  vi: { heading: 'Bạn muốn làm gì hôm nay?', products: ['Video AI', 'Ảnh AI', 'Giọng đọc AI', 'SubDub', 'Nội dung', 'Âm nhạc AI'],
    account: ['Xu khả dụng', 'Gói tài khoản', 'Đã sử dụng', 'Nạp Xu', 'Ví & lịch sử', 'Gói dịch vụ'], member: 'Thành viên', vip: 'Thành viên VIP' },
  en: { heading: 'What would you like to make today?', products: ['AI video', 'AI image', 'AI voice', 'SubDub', 'Content', 'AI music'],
    account: ['Available Xu', 'Account plan', 'Used so far', 'Top up Xu', 'Wallet & history', 'Plans & pricing'], member: 'Member', vip: 'VIP member' },
  zh: { heading: '今天想创作什么？', products: ['AI 视频', 'AI 图片', 'AI 语音', 'SubDub', '内容创作', 'AI 音乐'],
    account: ['可用 Xu', '账户套餐', '累计使用', '充值 Xu', '钱包与记录', '套餐与价格'], member: '会员', vip: 'VIP 会员' }
};
const mixedVi = /\b(?:copywriting|audio|poster|workspace|studio|library|prompt|voice|image|music|project|content|commercial|copyright)\b/i;
const allowedZh = new Set(['AI', 'SUBDUB', 'TOAN', 'AAS', 'XU', 'VIP']);
for (const locale of ['vi', 'en', 'zh']) {
  test(`Dashboard entry renders product and account labels in ${locale}`, () => {
    const r = render(locale), want = expected[locale];
    assert.equal(r.hero.match(/<h1[^>]*>([\s\S]*?)<\/h1>/)?.[1], want.heading);
    assert.deepEqual(Array.from(r.hero.matchAll(/<h3[^>]*>(.*?)<\/h3>/g), m => m[1]), want.products);
    for (const text of want.account) assert.ok(visible(r.account).includes(text), text);
  });
  test(`Dashboard entry fixed copy is clean ${locale} and does not promise unverified output quality`, () => {
    const text = visible(render(locale).hero + render(locale).account);
    if (locale === 'vi') assert.doesNotMatch(text, mixedVi);
    if (locale === 'en') assert.doesNotMatch(text, /[\u00c0-\u024f\u4e00-\u9fff]/u);
    if (locale === 'zh') assert.deepEqual((text.match(/[a-z][a-z0-9-]*/gi) || []).filter(w => !allowedZh.has(w.toUpperCase())), []);
    assert.doesNotMatch(text, /4K|bản quyền thương mại|commercial (?:rights|licen[sc]e)|商用版权|chuẩn khớp|tối ưu chuyển đổi/i);
  });
  test(`Dashboard membership fallbacks follow ${locale}, without inventing a named plan`, () => {
    const wallet = { balance_xu: 0, total_spent_xu: 0, is_vip: false };
    assert.ok(visible(render(locale, wallet).account).includes(expected[locale].member));
    assert.ok(visible(render(locale, { ...wallet, is_vip: true }).account).includes(expected[locale].vip));
  });
}
test('Dashboard copy leaves all six product and three account destinations unchanged', () => {
  const r = render('en');
  assert.deepEqual(Array.from(r.hero.matchAll(/href="([^"]+)"/g), m => m[1]), ['/studio', '/tools/image', '/voice', '/subdub', '/content', '/music']);
  assert.deepEqual(Array.from(r.account.matchAll(/href="([^"]+)"/g), m => m[1]), ['/wallet/topup', '/wallet', '/packages']);
});
test('Dashboard leaves missing canonical money as unknown, not a made-up zero', () => {
  const r = render('en');
  assert.equal((visible(r.account).match(/—/g) || []).length, 2);
});
test('Dashboard preserves and escapes server-issued plan data and money values', () => {
  const wallet = { balance_xu: 123, total_spent_xu: 45, is_vip: false, plan: { plan_name: '<img src=x onerror=alert(1)>Custom' } };
  const before = JSON.stringify(wallet), r = render('en', wallet);
  assert.ok(r.account.includes('&lt;img src=x onerror=alert(1)&gt;Custom'));
  assert.ok(visible(r.account).includes('123')); assert.ok(visible(r.account).includes('45'));
  assert.doesNotMatch(r.account, /<img src=x/); assert.equal(JSON.stringify(wallet), before);
});
const accountNames = { vi: 'Tóm tắt tài khoản', en: 'Account summary', zh: '账户概览' };
for (const locale of ['vi', 'en', 'zh']) {
  test(`Dashboard has one primary product H1 before its secondary workspace greeting in ${locale}`, () => {
    const r = render(locale);
    assert.equal((r.html.match(/<h1\b/g) || []).length, 1, 'The product-first screen needs one primary heading');
    assert.equal(r.html.match(/<h[123]\b/)?.[0], '<h1', 'Primary product purpose precedes the section headings');
    assert.match(r.hero, /<h1 id="dashboard-product-title"/);
    assert.ok(r.hero.includes(expected[locale].heading));
    assert.match(r.html, /<h2 id="workspace-overview-title">[^<]+<\/h2>/, 'Greeting remains a named secondary section, not another page title');
    assert.match(r.html, /aria-labelledby="workspace-overview-title"/);
  });
}
for (const locale of ['vi', 'en', 'zh']) {
  test(`Dashboard account region resolves its accessible name to one ${locale} heading`, () => {
    const r = render(locale), labelId = r.account.match(/aria-labelledby="([^"]+)"/)?.[1];
    assert.ok(labelId, 'The region needs a heading reference');
    const heading = r.account.match(new RegExp('<h2[^>]*id="' + labelId + '"[^>]*>([^<]+)<\\/h2>'));
    assert.equal(heading?.[1], accountNames[locale], 'The named heading must exist in the actual rendered region');
    assert.equal(r.html.split('id="' + labelId + '"').length - 1, 1, 'The label target must not be duplicated');
  });
}
for (const locale of ['vi', 'en', 'zh']) {
  test(`Dashboard uses the intended section and card heading roles in ${locale}`, () => {
    const r = render(locale, {}, 'ready');
    assert.match(r.html, /<h2 id="workspace-work-lane-title">/);
    assert.match(r.html, /<h2 id="workspace-canonical-lane-title">/);
    for (const title of r.dashboardTypeTitles) {
      assert.ok(r.html.includes(`<h3 class="portal-card-title">${title}</h3>`), `${locale}: ${title} must be a card-level heading`);
    }
    assert.doesNotMatch(r.html, /<h2 class="portal-card-title">/);
  });
}
test('Dashboard type rules stay scoped and preserve the readable roles', () => {
  assert.match(theme, /:root \.portal-dashboard-app :is\(\.portal-command-center-lane-heading h2, \.portal-command-center-state h2\) \{\s*font-size: clamp\(24px, 2\.4vw, 32px\);\s*line-height: 1\.25;/);
  assert.match(theme, /:root \.portal-dashboard-app :is\(h3, \.portal-card-title\) \{\s*font-size: 20px;\s*line-height: 1\.4;/);
  assert.match(theme, /:root \.portal-dashboard-app p \{\s*font-size: 16px !important;\s*line-height: 1\.65 !important;/);
  assert.match(theme, /:root \.portal-dashboard-app \.portal-button \{\s*font-size: 14px !important;\s*min-height: 44px;/);
});
