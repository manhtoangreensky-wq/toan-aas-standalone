import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync('static/portal/portal.js', 'utf8').replace(/\r\n/g, '\n');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const routes = ['/music/create', '/music/song'];
const session = { authenticated: true, csrfReady: true, csrfToken: 'fixture-session-a' };
const statuses = ['draft', 'ready', 'guarded', 'awaiting_confirm', 'queued', 'processing', 'completed', 'failed', 'failed_no_charge', 'error', 'cancelled', 'refunded'];
function fn(name, optional = false) {
  const start = source.indexOf(`  function ${name}(`);
  if (optional && start < 0) return '';
  assert.ok(start >= 0, `real function ${name}`);
  const end = source.indexOf('\n  }', start);
  assert.ok(end > start, `complete function ${name}`);
  return source.slice(start, end + 4);
}
function runtime(locale = 'vi', globals = true) {
  const ctx = { MUSIC_PRODUCT_ROUTES: routes, ALLOWED_STATES: new Set(statuses),
    FEATURE_TRACKING_JOB_STATES: new Set(statuses.slice(4)), FEATURE_TRACKING_ID_PATTERN: /^[A-Za-z0-9._:-]{1,160}$/, FEATURE_TRACKING_KEY_PATTERN: /^[a-z][a-z0-9_]{1,120}$/,
    STATE_LABELS: Object.fromEntries(statuses.map(s => [s, s])), STATE_I18N_KEYS: Object.fromEntries(statuses.map(s => [s, `state.${s}`])), RESULT_LABELS: { prompt: 'Prompt' },
    manifest: { '/music/create': { fields: [{ name: 'brief' }] }, '/music/song': { fields: [{ name: 'brief' }] } }, normalizePath: s => s };
  ctx.window = ctx; vm.createContext(ctx); vm.runInContext(catalogue, ctx); ctx.TOANAASI18n.setLocale(locale, { emit: false });
  if (globals) vm.runInContext((source.match(/^  (?:const musicSuggestionSnapshots|let musicSuggestionSnapshotSession) = .*;$/gm) || []).join('\n'), ctx);
  const names = ['portalI18n', 'uiText', 'safeText', 'stateLabel', 'badge', 'musicProductText', 'canonicalDraftText', 'featureDraftTarget', 'canonicalDraftActions', 'canonicalPreferredText', 'resultLabel', 'renderCanonicalValue', 'renderCanonicalSuggestions', 'renderCanonicalFlow', 'safeFeatureTracking', 'safeVoiceReport', 'renderFeatureTracking', 'flowQuoteExpiry', 'flowHasFreshEstimate', 'voiceQuoteAmount', 'renderMusicCanonicalSuggestions', 'renderMusicCanonicalReport', 'renderMusicFlowState'];
  vm.runInContext(names.map(name => fn(name)).join('\n') + '\n' + fn('synchronizeMusicSuggestionSnapshots', true), ctx);
  ctx.io = []; const forbidden = (...args) => { ctx.io.push(args); throw new Error('Unexpected application I/O'); };
  for (const key of ['fetch', 'XMLHttpRequest', 'WebSocket', 'setTimeout', 'setInterval', 'requestAnimationFrame']) ctx[key] = forbidden;
  ctx.localStorage = ctx.sessionStorage = { getItem: forbidden, setItem: forbidden, removeItem: forbidden, clear: forbidden };
  ctx.history = { pushState: forbidden, replaceState: forbidden }; ctx.document = { querySelector: forbidden, querySelectorAll: forbidden };
  return ctx;
}
const feature = route => route === '/music/song' ? 'music_song' : 'music_background';
const draft = (route, suggestions = [{ prompt: 'Original one' }, { prompt: 'Original two' }, { prompt: 'Original three' }]) => ({ feature: feature(route), phase: 'draft', status: 'draft', input: { brief: 'Original brief', tier: 'standard' }, data: { draft: { available: true, content: { suggestions } } } });
const estimate = route => ({ feature: feature(route), phase: 'estimate', status: 'awaiting_confirm', input: { brief: 'Original one', tier: 'standard' }, webQuoteReceipt: 'Q'.repeat(32), estimateFingerprint: 'fixture-fp', data: { estimate: { available: true, content: { estimated_xu: 0 } } } });
function sync(ctx, flows, signed = session) {
  if (ctx.synchronizeMusicSuggestionSnapshots) ctx.synchronizeMusicSuggestionSnapshots({ path: '/dashboard', session: signed, featureFlows: flows });
}
const cache = ctx => vm.runInContext('typeof musicSuggestionSnapshots === "undefined" ? null : musicSuggestionSnapshots', ctx);
const marker = ctx => vm.runInContext('typeof musicSuggestionSnapshotSession === "undefined" ? "" : musicSuggestionSnapshotSession', ctx);
const clean = value => JSON.parse(JSON.stringify(value));
const history = /data-music-suggestion-history/;
function prime(ctx, route = '/music/song') {
  sync(ctx, { [route]: draft(route) }); sync(ctx, { [route]: estimate(route) });
  const html = ctx.renderMusicFlowState(estimate(route), route);
  assert.match(html, history, 'real draft → estimate omission must retain previous options');
  return html;
}
for (const route of routes) test(`A01 real draft → estimate retains exactly three closed options: ${route}`, () => {
  const ctx = runtime(), html = prime(ctx, route);
  assert.equal((html.match(/data-music-suggestion-card=/g) || []).length, 3);
  for (const text of ['Original one', 'Original two', 'Original three']) assert.ok(html.includes(text));
  assert.match(html, /<details class="portal-music-suggestion-history" data-music-suggestion-history>/);
  assert.doesNotMatch(html, /<details[^>]*\bopen(?:\s|=|>)/i);
  assert.match(html, /data-music-sale-price>0 Xu</); assert.match(html, /data-canonical-field="brief"/);
  assert.ok(html.includes(`data-canonical-route="${route}"`));
  assert.equal((html.match(/data-portal-action="copy-canonical-draft"/g) || []).length, 3);
  assert.equal((html.match(/data-portal-action="apply-canonical-draft"/g) || []).length, 3);
});
test('A01 initial estimate and fresh runtime cannot manufacture history', () => {
  const ctx = runtime(); sync(ctx, { '/music/song': estimate('/music/song') });
  assert.doesNotMatch(ctx.renderMusicFlowState(estimate('/music/song'), '/music/song'), history);
  prime(ctx); assert.doesNotMatch(runtime().renderMusicFlowState(estimate('/music/song'), '/music/song'), history);
});
test('A01 current own suggestions replace the snapshot without duplicate history', () => {
  const ctx = runtime(); prime(ctx); const flow = estimate('/music/song');
  flow.data.estimate.content.suggestions = [{ prompt: 'New current option' }]; sync(ctx, { '/music/song': flow });
  const html = ctx.renderMusicFlowState(flow, '/music/song'); assert.doesNotMatch(html, history); assert.doesNotMatch(html, /Original one/);
  assert.equal((html.match(/data-music-suggestion-card=/g) || []).length, 1); assert.match(html, /New current option/);
});
test('A02 both routes capture independently even when context.path is not a Music route', () => {
  const ctx = runtime(); prime(ctx);
  sync(ctx, { '/music/create': draft('/music/create', [{ prompt: 'Background only' }]), '/music/song': draft('/music/song', [{ prompt: 'Song only' }]), '/foreign': draft('/music/song') });
  sync(ctx, { '/music/create': estimate('/music/create'), '/music/song': estimate('/music/song') });
  assert.equal(cache(ctx).size, 2);
  assert.match(ctx.renderMusicFlowState(estimate('/music/create'), '/music/create'), /Background only/);
  assert.doesNotMatch(ctx.renderMusicFlowState(estimate('/music/create'), '/music/create'), /Song only/);
  sync(ctx, { '/music/create': estimate('/music/create'), '/music/song': { ...estimate('/music/song'), feature: 'wrong' } });
  assert.equal(cache(ctx).size, 1); assert.match(ctx.renderMusicFlowState(estimate('/music/create'), '/music/create'), history);
  assert.doesNotMatch(ctx.renderMusicFlowState(estimate('/music/song'), '/music/song'), history);
});
test('A02 own scalars are cloned, normalized and whitelisted without mutation or deduplication', () => {
  const ctx = runtime(); prime(ctx); const long = 'm'.repeat(2000);
  const first = { prompt: ' \u0000First & <one>\n ', name: ' Name ', mood: long, tempo: '', instrument: 7, duration: {}, vocal: true, use_case: ' Raw use ', id: 'private', price: 999, token: 'private' };
  const second = Object.assign(Object.create({ mood: 'inherited metadata' }), { prompt: 'Same', name: 'n'.repeat(2001), tempo: '90 BPM' });
  const items = [first, Object.create({ prompt: 'inherited prompt' }), { prompt: false }, [], null, second, { prompt: 'Same', duration: '30s', vocal: ' Raw vocal ' }, { prompt: 'Fourth ignored' }];
  const flow = draft('/music/song', items), before = JSON.stringify(flow); sync(ctx, { '/music/song': flow });
  assert.equal(JSON.stringify(flow), before); const stored = cache(ctx).get('/music/song');
  assert.notEqual(stored.suggestions, items); assert.notEqual(stored.suggestions[0], first);
  assert.deepEqual(clean(stored), { feature: 'music_song', suggestions: [{ prompt: 'First & <one>', name: ' Name ', mood: long, tempo: '', use_case: ' Raw use ' }, { prompt: 'Same', tempo: '90 BPM' }, { prompt: 'Same', duration: '30s', vocal: ' Raw vocal ' }] });
  first.prompt = 'MUTATED'; items.length = 0; sync(ctx, { '/music/song': estimate('/music/song') });
  assert.match(ctx.renderMusicFlowState(estimate('/music/song'), '/music/song'), /First &amp; &lt;one&gt;/);
  assert.doesNotMatch(ctx.renderMusicFlowState(estimate('/music/song'), '/music/song'), /MUTATED|private|999|Fourth ignored/);
});
test('A02 prompt length, own-field and scalar validation accepts only real bounded prompts', () => {
  const ctx = runtime(); prime(ctx); const boundary = 'p'.repeat(2000);
  sync(ctx, { '/music/song': draft('/music/song', [{ prompt: 'p'.repeat(2001) }, Object.create({ prompt: 'inherited' }), { prompt: 42 }, { prompt: {} }, { prompt: ' \u0000 ' }, { prompt: boundary }]) });
  assert.deepEqual(clean(cache(ctx).get('/music/song')), { feature: 'music_song', suggestions: [{ prompt: boundary }] });
});
test('A02 strict nested session rejects missing, false, string-true and invalid tokens', () => {
  const cases = [null, {}, { ...session, authenticated: false }, { ...session, authenticated: 'true' }, { ...session, csrfReady: false }, { ...session, csrfReady: 'true' }, { authenticated: true, csrfToken: 'fixture' }, { ...session, csrfToken: '' }, { ...session, csrfToken: 7 }, { ...session, csrfToken: null }];
  for (const signed of cases) { const ctx = runtime(); prime(ctx); sync(ctx, { '/music/song': estimate('/music/song') }, signed);
    assert.equal(cache(ctx).size, 0); assert.equal(marker(ctx), ''); assert.doesNotMatch(ctx.renderMusicFlowState(estimate('/music/song'), '/music/song'), history); }
  const ctx = runtime(); prime(ctx); ctx.synchronizeMusicSuggestionSnapshots({ authenticated: true, csrfReady: true, csrfToken: 'fixture', featureFlows: { '/music/song': estimate('/music/song') } });
  assert.equal(cache(ctx).size, 0); assert.equal(marker(ctx), '');
});
test('A02 token rotation purges both routes before capture and logout clears the marker', () => {
  const ctx = runtime(); prime(ctx); sync(ctx, { '/music/create': draft('/music/create'), '/music/song': draft('/music/song') });
  sync(ctx, { '/music/create': estimate('/music/create'), '/music/song': estimate('/music/song') }, { ...session, csrfToken: 'fixture-session-b' });
  assert.equal(cache(ctx).size, 0); assert.equal(marker(ctx), 'fixture-session-b');
  sync(ctx, { '/music/song': draft('/music/song', [{ prompt: 'New session option' }]) }, { ...session, csrfToken: 'fixture-session-b' });
  assert.deepEqual(clean(cache(ctx).get('/music/song')), { feature: 'music_song', suggestions: [{ prompt: 'New session option' }] });
  sync(ctx, {}, { ...session, authenticated: false }); assert.equal(cache(ctx).size, 0); assert.equal(marker(ctx), '');
});
test('A02 invalid/missing flow, data, payload, phase and status clear rather than resurrect history', () => {
  const base = estimate('/music/song');
  const cases = [undefined, null, [], {}, { ...base, feature: 'music_background' }, { ...base, phase: 'confirm' }, { ...base, phase: 'submit' }, { ...base, status: 'error' }, { ...base, status: 'guarded' }, { ...base, status: 'draft' }, { ...draft('/music/song'), status: 'awaiting_confirm' }, { ...base, data: null }, { ...base, data: [] }, { ...base, data: {} }, { ...base, data: { estimate: [] } }, { ...base, data: { estimate: 'invalid' } }, { ...base, data: { estimate: { available: false } } }];
  for (const flow of cases) { const ctx = runtime(); prime(ctx); sync(ctx, { '/music/song': flow }); assert.equal(cache(ctx).size, 0); assert.doesNotMatch(ctx.renderMusicFlowState(base, '/music/song'), history); }
  const ctx = runtime(); prime(ctx); ctx.synchronizeMusicSuggestionSnapshots({ session }); assert.equal(cache(ctx).size, 0);
});
test('A02 own empty/malformed/all-invalid suggestions clear, absent estimate retains, absent draft clears', () => {
  for (const value of [[], {}, 'invalid', null, [null, []], [{ prompt: '' }], [Object.create({ prompt: 'inherited' })]]) {
    const ctx = runtime(); prime(ctx); const flow = estimate('/music/song'); flow.data.estimate.content.suggestions = value;
    sync(ctx, { '/music/song': flow }); assert.equal(cache(ctx).size, 0); assert.doesNotMatch(ctx.renderMusicFlowState(flow, '/music/song'), history);
  }
  const ctx = runtime(); prime(ctx); const flow = estimate('/music/song'); delete flow.data.estimate.content; flow.data.estimate.estimated_xu = 0;
  sync(ctx, { '/music/song': flow }); assert.match(ctx.renderMusicFlowState(flow, '/music/song'), history);
  sync(ctx, { '/music/song': { ...draft('/music/song'), data: { draft: { available: true, content: {} } } } }); assert.equal(cache(ctx).size, 0);
});
test('A02 inherited suggestions cannot seed snapshots; direct payload and ready draft can', () => {
  const ctx = runtime(); prime(ctx); const inherited = Object.create({ suggestions: [{ prompt: 'Inherited set' }] });
  const absent = estimate('/music/song'); absent.data.estimate.content = inherited; sync(ctx, { '/music/song': absent });
  assert.deepEqual(clean(cache(ctx).get('/music/song').suggestions), [{ prompt: 'Original one' }, { prompt: 'Original two' }, { prompt: 'Original three' }]);
  sync(ctx, { '/music/song': { ...draft('/music/song'), data: { draft: { content: inherited } } } }); assert.equal(cache(ctx).size, 0);
  sync(ctx, { '/music/song': { feature: 'music_song', phase: 'draft', status: 'ready', data: { draft: { suggestions: [{ prompt: 'Direct payload' }] } } } });
  assert.deepEqual(clean(cache(ctx).get('/music/song')), { feature: 'music_song', suggestions: [{ prompt: 'Direct payload' }] });
});
test('A02 renderer gates reject non-estimate, wrong route/feature, unavailable, own values and malformed cache', () => {
  const ctx = runtime(); prime(ctx); const base = estimate('/music/song');
  for (const flow of [{ ...base, phase: 'draft' }, { ...base, phase: 'confirm' }, { ...base, feature: 'wrong' }, { ...base, status: 'error' }, { ...base, status: 'guarded' }, { ...base, data: { estimate: { available: false } } }, { ...base, data: { estimate: [] } }]) assert.doesNotMatch(ctx.renderMusicFlowState(flow, '/music/song'), history);
  assert.doesNotMatch(ctx.renderMusicFlowState(base, '/other'), history);
  for (const value of [[], {}, null, 'bad']) { const flow = estimate('/music/song'); flow.data.estimate.content.suggestions = value; assert.doesNotMatch(ctx.renderMusicFlowState(flow, '/music/song'), history); }
  for (const value of [null, {}, { feature: 'wrong', suggestions: [{ prompt: 'Wrong' }] }, { feature: 'music_song', suggestions: [] }, { feature: 'music_song', suggestions: {} }]) { cache(ctx).set('/music/song', value); assert.doesNotMatch(ctx.renderMusicFlowState(base, '/music/song'), history); }
  prime(ctx); vm.runInContext('musicSuggestionSnapshotSession = ""', ctx); assert.doesNotMatch(ctx.renderMusicFlowState(base, '/music/song'), history);
});
test('A02 rendering is read-only, preserves quote/input identity and performs no application I/O', () => {
  const ctx = runtime(); prime(ctx); const flow = estimate('/music/song'), beforeFlow = JSON.stringify(flow), before = JSON.stringify([...cache(ctx)]), entry = cache(ctx).get('/music/song');
  const html = ctx.renderMusicFlowState(flow, '/music/song'); assert.match(html, history); ctx.renderMusicFlowState(flow, '/music/song');
  assert.equal(JSON.stringify([...cache(ctx)]), before); assert.equal(cache(ctx).get('/music/song'), entry); assert.equal(JSON.stringify(flow), beforeFlow);
  assert.deepEqual(ctx.io, []); assert.doesNotMatch(html, /fixture-session-a|fixture-fp|QQQQQQQQ|selectedID|<audio\b/);
});
test('A02 standalone renderer remains safe when new cache globals are absent', () => {
  const ctx = runtime('vi', false); assert.doesNotMatch(ctx.renderMusicFlowState(estimate('/music/song'), '/music/song'), history);
});
test('A02 retained prompt, name and all metadata remain fully HTML escaped through the real renderer', () => {
  const ctx = runtime(); prime(ctx); const text = '&<>\'"';
  sync(ctx, { '/music/song': draft('/music/song', [{ prompt: text, name: text, mood: text, tempo: text, instrument: text, duration: text, vocal: text, use_case: text }]) });
  sync(ctx, { '/music/song': estimate('/music/song') }); const html = ctx.renderMusicFlowState(estimate('/music/song'), '/music/song');
  assert.match(html, history); assert.equal((html.match(/&amp;&lt;&gt;&#39;&quot;/g) || []).length, 10); assert.ok(!html.includes(text));
});
for (const [locale, title, note] of [
  ['vi', 'Xem lại các phương án', 'Chọn hướng khác sẽ cần báo giá mới.'],
  ['en', 'Review previous options', 'Choosing another direction requires a new quote.'],
  ['zh', '查看之前的方案', '选择其他方向后需要重新报价。']
]) test(`A04 actual catalogue and renderer localize both history strings: ${locale}`, () => {
  const ctx = runtime(locale), i18n = ctx.TOANAASI18n;
  assert.equal(i18n.has('musicProduct.suggestion.historyTitle', locale), true); assert.equal(i18n.has('musicProduct.suggestion.historyNote', locale), true);
  assert.equal(i18n.t('musicProduct.suggestion.historyTitle', {}, locale), title); assert.equal(i18n.t('musicProduct.suggestion.historyNote', {}, locale), note);
  const html = prime(ctx); assert.ok(html.includes(`<summary>${title}</summary>`)); assert.ok(html.includes(`<p>${note}</p>`));
  assert.doesNotMatch(html, /musicProduct\.(?:musicProduct|flow\.suggestion)|\{number\}/);
});
