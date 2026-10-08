import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`  function ${name}(`), end = source.indexOf('\n  }', start) + 4;
  assert.ok(start >= 0 && end > start, name); return source.slice(start, end);
}
const expectedRoutes = ['/image/create', '/image-studio', '/image/edit', '/image/background-cleanup', '/image/resize', '/image/brand-overlay', '/image/storyboard-grid', '/image/prompt-composer'];
const textOf = html => html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
for (const locale of ['vi', 'en', 'zh']) {
  const ctx = { ICONS: { image: 'IMAGE_ICON', prompt: 'PROMPT_ICON' }, badge: () => '', renderNotes: () => '', portalIcon: value => value, FEATURE_PAGE_KEY_ALIASES: { '/image/create': 'image_create' }, resolvePage: path => ({ path }) };
  vm.createContext(ctx); vm.runInContext(catalogue, ctx);
  ctx.uiText = (key, fallback, params) => ctx.TOANAASI18n.has(key) ? ctx.TOANAASI18n.t(key, params, locale) : fallback;
  // The full shell/title resolver is covered by actual-template browser QA;
  // this unit isolates the real hub's content and destination projection.
  ctx.renderHero = page => `<h1>${page.title}</h1><p>${page.description}</p>`;
  vm.runInContext([fn('safeText'), fn('normalizePath'), fn('featureKeyForPage'), fn('featureConfirmExecutionReady'), fn('renderMediaHubPage'), fn('renderImageSuiteHub')].join('\n'), ctx);
  const render = () => ctx.renderImageSuiteHub({ path: '/tools/image', title: 'Image Operations Hub', description: 'Bộ công cụ toàn diện xử lý và sáng tạo ảnh AI' }, { interfaceLocale: locale, capabilities: {}, bridge: { available: false } });
  test(`Image hub keeps exactly eight unique existing destinations and puts creation first (${locale})`, () => {
    const html = render(), routes = [...html.matchAll(/href="([^"]+)"/g)].map(match => match[1]);
    assert.equal(routes.length, 8, 'No duplicated product navigation');
    assert.equal(new Set(routes).size, 8);
    assert.deepEqual([...routes].sort(), [...expectedRoutes].sort());
    assert.equal(routes[0], '/image/create');
  });
  test(`Image hub fixed title and descriptions follow ${locale}`, () => {
    const text = textOf(render());
    assert.ok(text.includes({ vi: 'Công cụ ảnh', en: 'Image tools', zh: '图像工具' }[locale]));
    if (locale === 'en') assert.equal(/[À-ỹ]/.test(text), false, 'Vietnamese fixed copy is mixed into English');
    if (locale === 'zh') assert.equal(/Công cụ|Tạo ảnh|Chỉnh|Chọn workflow|Điều hướng/.test(text), false, 'Vietnamese fixed copy is mixed into Chinese');
    if (locale === 'vi') assert.equal(/Lossless|\bResize\b|\bCrop\b|\bBrand Overlay\b|\bWorkspace\b|\bWorkflow\b|\bdeterministic\b|\bartboard\b/.test(text), false, 'Implementation jargon or generic English remains');
  });
  test(`Image hub without capabilities advertises navigation rather than fictional output quality (${locale})`, () => {
    const html = render(), text = textOf(html);
    assert.equal(/Lossless|Độ sắc nét tối đa|đã sẵn sàng hoạt động|Tách nền thông minh|4K/i.test(text), false, 'Unsupported quality or execution availability is advertised');
    assert.equal(/data-tool-state="ready"/.test(html), false, 'Route existence alone claims processing readiness');
    assert.equal(/<img\b|onclick=|feature-confirm/.test(html), false);
  });
}
