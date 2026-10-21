import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  return start < 0 ? '' : source.slice(start, source.indexOf('\n  }', start) + 4);
}
function harness(route = '/image/create') {
  const aliases = { '/image/new': '/image/create', '/image/image-to-image': '/image/transform' };
  const drafts = new Map();
  const field = (name, value, type = 'textarea') => ({ name, value, type, disabled: false, tagName: 'TEXTAREA' });
  const fields = [field('prompt', 'private <text> & literal'), field('tier', 'high'), field('format', '4:5'), field('token', 'never-copy'), field('source', 'path', 'file')];
  const form = { getAttribute: key => key === 'data-portal-route' ? aliases[route] || route : '', querySelectorAll: () => fields };
  const history = [], events = [], replacements = [];
  const browserWindow = { location: { pathname: route, origin: 'https://qa.invalid', href: 'https://qa.invalid' + route + '?lang=vi&theme=dark', replace(url) { replacements.push(url); } },
    history: { state: {}, pushState(_s, _t, url) { history.push(url); browserWindow.location.href = new URL(url, browserWindow.location.origin).href; browserWindow.location.pathname = new URL(browserWindow.location.href).pathname; } },
    __TOAN_AAS_PORTAL__: { path: route, session: { authenticated: true, csrfToken: 'qa-identity-A' }, featureFlows: {} },
    PopStateEvent: class { constructor(type) { this.type = type; } },
    dispatchEvent(event) { if(ctx.prepareImageWorkspaceHistoryNavigation)ctx.prepareImageWorkspaceHistoryNavigation(); events.push({ type: event.type, beforePath: this.__TOAN_AAS_PORTAL__.path }); if(this.adopt!==false)this.__TOAN_AAS_PORTAL__ = { ...this.__TOAN_AAS_PORTAL__, path: new URL(this.location.href).pathname }; return true; }
  };
  const ctx = { window: browserWindow, URL, PopStateEvent: browserWindow.PopStateEvent, transientFormDrafts: drafts,
    clearTransientFormDraft: key => drafts.delete(key), normalizePath: value => String(value || '').replace(/\/$/, ''),
    resolvePage: path => ({ path: aliases[path] || path }), getBootstrap: () => browserWindow.__TOAN_AAS_PORTAL__,
    validVaultAssetId: value => /^[0-9a-f-]{36}$/.test(value), validProjectId: value => /^[0-9a-f-]{36}$/.test(value),
    document: { querySelector: selector => selector.includes('data-portal-form') ? form : { focus() {} } } };
  vm.createContext(ctx); vm.runInContext(catalogue, ctx); ctx.uiText = (key, fallback) => ctx.window.TOANAASI18n.has(key) ? ctx.window.TOANAASI18n.t(key, {}, 'vi') : fallback;
  const start = source.indexOf('  const IMAGE_WORKSPACE_ROUTES');
  const constants = start < 0 ? '' : source.slice(start, source.indexOf('\n  function ', start));
  vm.runInContext([constants, fn('safeText'), fn('imageUiText'), fn('canonicalImageWorkspaceRoute'), fn('synchronizeImageWorkspaceDraftSession'), fn('captureImageWorkspaceDraft'), fn('prepareImageWorkspaceHistoryNavigation'), fn('navigateImageWorkspace'), fn('renderImageWorkspaceNavigation')].join('\n'), ctx);
  if (ctx.synchronizeImageWorkspaceDraftSession) ctx.synchronizeImageWorkspaceDraftSession(browserWindow.__TOAN_AAS_PORTAL__);
  const link = href => ({ getAttribute: key => key === 'href' ? href : '', hasAttribute: () => false });
  const event = values => ({ defaultPrevented: false, button: 0, preventDefault() { this.defaultPrevented = true; }, ...values });
  return { ctx, drafts, fields, history, events, replacements, browserWindow, link, event };
}

