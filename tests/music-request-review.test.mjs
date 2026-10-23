import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../static/portal/portal.js', import.meta.url), 'utf8');
const catalogue = {};
vm.runInNewContext(fs.readFileSync(new URL('../static/portal/portal-i18n.js', import.meta.url), 'utf8'), catalogue);
const i18n = catalogue.TOANAASI18n;
function extract(name) {
  const start = source.indexOf(`  function ${name}(`), end = source.indexOf('\n  }', start);
  assert.ok(start >= 0 && end > start, `Missing actual production function: ${name}`);
  return source.slice(start, end + 4);
}
const functions = ['safeText', 'normalizePath', 'musicProductText', 'musicProductOptionLabel', 'musicProductRouteMode',
  'musicProductFields', 'featureKeyForPage', 'featureConfirmExecutionReady', 'flowQuoteExpiry', 'flowHasFreshEstimate',
  'voiceQuoteExpiryState', 'voiceQuoteAmount', 'voiceQuoteHasEdits', 'musicQuoteHasEdits', 'musicQuoteState', 'renderFormCard'];
const production = functions.map(extract).join('\n');
function fixture(route = '/music/song') {
  const state = { allowed: true, draft: {}, locale: 'vi' };
  // Only UI plumbing is doubled; the renderer, catalogue, escaping and every quote/edit/price gate are real.
  const runtime = {
    canAct: () => state.allowed, actionBlockReason: () => '', workspaceDraftIdForRoute: () => '',
    classifyPageBoundary: () => 'runtime_generator', transientFormValues: () => state.draft,
    renderFields: () => '', badge: () => '', stateFor: () => 'guarded', renderNotes: () => '',
    voiceUiText: (key, fallback) => fallback, imageUiText: (key, fallback) => fallback,
    uiText: (key, fallback, params) => i18n.has(key) ? i18n.t(key, params, state.locale) : fallback,
    window: { location: { pathname: route } }, FEATURE_PAGE_KEY_ALIASES: {},
    MUSIC_PRODUCT_ROUTES: ['/music/create', '/music/song'],
    ALLOWED_STATES: new Set(['draft', 'guarded', 'awaiting_confirm', 'processing', 'failed', 'queued', 'completed'])
  };
  vm.runInNewContext(production, runtime);
  const feature = route === '/music/song' ? 'music_song' : 'music_background';
  const page = { path: route, type: 'feature', action: 'feature-estimate', fields:
    ['brief', 'tier', 'mode', 'vocal_mode', 'lyrics', 'song_length_mode', 'duration_seconds'].map(name => ({ name, type: 'text' })) };
  const flow = { feature, phase: 'estimate', status: 'awaiting_confirm', estimateFingerprint: 'fp-valid', webQuoteReceipt: 'Q'.repeat(32),
    input: { brief: 'Original brief', tier: 'standard', mode: 'lyrics', vocal_mode: 'duet', lyrics: 'Original lyrics',
      song_length_mode: 'seconds', duration_seconds: '45' },
    data: { estimate: { available: true, content: { estimated_xu: 0 }, tier_required: false, scene_count_required: false },
      quote_expires_at: new Date(Date.now() + 600000).toISOString() } };
  const context = { session: { authenticated: true, csrfReady: true }, featureFlows: { [route]: flow },
    catalog: [{ key: feature, route }], capabilities: { 'feature-confirm': true },
    bridge: { featureExecutionFeatures: [feature], featureExecutionAvailable: true } };
  return { state, runtime, page, flow, context, render: () => runtime.renderFormCard(page, context) };
}
function review(html) {
  const section = html.match(/<section\b[^>]*data-music-request-review[^>]*>[\s\S]*?<\/section>/g) || [];
  assert.equal(section.length, 1, 'Expected one real Music request review section');
  return section[0];
}
const hasRow = (html, field) => html.includes(`data-music-review-field="${field}"`);
const row = (html, field) => html.match(new RegExp(`<div\\b[^>]*data-music-review-field="${field}"[^>]*>[\\s\\S]*?<\\/div>`))?.[0] || '';
const copy = [
  ['title', 'Kiểm tra yêu cầu', 'Review your request', '核对请求'],
  ['note', 'Các lựa chọn đã gửi để nhận báo giá này.', 'These are the selections submitted for this quote.', '以下为获取此报价时提交的选项。'],
  ['product', 'Sản phẩm', 'Product', '产品'], ['lyrics', 'Xem lời bài hát', 'View lyrics', '查看歌词']
];
for (const [column, locale] of ['vi', 'en', 'zh'].entries()) {
  test(`Review catalogue exposes the four requested ${locale} translations`, () => {
    for (const [key, ...values] of copy) {
      assert.equal(i18n.has(`musicProduct.review.${key}`), true, `Missing musicProduct.review.${key}`);
      assert.equal(i18n.t(`musicProduct.review.${key}`, {}, locale), values[column]);
    }
    assert.deepEqual(Object.keys(i18n.messages[locale]).filter(k => k.startsWith('musicProduct.review.')).sort(),
      copy.map(([key]) => `musicProduct.review.${key}`).sort());
  });
  test(`A valid zero-price snapshot renders escaped, complete private text in ${locale} without mutation`, () => {
    const f = fixture(); f.state.locale = locale;
    f.flow.input.brief = '  Xin chào & <b>"đêm"</b> \'你好\'\n'.repeat(180) + 'BRIEF_END';
    f.flow.input.lyrics = 'Hát & <i>"é"</i> \'歌\'\n'.repeat(180) + 'LYRICS_END';
    Object.assign(f.flow.input, { token: 'EXTRA_KEY_SENTINEL', provider_cost: 'EXTRA_KEY_SENTINEL', id: 'EXTRA_KEY_SENTINEL' });
    f.state.draft = { brief: f.flow.input.brief, lyrics: f.flow.input.lyrics, unknown: 'DRAFT_SENTINEL' };
    const originalInput = f.flow.input, before = structuredClone({ context: f.context, draft: f.state.draft, page: f.page });
    const html = f.render();
    assert.deepEqual({ context: f.context, draft: f.state.draft, page: f.page }, before);
    assert.equal(f.flow.input, originalInput);
    const section = review(html);
    assert.match(section, /class="portal-music-request-review"/);
    assert.match(section, /aria-labelledby="music-request-review-title"/);
    assert.match(section, /<h3\b[^>]*id="music-request-review-title"/);
    for (const [, ...values] of copy) assert.ok(section.includes(values[column]));
    assert.ok(section.includes('  Xin chào &amp; &lt;b&gt;&quot;đêm&quot;&lt;/b&gt; &#39;你好&#39;\n'.repeat(180) + 'BRIEF_END'));
    assert.ok(section.includes('Hát &amp; &lt;i&gt;&quot;é&quot;&lt;/i&gt; &#39;歌&#39;\n'.repeat(180) + 'LYRICS_END'));
    assert.match(section, /<strong>[^<]+<\/strong>/);
    assert.match(section, /<p\b[^>]*class="portal-music-review-text"[^>]*data-music-review-brief/);
    assert.match(section, /<details\b[^>]*data-music-review-lyrics[^>]*>\s*<summary>/);
    assert.match(section, /<pre\b[^>]*class="portal-music-review-text"/);
    assert.doesNotMatch(section, /<details[^>]*\sopen(?:[\s=>])|aria-live|autofocus|tabindex|<(?:form|input|button|a)\b|data-portal-action|EXTRA_KEY_SENTINEL|DRAFT_SENTINEL|<b>|<i>/);
    assert.ok(html.indexOf('</form>') < html.indexOf(section));
    assert.ok(html.indexOf(section) + section.length <= html.indexOf('<div class="portal-flow-actions">'));
    assert.equal((html.match(/data-portal-action="feature-confirm"/g) || []).length, 1);
    assert.ok(row(section, 'product').includes(['Bài hát', 'Song', '歌曲'][column]));
    for (const field of ['tier', 'mode', 'vocal_mode', 'song_length_mode', 'duration_seconds']) assert.ok(hasRow(section, field));
  });
}

