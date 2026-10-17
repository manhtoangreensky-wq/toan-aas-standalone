import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');

function functionSource(name) {
  const start = source.indexOf(`  function ${name}(`);
  const end = source.indexOf('\n  }', start) + 4;
  assert.ok(start >= 0 && end > start, `Missing function ${name}`);
  return source.slice(start, end);
}

function functionSourceOr(name, fallback) {
  return source.includes(`  function ${name}(`) ? functionSource(name) : fallback;
}

const textOf = html => {
  const visible = html.replace(/<[^>]*>/g, ' ');
  const accessible = [...html.matchAll(/\b(?:placeholder|aria-label|title)="([^"]*)"/g)]
    .map(match => match[1]).join(' ');
  return `${visible} ${accessible}`.replace(/\s+/g, ' ').trim();
};

function createHarness(locale) {
  const ctx = {
    window: null,
    ICONS: { legal: '', security: '' },
    SUPPORT_TICKET_HERO_DETAIL_PATH: { test: () => false },
    ADMIN_DATA_VIEW_ROUTE_KEYS: {},
    ADMIN_ERP_ROUTE_I18N: {},
    CUSTOMER_APPLICATION_ROUTE: /^\/[a-z0-9][a-z0-9._~/-]*$/i,
    portalIcon: () => '',
    normalizePath: value => String(value || '/').split('?')[0].replace(/\/$/, '') || '/',
    displayPageTitle: page => String(page.title || ''),
    localizedNavigationLabel: value => String(value || ''),
    featureFamilyForPath: () => '',
    featureCatalogGroupCopy: () => '',
    adminDataViewRouteKey: () => '',
    safeCatalogRoute: page => String(page || ''),
    isNavCurrent: () => false,
    imageVaultItems: context => Array.isArray(context.imageAssets) ? context.imageAssets : [],
    transientFormValues: () => ({}),
    vaultBytes: () => '1 KB',
    badge: () => '',
    renderHero: page => `<header><span>${ctx.supportTicketHeroSection(page)}</span><h1>${ctx.localizedPageTitle(page, {})}</h1><p>${ctx.localizedPageDescription(page)}</p></header>`
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(catalogue, ctx);
  ctx.TOANAASI18n.setLocale(locale);
  vm.runInContext([
    functionSource('portalI18n'),
    functionSource('uiText'),
    functionSourceOr('mediaOperationText', 'function mediaOperationText(key, fallback) { return fallback; }'),
    functionSourceOr('mediaOperationStatusBadge', 'function mediaOperationStatusBadge(status, scope, options) { return ""; }'),
    functionSourceOr('mediaOperationStatusReason', 'function mediaOperationStatusReason(reason, scope) { return String(reason || ""); }'),
    functionSourceOr('renderMediaOperationNotes', 'function renderMediaOperationNotes(page) { return renderNotes(page); }'),
    functionSource('safeText'),
    functionSource('renderNotes'),
    functionSource('localizedPageTitle'),
    functionSource('localizedPageDescription'),
    functionSource('supportTicketHeroRouteKey'),
    functionSource('supportTicketHeroSection'),
    functionSource('currentCustomerWorkflowGroup'),
    functionSource('renderImageUpscale'),
    functionSource('renderImageTransform'),
    functionSource('renderMusicSfx')
  ].join('\n'), ctx);
  return ctx;
}

const routes = [
  {
    path: '/image/upscale', renderer: 'renderImageUpscale',
    page: { path: '/image/upscale', routePath: '/image/upscale', title: 'Nâng cấp ảnh (Upscale)', description: 'Nâng độ phân giải ảnh 2x hoặc 4x.', section: 'AI Studio', access: 'member', notes: [] },
    required: ['data-portal-action="image-upscale-submit"', 'name="image_asset_id"', 'name="scale_factor"'],
    visible: { vi: 'Nâng độ phân giải ảnh', en: 'Upscale image', zh: '提升图像分辨率' }
  },
  {
    path: '/image/transform', renderer: 'renderImageTransform',
    page: { path: '/image/transform', routePath: '/image/transform', title: 'Biến đổi ảnh (Image Transform)', description: 'Tạo biến thể từ ảnh nguồn.', section: 'AI Studio', access: 'member', notes: [] },
    required: ['data-portal-action="image-transform-submit"', 'name="image_asset_id"', 'name="transform_instruction"', 'name="aspect_ratio"'],
    visible: { vi: 'Biến đổi ảnh', en: 'Transform image', zh: '转换图像' }
  },
  {
    path: '/music/sfx', renderer: 'renderMusicSfx',
    page: { path: '/music/sfx', routePath: '/music/sfx', title: 'Hiệu ứng âm thanh (Music SFX)', description: 'Tạo hiệu ứng âm thanh từ mô tả.', section: 'AI Studio', access: 'member', notes: [] },
    required: ['data-portal-action="music-sfx-submit"', 'name="brief"'],
    visible: { vi: 'Hiệu ứng âm thanh', en: 'Sound effects', zh: '音效' }
  }
];

function assertLocalePurity(locale, text) {
  if (locale === 'vi') {
    assert.doesNotMatch(text, /\b(?:Web-native|Browser|Job Bridge|Status Reason|Provider|Upscale|Transform|Scale|Aspect Ratio|Prompt|Brief|SPEC|SQLite|durable|canonical|queued|fail-closed|active|Generative AI)\b/i,
      'Vietnamese fixed product copy contains unexplained English jargon');
  } else if (locale === 'en') {
    assert.doesNotMatch(text, /[ăâđêôơưáàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ]|\b(?:chọn|ảnh|tác vụ|đang|không|của|hệ số|trạng thái|lịch sử|quy trình|để|và|được|chỉ|sẵn|chờ|mới|hỗ trợ|mô tả)\b/i,
      'English fixed product copy contains Vietnamese');
  } else {
    const withoutProperNouns = text
      .replace(/Asset Vault/g, '')
      .replace(/\b(?:PNG|JPG|JPEG|WebP|AI|Xu|Story|Reels|Shorts)\b/g, '');
    assert.doesNotMatch(withoutProperNouns, /[A-Za-z]{3,}/,
      'Chinese fixed product copy contains unexplained English');
  }
}

for (const locale of ['vi', 'en', 'zh']) {
  for (const route of routes) {
    test(`${route.path} keeps its form contract and clean ${locale} copy`, () => {
      const ctx = createHarness(locale);
      const html = ctx[route.renderer](route.page, { imageAssets: [] });
      const visible = textOf(html);
      assert.ok(visible.includes(route.visible[locale]), 'The route title and main action must use the selected language');
      for (const contract of route.required) assert.ok(html.includes(contract), `Preserve ${contract}`);
      const navGroup = ctx.currentCustomerWorkflowGroup(route.page, []);
      assert.equal(navGroup?.links?.[0]?.[1], route.visible[locale], 'The current-workflow navigation label follows the selected language');
      assertLocalePurity(locale, visible);
    });
  }

  test(`job receipt states on all three media screens use ${locale} copy, not internal reason codes`, () => {
    const ctx = createHarness(locale);
    for (const route of routes) {
      const job = {
        id: '12345', status: 'queued',
        status_reason: 'AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE',
        brief: 'quiet ocean at dusk',
        transform_instruction: 'add blue flowers'
      };
      const context = route.path === '/music/sfx'
        ? { musicSfxLastJob: job }
        : { featureFlows: { [route.path]: { job } }, imageAssets: [] };
      const html = ctx[route.renderer](route.page, context);
      const visible = textOf(html);
      if (route.path === '/music/sfx') assert.ok(visible.includes(job.brief), 'Keep customer-authored audio descriptions unchanged');
      if (route.path === '/image/transform') assert.ok(visible.includes(job.transform_instruction), 'Keep customer-authored image instructions unchanged');
      const fixedCopyOnly = visible.replace(job.brief, '').replace(job.transform_instruction, '');
      assertLocalePurity(locale, fixedCopyOnly);
      assert.equal(html.includes('AWAITING_OWNER_AUTHORIZED_VISIBLE_LIVE_ACCEPTANCE'), false,
        'An internal status reason must not be exposed as customer-facing copy');
    }
  });
}
