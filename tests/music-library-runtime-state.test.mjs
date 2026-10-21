import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/integration.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function fn(name) {
  let start = source.indexOf(`  function ${name}(`);
  if (start < 0) start = source.indexOf(`  async function ${name}(`);
  assert.ok(start >= 0, `missing function ${name}`);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}
function between(start, end) { return source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start))); }
const boundary = {
  execution: 'web_native_media_library_read_only', library_persisted: false, collection_mutated: false,
  input_persisted: false, source_audio_inspected: false, provider_called: false, catalog_searched: false,
  player_opened: false, preview_created: false, audio_created: false, output_created: false, job_created: false,
  wallet_mutated: false, payment_started: false, asset_saved: false, delivery_created: false, bot_called: false,
  telegram_called: false, rights_verified: false, release_approved: false
};
function response(url, items = [], hasMore = false) {
  const params = new URL(url, 'http://qa.invalid').searchParams;
  const offset = Number(params.get('offset'));
  return { status: 'read_only', data: { items, filters: { role: params.get('role'), q: params.get('q') || '' },
    pagination: { limit: 24, offset, returned: items.length, has_more: hasMore, next_offset: hasMore ? offset + 24 : null }, boundary } };
}
function harness({ path = '/music/library', locale = 'vi', priorRole = 'music', query = '', offset = 0 } = {}) {
  let state = { path, mediaWorkspaceEnabled: true, session: { authenticated: true }, capabilities: { 'music-library-view': true },
    musicLibraryReadState: 'loading', musicLibraryItems: [{ reference_title: 'STALE_PRIVATE_ITEM' }],
    musicLibraryListing: { filters: { role: priorRole, q: query }, pagination: { offset } } };
  const calls = [], toasts = [];
  const ctx = { window: null, URLSearchParams,
    base: () => state, merge: patch => { state = { ...state, ...patch }; },
    toast: (message, type) => toasts.push({ message, type: type || 'success' }),
    // Sensitive-content policy is not under test; real bounded line/role/DTO/epoch checks remain active.
    mediaWorkspaceSafetyError: () => '', validMediaCollectionId: value => /^[0-9a-f-]{8,64}$/i.test(value),
    MEDIA_WORKSPACE_MAX_LIST_OFFSET: 10000, musicLibraryHydrationEpoch: 0, mediaWorkspaceSessionEpoch: 1,
    api: async url => { calls.push(url); return ctx.transport(url); }, transport: async url => response(url),
    location: { pathname: path }
  };
  ctx.window = ctx;
  vm.createContext(ctx); vm.runInContext(catalogue, ctx); ctx.TOANAASI18n.setLocale(locale, { emit: false });
  const names = ['currentPortalPath', 'musicLibraryRoleForPath', 'isNativeMusicLibraryPath', 'mediaWorkspaceLine',
    'mediaWorkspaceListOffset', 'musicPromptComposerExactKeys', 'musicLibraryFilterPayload', 'musicLibraryListOffset',
    'musicLibraryListPath', 'musicLibraryReadLine', 'musicLibraryReadTimestamp', 'musicLibraryItemProjection',
    'musicLibraryBoundaryIsSafe', 'musicLibraryListingProjection', 'musicLibraryResponseProjection',
    'musicLibraryRequestIsCurrent', 'hydrateMusicLibrary', 'handleAction'];
  if (source.includes('function musicLibraryFeedbackText(')) names.push('musicLibraryFeedbackText');
  vm.runInContext(between('  const MUSIC_LIBRARY_ROLES', '  function musicLibraryRoleForPath') +
    between('  const MUSIC_LIBRARY_LIST_LIMIT', '  function musicLibraryFilterPayload') + names.map(fn).join('\n'), ctx);
  return { ctx, calls, toasts, get state() { return state; }, setState: patch => { state = { ...state, ...patch }; },
    action: (action, fields = {}, route = state.path) => ctx.handleAction({ detail: { action, fields, route } }) };
}

test('SFX bootstrap discards the Music listing instead of throwing before its first GET', async () => {
  const h = harness({ path: '/music/sfx-library', query: 'PRIVATE_MUSIC_QUERY', offset: 24 });
  await h.ctx.hydrateMusicLibrary();
  assert.deepEqual(h.calls, ['/media-workspace/library-items?role=sfx&limit=24&offset=0']);
  assert.equal(h.state.musicLibraryReadState, 'ready');
  assert.equal(h.state.musicLibraryItems.length, 0);
});
test('same-role refresh preserves the normalized search and current page', async () => {
  const h = harness({ query: '  calm   piano  ', offset: 24 });
  await h.ctx.hydrateMusicLibrary();
  assert.deepEqual(h.calls, ['/media-workspace/library-items?role=music&limit=24&offset=24&q=calm+piano']);
  assert.equal(h.state.musicLibraryReadState, 'ready');
});
test('API failure clears old cards while retaining the requested filter', async () => {
  const h = harness(); h.ctx.transport = async () => { throw new Error('transport failed'); };
  const result = await h.ctx.hydrateMusicLibrary({ q: 'calm', role: 'music' }, 0);
  assert.equal(result.failed, true); assert.equal(h.state.musicLibraryReadState, 'failed');
  assert.equal(h.state.musicLibraryItems.length, 0); assert.equal(h.state.musicLibraryFilter.q, 'calm');
});
test('role-mismatched responses fail closed without exposing old or foreign cards', async () => {
  const h = harness(); h.ctx.transport = async url => ({ ...response(url), data: { ...response(url).data, filters: { role: 'sfx', q: '' } } });
  const result = await h.ctx.hydrateMusicLibrary(); assert.equal(result.failed, true);
  assert.equal(h.state.musicLibraryItems.length, 0); assert.equal(h.state.musicLibraryReadState, 'failed');
});

