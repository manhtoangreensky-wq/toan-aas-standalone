import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const auth = fs.readFileSync('static/portal/portal-auth.js', 'utf8');
const portalCss = fs.readFileSync('static/portal/portal.css', 'utf8');
const theme = fs.readFileSync('static/portal/portal-theme.css', 'utf8');
const motion = fs.readFileSync('static/portal/portal-motion.js', 'utf8');

function selectorBlock(source, selector) {
  const start = source.indexOf(selector);
  assert.ok(start >= 0, `missing selector: ${selector}`);
  const open = source.indexOf('{', start);
  assert.ok(open >= 0, `missing declaration block: ${selector}`);
  let depth = 0;
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1;
    if (source[index] === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(open + 1, index);
    }
  }
  throw new Error(`unterminated block: ${selector}`);
}

async function mountAuthMotionLifecycle() {
  const source = auth;
  const attributes = new Map();
  const documentListeners = new Map();
  const windowListeners = new Map();
  const frames = [];
  const timers = [];
  const requests = [];
  let mainWrites = 0;
  let card = null;
  let primary = null;
  let social = null;
  let resolveProviders;
  let resolveConnection;
  const providersGate = new Promise(resolve => { resolveProviders = resolve; });
  const connectionGate = new Promise(resolve => { resolveConnection = resolve; });
  const response = (payload, ok = true) => ({ ok, json: async () => payload });
  const bootstrap = { textContent: JSON.stringify({ path: '/login', interfaceLocale: 'vi' }) };
  const classList = { add() {}, remove() {}, contains() { return false; } };
  const makeSocial = markup => ({ markup, remove() { social = null; } });
  const makePrimary = markup => {
    const node = { markup };
    Object.defineProperty(node, 'innerHTML', {
      get() { return node.markup; },
      set(value) { node.markup = String(value); }
    });
    return node;
  };
  const makeCard = markup => {
    primary = makePrimary(markup);
    social = markup.includes('portal-direct-social-auth') ? makeSocial(markup) : null;
    return {
      querySelector(selector) {
        if (selector === '.portal-auth-primary') return primary;
        if (selector === '.portal-direct-social-auth') return social;
        return null;
      },
      replaceChild(next, previous) { if (social === previous) social = next; },
      appendChild(next) { social = next; }
    };
  };
  const main = {
    dataset: {},
    hasAttribute(name) { return attributes.has(name); },
    getAttribute(name) { return attributes.get(name) || null; },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    querySelector(selector) { return selector === '.portal-auth-card' ? card : null; }
  };
  Object.defineProperty(main, 'innerHTML', {
    get() { return main.markup || ''; },
    set(value) { mainWrites += 1; main.markup = String(value); card = makeCard(main.markup); }
  });
  const document = {
    body: { classList }, visibilityState: 'visible',
    getElementById(id) {
      if (id === 'portal-bootstrap') return bootstrap;
      if (id === 'portal-main') return main;
      return null;
    },
    querySelector(selector) {
      if (selector === '[data-portal-shell]') return { classList: { add() {} } };
      if (selector === '[data-portal-sidebar]' || selector === '[data-portal-header]' || selector === '[data-portal-mobile-nav]') return { hidden: false };
      return null;
    },
    createElement() {
      const node = { firstElementChild: null, className: '', textContent: '' };
      Object.defineProperty(node, 'innerHTML', {
        set(value) { node.firstElementChild = makeSocial(String(value)); }
      });
      return node;
    },
    addEventListener(name, handler) { documentListeners.set(name, handler); }
  };
  const fetch = url => {
    requests.push(url);
    if (url.endsWith('/auth/providers')) return providersGate.then(() => response({ data: { providers: { google: { enabled: true } } } }));
    if (url.endsWith('/auth/telegram/connection/status')) return connectionGate.then(() => response({ data: { ready: true } }));
    if (url.endsWith('/auth/telegram/login/status')) return Promise.resolve(response({ ok: true, data: { ready: false } }));
    return Promise.resolve(response({ ok: false, message: 'unexpected' }, false));
  };
  const window = {
    location: { search: '' },
    matchMedia: () => ({ matches: false }),
    requestAnimationFrame(callback) { frames.push(callback); return frames.length; },
    cancelAnimationFrame() {},
    setTimeout(callback) { timers.push(callback); return timers.length; },
    clearTimeout() {},
    addEventListener(name, handler) { windowListeners.set(name, handler); },
    TOANAASPortalTheme: { syncControls() {} }
  };
  vm.runInNewContext(source, {
    window, document, fetch, Headers, URL, URLSearchParams, Uint8Array,
    crypto: { getRandomValues(array) { return array; } },
    Promise, Date, JSON, Object, Array, Error
  }, { filename: 'portal-auth.js' });
  const flush = async () => {
    for (let index = 0; index < 4; index += 1) await new Promise(resolve => setImmediate(resolve));
  };
  return {
    attributes, card, getCard: () => card, getMainWrites: () => mainWrites,
    resolveProviders, resolveConnection, flush,
    flushFrame() { const pending = frames.splice(0); pending.forEach(callback => callback()); },
    runTimers() { const pending = timers.splice(0); pending.forEach(callback => callback()); },
    requests
  };
}

