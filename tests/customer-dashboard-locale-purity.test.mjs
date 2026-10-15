import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');

function loadMessages() {
  const documentElement = {
    lang: 'vi',
    dir: 'ltr',
    setAttribute() {}
  };
  const document = {
    documentElement,
    title: '',
    getElementById() { return null; }
  };
  const context = {
    document,
    console,
    JSON,
    URL,
    URLSearchParams,
    CustomEvent: function CustomEvent() {},
    dispatchEvent() { return true; }
  };
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(source, context, { filename: 'portal-i18n.js' });
  return context.TOANAASI18n.messages;
}

const messages = loadMessages();
const dashboardEntries = Object.keys(messages.vi)
  .filter((key) => key.startsWith('dashboard.'));
const allowedProductNamesAndAcronyms = new Set([
  '3D', 'AI', 'AAS', 'API', 'BOT', 'ID', 'MP3', 'OCR', 'PDF', 'SUBDUB',
  'TELEGRAM', 'TOAN', 'TTS', 'URL', 'VIP', 'XU'
]);
const untranslatedVietnameseTerms = /\b(?:web|dashboard|canonical|core bridge|metadata|output|delivery|asset vault|job center|owner-scoped|projection|workspace|draft|workflow|studio|project|asset|job|vault|web-native|current window)\b/i;

function untranslatedWords(value) {
  return (value.replace(/\{[^}]+\}/g, ' ').match(/\b[A-Za-z][A-Za-z0-9.-]*\b/g) || [])
    .filter((word) => !allowedProductNamesAndAcronyms.has(word.toUpperCase()));
}

for (const locale of ['vi', 'en', 'zh']) {
  test(`all Dashboard copy follows the selected ${locale} language`, () => {
    assert.ok(dashboardEntries.length > 0, 'Dashboard copy inventory must not be empty');
    const untranslated = dashboardEntries.flatMap((key) => {
      const value = messages[locale][key];
      assert.equal(typeof value, 'string', `${locale} is missing ${key}`);
      if (locale === 'en') {
        return /[\u00c0-\u024f\u4e00-\u9fff]/u.test(value) ? [{ key, value }] : [];
      }
      const words = locale === 'vi'
        ? (untranslatedVietnameseTerms.test(value) ? [value.match(untranslatedVietnameseTerms)?.[0] || 'untranslated term'] : [])
        : untranslatedWords(value);
      return words.length ? [{ key, value, words }] : [];
    });
    assert.equal(untranslated.length, 0, `Mixed-language Dashboard keys: ${untranslated.map((item) => item.key).join(', ')}`);
  });
}
