import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalog = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, name);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}
const allRoutes = ['/admin', '/admin/topups', '/admin/customers', '/admin/jobs', '/admin/jobs/failed', '/admin/support'];
function harness(locale) {
  const ctx = {
    ICONS: {security: 'security'}, portalIcon: () => '', badge: () => '',
    renderRowsTable: () => '', renderSummary: () => '', renderAdminDashboardAnalytics: () => '',
    renderAdminWorkQueues: () => '', renderAdminDirectory: () => '', renderAdminModuleTabs: () => '',
    adminDashboardMetricRows: () => [],
    adminErpNavigation: context => ({routes: new Set(context.allowedRoutes), canonicalAdmin: context.allowedRoutes.length === allRoutes.length, supportRole: 'operator'})
  };
  vm.createContext(ctx); vm.runInContext(catalog, ctx);
  ctx.TOANAASI18n.setLocale(locale, {emit: false});
  ctx.uiText = (key, fallback, params) => ctx.TOANAASI18n.has(key) ? ctx.TOANAASI18n.t(key, params) : fallback;
  vm.runInContext([fn('safeText'), fn('normalizePath'), fn('serverAuthorizesAdminRoute'), fn('renderAdminOverview')].join('\n'), ctx);
  return (counts = {}, allowedRoutes = allRoutes, extra = {}) => ctx.renderAdminOverview({path:'/admin'}, {allowedRoutes, adminData: {counts}, capabilities: {}, ...extra});
}
function topupPanel(html) { return html.match(/<section[^>]*portal-admin-topup-hero[\s\S]*?<\/section>/)?.[0] || ''; }
function quickPanel(html) { return html.match(/<section[^>]*portal-admin-quick-actions[\s\S]*?<\/section>/)?.[0] || ''; }

for (const locale of ['vi', 'en', 'zh']) {
  const render = harness(locale);
  test(`Operator shortcuts show only server-issued modules (${locale})`, () => {
    const html = render({pending_topups: 8, failed_jobs: 3}, ['/admin', '/admin/support']);
    assert.doesNotMatch(html, /portal-admin-topup-hero|portal-admin-incident-alert|href="\/admin\/(?:topups|customers|jobs)(?:["/])/);
    assert.match(quickPanel(html), /href="\/admin\/support"/);
  });
  test(`No issued operational modules means no dead shortcut section (${locale})`, () => {
    assert.equal(quickPanel(render({}, ['/admin'])), '');
  });
  test(`Top-up totals distinguish unknown from a real zero (${locale})`, () => {
    for (const value of [undefined, null, '', false, -1, 0.5, 'unknown']) {
      const html = topupPanel(render({pending_topups: value}));
      assert.ok(html.includes('—'), `invalid count ${String(value)} must remain unknown`);
      assert.ok(html.includes({vi:'Chưa xác định',en:'Unknown',zh:'未知'}[locale]), 'unknown label follows the interface locale');
    }
    const zero = topupPanel(render({pending_topups: 0}));
    assert.match(zero, /(?:>[^<]*|\s)0(?:\s|<)/);
    assert.doesNotMatch(zero, /—/);
    assert.ok(topupPanel(render({pending_topups: 12})).includes('12'));
  });
  test(`A bounded top-up page is not presented as the queue total (${locale})`, () => {
    const html = topupPanel(render({}, allRoutes, {adminManualTopupState: {items:[{status:'pending_admin_review'}]}}));
    assert.ok(html.includes('—'));
  });
  test(`Exact job module admits its failed-job detail link without granting top-ups (${locale})`, () => {
    const html = render({failed_jobs: 3}, ['/admin', '/admin/jobs']);
    assert.match(html, /portal-admin-incident-alert/);
    assert.match(html, /href="\/admin\/jobs\/failed"/);
    assert.doesNotMatch(html, /href="\/admin\/topups"/);
  });
  test(`Operational banners use one locale and only navigate (${locale})`, () => {
    const html = render({pending_topups: 2, failed_jobs: 3});
    const panels = topupPanel(html) + quickPanel(html) + (html.match(/<section[^>]*portal-admin-incident-alert[\s\S]*?<\/section>/)?.[0] || '');
    assert.doesNotMatch(panels, /<form\b|data-portal-action|\{count\}/);
    assert.ok(panels.includes({vi:'HÀNG ĐỢI DUYỆT TIỀN', en:'PENDING TOP-UP QUEUE', zh:'待审核充值队列'}[locale]));
    if (locale === 'en') assert.doesNotMatch(panels, /[À-ỹĐđ]/);
    if (locale === 'zh') assert.doesNotMatch(panels.replace(/<[^>]*>/g, ''), /[À-ỹĐđ]/);
    if (locale !== 'vi') assert.doesNotMatch(html.replace(/<[^>]*>/g, ''), /Chẩn đoán|Kết nối kỹ thuật/);
  });
}