const gates = [
  ['disabled', f => { f.state.allowed = false; }], ['no session', f => { delete f.context.session; }],
  ...['authenticated', 'csrfReady'].flatMap(key => [undefined, false, 'true', 1].map(value =>
    [`strict session ${key}=${String(value)}`, f => { if (value === undefined) delete f.context.session[key]; else f.context.session[key] = value; }])),
  ['no flow map', f => { delete f.context.featureFlows; }], ['missing flow', f => { delete f.context.featureFlows[f.page.path]; }],
  ['null flow', f => { f.context.featureFlows[f.page.path] = null; }], ['array flow', f => { f.context.featureFlows[f.page.path] = []; }],
  ['wrong feature', f => { f.flow.feature = 'voice_tts'; }], ['other Music feature', f => { f.flow.feature = 'music_background'; }],
  ...['draft', 'confirm', 'report', undefined].map(phase => [`phase ${phase}`, f => { f.flow.phase = phase; }]),
  ...['draft', 'processing', 'completed', undefined].map(status => [`status ${status}`, f => { f.flow.status = status; }]),
  ['no receipt', f => { delete f.flow.webQuoteReceipt; }], ['invalid receipt', f => { f.flow.webQuoteReceipt = 'bad!'; }],
  ['no fingerprint', f => { delete f.flow.estimateFingerprint; }], ['empty fingerprint', f => { f.flow.estimateFingerprint = ''; }],
  ['expired', f => { f.flow.data.quote_expires_at = new Date(Date.now() - 1000).toISOString(); }],
  ['no estimate', f => { delete f.flow.data.estimate; }], ['unavailable estimate', f => { f.flow.data.estimate.available = false; }],
  ['string available', f => { f.flow.data.estimate.available = 'true'; }],
  ...['tier_required', 'scene_count_required'].map(key => [key, f => { f.flow.data.estimate[key] = true; }]),
  ...[undefined, null, 'unknown', '0', '10', -1, NaN, Infinity, true, {}].map(value =>
    [`invalid price ${String(value)}`, f => { if (value === undefined) delete f.flow.data.estimate.content.estimated_xu; else f.flow.data.estimate.content.estimated_xu = value; }]),
  ['conflicting prices', f => { f.flow.data.estimate.quote_xu = 10; }],
  ...[undefined, null, [], 'bad'].map(input => [`invalid input ${String(input)}`, f => { f.flow.input = input; }]),
  ...[undefined, '', ' \n ', null, 42, true, {}, []].map(brief => [`invalid brief ${String(brief)}`, f => { f.flow.input.brief = brief; }]),
  ['inherited brief', f => { f.flow.input = Object.create({ brief: 'INHERITED_PRIVATE' }); }],
  ...['brief', 'tier', 'mode', 'vocal_mode', 'lyrics', 'song_length_mode', 'duration_seconds'].map(key =>
    [`edited ${key}`, f => { f.state.draft[key] = 'EDITED_PRIVATE'; }])
];
for (const [name, mutate] of gates) test(`Review is absent for ${name}`, () => {
  const f = fixture(); mutate(f);
  const before = structuredClone({ context: f.context, draft: f.state.draft });
  assert.doesNotMatch(f.render(), /data-music-request-review|music-request-review-title/);
  assert.deepEqual(structuredClone({ context: f.context, draft: f.state.draft }), before);
});
test('Background rejects a song feature and a non-Music route never acquires a review', () => {
  const bg = fixture('/music/create'); bg.flow.feature = 'music_song'; assert.doesNotMatch(bg.render(), /data-music-request-review/);
  const other = fixture('/tools/plan'); assert.doesNotMatch(other.render(), /data-music-request-review/);
});
for (const price of [0, 5]) test(`Valid numeric price ${price} retains the existing confirm gate`, () => {
  const f = fixture(); f.flow.data.estimate.content.estimated_xu = price;
  assert.equal(f.runtime.musicQuoteState(f.page, f.flow, f.state.draft).confirmAllowed, true);
  review(f.render());
});

