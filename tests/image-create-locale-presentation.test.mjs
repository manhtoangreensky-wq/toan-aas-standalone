import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function section(start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, `Production boundary: ${start}`);
  return source.slice(a, b);
}
function fn(name) {
  const a = source.indexOf(`  function ${name}(`), b = source.indexOf('\n  }', a) + 4;
  assert.ok(a >= 0 && b > a, `Production function: ${name}`);
  return source.slice(a, b);
}
const route = '/image/create';
const page = { path: route, access: 'member', type: 'feature', action: 'feature-draft', actionLabel: 'Tạo bản nháp', status: 'guarded', fields: [
  { name: 'prompt', label: 'Mô tả hình ảnh', control: 'textarea', placeholder: 'Chủ thể, phong cách, bối cảnh, tỷ lệ…', required: true, minLength: 1 },
  { name: 'tier', label: 'Tier ảnh', control: 'select', optionsFrom: 'imageTiers', emptyLabel: 'Để Bot trả lựa chọn tier canonical', help: 'Có thể để trống khi tạo draft/khám phá quote.' },
  { name: 'format', label: 'Ưu tiên tỷ lệ khi chạy', control: 'select', options: ['1:1', '4:5', '16:9', '9:16'], help: 'Lựa chọn là preference cho adapter image canonical tương lai.' }
] };
const visible = html => html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
const expected = { vi: { form: 'Mô tả hình ảnh', report: 'Báo cáo và kết quả' }, en: { form: 'Image description', report: 'Report and results' }, zh: { form: '图像描述', report: '报告与结果' } };
function model(locale) {
  const ctx = {
    manifest: { [route]: page }, FEATURE_PAGE_KEY_ALIASES: { [route]: 'image_create' }, WEB_LOCAL_ACTIONS: new Set(),
    transientWorkspaceDraftIds: new Map(), transientFormDrafts: new Map(),
    renderHero: () => '', renderSummary: () => '', renderStatusCard: () => '', renderNotes: () => '',
    renderInteractiveFeatureWorkbench: () => '', renderSubtitleStudioCompanionLink: () => '', renderFeatureBotHandoff: () => '',
    renderEmpty: (title, body) => `<h3>${title}</h3><p>${body}</p>`, classifyPageBoundary: () => 'runtime_generator'
  };
  vm.createContext(ctx); vm.runInContext(catalogue, ctx);
  ctx.uiText = (key, fallback, params) => ctx.TOANAASI18n.has(key) ? ctx.TOANAASI18n.t(key, params, locale) : fallback;
  vm.runInContext([
    fn('safeText'), fn('safeTelegramLink'), fn('normalizePath'), fn('validProjectId'), fn('validWorkspaceDraftId'),
    section('  const ALLOWED_STATES', '  const PAYMENT_STATUS_LABELS'),
    section('  const FEATURE_BOT_HANDOFFS', '  function copyFields('),
    fn('badge'), fn('canAct'), fn('telegramIdentityLinked'), fn('actionBlockReason'), fn('stateFor'), fn('voiceUiText'), fn('workspaceDraftIdForRoute'),
    section('  function renderFields(', '  function statusMessage('),
    section('  function flowHasFreshEstimate(', '  const ADMIN_TAB_GROUPS'),
    section('  const RESULT_LABELS', '  const SUBTITLE_STUDIO_COMPANION_INTENTS'), fn('renderWorkspace')
  ].join('\n'), ctx);
  const context = (overrides = {}) => ({
    path: route, interfaceLocale: locale, session: { authenticated: true, csrfReady: true },
    bridge: { available: true, csrfReady: true, featureExecutionFeatures: ['image_create'], featureExecutionAvailable: true },
    capabilities: { 'feature-draft': true, 'feature-estimate': true, 'feature-confirm': true },
    catalog: [{ key: 'image_create', route }], pricingCatalog: { image_tiers: [{ code: 'high', label: 'QA_TIER_LABEL' }] },
    workspaceDraftFeatures: [], pageStates: {}, ...overrides
  });
  return { ctx, context, render: (flow, overrides = {}) => ctx.renderWorkspace(page, { ...context(overrides), featureFlows: flow ? { [route]: flow } : {} }) };
}
const quote = (amount = 8) => ({ phase: 'estimate', status: 'awaiting_confirm', feature: 'image_create', estimateFingerprint: 'qa-image-fingerprint', webQuoteReceipt: 'Q'.repeat(48), input: { prompt: 'QA_PROMPT <script>', tier: 'high', format: '4:5' }, data: { estimate: { available: true, estimated_xu: amount, source: 'internal_catalog', source_price_usd: 'QA_PRIVATE_COST', cost_minor: 981234 } } });

