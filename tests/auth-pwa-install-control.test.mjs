import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-auth.js', 'utf8');
const shellSource = fs.readFileSync('static/portal/portal.js', 'utf8');

test('Auth shell install entry uses reviewed locale copy instead of legacy mixed-language text', () => {
  assert.doesNotMatch(shellSource, /Táº£i & CÃ i Äáº·t App TOAN AAS/);
  assert.match(shellSource, /uiText\("installGuide\.title", "CÃ i á»©ng dá»¥ng TOAN AAS"\)/);
  assert.doesNotMatch(source, /ð²/u);
  assert.match(source, /class="portal-auth-install-icon"/);
  assert.match(source, /<svg class="portal-icon"/);
});

function mountAuth({ locale = 'vi', userAgent = '', platform = '', standalone = false } = {}) {
  const windowListeners = new Map();
  const documentListeners = new Map();
  const attributes = new Map();
  const label = { textContent: '' };
  const helper = { hidden: true, textContent: '' };
  const status = { hidden: true, textContent: '' };
  const control = {
    hidden: true,
    disabled: true,
    dataset: { portalAction: 'pwa-install-prompt' },
    querySelector(selector) { return selector === '[data-pwa-install-label]' ? label : null; },
    setAttribute(name, value) { attributes.set(name, String(value)); },
    removeAttribute(name) { attributes.delete(name); },
    getAttribute(name) { return attributes.get(name) ?? null; }
  };
  const mainAttributes = new Map();
  const main = {
    dataset: {},
    markup: '',
    hasAttribute(name) { return mainAttributes.has(name); },
    setAttribute(name, value) { mainAttributes.set(name, String(value)); },
    querySelector() { return null; }
  };
  Object.defineProperty(main, 'innerHTML', {
    get() { return main.markup; },
    set(value) { main.markup = String(value); }
  });
  const bootstrap = { textContent: JSON.stringify({ path: '/login', interfaceLocale: locale }) };
  const document = {
    body: { classList: { add() {} } },
    visibilityState: 'visible',
    getElementById(id) {
      if (id === 'portal-bootstrap') return bootstrap;
      if (id === 'portal-main') return main;
      return null;
    },
    querySelector(selector) {
      if (selector === '[data-portal-action="pwa-install-prompt"]') return control;
      if (selector === '[data-pwa-install-help]') return helper;
      if (selector === '[data-pwa-install-status]') return status;
      return null;
    },
    addEventListener(name, listener) { documentListeners.set(name, listener); }
  };
  const window = {
    location: { search: `?lang=${locale}` },
    matchMedia: query => ({ matches: standalone && query === '(display-mode: standalone)' }),
    setTimeout() { return 1; },
    clearTimeout() {},
    addEventListener(name, listener) { windowListeners.set(name, listener); }
  };
  const never = () => new Promise(() => {});
  const navigator = { userAgent, platform, standalone, maxTouchPoints: 0 };
  vm.runInNewContext(source, {
    window,
    document,
    navigator,
    fetch: never,
    URL,
    URLSearchParams,
    Promise,
    Date,
    JSON,
    Object,
    Array,
    Error
  }, { filename: 'portal-auth.js' });
  return { window, document, main, control, label, helper, status, windowListeners, documentListeners };
}

function clickInstall(app) {
  const listener = app.documentListeners.get('click');
  listener({ target: { closest: selector => selector === '[data-portal-action]' ? app.control : null } });
}

const instructionCases = [
  { locale: 'vi', platform: 'iOS', userAgent: 'iPhone', expected: 'ThÃªm vÃ o MÃ n hÃ¬nh chÃ­nh' },
  { locale: 'vi', platform: 'Android', userAgent: 'Android', expected: 'ThÃªm vÃ o mÃ n hÃ¬nh chÃ­nh' },
  { locale: 'vi', platform: 'desktop', userAgent: 'Windows', expected: 'thanh Äá»a chá»' },
  { locale: 'en', platform: 'iOS', userAgent: 'iPhone', expected: 'Add to Home Screen' },
  { locale: 'en', platform: 'Android', userAgent: 'Android', expected: 'browser menu' },
  { locale: 'en', platform: 'desktop', userAgent: 'Windows', expected: 'address bar' },
  { locale: 'zh', platform: 'iOS', userAgent: 'iPhone', expected: 'æ·»å å°ä¸»å±å¹' },
  { locale: 'zh', platform: 'Android', userAgent: 'Android', expected: 'æµè§å¨èå' },
  { locale: 'zh', platform: 'desktop', userAgent: 'Windows', expected: 'å°åæ ' }
];

for (const item of instructionCases) {
  test(`No native install prompt shows ${item.platform} installation steps in ${item.locale}`, () => {
    const app = mountAuth(item);
    assert.equal(app.control.hidden, false);
    assert.equal(app.control.disabled, false);
    assert.equal(app.label.textContent, { vi: 'CÃ¡ch cÃ i Äáº·t', en: 'How to install', zh: 'å®è£è¯´æ' }[item.locale]);
    assert.equal(app.control.getAttribute('aria-label'), app.label.textContent);
    assert.match(app.main.markup, /data-pwa-install-help/);
    assert.match(app.main.markup, /aria-controls="portal-pwa-install-help"/);
    clickInstall(app);
    assert.equal(app.helper.hidden, false);
    assert.ok(app.helper.textContent.includes(item.expected));
    assert.equal(app.control.getAttribute('aria-expanded'), 'true');
  });
}

test('A valid beforeinstallprompt invokes the native install prompt', async () => {
  const app = mountAuth({ locale: 'vi', userAgent: 'Android', platform: 'Android' });
  let promptCalls = 0;
  const installEvent = {
    preventDefault() {},
    async prompt() { promptCalls += 1; },
    userChoice: Promise.resolve({ outcome: 'accepted' })
  };
  app.windowListeners.get('beforeinstallprompt')(installEvent);
  assert.equal(app.label.textContent, 'CÃ i Äáº·t á»©ng dá»¥ng TOAN AAS');
  assert.equal(app.control.getAttribute('aria-label'), 'CÃ i Äáº·t á»©ng dá»¥ng TOAN AAS');
  clickInstall(app);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(promptCalls, 1);
  assert.equal(app.control.hidden, true);
  assert.equal(app.status.hidden, false);
  assert.equal(app.status.textContent, 'á»¨ng dá»¥ng TOAN AAS ÄÃ£ ÄÆ°á»£c cÃ i Äáº·t.');
});

test('An already-installed or standalone app does not show an install action', () => {
  const standalone = mountAuth({ locale: 'vi', standalone: true });
  assert.equal(standalone.control.hidden, true);
  assert.equal(standalone.control.disabled, true);
  assert.equal(standalone.status.hidden, false);
  assert.equal(standalone.status.textContent, 'á»¨ng dá»¥ng TOAN AAS ÄÃ£ ÄÆ°á»£c cÃ i Äáº·t.');

  const installed = mountAuth({ locale: 'en' });
  installed.windowListeners.get('appinstalled')();
  assert.equal(installed.control.hidden, true);
  assert.equal(installed.status.textContent, 'TOAN AAS is installed.');
});

// whitespace-clean regression guard (LF)
