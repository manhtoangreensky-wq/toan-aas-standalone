import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const i18nSource = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const portalSource = fs.readFileSync('static/portal/portal.js', 'utf8');
const accountStart = i18nSource.indexOf('const ACCOUNT_CENTER_MESSAGES = {');
const viStart = i18nSource.indexOf('    vi: {', accountStart);
const enStart = i18nSource.indexOf('    en: {', viStart);
assert.ok(accountStart >= 0 && viStart > accountStart && enStart > viStart, 'Account Center catalogue must remain present');
const vi = i18nSource.slice(viStart, enStart);
const values = [...vi.matchAll(/^\s*"accountCenter\.profile\.[^"]+":\s*"([^"]*)"/gm)].map((match) => match[1]);

const renderStart = portalSource.indexOf('  function renderAccount(');
const renderEnd = portalSource.indexOf('  function renderInterfaceLocaleNavigator', renderStart);
assert.ok(renderStart >= 0 && renderEnd > renderStart, 'Account renderer must remain present');
const renderer = portalSource.slice(renderStart, renderEnd);
const fallbacks = [...renderer.matchAll(/copy\("[^"]+",\s*"([^"\\]*(?:\\.[^"\\]*)*)"/g)].map((match) => match[1]);

const genericEnglish = /\b(?:signed|server|canonical|provider|metadata|workflow|contract|timezone|runtime|mode|locale|browser|policy|account|session|password|logout|security\s+center|wallet|jobs|assets|handoff|data\s+control\s+center|asset\s+vault|identity|role|audit|token|studio\s+avatar|avatar|cyber|creator|business\s+leader|digital\s+artist|sign\s+in|login|link)\b/i;

test('Vietnamese Account profile catalogue keeps one language', () => {
  assert.equal(values.length, 101, 'Account profile must keep the complete fixed catalogue');
  const visibleCopy = values.join(' | ').replace(/\{[^}]+\}/g, '');
  assert.doesNotMatch(visibleCopy, genericEnglish, 'generic English leaked into the Vietnamese Account profile catalogue');
});

test('Account renderer fallbacks stay Vietnamese and preserve profile contracts', () => {
  assert.ok(fallbacks.length >= 45, 'Account renderer must keep explicit safe fallbacks');
  const visibleCopy = fallbacks.join(' | ').replace(/\{[^}]+\}/g, '');
  assert.doesNotMatch(visibleCopy, genericEnglish, 'generic English leaked into Account renderer fallbacks');
  assert.match(renderer, /data-portal-action="update-profile"/);
  assert.match(renderer, /data-portal-action="upgrade-telegram-account"/);
  assert.match(renderer, /data-portal-action="select-avatar-preset"/);
  assert.match(renderer, /data-portal-action="auth-logout"/);
  assert.match(renderer, /display_name/);
  assert.match(renderer, /avatar_url/);
  assert.match(renderer, /locale: profile\.locale/);
  assert.match(renderer, /timezone: profile\.timezone/);
  assert.match(renderer, /href="\/account\/security"/);
  assert.match(renderer, /href="\/account\/data-controls"/);
});
