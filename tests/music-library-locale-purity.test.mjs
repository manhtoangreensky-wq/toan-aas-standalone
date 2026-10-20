import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');

function functionSource(name) {
  const start = source.indexOf(`  function ${name}(`);
  const end = source.indexOf('\n  }', start) + 4;
  assert.ok(start >= 0 && end > start, `Missing production function ${name}`);
  return source.slice(start, end);
}

const textOf = html => html
  .replace(/<[^>]*>/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

function createHarness(locale) {
  const ctx = {
    window: null,
    ICONS: { music: 'music' },
    portalIcon: () => '',
    displayPageTitle: page => String(page && page.title || ''),
    normalizePath: value => String(value || '/').split('?')[0].replace(/\/$/, '') || '/',
    validMediaCollectionId: value => /^[0-9a-f-]{8,64}$/i.test(String(value || '')),
    memoryListingPagination: sourceListing => sourceListing && typeof sourceListing === 'object' ? sourceListing : {},
    mediaCollectionTags: value => Array.isArray(value) ? value.map(String).slice(0, 16) : [],
    renderFields: fields => fields.map(field => `<label>${field.label}<input placeholder="${field.placeholder || ''}"></label>`).join(''),
    renderEmpty: (title, body) => `<section data-empty><h2>${title}</h2><p>${body}</p></section>`,
    badge: state => `<span data-badge="${state}">${state}</span>`
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(catalogue, ctx);
  ctx.TOANAASI18n.setLocale(locale, { emit: false });
  vm.runInContext([
    functionSource('portalI18n'),
    functionSource('uiText'),
    functionSource('safeText'),
    functionSource('musicLibraryText'),
    functionSource('musicLibraryRoleForPage'),
    functionSource('musicLibraryFilterState'),
    functionSource('musicLibraryListing'),
    functionSource('musicLibraryItems'),
    functionSource('musicLibraryDurationLabel'),
    functionSource('renderMusicLibraryCards'),
    functionSource('renderMemoryPagination'),
    functionSource('localizedPageTitle'),
    functionSource('localizedPageDescription'),
    functionSource('renderMusicLibrary')
  ].join('\n'), ctx);
  ctx.renderHero = (page, context) => `<header><h1>${ctx.localizedPageTitle(page, context)}</h1><p>${ctx.localizedPageDescription(page)}</p></header>`;
  return ctx;
}

const pageFor = path => ({
  path,
  routePath: path,
  title: path === '/music/sfx-library' ? 'Thư viện SFX' : 'Thư viện nhạc',
  description: 'fallback',
  musicLibraryRole: path === '/music/sfx-library' ? 'sfx' : 'music'
});

const fixedText = html => textOf(html
  .replace(/<h3>Bản nhạc collection<\/h3>/g, '')
  .replace(/<strong>Bản nhạc collection<\/strong>/g, '')
  .replace(/<span>private<\/span>/g, '')
  .replace(/<span>active<\/span>/g, '')
  .replace(/<dd>2026-10-14T10:00:00Z<\/dd>/g, ''));

function assertLocalePurity(locale, text) {
  if (locale === 'vi') {
    assert.doesNotMatch(text, /\b(?:collection|metadata|read\s+only|private|player|catalog|active|reference|signed|generic|audio|tags?|Music)\b/i);
  } else if (locale === 'en') {
    assert.doesNotMatch(text, /[À-ỹĐđ]|\b(?:thư viện|nhạc|hiệu ứng|đang|chưa|riêng tư|chỉ đọc|mở|tìm|cập nhật|thời lượng)\b/i);
  } else {
    const withoutAllowed = text.replace(/\b(?:SFX|Bot|TOAN AAS|Telegram)\b/g, '');
    assert.doesNotMatch(withoutAllowed, /[A-Za-z]{3,}/);
  }
}

for (const locale of ['vi', 'en', 'zh']) {
  for (const path of ['/music/library', '/music/sfx-library']) {
    test(`${path} renders fixed copy in clean ${locale}`, () => {
      const ctx = createHarness(locale);
      const context = {
        path,
        capabilities: { 'music-library-view': true },
        musicLibraryReadState: 'ready',
        musicLibraryFilter: { q: '' },
        musicLibraryListing: { pagination: {} },
        musicLibraryItems: [{
          collection_id: '12345678-abcd',
          role: path === '/music/sfx-library' ? 'sfx' : 'music',
          reference_title: 'Bản nhạc collection',
          collection_title: 'Bản nhạc collection',
          tags: ['private', 'active'],
          favorite: true,
          user_declared_duration_seconds: 125,
          updated_at: '2026-10-14T10:00:00Z'
        }]
      };
      const html = ctx.renderMusicLibrary(pageFor(path), context);
      const text = fixedText(html);
      assertLocalePurity(locale, text);
      assert.match(html, /data-portal-action="music-library-filter"/);
      assert.match(html, /data-portal-action="music-library-refresh"/);
      assert.match(html, /href="\/media-workspace\/12345678-abcd"/);
      assert.match(html, /Bản nhạc collection/);
      assert.equal(ctx.localizedPageTitle(pageFor(path), {}),
        locale === 'vi' ? (path === '/music/sfx-library' ? 'Thư viện hiệu ứng âm thanh' : 'Thư viện nhạc')
          : locale === 'en' ? (path === '/music/sfx-library' ? 'Sound-effects library' : 'Music library')
            : (path === '/music/sfx-library' ? '音效库' : '音乐库'));
    });
  }

  test(`Music Library guarded and empty states stay localized in ${locale}`, () => {
    const ctx = createHarness(locale);
    for (const readState of ['loading', 'failed', 'guarded']) {
      const path = '/music/library';
      const html = ctx.renderMusicLibrary(pageFor(path), {
        path,
        capabilities: { 'music-library-view': true },
        musicLibraryReadState: readState,
        musicLibraryItems: []
      });
      assertLocalePurity(locale, textOf(html));
    }
    const cards = ctx.renderMusicLibraryCards([], 'music', '/music/library');
    assertLocalePurity(locale, textOf(cards));
  });

  test(`a search with no matches is not presented as an empty library (${locale})`, () => {
    const ctx = createHarness(locale);
    const html = ctx.renderMusicLibrary(pageFor('/music/library'), {
      path: '/music/library', capabilities: { 'music-library-view': true },
      musicLibraryReadState: 'ready', musicLibraryItems: [],
      musicLibraryListing: { filters: { q: 'User & Query' }, pagination: {} }
    });
    const want = { vi: 'Không tìm thấy kết quả', en: 'No matches found', zh: '未找到匹配结果' }[locale];
    assert.match(html, new RegExp(want));
    assert.match(html, /User &amp; Query/);
    assertLocalePurity(locale, textOf(html).replace(/User &amp; Query/g, ''));
  });

  test(`loading announces busy state and cannot be refreshed twice (${locale})`, () => {
    const ctx = createHarness(locale);
    const html = ctx.renderMusicLibrary(pageFor('/music/sfx-library'), {
      path: '/music/sfx-library', capabilities: { 'music-library-view': true },
      musicLibraryReadState: 'loading', musicLibraryItems: [{ reference_title: 'STALE_PRIVATE_ITEM' }]
    });
    assert.match(html, /aria-busy="true"/);
    assert.match(html, /data-state="processing"/);
    assert.match(html, /data-portal-action="music-library-refresh"[^>]* disabled/);
    assert.doesNotMatch(html, /STALE_PRIVATE_ITEM/);
  });

  test(`real library pagination retains offsets and localizes both directions (${locale})`, () => {
    const ctx = createHarness(locale);
    const html = ctx.renderMemoryPagination({ pagination: {
      offset: 24, returned: 24, previous_offset: 0, has_more: true, next_offset: 48
    } }, locale === 'vi' ? 'nhạc' : locale === 'en' ? 'music' : '音乐', 'music-library-page', '/music/library', 'data-music-library-offset', 'portal-music-library-pagination');
    assertLocalePurity(locale, textOf(html));
    assert.match(html, /data-music-library-offset="0"/);
    assert.match(html, /data-music-library-offset="48"/);
    assert.match(html, /25[–-]48/);
    const before = { vi: 'Trang trước', en: 'Previous page', zh: '上一页' }[locale];
    assert.match(html, new RegExp(before));
  });
}
