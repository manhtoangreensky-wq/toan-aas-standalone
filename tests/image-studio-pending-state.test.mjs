import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');

function extractFn(name) {
  const a = source.indexOf(`function ${name}(`);
  assert.ok(a >= 0, `Production function ${name} must exist`);
  const next = source.slice(a + 12).search(/\n\s*function /);
  return next >= 0 ? source.slice(a, a + 12 + next) : source.slice(a);
}

const expectedLoading = {
  vi: { title: 'Đang tải không gian làm ảnh', body: 'Vui lòng chờ trong giây lát.' },
  en: { title: 'Loading your image workspace', body: 'Please wait a moment.' },
  zh: { title: '正在加载图像工作区', body: '请稍候。' }
};

function render(locale, readState = 'loading') {
  const ctx = {
    isImageHubRoute: () => false,
    renderHero: () => '<header class="portal-hero">HERO</header>',
    renderImageWorkspaceNavigation: () => '<nav data-image-workflow-nav>NAV_4_MODES</nav>',
    renderEmpty: (t, b) => `<div class="empty">${t}:${b}</div>`,
    imageStudioText: (k, fb) => fb,
    imageStudioLibraryText: (k, fb) => fb,
    imageStudioStateLabel: () => 'Active',
    validImageStudioArtboardId: () => false,
    imageStudioArtboardValues: () => ({}),
    transientFormValues: () => ({}),
    imageStudioArtboardFields: () => [],
    renderFields: () => '',
    badge: () => '',
    renderImageStudioBoundary: () => '',
    renderImageStudioArtboardLibrary: () => '',
    renderImageStudioReferenceLibrary: () => '',
    renderImageHubOverview: () => '',
    renderImageHubNextSteps: () => '',
    ICONS: { image: 'image' }
  };
  vm.createContext(ctx);
  vm.runInContext(catalogue, ctx);
  ctx.safeText = (str) => String(str || '');
  ctx.imageUiText = (key, fallback) => {
    const fullKey = `imageUi.${key}`;
    return ctx.TOANAASI18n.has(fullKey, locale) ? ctx.TOANAASI18n.t(fullKey, {}, locale) : fallback;
  };
  vm.runInContext(extractFn('renderImageStudio'), ctx);

  const page = { routePath: '/image-studio', path: '/image-studio' };
  const context = {
    capabilities: { 'image-studio-view': true, 'image-artboard-create': true },
    imageStudioEnabled: true,
    imageStudioReadState: readState,
    imageArtboards: [],
    imageStudioSummary: {}
  };
  return ctx.renderImageStudio(page, context);
}

for (const locale of ['vi', 'en', 'zh']) {
  test(`Image Studio exposes truthful loading state without forms or speculative metrics in ${locale}`, () => {
    const html = render(locale, 'loading');
    const exp = expectedLoading[locale];
    assert.match(html, /role="status"/);
    assert.match(html, /aria-live="polite"/);
    assert.match(html, /aria-busy="true"/);
    assert.ok(html.includes(exp.title), `Loading title mismatch in ${locale}: ${html}`);
    assert.ok(html.includes(exp.body), `Loading body mismatch in ${locale}: ${html}`);
    assert.match(html, /<nav data-image-workflow-nav>NAV_4_MODES<\/nav>/, 'Workspace navigation must remain present');
    assert.doesNotMatch(html, /data-portal-action="image-artboard-create"/, 'Creation action must be suppressed during loading');
    assert.doesNotMatch(html, /data-portal-form/, 'Form must not render during loading');
    assert.doesNotMatch(html, /portal-image-studio-metrics|portal-image-hub-overview/, 'Speculative metrics must not render');
  });
}
