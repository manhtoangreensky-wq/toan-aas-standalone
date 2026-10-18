import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalog = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}
const start = source.indexOf('  function renderFields(');
const end = source.indexOf('  function statusMessage(', start);
const feedbackStart = source.indexOf('  function voiceFeedbackMetrics(');
const feedbackEnd = source.indexOf('  const ADMIN_TAB_GROUPS', feedbackStart);

for (const locale of ['vi', 'en', 'zh']) {
  const ctx = {
    canAct: () => true, actionBlockReason: () => '', flowHasFreshEstimate: () => false,
    featureKeyForPage: () => 'voice_stt', workspaceDraftIdForRoute: () => '',
    featureConfirmExecutionReady: () => false, transientFormValues: () => ({}),
    classifyPageBoundary: () => 'runtime_generator', ALLOWED_STATES: new Set(['guarded'])
  };
  vm.createContext(ctx);
  vm.runInContext(catalog, ctx);
  ctx.uiText = (key, fallback, params) => ctx.TOANAASI18n.has(key) ? ctx.TOANAASI18n.t(key, params, locale) : fallback;
  ctx.voiceUiText = (key, fallback, params) => ctx.uiText(`voiceUi.${key}`, fallback, params);
  vm.runInContext(fn('safeText') + '\n' + source.slice(start, end) + '\n' + source.slice(feedbackStart, feedbackEnd), ctx);
  Object.assign(ctx, {renderSubtitleStudioCompanionLink: () => '', renderInteractiveFeatureWorkbench: () => '', renderHero: () => '', renderEmpty: (title, body) => `<h3>${title}</h3><p>${body}</p>`});
  vm.runInContext(fn('renderWorkspace'), ctx);
  const page = { path: '/voice/stt', type: 'feature', action: 'feature-estimate', fields: [
    { name: 'source', label: 'Source', type: 'file', accept: 'audio/mpeg,video/mp4', requiredUpload: true },
    { name: 'output_format', label: 'Format', control: 'select', options: [{value: 'txt', label: 'Text'}, {value: 'srt', label: 'SRT'}] }
  ] };
  test(`STT form describes transcription instead of generating speech (${locale})`, () => {
    const html = ctx.renderFormCard(page, {bridge: {featureExecutionFeatures: ['voice_stt']}});
    assert.match(html, new RegExp({vi: 'Chuẩn bị bản chép lời', en: 'Prepare transcription', zh: '准备转写'}[locale]));
    assert.match(html, new RegExp({vi: 'bản chép lời', en: 'transcript', zh: '转写'}[locale]));
    assert.doesNotMatch(html, /data-voice-input-feedback|data-voice-text-count|data-voice-muted-warning/);
    assert.doesNotMatch(html, /Chỉ tạo âm thanh|Audio is created|生成音频|speech generation|tạo giọng/);
    assert.match(html, /name="source"[^>]*type="file"/);
    assert.doesNotMatch(html, /<audio\b|download=|data-portal-action="feature-confirm"/);
  });
  test(`STT file input stays disabled without processing access even when scalar drafts are allowed (${locale})`, () => {
    const original = ctx.canAct;
    ctx.canAct = () => false;
    try {
      const html = ctx.renderFormCard(page, {session: {authenticated: true, csrfReady: true}, workspaceDraftFeatures: ['voice_stt'], capabilities: {'workspace-draft-save': true}});
      assert.match(html, /name="source"[^>]* disabled/);
      assert.match(html, /data-portal-action="workspace-draft-save"/);
      assert.doesNotMatch(html, /name="output_format"[^>]* disabled/);
      assert.match(html, new RegExp({vi: 'chưa tạo bản chép lời', en: 'does not create a transcript', zh: '不会生成转写'}[locale]));
    } finally { ctx.canAct = original; }
  });
  test(`TTS retains its text feedback when STT presentation changes (${locale})`, () => {
    const html = ctx.renderFormCard({...page, path: '/voice/tts'}, {});
    assert.match(html, /data-voice-text-count/);
    assert.match(html, new RegExp({vi: 'Chuẩn bị giọng đọc', en: 'Prepare speech', zh: '准备语音'}[locale]));
  });
  test(`Generic bridge access cannot unlock STT upload or quote without STT capability (${locale})`, () => {
    const html = ctx.renderFormCard(page, {bridge: {available: true, featureExecutionFeatures: ['voice_tts']}});
    assert.match(html, /name="source"[^>]* disabled/);
    assert.match(html, /type="submit"[^>]* disabled/);
    assert.doesNotMatch(html, /data-portal-action="feature-confirm"/);
  });
  test(`STT empty results describe a transcript, not a missing audio output (${locale})`, () => {
    const html = ctx.renderWorkspace(page, {bridge: {featureExecutionFeatures: []}});
    assert.match(html, new RegExp({vi: 'Chưa có bản chép lời', en: 'No transcript yet', zh: '暂无转写结果'}[locale]));
    assert.doesNotMatch(html, /Chưa có kết quả âm thanh|No audio results|暂无音频结果/);
  });
  test(`A permitted STT quote confirms transcription, not speech generation (${locale})`, () => {
    ctx.flowHasFreshEstimate = () => true;
    ctx.featureConfirmExecutionReady = () => true;
    ctx.voiceQuoteAmount = () => 3;
    try {
      const html = ctx.renderFormCard(page, {bridge: {featureExecutionFeatures: ['voice_stt']}, featureFlows: {'/voice/stt': {phase: 'estimate', status: 'awaiting_confirm', input: {}}}});
      const button = html.match(/<button[^>]*data-portal-action="feature-confirm"[^>]*>([^<]*)<\/button>/);
      assert.ok(button);
      assert.equal(button[1], {vi: 'Xác nhận chép lời', en: 'Confirm transcription', zh: '确认转写'}[locale]);
      assert.doesNotMatch(html, /speech generation|Xác nhận tạo giọng|确认生成语音/);
    } finally {
      ctx.flowHasFreshEstimate = () => false;
      ctx.featureConfirmExecutionReady = () => false;
    }
  });
}