test('Auth hydration keeps entry phase until the bounded lifecycle settles', () => {
  const renderStart = auth.indexOf('  function render(options = {})');
  const renderEnd = auth.indexOf('  function setBusy', renderStart);
  const render = auth.slice(renderStart, renderEnd);
  assert.match(auth, /AUTH_MOTION_ENTRY_MS\s*=\s*680/);
  assert.match(auth, /scheduleAuthMotionSettle\(main\)/);
  assert.match(auth, /authMotionPhase\(main\)\s*===\s*["']entry["']/);
  assert.match(render, /if \(authMotionPhase\(main\) !== ["']entry["']\)\s*main\.setAttribute\([\s\S]*?settled/);
  assert.match(render, /const oldSocial = card\.querySelector\("\.portal-direct-social-auth"\)/);
  assert.doesNotMatch(render.slice(0, render.indexOf('main.innerHTML =')), /main\.innerHTML/);
});

test('Portal motion timing keeps micro interactions readable and exit faster than entry', () => {
  const fast = theme.match(/--portal-motion-fast:\s*(\d+)ms/);
  const base = theme.match(/--portal-motion-base:\s*(\d+)ms/);
  const authEntry = auth.match(/AUTH_MOTION_ENTRY_MS\s*=\s*(\d+)/);
  const landingHero = theme.match(/--portal-landing-motion-hero:\s*(\d+)ms/);
  assert.ok(fast && base && authEntry && landingHero, 'motion timing tokens must remain explicit');
  const fastMs = Number(fast[1]);
  const baseMs = Number(base[1]);
  assert.ok(fastMs >= 150 && fastMs <= 300, 'micro interactions stay in the 150–300ms window');
  assert.ok(baseMs >= 150 && baseMs <= 300, 'route entry stays in the 150–300ms window');
  assert.ok(fastMs < baseMs, 'exit/feedback timing remains faster than route entry');
  assert.equal(Number(authEntry[1]), 680, 'auth entrance keeps its observable 680ms contract');
  assert.equal(Number(landingHero[1]), 980, 'landing cinematic hero keeps its 980ms contract');
});

test('Auth provider hydration does not restart or cut the entry animation', async () => {
  const app = await mountAuthMotionLifecycle();
  assert.equal(app.attributes.get('data-auth-motion-phase'), 'entry');
  const firstCard = app.getCard();
  app.resolveProviders();
  app.resolveConnection();
  await app.flush();
  assert.equal(app.getMainWrites(), 1);
  assert.equal(app.getCard(), firstCard);
  assert.equal(app.attributes.get('data-auth-motion-phase'), 'entry');
  app.flushFrame();
  app.flushFrame();
  assert.equal(app.attributes.get('data-auth-motion-phase'), 'entry');
  app.runTimers();
  assert.equal(app.attributes.get('data-auth-motion-phase'), 'settled');
});

test('Auth provider area reserves the late provider row', () => {
  const block = selectorBlock(portalCss, '.portal-direct-social-auth');
  assert.match(block, /min-height\s*:\s*86px/);
  assert.match(auth, /class="portal-direct-social-auth"/);
});

test('Landing sheen uses compositor transform instead of left transition', () => {
  const marker = '.landing-motion-scroll[data-landing-scroll-motion="active"] .landing-motion-final::before';
  const block = selectorBlock(theme, marker);
  assert.match(block, /left\s*:\s*0/);
  assert.match(block, /transform\s*:\s*translate3d\(/);
  assert.doesNotMatch(block, /transition\s*:\s*(?:left|transform)\b/);
});

test('Scroll-driven transforms do not carry scrub transitions that lag input', () => {
  for (const selector of [
    '.landing-motion-scroll[data-landing-scroll-motion="active"] .portal-landing-hero-copy',
    '.landing-motion-scroll[data-landing-scroll-motion="active"] .landing-motion-parallax',
    '.landing-motion-scroll[data-landing-scroll-motion="active"] .landing-motion-workflow li',
    '.landing-motion-scroll[data-landing-scroll-motion="active"] .portal-landing-trust-grid > article',
  ]) {
    const block = selectorBlock(theme, selector);
    assert.doesNotMatch(block, /transition\s*:[^;]*transform[^;]*var\(--portal-landing-scroll-scrub/);
  }
  assert.match(motion, /requestAnimationFrame\(syncHeader\)/);
});

test('Scroll-driven landing scenes do not repaint backgrounds from progress variables', () => {
  for (const selector of [
    '.landing-motion-scroll[data-landing-scroll-motion="active"] .landing-motion-features',
    '.landing-motion-scroll[data-landing-scroll-motion="active"] .landing-motion-feature',
  ]) {
    const block = selectorBlock(theme, selector);
    assert.doesNotMatch(block, /background(?:-color)?\s*:/);
  }
});

test('Global compositor hints are not blanket-applied to every Portal surface', () => {
  assert.doesNotMatch(theme, /\.portal-page\s*,\s*\.portal-card[\s\S]*?will-change:\s*transform, opacity/);
  assert.doesNotMatch(theme, /\.portal-header\s*\{\s*transform:\s*translateZ\(0\)/);
});

test('Landing reduced-motion changes detach the active presentation lifecycle', () => {
  assert.match(motion, /matchMedia\(REDUCED_MOTION_QUERY\)/);
  assert.match(motion, /removeReducedMotionListener/);
  assert.match(motion, /if \(event && event\.matches\) unmountLanding\(\)/);
});

test('Landing scroll metadata avoids redundant DOM writes and dead offset variables', () => {
  const syncStart = motion.indexOf('const syncScrollMotion = () => {');
  const syncEnd = motion.indexOf('\n    const resetPointer', syncStart);
  const sync = motion.slice(syncStart, syncEnd);
  assert.match(sync, /progressPercent/);
  assert.match(sync, /getAttribute\("data-landing-scroll-progress"\)/);
  assert.match(sync, /getAttribute\("data-landing-motion-section"\)/);
  assert.doesNotMatch(sync, /--landing-section-offset/);
});

test('Reduced-motion remains an explicit static fallback for landing motion', () => {
  const landingStart = theme.indexOf('.landing-motion-scroll[data-landing-scroll-motion="active"]');
  const reducedStart = theme.indexOf('@media (prefers-reduced-motion: reduce)', landingStart);
  assert.ok(reducedStart >= 0);
  const reduced = theme.slice(reducedStart, reducedStart + 2600);
  assert.match(reduced, /transform:\s*none\s*!important/);
  assert.match(reduced, /transition:\s*none\s*!important/);
  const authReduced = theme.slice(theme.indexOf('@media (prefers-reduced-motion: reduce)', theme.indexOf('/* Auth Motion Contract')));
  assert.match(authReduced, /animation:\s*none\s*!important/);
});