test('Image mode switch captures the main scalar draft and lets existing history hydration adopt the route', () => {
  const h = harness(); assert.equal(typeof h.ctx.navigateImageWorkspace, 'function');
  const e = h.event(); assert.equal(h.ctx.navigateImageWorkspace(e, h.link('/image/transform')), true);
  assert.equal(e.defaultPrevented, true);
  assert.deepEqual(JSON.parse(JSON.stringify(h.drafts.get('/image/create'))), { prompt: 'private <text> & literal', tier: 'high', format: '4:5' });
  assert.equal(h.history.length, 1); assert.equal(new URL(h.history[0], 'https://qa.invalid').pathname, '/image/transform');
  assert.equal(new URL(h.history[0], 'https://qa.invalid').search, '?lang=vi&theme=dark');
  assert.deepEqual(h.events, [{ type: 'popstate', beforePath: '/image/create' }]);
});

test('Image finite navigation preserves modified clicks and refuses unknown paths, queries and unsigned sessions', () => {
  const h = harness(); assert.equal(typeof h.ctx.navigateImageWorkspace, 'function');
  for (const overrides of [{ ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }, { defaultPrevented: true }]) assert.equal(h.ctx.navigateImageWorkspace(h.event(overrides), h.link('/image/edit')), false);
  for (const href of ['https://bad.invalid/image/edit', '//bad.invalid/image/edit', '/admin', '/image-studio/foreign', '/image/edit?token=x', '/image/edit#x']) assert.equal(h.ctx.navigateImageWorkspace(h.event(), h.link(href)), false);
  h.browserWindow.__TOAN_AAS_PORTAL__.session.authenticated = false;
  assert.equal(h.ctx.navigateImageWorkspace(h.event(), h.link('/image/edit')), false); assert.equal(h.history.length, 0);
});

test('Image aliases use canonical draft keys, same mode does not duplicate history, identity cleanup is scoped', () => {
  const h = harness('/image/new'); assert.equal(typeof h.ctx.navigateImageWorkspace, 'function');
  assert.equal(h.ctx.navigateImageWorkspace(h.event(), h.link('/image/create')), true); assert.equal(h.history.length, 0);
  h.ctx.captureImageWorkspaceDraft('/image/create'); h.drafts.set('/music/create', { prompt: 'protected' });
  h.ctx.synchronizeImageWorkspaceDraftSession({ session: { authenticated: true, csrfToken: 'qa-identity-A' } }); assert.ok(h.drafts.has('/image/create'));
  h.ctx.synchronizeImageWorkspaceDraftSession({ session: { authenticated: true, csrfToken: 'qa-identity-B' } }); assert.equal(h.drafts.has('/image/create'), false); assert.ok(h.drafts.has('/music/create'));
});

test('common Image navigation localizes four destinations and exposes only its current page', () => {
  const h = harness(); assert.equal(typeof h.ctx.renderImageWorkspaceNavigation, 'function');
  for (const route of ['/image/create', '/image-studio', '/image/transform', '/image/edit']) {
    const html = h.ctx.renderImageWorkspaceNavigation({ path: route });
    assert.equal((html.match(/data-image-mode=/g) || []).length, 4);
    const selected = html.match(/<a[^>]*aria-current="page"[^>]*>/g) || [];
    assert.equal(selected.length, 1); assert.ok(selected[0].includes(`href="${route}"`));
  }
});