const actions = ['music-library-refresh', 'music-library-page', 'music-library-filter', 'music-library-filter-clear'];
for (const locale of ['vi', 'en', 'zh']) {
  test(`all four library actions report transport failure instead of success (${locale})`, async () => {
    for (const action of actions) {
      const h = harness({ locale }); h.ctx.transport = async () => { throw new Error('API down'); };
      await h.action(action, { q: 'calm', __musicLibraryOffset: 24 });
      assert.equal(h.toasts.length, 1); assert.equal(h.toasts[0].type, 'error', action);
      assert.equal(h.state.musicLibraryReadState, 'failed'); assert.equal(h.state.musicLibraryItems.length, 0);
      if (locale === 'en') assert.doesNotMatch(h.toasts[0].message, /[À-ỹĐđ]/);
      if (locale === 'zh') assert.match(h.toasts[0].message, /[\u4e00-\u9fff]/);
    }
  });
  test(`successful library actions keep fixed feedback in the actual locale (${locale})`, async () => {
    for (const action of actions) {
      const h = harness({ locale, query: 'old', offset: 24 });
      await h.action(action, { q: '  calm  ', __musicLibraryOffset: 0 });
      assert.equal(h.state.musicLibraryReadState, 'ready'); assert.equal(h.toasts.length, 1);
      assert.equal(h.toasts[0].type, 'success');
      if (locale === 'vi') assert.doesNotMatch(h.toasts[0].message, /metadata|active|Web account|Audio Workspace/i);
      if (locale === 'en') assert.doesNotMatch(h.toasts[0].message, /[À-ỹĐđ]/);
      if (locale === 'zh') assert.match(h.toasts[0].message, /[\u4e00-\u9fff]/);
      if (action === 'music-library-filter-clear') assert.equal(h.state.musicLibraryFilter.q, '');
      if (action === 'music-library-page') assert.equal(h.state.musicLibraryListing.pagination.offset, 0);
    }
  });
}
test('every library action stays silent when its pending response belongs to a departed route', async () => {
  for (const action of actions) {
    const h = harness(); let resolve;
    h.ctx.transport = url => new Promise(done => { resolve = () => done(response(url)); });
    const pending = h.action(action, { q: 'calm', __musicLibraryOffset: 24 });
    assert.equal(h.state.musicLibraryReadState, 'loading'); assert.equal(h.state.musicLibraryItems.length, 0);
    h.setState({ path: '/music/sfx-library' }); resolve(); await pending;
    assert.deepEqual(h.toasts, []); assert.equal(h.state.musicLibraryItems.length, 0);
  }
});
test('a later search wins and the earlier response cannot overwrite it', async () => {
  const h = harness(); const pending = [];
  h.ctx.transport = url => new Promise(resolve => pending.push(() => resolve(response(url))));
  const first = h.ctx.hydrateMusicLibrary({ role: 'music', q: 'first' }, 0);
  const second = h.ctx.hydrateMusicLibrary({ role: 'music', q: 'second' }, 0);
  pending[1](); await second; pending[0](); const stale = await first;
  assert.equal(stale.stale, true); assert.equal(h.state.musicLibraryFilter.q, 'second');
});

for (const change of ['logout', 'session', 'capability']) {
  test(`pending library data is ignored after ${change}`, async () => {
    const h = harness(); let resolve;
    h.ctx.transport = url => new Promise(done => { resolve = () => done(response(url)); });
    const pending = h.action('music-library-refresh');
    assert.equal(h.state.musicLibraryItems.length, 0);
    if (change === 'logout') h.setState({ session: { authenticated: false } });
    if (change === 'session') h.ctx.mediaWorkspaceSessionEpoch += 1;
    if (change === 'capability') h.setState({ capabilities: { 'music-library-view': false } });
    resolve(); await pending;
    assert.equal(h.state.musicLibraryItems.length, 0); assert.deepEqual(h.toasts, []);
  });
}

for (const locale of ['vi', 'en', 'zh']) {
  test(`library action rejects missing capability before GET (${locale})`, async () => {
    const h = harness({ locale }); h.setState({ capabilities: { 'music-library-view': false } });
    await h.action('music-library-refresh');
    assert.deepEqual(h.calls, []); assert.equal(h.toasts[0].type, 'error');
    if (locale === 'en') assert.doesNotMatch(h.toasts[0].message, /[À-ỹĐđ]/);
    if (locale === 'zh') assert.match(h.toasts[0].message, /[\u4e00-\u9fff]/);
  });
}
