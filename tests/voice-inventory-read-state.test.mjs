import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const integration = fs.readFileSync('static/portal/integration.js', 'utf8');
const catalog = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');

function functionBody(text, name, async = false) {
  const start = text.indexOf(`  ${async ? 'async ' : ''}function ${name}(`);
  const end = text.indexOf('\n  }', start) + 4;
  assert.ok(start >= 0 && end > start, `Missing production function: ${name}`);
  return text.slice(start, end);
}

const oldVoice = { id: 17, display_name: 'PRIVATE_PRIOR_ACCOUNT', status: 'active', tts_ready: true };

function renderer(locale) {
  const context = vm.createContext({ ICONS: { voice: '' }, renderEmpty: (title, body) => `<h3>${title}</h3><p>${body}</p>` });
  vm.runInContext(catalog, context);
  context.voiceUiText = (key, fallback, params) => context.TOANAASI18n.t(`voiceUi.${key}`, params, locale) || fallback;
  vm.runInContext(functionBody(source, 'safeText') + '\n' + functionBody(source, 'renderVoiceVault'), context);
  return context;
}

for (const locale of ['vi', 'en', 'zh']) {
  for (const state of ['loading', 'failed', 'guarded']) {
    test(`Voice library ${state} hides stale voices and stays localized (${locale})`, () => {
      const context = renderer(locale);
      const html = context.renderVoiceVault({ voiceProfiles: [oldVoice], voiceInventoryReadState: state });
      assert.doesNotMatch(html, /PRIVATE_PRIOR_ACCOUNT|data-voice-vault-management="ready"/);
      assert.match(html, new RegExp(`data-voice-inventory-state="${state}"`));
      assert.doesNotMatch(html, /No saved voices|Chưa có giọng đã lưu|暂无已保存的声音/);
      assert.doesNotMatch(html, /voiceUi\.|library\./);
      if (locale === 'en') assert.doesNotMatch(html.replace(/<[^>]+>/g, ''), /[À-ỹĐđ]/);
      if (state === 'loading') assert.match(html, /role="status"/);
      else assert.match(html, /data-portal-action="refresh-voice-inventory"/);
    });
  }
  test(`Only a successful empty library shows the empty state (${locale})`, () => {
    const html = renderer(locale).renderVoiceVault({ voiceProfiles: [], voiceInventoryReadState: 'ready' });
    assert.match(html, locale === 'vi' ? /Chưa có giọng đã lưu/ : locale === 'en' ? /No saved voices/ : /暂无已保存的声音/);
    assert.doesNotMatch(html, /data-voice-vault-management="ready"|<audio\b/);
  });
}

function hydration(api) {
  const states = [];
  let current = { voiceProfiles: [oldVoice], voiceInventoryReadState: 'ready', readiness: { stale: true } };
  const context = vm.createContext({
    api, base: () => current,
    merge: next => { current = { ...current, ...next }; states.push(current); },
    featurePageStates: () => ({})
  });
  vm.runInContext(functionBody(integration, 'hydrateCanonicalVoiceData', true), context);
  return { context, states, read: () => current };
}

test('Voice hydration clears prior names before awaiting the read', async () => {
  let release;
  const delayed = new Promise(resolve => { release = resolve; });
  const h = hydration(path => path === '/voice/profiles' ? delayed : Promise.resolve({ ok: true, data: { features: {} } }));
  const pending = h.context.hydrateCanonicalVoiceData('/voice/saved', () => true);
  assert.equal(h.read().voiceProfiles.length, 0);
  assert.equal(h.read().voiceInventoryReadState, 'loading');
  release({ ok: true, data: { items: [{ id: 18, display_name: 'Current voice', tts_ready: true }] } });
  await pending;
  assert.equal(h.read().voiceInventoryReadState, 'ready');
  assert.equal(h.read().voiceProfiles[0].display_name, 'Current voice');
});

test('A profile read failure cannot become an empty library or retain old voices', async () => {
  const h = hydration(path => path === '/voice/profiles' ? Promise.reject(new Error('network unavailable')) : Promise.resolve({ ok: true, data: { features: {} } }));
  await h.context.hydrateCanonicalVoiceData('/voice/saved', () => true);
  assert.equal(h.read().voiceInventoryReadState, 'failed');
  assert.equal(h.read().voiceProfiles.length, 0);
});

test('An explicit guarded response remains unavailable, including HTTP 200', async () => {
  const h = hydration(path => Promise.resolve(path === '/voice/profiles'
    ? { ok: false, status: 'guarded', data: {} }
    : { ok: true, data: { features: {} } }));
  await h.context.hydrateCanonicalVoiceData('/voice/saved', () => true);
  assert.equal(h.read().voiceInventoryReadState, 'guarded');
  assert.equal(h.read().voiceProfiles.length, 0);
});

test('An explicit failed read keeps the connection error state', async () => {
  const h = hydration(() => Promise.resolve({ ok: false, status: 'failed', data: {} }));
  await h.context.hydrateCanonicalVoiceData('/voice/saved', () => true);
  assert.equal(h.read().voiceInventoryReadState, 'failed');
  assert.equal(h.read().voiceProfiles.length, 0);
});

test('Malformed profile responses stay failed and do not invent zero totals', async () => {
  for (const data of [{}, { items: null }, { items: {} }]) {
    const h = hydration(() => Promise.resolve({ ok: true, data }));
    await h.context.hydrateCanonicalVoiceData('/voice/saved', () => true);
    assert.equal(h.read().voiceInventoryReadState, 'failed');
    assert.equal(h.read().voiceProfiles.length, 0);
    assert.equal(h.read().voiceVaultPage, undefined);
  }
});

test('Readiness failure does not conceal an independently successful voice list', async () => {
  const h = hydration(path => path === '/voice/profiles'
    ? Promise.resolve({ ok: true, data: { items: [{ id: 18, display_name: 'Current voice' }], total: 1 } })
    : Promise.reject(new Error('readiness unavailable')));
  await h.context.hydrateCanonicalVoiceData('/voice/saved', () => true);
  assert.equal(h.read().voiceInventoryReadState, 'ready');
  assert.equal(h.read().voiceProfiles.length, 1);
  assert.equal(Object.keys(h.read().readiness).length, 0);
});

test('A delayed prior-account response cannot replace a new account library', async () => {
  let release;
  let isCurrent = true;
  const delayed = new Promise(resolve => { release = resolve; });
  const h = hydration(path => path === '/voice/profiles' ? delayed : Promise.resolve({ ok: true, data: { features: {} } }));
  const pending = h.context.hydrateCanonicalVoiceData('/voice/saved', () => isCurrent);
  isCurrent = false;
  const mergeCount = h.states.length;
  release({ ok: true, data: { items: [oldVoice] } });
  await pending;
  assert.equal(h.states.length, mergeCount);
  assert.equal(h.read().voiceProfiles.length, 0);
});
