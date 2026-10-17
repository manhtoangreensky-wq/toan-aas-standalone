import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-auth.js', 'utf8');

function createStorage() {
  const values = new Map();
  return {
    getItem(key) { return values.has(key) ? values.get(key) : null; },
    setItem(key, value) { values.set(key, String(value)); },
    removeItem(key) { values.delete(key); }
  };
}

function mount(storage, input, path = '/login') {
  const listeners = new Map();
  const mainAttributes = new Map();
  const main = {
    dataset: {},
    hasAttribute(name) { return mainAttributes.has(name); },
    setAttribute(name, value) { mainAttributes.set(name, String(value)); },
    querySelector() { return null; }
  };
  Object.defineProperty(main, 'innerHTML', { set() {}, get() { return ''; } });
  const document = {
    body: { classList: { add() {} } },
    visibilityState: 'visible',
    getElementById(id) {
      if (id === 'portal-bootstrap') return { textContent: JSON.stringify({ path, interfaceLocale: 'vi' }) };
      if (id === 'portal-main') return main;
      return null;
    },
    querySelector(selector) {
      if (selector === 'input[name="email"]') return input;
      return null;
    },
    addEventListener(name, listener) { listeners.set(name, listener); }
  };
  const window = {
    sessionStorage: storage,
    location: { search: '?lang=vi' },
    matchMedia: () => ({ matches: false }),
    setTimeout() { return 1; },
    clearTimeout() {},
    addEventListener() {}
  };
  vm.runInNewContext(source, {
    window,
    document,
    navigator: { userAgent: 'QA', platform: 'QA', standalone: false, maxTouchPoints: 0 },
    fetch: () => new Promise(() => {}),
    Headers,
    URL,
    URLSearchParams,
    Uint8Array,
    crypto: { getRandomValues(array) { return array; } },
    Promise,
    Date,
    JSON,
    Object,
    Array,
    Error
  }, { filename: 'portal-auth.js' });
  return listeners;
}

test('keeps only the email draft while switching auth tabs', () => {
  const storage = createStorage();
  const firstInput = { name: 'email', value: 'owner@example.com' };
  const firstListeners = mount(storage, firstInput);
  firstListeners.get('click')({ target: { closest(selector) { return selector === '.portal-auth-switch a' ? {} : null; } } });

  const secondInput = { name: 'email', value: '' };
  mount(storage, secondInput, '/register');
  assert.equal(secondInput.value, 'owner@example.com');
  assert.equal(storage.getItem('toanaas.auth.email-draft'), 'owner@example.com');
});

test('does not persist a password or secret field', () => {
  const storage = createStorage();
  const emailInput = { name: 'email', value: 'owner@example.com' };
  const listeners = mount(storage, emailInput);
  listeners.get('input')({ target: { name: 'password', value: 'super-secret' } });
  assert.equal(storage.getItem('toanaas.auth.email-draft'), null);
});
