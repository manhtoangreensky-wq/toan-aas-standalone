import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-auth.js', 'utf8');
const telegramUrl = 'https://t.me/toanaasbot?start=login-session-123';

async function mountAuth() {
  const documentListeners = new Map();
  const windowListeners = new Map();
  const requests = [];
  const order = [];
  const popups = [];
  let resolveStart;
  let rejectStart;
  let popupBlocked = false;
  const startGate = new Promise((resolve, reject) => {
    resolveStart = resolve;
    rejectStart = reject;
  });
  const response = (payload, ok = true) => ({ ok, json: async () => payload });
  const bootstrap = { textContent: JSON.stringify({ path: '/login', interfaceLocale: 'vi' }) };
  const classList = { add() {}, remove() {}, contains() { return false; } };
  const mainAttributes = new Map();
  const main = {
    dataset: {}, classList, markup: '',
    hasAttribute(name) { return mainAttributes.has(name); },
    setAttribute(name, value) { mainAttributes.set(name, String(value)); },
    querySelector() { return null; }
  };
  Object.defineProperty(main, 'innerHTML', {
    get() { return main.markup; },
    set(value) { main.markup = String(value); }
  });
  const pwaLabel = { textContent: '' };
  const pwaControl = {
    hidden: true, disabled: true, dataset: { portalAction: 'pwa-install-prompt' },
    querySelector() { return pwaLabel; },
    setAttribute() {}, removeAttribute() {}
  };
  const pwaHelp = { hidden: true, textContent: '' };
  const pwaStatus = { hidden: true, textContent: '' };
  const toastRegion = { appendChild() {} };
  const document = {
    body: { classList }, visibilityState: 'visible',
    getElementById(id) {
      if (id === 'portal-bootstrap') return bootstrap;
      if (id === 'portal-main') return main;
      return null;
    },
    querySelector(selector) {
      if (selector === '[data-portal-action="pwa-install-prompt"]') return pwaControl;
      if (selector === '[data-pwa-install-help]') return pwaHelp;
      if (selector === '[data-pwa-install-status]') return pwaStatus;
      if (selector === '[data-portal-toast]') return toastRegion;
      return null;
    },
    createElement() { return { className: '', textContent: '', remove() {} }; },
    addEventListener(name, handler) { documentListeners.set(name, handler); }
  };
  const fetch = url => {
    requests.push(url);
    if (url.endsWith('/auth/providers')) return Promise.resolve(response({ data: { providers: {} } }));
    if (url.endsWith('/auth/telegram/connection/status')) return Promise.resolve(response({ data: { ready: true } }));
    if (url.endsWith('/auth/telegram/login/start')) {
      order.push('api-start');
      return startGate;
    }
    return Promise.resolve(response({ ok: false, error_code: 'UNEXPECTED_TEST_REQUEST' }, false));
  };
  const window = {
    location: { search: '', assigned: [], assign(url) { this.assigned.push(url); } },
    TOANAASPortalTheme: { syncControls() {} },
    matchMedia: () => ({ matches: false }),
    setTimeout() { return 1; }, clearTimeout() {},
    addEventListener(name, handler) { windowListeners.set(name, handler); },
    open(url, target) {
      order.push(`open:${url}`);
      if (popupBlocked) return null;
      const popup = {
        location: { href: url }, target, closed: false, opener: window,
        close() { this.closed = true; }
      };
      popups.push(popup);
      return popup;
    }
  };

  vm.runInNewContext(source, {
    window, document, fetch, Headers, URL, URLSearchParams, Uint8Array,
    crypto: { getRandomValues(array) { return array; } },
    Promise, Date, JSON, Object, Array, Error
  }, { filename: 'portal-auth.js' });
  const flush = async () => {
    for (let index = 0; index < 4; index += 1) await new Promise(resolve => setImmediate(resolve));
  };
  await flush();
  order.length = 0;
  const action = { dataset: { portalAction: 'start-telegram-login' }, disabled: false, setAttribute() {} };
  const click = () => documentListeners.get('click')({
    target: { closest(selector) {
      if (selector === '[data-portal-toggle-password]') return null;
      if (selector === '[data-portal-action]') return action;
      return null;
    } }
  });
  return {
    action, click, documentListeners, flush, order, popups, requests,
    resolveStart, rejectStart,
    setPopupBlocked(value) { popupBlocked = value; }, window
  };
}

function successfulStart(code) {
  return {
    ok: true,
    json: async () => ({
      ok: true,
      status: 'awaiting_confirm',
      message: 'Continue in Telegram',
      data: { deep_link: telegramUrl, code, expires_in_minutes: 5 }
    })
  };
}

test('Opens the Telegram tab in the click before login-start resolves', async () => {
  const app = await mountAuth();
  app.click();
  assert.deepEqual(app.order.slice(0, 2), ['open:about:blank', 'api-start']);
  assert.equal(app.popups.length, 1);
  assert.equal(app.popups[0].target, '_blank');
  assert.equal(app.popups[0].opener, null);
  assert.equal(app.popups[0].location.href, 'about:blank');
  app.resolveStart(successfulStart('A'.repeat(12)));
  await app.flush();
  assert.equal(app.popups[0].location.href, telegramUrl);
  assert.equal(app.popups[0].closed, false);
  assert.equal(app.requests.filter(url => url.endsWith('/auth/telegram/login/start')).length, 1);
});

test('Closes the synchronously opened blank tab when login-start fails', async () => {
  const app = await mountAuth();
  app.click();
  assert.equal(app.popups.length, 1);
  app.rejectStart(new Error('local QA failure'));
  await app.flush();
  assert.equal(app.popups[0].closed, true);
});

test('Falls back to the validated deep link in the same tab when the popup is blocked', async () => {
  const app = await mountAuth();
  app.setPopupBlocked(true);
  app.click();
  assert.deepEqual(app.order.slice(0, 2), ['open:about:blank', 'api-start']);
  app.resolveStart(successfulStart('B'.repeat(12)));
  await app.flush();
  assert.deepEqual(app.window.location.assigned, [telegramUrl]);
});

test('Closes a blank tab when the server returns an invalid deep link', async () => {
  const app = await mountAuth();
  app.click();
  app.resolveStart({
    ok: true,
    json: async () => ({ ok: true, status: 'awaiting_confirm', data: { deep_link: 'javascript:alert(1)' } })
  });
  await app.flush();
  assert.equal(app.popups[0].closed, true);
  assert.deepEqual(app.window.location.assigned, []);
});
