import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-auth.js', 'utf8');
const shellSource = fs.readFileSync('static/portal/portal.js', 'utf8');

test('Auth shell install entry uses reviewed locale copy instead of legacy mixed-language text', () => {
  assert.doesNotMatch(shellSource, /Tải & Cài đặt App TOAN AAS/);
  assert.match(shellSource, /uiText\("installGuide\.title", "Cài ứng dụng TOAN AAS"\)/);
  assert.doesNotMatch(source, /📲/u);
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
  { locale: 'vi', platform: 'iOS', userAgent: 'iPhone', expected: 'Thêm vào Màn hình chính' },
  { locale: 'vi', platform: 'Android', userAgent: 'Android', expected: 'Thêm vào màn hình chính' },
  { locale: 'vi', platform: 'desktop', userAgent: 'Windows', expected: 'thanh địa chỉ' },
  { locale: 'en', platform: 'iOS', userAgent: 'iPhone', expected: 'Add to Home Screen' },
  { locale: 'en', platform: 'Android', userAgent: 'Android', expected: 'browser menu' },
  { locale: 'en', platform: 'desktop', userAgent: 'Windows', expected: 'address bar' },
  { locale: 'zh', platform: 'iOS', userAgent: 'iPhone', expected: '添加到主屏幕' },
  { locale: 'zh', platform: 'Android', userAgent: 'Android', expected: '浏览器菜单' },
  { locale: 'zh', platform: 'desktop', userAgent: 'Windows', expected: '地址栏' }
];

for (const item of instructionCases) {
  test(`No native install prompt shows ${item.platform} installation steps in ${item.locale}`, () => {
    const app = mountAuth(item);
    assert.equal(app.control.hidden, false);
    assert.equal(app.control.disabled, false);
    assert.equal(app.label.textContent, { vi: 'Cách cài đặt', en: 'How to install', zh: '安装说明' }[item.locale]);
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
  assert.equal(app.label.textContent, 'Cài đặt ứng dụng TOAN AAS');
  assert.equal(app.control.getAttribute('aria-label'), 'Cài đặt ứng dụng TOAN AAS');
  clickInstall(app);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(promptCalls, 1);
  assert.equal(app.control.hidden, true);
  assert.equal(app.status.hidden, false);
  assert.equal(app.status.textContent, 'Ứng dụng TOAN AAS đã được cài đặt.');
});

test('An already-installed or standalone app does not show an install action', () => {
  const standalone = mountAuth({ locale: 'vi', standalone: true });
  assert.equal(standalone.control.hidden, true);
  assert.equal(standalone.control.disabled, true);
  assert.equal(standalone.status.hidden, false);
  assert.equal(standalone.status.textContent, 'Ứng dụng TOAN AAS đã được cài đặt.');

  const installed = mountAuth({ locale: 'en' });
  installed.windowListeners.get('appinstalled')();
  assert.equal(installed.control.hidden, true);
  assert.equal(installed.status.textContent, 'TOAN AAS is installed.');
});