test('Image capture keeps only each main form contract and drops unverified asset and project references', () => {
  for (const [route, names] of [
    ['/image-studio', ['creative_brief', 'style_direction', 'negative_direction']],
    ['/image/transform', ['transform_instruction', 'aspect_ratio']],
    ['/image/edit', ['preset', 'brightness', 'basic_upscale']]
  ]) {
    const h = harness(route); h.fields.splice(0, h.fields.length, ...names.map(name => ({ name, value: name === 'brightness' ? '0.5' : 'kept text', type: 'text', tagName: 'INPUT' })),
      { name: 'source_asset_id', value: '00000000-0000-0000-0000-000000000001', type: 'select-one', tagName: 'SELECT', options: [{ value: '' }] },
      { name: 'project_id', value: 'foreign', type: 'text', tagName: 'INPUT' }, { name: 'webQuoteReceipt', value: 'never copy', type: 'hidden' });
    assert.equal(h.ctx.captureImageWorkspaceDraft(route), true);
    const draft = JSON.parse(JSON.stringify(h.drafts.get(route)));
    for (const name of names) assert.equal(draft[name], name === 'brightness' ? '0.5' : 'kept text');
    assert.equal(draft.source_asset_id, undefined); assert.equal(draft.project_id, undefined); assert.equal(draft.webQuoteReceipt, undefined);
  }
});

test('Image navigation invalidates only pending estimates and never discards confirmed job reports', () => {
  const h = harness();
  const job = { phase: 'confirm', feature: 'image_create', status: 'queued', job: { id: 'qa-job' } };
  h.browserWindow.__TOAN_AAS_PORTAL__.featureFlows = { '/image/create': { phase: 'estimate', webQuoteReceipt: 'old' }, '/image/new': { phase: 'estimate' }, '/music/create': job };
  h.ctx.navigateImageWorkspace(h.event(), h.link('/image/edit'));
  assert.equal(h.browserWindow.__TOAN_AAS_PORTAL__.featureFlows['/image/create'], undefined);
  assert.equal(h.browserWindow.__TOAN_AAS_PORTAL__.featureFlows['/image/new'], undefined);
  assert.equal(h.browserWindow.__TOAN_AAS_PORTAL__.featureFlows['/music/create'], job);
  const preserved = harness(); preserved.browserWindow.__TOAN_AAS_PORTAL__.featureFlows = { '/image/create': job };
  preserved.ctx.navigateImageWorkspace(preserved.event(), preserved.link('/image/edit'));
  assert.equal(preserved.browserWindow.__TOAN_AAS_PORTAL__.featureFlows['/image/create'], job);
});

test('Image navigation falls back to a document load when the history integration does not adopt the target', () => {
  const h=harness();h.browserWindow.adopt=false;
  assert.equal(h.ctx.navigateImageWorkspace(h.event(),h.link('/image/edit')),true);
  assert.deepEqual(h.replacements,['/image/edit?lang=vi&theme=dark']);
});

test('Image history preparation clears old destination projections before the first integration mount', () => {
  const h=harness();assert.equal(typeof h.ctx.prepareImageWorkspaceHistoryNavigation,'function');
  h.browserWindow.__TOAN_AAS_PORTAL__.imageArtboards=[{title:'OLD_PRIVATE_RECORD'}];h.browserWindow.__TOAN_AAS_PORTAL__.imageStudioReadState='ready';
  h.browserWindow.location.pathname='/image-studio';h.ctx.prepareImageWorkspaceHistoryNavigation();
  assert.deepEqual(Array.from(h.browserWindow.__TOAN_AAS_PORTAL__.imageArtboards),[]);assert.equal(h.browserWindow.__TOAN_AAS_PORTAL__.imageStudioReadState,'loading');
  h.browserWindow.__TOAN_AAS_PORTAL__.path='/image-studio';h.browserWindow.__TOAN_AAS_PORTAL__.imageOperationAssetReferences={items:[{id:'OLD'}],pinned:[{id:'PINNED'}]};
  h.browserWindow.location.pathname='/image/transform';h.ctx.prepareImageWorkspaceHistoryNavigation();
  assert.deepEqual(Array.from(h.browserWindow.__TOAN_AAS_PORTAL__.imageOperationAssetReferences.items),[]);assert.deepEqual(Array.from(h.browserWindow.__TOAN_AAS_PORTAL__.imageOperationAssetReferences.pinned),[]);
});