for (const locale of ['vi', 'en', 'zh']) {
  const { ctx, render } = model(locale);
  test(`Image fixed form and empty report follow ${locale} while preserving real field contracts`, () => {
    const html = render(null), text = visible(html);
    assert.ok(text.includes(expected[locale].form), 'The description label follows the selected locale');
    assert.ok(text.includes(expected[locale].report), 'The report heading follows the selected locale');
    assert.match(html, /<form[^>]*data-portal-action="feature-draft"/);
    for (const name of ['prompt', 'tier', 'format']) assert.equal((html.match(new RegExp(`name="${name}"`, 'g')) || []).length, 1);
    for (const value of ['1:1', '4:5', '16:9', '9:16', 'high']) assert.ok(html.includes(`value="${value}"`));
    assert.match(html, /QA_TIER_LABEL/); assert.match(html, /name="prompt"[^>]*required[^>]*minlength="1"/);
    if (locale === 'en') assert.doesNotMatch(text, /[À-ỹ]/);
    if (locale === 'zh') assert.doesNotMatch(text, /Chuẩn bị|Tạo bản nháp|Ưu tiên tỷ lệ|Các trường/);
    if (locale === 'vi') assert.doesNotMatch(text, /canonical|Core Bridge|\bTier\b|\bestimate\b|\bdraft\b|\bprovider\b|\bOutput\b/);
  });
  test(`Image quote shows only the public sale amount and preserves unknown versus zero (${locale})`, () => {
    const html = render(quote()); assert.match(visible(html), /8 Xu/);
    assert.doesNotMatch(html, /QA_PRIVATE_COST|981234|source_price_usd|cost_minor|internal_catalog/);
    assert.match(visible(render(quote(0))), /0 Xu/);
    assert.doesNotMatch(visible(render(quote(null))), /0 Xu/);
    const costOnly = quote(null); costOnly.data.estimate.cost_xu = 67890;
    assert.doesNotMatch(visible(render(costOnly)), /67890/);
  });
  test(`Image sale quote is presented before its confirmation control (${locale})`, () => {
    const html = render(quote());
    assert.ok(html.indexOf('data-image-sale-price') < html.indexOf('data-portal-action="feature-confirm"'), 'Price must be reviewed before the paid confirmation action');
  });
  test(`Image estimate and confirmation labels are localized without weakening receipt and execution gates (${locale})`, () => {
    assert.match(render(quote()), /data-portal-action="feature-confirm"/);
    const html = render(quote());
    if (locale === 'en') assert.doesNotMatch(visible(html), /[À-ỹ]/);
    if (locale === 'vi') assert.doesNotMatch(visible(html), /canonical|Core Bridge|\bestimate\b|\bprovider\b/);
    for (const invalid of [{ ...quote(), webQuoteReceipt: '' }, { ...quote(), estimateFingerprint: '' }, { ...quote(), data: { estimate: { available: false } } }, { ...quote(), data: { estimate: { available: true, tier_required: true } } }]) assert.doesNotMatch(render(invalid), /data-portal-action="feature-confirm"/);
    assert.doesNotMatch(render(quote(), { capabilities: { 'feature-draft': true, 'feature-estimate': true, 'feature-confirm': false } }), /data-portal-action="feature-confirm"/);
  });
  test(`Image Web draft action remains owner-gated and localized (${locale})`, () => {
    const overrides = { bridge: { available: false }, workspaceDraftFeatures: ['image_create'], capabilities: { 'workspace-draft-save': true } };
    const html = render(null, overrides);
    assert.match(html, /<form[^>]*data-portal-action="workspace-draft-save"/);
    if (locale === 'en') assert.doesNotMatch(visible(html), /[À-ỹ]/);
    if (locale === 'vi') assert.doesNotMatch(visible(html), /canonical|\bbrief\b|\bjob\b|\bprovider\b/);
    assert.doesNotMatch(render(null, { ...overrides, capabilities: {} }), /data-portal-action="workspace-draft-save"/);
  });
  test(`Image suggestions keep their real prompt and copy/apply controls (${locale})`, () => {
    const html = render({ phase: 'draft', status: 'draft', feature: 'image_create', data: { draft: { available: true, content: { suggestions: [{ name: 'QA_SUGGESTION', prompt: 'QA_IMAGE_PROMPT <script>' }] } } } });
    assert.match(html, /QA_SUGGESTION/); assert.match(html, /QA_IMAGE_PROMPT &lt;script&gt;/);
    assert.match(html, /data-portal-action="copy-canonical-draft"/); assert.match(html, /data-portal-action="apply-canonical-draft"/);
    assert.match(html, /data-canonical-field="prompt"/); assert.doesNotMatch(html, /<img\b|<script\b/);
    if (locale === 'en') assert.doesNotMatch(visible(html), /[À-ỹ]/);
  });
  test(`Image confirmed-task report uses only the matching tracking identity (${locale})`, () => {
    const flow = { phase: 'confirm', status: 'completed', feature: 'image_create', message: 'QA_SERVER_MESSAGE <script>', data: { tracking: { id: 'QA-image-01', feature: 'image_create', status: 'completed' }, output_available: true, output_url: 'https://invalid.example/private.png' } };
    const html = render(flow); assert.match(html, /href="\/jobs\/QA-image-01"/); assert.match(html, /QA_SERVER_MESSAGE &lt;script&gt;/);
    assert.doesNotMatch(html, /<img\b|<script\b|invalid\.example/);
    assert.doesNotMatch(render({ ...flow, data: { tracking: { ...flow.data.tracking, feature: 'voice_tts' } } }), /href="\/jobs\/QA-image-01"/);
    if (locale === 'en') assert.doesNotMatch(visible(html), /[À-ỹ]/);
  });
  test(`Image task report comes first and its old form is an optional disclosure (${locale})`, () => {
    const flow = { phase: 'confirm', status: 'processing', feature: 'image_create', data: { tracking: { id: 'QA-image-01', feature: 'image_create', status: 'processing' } } };
    const html = render(flow);
    assert.ok(html.indexOf('data-image-flow-state') < html.indexOf('data-portal-form'));
    assert.match(html, /<details[^>]*data-image-task-form/);
    assert.match(html, /name="prompt"/);
  });
}
