import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const mount = source.indexOf('  function mountPortal(override) {');
const start = source.indexOf('    const actualPath =', mount);
const end = source.indexOf('    const surface = portalSurface(page);', start);
const renderStart = source.indexOf('    function renderShell() {', end) + '    function renderShell() {'.length;
const renderEnd = source.indexOf('      main.innerHTML = renderPage(page, context);', renderStart);
assert.ok(mount > 0 && end > start && renderEnd > renderStart);

function harness() {
  const sidebar = { open: false, writes: 0, accessible: false, focused: false,
    classList: { contains: () => sidebar.open },
    set innerHTML(value) { this.writes++; this.markup = value; this.focused = false; },
  };
  const header = { writes: 0, set innerHTML(value) { this.writes++; this.markup = value; } };
  const context = { path: '/workspace-menu', header: '<header>A</header>', sidebar: '<nav>A</nav>', session: { authenticated: true, csrfToken: 'fixture-a' } };
  const runtime = vm.createContext({
    sidebar, header, context, page: { admin: false }, options: { reason: 'entry' },
    commandPalette: null, mobile: true,
    window: { location: { pathname: '/workspace-menu' } },
    normalizePath: value => value, isAdminPortalSurface: page => page.admin,
    renderHeader: (_page, value) => value.header, renderSidebar: (_page, value) => value.sidebar,
    mobileSidebarDialogSupported: () => runtime.mobile,
    closeSidebar() { sidebar.open = false; sidebar.focused = false; },
    setSidebarAccessibilityState(opened) { sidebar.accessible = opened; },
  });
  vm.runInContext("let lastNormalizedRoute='/workspace-menu'; let lastCustomerHeaderMarkup=null; let lastCustomerSidebarMarkup=null; let lastCustomerHeaderSessionToken=null;", runtime);
  const render = () => vm.runInContext(`(() => { ${source.slice(start, end)} ${source.slice(renderStart, renderEnd)} })()`, runtime);
  render(); sidebar.open = true; sidebar.focused = true; runtime.options.reason = 'data-hydration';
  return { sidebar, header, runtime, render };
}

test('Unchanged customer hydration retains open drawer, focused node and accessibility state', () => {
  const h = harness(); h.render();
  assert.equal(h.sidebar.open, true);
  assert.equal(h.sidebar.focused, true);
  assert.equal(h.sidebar.accessible, true);
  assert.equal(h.sidebar.writes, 1);
  assert.equal(h.header.writes, 1);
});

test('Changed route, session, authority projection or markup cannot retain the mobile drawer', () => {
  const changes = [
    h => { h.runtime.context.path = '/studio'; },
    h => { h.runtime.context.session.csrfToken = 'fixture-b'; },
    h => { h.runtime.context.session.authenticated = false; },
    h => { h.runtime.page.admin = true; },
    h => { h.runtime.context.sidebar = '<nav>B</nav>'; },
    h => { h.runtime.context.header = '<header>B</header>'; },
    h => { h.runtime.mobile = false; },
  ];
  for (const change of changes) {
    const h = harness(); change(h); h.render();
    assert.equal(h.sidebar.open, false);
    assert.equal(h.sidebar.focused, false);
    assert.equal(h.sidebar.accessible, false);
    assert.equal(h.sidebar.writes, 2);
  }
});
