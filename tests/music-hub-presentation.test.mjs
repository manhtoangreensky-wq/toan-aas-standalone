import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalog = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const theme = fs.readFileSync('static/portal/portal-theme.css', 'utf8');

function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  const end = source.indexOf('\n  }', start) + 4;
  assert.ok(start >= 0 && end > start, `missing production function ${name}`);
  return source.slice(start, end);
}

const page = {
  path: '/music',
  routePath: '/music',
  title: 'Music & SFX Hub · TOAN AAS',
  description: 'unlocalized server fallback'
};
const expectedRoutes = [
  '/music/create', '/music/song', '/music/sfx',
  '/audio/assets', '/music/library', '/music/sfx-library'
];
const plainText = (html) => html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
const containsAny = (text, values) => values.some((value) => text.includes(value));

for (const locale of ['vi', 'en', 'zh']) {
  const context = {
    ICONS: { music: 'music' },
    portalIcon: () => '<svg aria-hidden="true"></svg>'
  };
  vm.createContext(context);
  vm.runInContext(catalog, context);
  context.TOANAASI18n.setLocale(locale, { emit: false });
  context.uiText = (key, fallback, params) => context.TOANAASI18n.has(key)
    ? context.TOANAASI18n.t(key, params)
    : fallback;
  context.normalizePath = (path) => String(path || '').split('?')[0];
  context.displayPageTitle = (value) => String(value && value.title || '');
  vm.runInContext([
    fn('safeText'), fn('musicHubText'), fn('renderMusicHub'),
    fn('localizedPageTitle'), fn('localizedPageDescription')
  ].join('\n'), context);

  test(`Music hub renders clean ${locale} copy and preserves the page title`, () => {
    const html = context.renderMusicHub(page, {});
    const text = plainText(html);
    assert.match(html, new RegExp(`<h1 class="portal-title">${context.uiText('musicHub.page.title', '')}</h1>`));
    assert.equal(context.localizedPageTitle(page, {}), context.uiText('musicHub.page.title', ''));
    assert.equal(context.localizedPageDescription(page), context.uiText('musicHub.page.description', ''));
    assert.equal(html.match(/data-music-group="creation"/g)?.length, 1);
    assert.equal(html.match(/data-music-group="library"/g)?.length, 1);
    assert.ok(html.indexOf('data-music-group="creation"') < html.indexOf('data-music-group="library"'));
    assert.doesNotMatch(html, /portal-document-board-actions|Khởi tạo nhanh|Quick start|快速开始/);
    assert.match(html, /data-music-route-count="6"/);
    assert.doesNotMatch(text, /Stereo\s*320k|Royalty-Free|commercial rights|bản quyền thương mại|chuẩn phòng thu/i);
    assert.doesNotMatch(html, /<audio\b|<source\b|data-portal-action="feature-confirm"|provider_called|wallet_mutated/i);
    if (locale === 'en') {
      assert.doesNotMatch(text, /[À-ỹĐđ]/);
      assert.match(text, /AI music creation/i);
    }
    if (locale === 'vi') {
      assert.doesNotMatch(text, /\b(audio|workflow|private|adapter|royalty-free|stereo|sound effects|collection|metadata|studio)\b/i);
      assert.match(text, /Chưa khả dụng/);
    }
    if (locale === 'zh') {
      assert.doesNotMatch(text, /[À-ỹĐđ]/);
      assert.match(text, /暂不可用/);
    }
  });

  test(`Music hub exposes exactly six unique existing routes in ${locale}`, () => {
    const html = context.renderMusicHub(page, {});
    const hrefs = [...html.matchAll(/href="([^"]+)"/g)].map((match) => match[1]);
    assert.equal(new Set(hrefs).size, 6);
    assert.deepEqual([...hrefs].sort(), [...expectedRoutes].sort());
    assert.equal(html.match(/data-tool-state="guarded"/g)?.length, 3);
    assert.equal(html.match(/data-tool-state="ready"/g)?.length, 3);
    assert.match(html, /data-status="guarded"/);
    assert.equal(html.match(/data-music-primary/g)?.length, 1);
    assert.match(html, /href="\/music\/create"[^>]*data-music-primary/);
    assert.ok(containsAny(plainText(html), [
      context.uiText('musicHub.actions.details', ''),
      context.uiText('musicHub.actions.open', '')
    ]));
  });
}

test('Music text and status colors stay route-scoped and readable in both themes', () => {
  assert.match(theme, /\.portal-music-hub \.portal-module-grid\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/s);
  assert.match(theme, /\.portal-page\.portal-music-hub \.portal-eyebrow\s*\{[^}]*color:\s*var\(--portal-context\)/s);
  assert.match(theme, /html\[data-portal-theme="dark"\] \.portal-page\.portal-music-hub \.portal-eyebrow\s*\{[^}]*color:\s*var\(--portal-teal-dark-border-strong\)/s);
  assert.match(theme, /\.portal-music-hub \.portal-badge\[data-status="guarded"\]\s*\{[^}]*color:\s*var\(--portal-ink\)/s);
  assert.match(theme, /\.portal-music-hub \.portal-notice--info p\s*\{[^}]*color:\s*var\(--portal-muted\)/s);
  assert.match(theme, /\.portal-music-hub \.portal-notice--info strong\s*\{[^}]*color:\s*var\(--portal-ink\)/s);
  assert.match(theme, /html\[data-portal-theme="dark"\] \.portal-music-hub \.portal-notice--info p\s*\{[^}]*color:\s*var\(--portal-teal-dark-ink\)/s);
  assert.match(theme, /html\[data-portal-theme="dark"\]\s+\.portal-music-hub \.portal-module-card p,\s*html\[data-portal-theme="dark"\]\s+\.portal-music-hub \.portal-notice--info p\s*\{[^}]*color:\s*var\(--portal-teal-dark-ink\)/s);
});
