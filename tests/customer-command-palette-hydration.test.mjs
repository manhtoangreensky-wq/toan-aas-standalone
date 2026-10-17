import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const mount = source.indexOf('  function mountPortal(override) {');
const start = source.indexOf('    // A hydration remount', mount);
const end = source.indexOf('    const surface = portalSurface(page);', start);
const closeStart = source.indexOf('  function closeCommandPalette(options) {');
const closeEnd = source.indexOf('  function isStandaloneApp()', closeStart);
assert.ok(start > 0 && end > start && closeEnd > closeStart);

function harness() {
  const palette = { hidden: false, innerHTML: '<dialog>unchanged</dialog>', query: 'voice', focusInside: true };
  const runtime = vm.createContext({
    commandPalette: palette, sidebar: { classList: { contains: () => false } },
    options: { reason: 'data-hydration' }, context: { path: '/dashboard', session: { authenticated: true, csrfToken: 'qa-session-a' }, palette: '<dialog>unchanged</dialog>' }, page: { admin: false },
    window: { location: { pathname: '/dashboard' } }, document: { querySelector: () => palette },
    normalizePath: value => value, isAdminPortalSurface: page => page.admin,
    renderCommandPalette: (_page, context) => context.palette,
    setCommandPaletteBackgroundInert() {}, closeSidebar() {}
  });
  vm.runInContext("let lastNormalizedRoute='/dashboard'; let lastCustomerHeaderSessionToken='qa-session-a'; let commandPaletteMarkup='<dialog>unchanged</dialog>'; let commandPaletteReturnFocus=null;", runtime);
  vm.runInContext(source.slice(closeStart, closeEnd), runtime);
  return { palette, runtime, render: () => vm.runInContext(`(() => { ${source.slice(start, end)} })()`, runtime) };
}

test('Unrelated customer hydration preserves an open quick switch and its typed search', () => {
  const h=harness(); h.render();
  assert.equal(h.palette.hidden, false);
  assert.equal(h.palette.innerHTML, '<dialog>unchanged</dialog>');
  assert.equal(h.palette.query, 'voice'); assert.equal(h.palette.focusInside, true);
});

test('A changed destination list closes the prior quick-switch projection', () => {
  const h=harness(); h.runtime.context.palette='<dialog>new authorized destinations</dialog>'; h.render();
  assert.equal(h.palette.hidden,true); assert.equal(h.palette.innerHTML,'');
});

test('Route, session and sign-out changes discard the open customer quick switch', () => {
  for(const change of [h=>{h.runtime.context.path='/account'},h=>{h.runtime.context.session.csrfToken='qa-session-b'},h=>{h.runtime.context.session.authenticated=false}]) {
    const h=harness(); change(h); h.render(); assert.equal(h.palette.hidden,true); assert.equal(h.palette.innerHTML,'');
  }
});

test('Admin quick-switch updates retain their existing close behavior', () => {
  const h=harness(); h.runtime.page.admin=true; h.render(); assert.equal(h.palette.hidden,true);
});
