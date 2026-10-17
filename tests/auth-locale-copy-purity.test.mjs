import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const authSource = fs.readFileSync('static/portal/portal-auth.js', 'utf8');
const i18nSource = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const objectStart = authSource.indexOf('  const text = {');
const objectOpen = authSource.indexOf('{', objectStart);
const objectMarker = authSource.indexOf('\n  }[locale];', objectOpen);
assert.ok(objectStart >= 0 && objectOpen > objectStart && objectMarker > objectOpen, 'Public-auth locale catalog exists');
const publicAuthCopy = vm.runInNewContext(`(${authSource.slice(objectOpen, objectMarker + 4)})`);

const i18nContext = {};
i18nContext.window = i18nContext;
vm.createContext(i18nContext);
vm.runInContext(i18nSource, i18nContext);
const authShellKeys = [
  'access.alternatives.loginHint',
  'access.help.loginEmail',
  'access.notice.registrationHandoffBody',
  'access.oauth.unavailable',
  'access.oauth.cancelled',
  'access.oauth.failed',
  'access.oauth.state',
  'access.oauth.session',
  'access.oauth.linkRequired',
  'access.oauth.linked',
  'access.notice.defaultProfileBody'
];

function accessValuesFor(locale) {
  const catalogStart = i18nSource.indexOf('const MESSAGES = {');
  const start = i18nSource.indexOf(`    ${locale}: {`, catalogStart);
  const nextLocale = locale === 'vi' ? '    en: {' : locale === 'en' ? '    zh: {' : '';
  const end = nextLocale
    ? i18nSource.indexOf(nextLocale, start + 1)
    : i18nSource.indexOf('\n  };', start + 1);
  assert.ok(catalogStart >= 0 && start > catalogStart && end > start, `Missing ${locale} catalog`);
  const block = i18nSource.slice(start, end);
  return [...block.matchAll(/"access\.[^"]+"\s*:\s*"((?:\\.|[^"\\])*)"/g)]
    .map(match => match[1].replace(/\\"/g, '"'));
}

function shellCopy(locale) {
  return [
    ...authShellKeys.map(key => i18nContext.TOANAASI18n.t(key, {}, locale)),
    ...accessValuesFor(locale)
  ].join(' ');
}

function authLocaleKeys(locale) {
  const start = authSource.indexOf(`    ${locale}: {`, objectOpen);
  const nextLocale = locale === 'vi' ? '    en: {' : locale === 'en' ? '    zh: {' : '';
  const end = nextLocale ? authSource.indexOf(nextLocale, start + 1) : objectMarker;
  assert.ok(start > objectOpen && end > start, `Missing auth ${locale} block`);
  return [...authSource.slice(start, end).matchAll(/^      ([A-Za-z][A-Za-z0-9]*):/gm)].map(match => match[1]);
}

test('Public-auth locale catalog does not declare duplicate keys', () => {
  for (const locale of ['vi', 'en', 'zh']) {
    const keys = authLocaleKeys(locale);
    assert.equal(new Set(keys).size, keys.length, `Duplicate auth copy key in ${locale}`);
  }
});

test('Vietnamese public-auth copy does not leak generic English auth jargon', () => {
  const copy = [...Object.values(publicAuthCopy.vi), shellCopy('vi')].join(' ');
  assert.doesNotMatch(copy, /\b(?:Signed session|App|Web App|Web account|provider|server|token|menu|gradient|Locale|workspace|Web Workspace|Telegram Login|Sign in with Apple)\b/i);
  assert.match(copy, /Phiên đăng nhập/);
  assert.match(copy, /ứng dụng TOAN AAS/);
});

test('English public-auth copy contains no Vietnamese text', () => {
  const copy = [...Object.values(publicAuthCopy.en), shellCopy('en')].join(' ');
  assert.doesNotMatch(copy, /[ăâđêôơưáàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ]/i);
});

test('Chinese public-auth copy does not leak generic English interface jargon', () => {
  const copy = [...Object.values(publicAuthCopy.zh), shellCopy('zh')].join(' ');
  const withoutNames = copy.replace(/TOAN AAS|Gmail|Google|Apple|Telegram|OAuth|Bot|Asia\/Ho_Chi_Minh/g, '');
  assert.doesNotMatch(withoutNames, /\b(?:App|Web App|Web account|signed session|provider|server|token|menu|gradient|Locale|workspace|Login|Sign in)\b/i);
  assert.match(copy, /应用/);
  assert.match(copy, /登录会话/);
});