const enums = {
  tier: [['basic', 'Cơ bản'], ['standard', 'Tiêu chuẩn'], ['premium', 'Cao cấp']],
  mode: [['lyrics', 'Bài hát có lời gốc'], ['melody', 'Giai điệu không lời'], ['custom', 'Theo mô tả riêng']],
  vocal_mode: [['auto', 'Tự động'], ['male', 'Giọng nam'], ['female', 'Giọng nữ'], ['duet', 'Song ca nam và nữ']],
  song_length_mode: [['seconds', 'Theo số giây'], ['half', 'Bản nửa'], ['full', 'Bản đầy đủ']]
};
for (const [field, options] of Object.entries(enums)) for (const [value, label] of options) test(`Own ${field}=${value} uses its catalogue label`, () => {
  const f = fixture(); f.flow.input[field] = value; assert.ok(row(review(f.render()), field).includes(`<dd>${label}</dd>`));
});
for (const field of Object.keys(enums)) for (const value of [undefined, 'EXTRA_KEY_SENTINEL', null, true, 7, { private: 'EXTRA_KEY_SENTINEL' }, []]) {
  test(`Invalid ${field}=${String(value)} is omitted without leaking data`, () => {
    const f = fixture(); if (value === undefined) delete f.flow.input[field]; else f.flow.input[field] = value;
    const section = review(f.render()); assert.equal(hasRow(section, field), false); assert.doesNotMatch(section, /EXTRA_KEY_SENTINEL|\[object Object\]/);
    if (field === 'mode') assert.doesNotMatch(section, /data-music-review-field="vocal_mode"|data-music-review-lyrics/);
    if (field === 'song_length_mode') assert.equal(hasRow(section, 'duration_seconds'), false);
  });
}
test('Inherited fields never provide rows or enable own dependent vocal/lyrics/duration', () => {
  const f = fixture(), inherited = { ...f.flow.input };
  f.flow.input = Object.assign(Object.create(inherited), { brief: 'Own brief', vocal_mode: 'male', lyrics: 'INHERITED_MODE_LEAK', duration_seconds: 60 });
  const section = review(f.render());
  for (const field of Object.keys(enums).concat('duration_seconds')) assert.equal(hasRow(section, field), false, field);
  assert.doesNotMatch(section, /data-music-review-lyrics|INHERITED_MODE_LEAK|Original lyrics/);
});
for (const route of ['/music/song', '/music/create']) for (const mode of ['melody', 'custom', 'background', 'lyrics']) {
  test(`${route} mode=${mode} respects route-specific and inactive fields`, () => {
    const f = fixture(route); f.flow.input.mode = mode; const section = review(f.render());
    const song = route === '/music/song', activeLyrics = song && ['lyrics', 'custom'].includes(mode);
    assert.equal(hasRow(section, 'mode'), song ? mode !== 'background' : mode !== 'lyrics');
    assert.equal(hasRow(section, 'vocal_mode'), activeLyrics); assert.equal(section.includes('data-music-review-lyrics'), activeLyrics);
    if (!activeLyrics) assert.doesNotMatch(section, /Original lyrics/);
    assert.ok(row(section, 'product').includes(song ? 'Bài hát' : 'Nhạc nền'));
  });
}
for (const length of ['half', 'full']) test(`${length} song length never displays a duration`, () => {
  const f = fixture(); f.flow.input.song_length_mode = length; assert.equal(hasRow(review(f.render()), 'duration_seconds'), false);
});
for (const route of ['/music/song', '/music/create']) for (const value of [1, 45, 600, '1', '001', '45', '600']) {
  test(`${route} preserves valid duration ${JSON.stringify(value)}`, () => {
    const f = fixture(route); f.flow.input.duration_seconds = value; if (route === '/music/create') delete f.flow.input.song_length_mode;
    assert.ok(row(review(f.render()), 'duration_seconds').includes(`<dd>${value}</dd>`));
  });
}
for (const value of [undefined, null, '', ' ', '0', '000', '0001', '601', '1.5', '1e2', '+1', ' 1', '1 ', 0, -1, 601, 1.5, NaN, Infinity, true, false, {}, []]) {
  test(`Invalid duration ${String(value)} is omitted from a nonempty review`, () => {
    const f = fixture('/music/create'); f.flow.input.duration_seconds = value;
    assert.equal(hasRow(review(f.render()), 'duration_seconds'), false);
  });
}
for (const value of [undefined, '', null, 7, true, {}, []]) test(`Inactive/invalid lyrics ${String(value)} are not disclosed`, () => {
  const f = fixture(); f.flow.input.lyrics = value; assert.doesNotMatch(review(f.render()), /data-music-review-lyrics/);
});
test('Own nonempty whitespace lyrics are preserved, not silently trimmed', () => {
  const f = fixture(); f.flow.input.lyrics = ' \n '; assert.ok(review(f.render()).includes('<pre class="portal-music-review-text"> \n </pre>'));
});
test('Edit/remount suppresses the old snapshot, exact revert restores it, and a new estimate replaces it', () => {
  const f = fixture(), original = review(f.render());
  f.state.draft = { brief: 'Edited new brief' }; assert.doesNotMatch(f.render(), /data-music-request-review/);
  assert.equal(f.runtime.musicQuoteState(f.page, f.flow, f.state.draft).confirmAllowed, false);
  assert.equal(f.flow.input.brief, 'Original brief'); f.state.draft = { brief: 'Original brief' };
  assert.equal(review(f.render()), original); assert.equal(f.runtime.musicQuoteState(f.page, f.flow, f.state.draft).confirmAllowed, true);
  f.flow.input = { ...f.flow.input, brief: 'New estimate brief' }; f.flow.estimateFingerprint = 'new-fingerprint'; f.state.draft = {};
  const next = review(f.render()); assert.ok(next.includes('New estimate brief')); assert.doesNotMatch(next, /Original brief/);
  f.flow.data.quote_expires_at = new Date(Date.now() - 1000).toISOString(); assert.doesNotMatch(f.render(), /data-music-request-review/);
  f.flow.data.quote_expires_at = new Date(Date.now() + 600000).toISOString(); f.context.session.authenticated = false;
  assert.doesNotMatch(f.render(), /data-music-request-review|New estimate brief/);
});
