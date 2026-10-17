import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const renderStart = source.indexOf('    function renderShell() {');
const headerStart = source.indexOf('      setSidebarAccessibilityState(false);', renderStart) + '      setSidebarAccessibilityState(false);'.length;
const headerEnd = source.indexOf('      main.innerHTML = renderPage(page, context);', headerStart);
assert.ok(renderStart > 0 && headerEnd > headerStart);
const headerCode = source.slice(headerStart, headerEnd);

function harness() {
  const header = { writes: 0, menuOpen: false, focusInside: false, set innerHTML(value) { this.writes++; this.markup = value; this.menuOpen = false; this.focusInside = false; } };
  const runtime = vm.createContext({ header, page: { admin: false }, context: { header: '<header>A</header>', session: { authenticated: true, csrfToken: 'qa-session-a' } }, isHydration: false, renderHeader: (_page, context) => context.header, isAdminPortalSurface: page => page.admin });
  vm.runInContext('let lastCustomerHeaderMarkup = null; let lastCustomerHeaderSessionToken = null;', runtime);
  return { header, runtime, render: () => vm.runInContext(`(() => { ${headerCode} })()`, runtime) };
}

test('Unchanged signed customer header survives unrelated hydration with menu and focus intact', () => {
  const h = harness(); h.render(); h.header.menuOpen = true; h.header.focusInside = true;
  h.runtime.isHydration = true; h.render();
  assert.equal(h.header.writes, 1, 'Background data must not replace unchanged header DOM');
  assert.equal(h.header.menuOpen, true);
  assert.equal(h.header.focusInside, true);
});

test('Changed header data is rendered for the same signed customer', () => {
  const h = harness(); h.render(); h.runtime.isHydration = true;
  h.runtime.context.header = '<header>B</header>'; h.render();
  assert.equal(h.header.writes, 2); assert.equal(h.header.markup, '<header>B</header>');
});

test('Session replacement or sign-out cannot reuse the prior customer header', () => {
  for (const session of [{ authenticated: true, csrfToken: 'qa-session-b' }, { authenticated: false, csrfToken: '' }]) {
    const h = harness(); h.render(); h.header.menuOpen = true; h.runtime.isHydration = true;
    h.runtime.context.session = session; h.render();
    assert.equal(h.header.writes, 2); assert.equal(h.header.menuOpen, false);
  }
});

test('Route presentation and Admin header keep their normal update behavior', () => {
  for (const admin of [false, true]) {
    const h = harness(); h.runtime.page.admin = admin; h.render(); h.runtime.isHydration = admin; h.render();
    assert.equal(h.header.writes, 2);
  }
});
