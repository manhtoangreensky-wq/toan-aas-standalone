import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');

function fn(text, name) {
  const a = text.indexOf(`  function ${name}(`);
  assert.ok(a >= 0, `function ${name} not found`);
  return text.slice(a, text.indexOf('\n  }', a) + 4);
}

const statuses = ['draft', 'ready', 'guarded', 'awaiting_confirm', 'queued', 'processing', 'completed', 'failed', 'failed_no_charge', 'error', 'cancelled', 'refunded'];
const routes = ['/music/create', '/music/song'];
const locales = ['vi', 'en', 'zh'];

function runtime(locale = 'vi', text = source) {
  const ctx = {
    MUSIC_PRODUCT_ROUTES: ['/music/create', '/music/song'],
    ALLOWED_STATES: new Set(statuses),
    FEATURE_TRACKING_JOB_STATES: new Set(statuses.slice(4)),
    FEATURE_TRACKING_ID_PATTERN: /^[A-Za-z0-9._:-]{1,160}$/,
    FEATURE_TRACKING_KEY_PATTERN: /^[a-z][a-z0-9_]{1,120}$/,
    STATE_LABELS: Object.fromEntries(statuses.map(s => [s, s])),
    STATE_I18N_KEYS: Object.fromEntries(statuses.map(s => [s, `state.${s}`])),
    RESULT_LABELS: { prompt: 'Prompt' },
    manifest: Object.fromEntries(routes.map(r => [r, { fields: [{ name: 'brief' }] }])),
    normalizePath: s => s,
    renderHero: () => '<h1>Hero Music</h1>',
    renderFormCard: () => '<form data-test-form><button type="submit">Submit</button></form>',
    renderSubtitleStudioCompanionLink: () => '',
    renderMusicProductGuidance: () => '<div class="portal-music-guidance-card">Guidance</div>',
    renderInteractiveFeatureWorkbench: () => '',
    stateFor: () => 'guarded',
    badge: val => `<span class="portal-badge">${val || 'guarded'}</span>`,
    renderEmpty: (title, body) => `<div class="portal-empty">${title} - ${body}</div>`
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(catalogue, ctx);
  ctx.TOANAASI18n.setLocale(locale, { emit: false });
  const names = [
    'portalI18n', 'uiText', 'safeText', 'stateLabel', 'badge', 'musicProductText',
    'canonicalDraftText', 'featureDraftTarget', 'canonicalDraftActions', 'canonicalPreferredText',
    'resultLabel', 'renderCanonicalValue', 'renderCanonicalSuggestions', 'renderCanonicalFlow',
    'safeFeatureTracking', 'safeVoiceReport', 'renderFeatureTracking', 'flowQuoteExpiry',
    'flowHasFreshEstimate', 'voiceQuoteAmount'
  ];
  for (const name of ['renderMusicCanonicalSuggestions', 'renderMusicCanonicalReport', 'renderMusicFlowState']) {
    if (text.includes(`  function ${name}(`)) names.push(name);
  }
  names.push('renderWorkspace');
  vm.runInContext(names.map(name => fn(text, name)).join('\n'), ctx);
  return ctx;
}

const emptyFlowCases = [
  ['missing', undefined],
  ['null', null],
  ['false', false],
  ['zero', 0],
  ['empty_string', ''],
  ['string', 'some_text'],
  ['empty_array', []],
  ['nonempty_array', ['item']],
  ['empty_object', {}]
];

const realFlowCases = [
  ['error_flow', { status: 'error', message: 'Tạo thất bại do lỗi engine' }],
  ['guarded_flow', { status: 'guarded', message: 'Hệ thống đang bảo vệ luồng' }],
  ['wrong_feature', { feature: 'wrong_feature', phase: 'ready', status: 'ready' }],
  ['draft_suggestions', {
    feature: 'music_song', phase: 'draft', status: 'draft', message: 'Draft ready',
    data: { draft: { available: true, content: { suggestions: [{ name: 'S1', prompt: 'P1' }, { name: 'S2', prompt: 'P2' }, { name: 'S3', prompt: 'P3' }] } } }
  }],
  ['estimate_zero', { status: 'awaiting_confirm', quote: { fee: 0, expires_at: 1893456000 } }],
  ['unknown_quote', { status: 'awaiting_confirm', quote: {} }],
  ['queued', { status: 'queued', tracking: { job_id: 'JOB-001' } }],
  ['processing', { status: 'processing', tracking: { job_id: 'JOB-002' } }],
  ['report_tracking', { status: 'completed', tracking: { job_id: 'JOB-003', progress: 50 } }]
];

for (const route of routes) {
  for (const locale of locales) {
    test(`H01: empty flow omits output card on ${route} (${locale})`, () => {
      const ctx = runtime(locale);
      const expectedTitle = ctx.safeText(ctx.musicProductText('output.title', 'Kết quả và trạng thái'));
      const titleHeader = `<h2 class="portal-card-title">${expectedTitle}</h2>`;
      for (const [tag, flowVal] of emptyFlowCases) {
        const featureFlows = flowVal === undefined ? {} : { [route]: flowVal };
        const html = ctx.renderWorkspace({ routePath: route, fields: [{ name: 'brief' }] }, { routePath: route, featureFlows });
        assert.ok(html.includes('data-test-form'), `form missing for ${tag}`);
        assert.ok(html.includes('portal-music-guidance-card'), `guidance missing for ${tag}`);
        assert.ok(!html.includes(titleHeader), `output card present for empty flow case: ${tag}`);
      }
    });

    test(`H02: real flow preserves output card on ${route} (${locale})`, () => {
      const ctx = runtime(locale);
      const expectedTitle = ctx.safeText(ctx.musicProductText('output.title', 'Kết quả và trạng thái'));
      const titleHeader = `<h2 class="portal-card-title">${expectedTitle}</h2>`;
      for (const [tag, flowVal] of realFlowCases) {
        const html = ctx.renderWorkspace({ routePath: route, fields: [{ name: 'brief' }] }, { routePath: route, featureFlows: { [route]: flowVal } });
        assert.ok(html.includes('data-test-form'), `form missing for ${tag}`);
        assert.ok(html.includes(titleHeader), `output card omitted for real flow case: ${tag}`);
      }
    });
  }
}
