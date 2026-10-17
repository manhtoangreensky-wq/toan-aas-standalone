import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const portal = fs.readFileSync('static/portal/portal.js', 'utf8');
const messages = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const noop = () => {};
function trigger(locale, session, route = '/dashboard', profile = {}) {
  const document = { readyState: 'loading', title: '', addEventListener: noop, querySelector: () => null,
    querySelectorAll: () => [], getElementById: () => null,
    documentElement: { lang: locale, setAttribute: noop, getAttribute: () => null, classList: { add: noop, remove: noop } },
    body: { classList: { add: noop, remove: noop, toggle: noop }, setAttribute: noop } };
  const window = { document, navigator: { language: locale, userAgent: 'QA' },
    location: { pathname: route, search: '', href: 'http://127.0.0.1:4178' + route },
    addEventListener: noop, dispatchEvent: noop, CustomEvent: function () {},
    matchMedia: () => ({ matches: false, addEventListener: noop }), localStorage: { getItem: () => null } };
  const sandbox = vm.createContext({ window, document, navigator: window.navigator, URL, URLSearchParams, Intl, console, setTimeout, clearTimeout });
  vm.runInContext(messages, sandbox);
  vm.runInContext(portal.replace('  window.TOANAASPortal = Object.freeze({',
    '  window.__ReadinessTest = { renderHeader, normalizeBootstrap };\n  window.TOANAASPortal = Object.freeze({'), sandbox);
  window.TOANAASI18n.setLocale(locale, { emit: false });
  const ctx = window.__ReadinessTest.normalizeBootstrap({ path: route, session, profile: { ...profile, locale } });
  const html = window.__ReadinessTest.renderHeader(window.TOANAASPortal.resolvePage(route), ctx);
  const button = html.match(/<button class="portal-command-trigger"[\s\S]*?<\/button>/)?.[0];
  assert.ok(button, 'The existing quick-switch control must remain present'); return button;
}
const loading = { vi: 'Tìm kiếm chưa sẵn sàng', en: 'Search not ready', zh: '搜索尚未就绪' };
const ready = { vi: 'Tìm trong không gian làm việc', en: 'Search workspace', zh: '搜索工作台' };
for (const locale of ['vi', 'en', 'zh']) {
  test(`Customer quick-switch is disabled with a ${locale} explanation before signed hydration`, () => {
    const button = trigger(locale, { authenticated: false });
    assert.match(button, /\sdisabled(?:\s|>)/); assert.ok(button.includes('aria-label="' + loading[locale] + '"'));
  });
  test(`Signed customer quick-switch enables the real ${locale} action without a loading label`, () => {
    const button = trigger(locale, { authenticated: true, csrfToken: 'qa' });
    assert.doesNotMatch(button, /\sdisabled(?:\s|>)/); assert.ok(button.includes('aria-label="' + ready[locale] + '"'));
    assert.ok(!button.includes(loading[locale]));
  });
}
test('Cached profile and browser role cannot enable an unsigned customer trigger', () => {
  assert.match(trigger('vi', { authenticated: false, role: 'admin' }, '/dashboard', { role: 'admin', displayName: 'Cached account' }), /\sdisabled(?:\s|>)/);
});
test('Admin trigger presentation stays unchanged outside the customer readiness branch', () => {
  const button = trigger('en', { authenticated: false }, '/admin');
  assert.doesNotMatch(button, /\sdisabled(?:\s|>)/); assert.ok(button.includes('aria-label="Search administration"'));
});
