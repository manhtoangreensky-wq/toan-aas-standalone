import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalog = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const voiceStart = source.indexOf('    voice: [');
const voiceEnd = source.indexOf('    voiceSaved: [', voiceStart);
const fieldsStart = source.indexOf('  function renderFields(');
const fieldsEnd = source.indexOf('  function statusMessage(', fieldsStart);
const formStart = source.indexOf('  function voiceFeedbackMetrics(');
const formEnd = source.indexOf('  const ADMIN_TAB_GROUPS', formStart);
assert.ok(voiceStart >= 0 && voiceEnd > voiceStart);
assert.ok(fieldsStart >= 0 && fieldsEnd > fieldsStart);
assert.ok(formStart >= 0 && formEnd > formStart);

function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}

function renderer(locale) {
  const ctx = {
    canAct: () => true, actionBlockReason: () => '', flowHasFreshEstimate: () => false,
    featureKeyForPage: () => 'voice_tts', workspaceDraftIdForRoute: () => '',
    featureConfirmExecutionReady: () => false, classifyPageBoundary: () => 'runtime_generator',
    ALLOWED_STATES: new Set(['guarded']), testDraft: {},
  };
  ctx.transientFormValues = () => ctx.testDraft;
  vm.createContext(ctx);
  vm.runInContext(catalog, ctx);
  ctx.uiText = (key, fallback, params) => ctx.TOANAASI18n.has(key)
    ? ctx.TOANAASI18n.t(key, params, locale) : fallback;
  ctx.voiceUiText = (key, fallback, params) => ctx.uiText(`voiceUi.${key}`, fallback, params);
  vm.runInContext(fn('safeText') + '\n' + source.slice(fieldsStart, fieldsEnd)
    + '\n' + source.slice(formStart, formEnd), ctx);
  vm.runInContext(`this.voiceFields = ({${source.slice(voiceStart, voiceEnd)}}).voice;`, ctx);
  const page = {path: '/voice/tts', type: 'feature', action: 'feature-estimate', fields: ctx.voiceFields};
  return {
    render(context = {}, draft = {}) {
      ctx.testDraft = draft;
      const html = ctx.renderFormCard(page, context);
      const select = html.match(/<select\b[^>]*name="default_voice_gender"[^>]*>[\s\S]*?<\/select>/);
      assert.ok(select, 'The actual Voice renderer must include the required gender select');
      return {html, select: select[0]};
    },
  };
}

for (const locale of ['vi', 'en', 'zh']) {
  const ui = renderer(locale);
  const labels = {vi: ['Nữ', 'Nam'], en: ['Female', 'Male'], zh: ['女声', '男声']}[locale];

  test(`Default voice renders localized female/male choices and requires an explicit initial selection (${locale})`, () => {
    const {select} = ui.render();
    assert.match(select, /\srequired\s/);
    assert.deepEqual([...select.matchAll(/<option value="([^"]*)"/g)].map(match => match[1]), ['', 'female', 'male']);
    assert.match(select, /<option value="" selected>/);
    assert.ok(select.includes(`<option value="female">${labels[0]}</option>`));
    assert.ok(select.includes(`<option value="male">${labels[1]}</option>`));
    assert.doesNotMatch(select, /Nữ \(female\)|Nam \(male\)/);
  });

  for (const gender of ['female', 'male']) {
    test(`Default voice keeps the selected ${gender} and original Unicode script after render (${locale})`, () => {
      const {html, select} = ui.render({}, {
        default_voice_gender: gender, script: 'Xin chào\n你好 & <script>test</script>',
        speed: '0.85', volume_percent: '0',
      });
      assert.ok(select.includes(`<option value="${gender}" selected>`));
      assert.equal([...select.matchAll(/<option[^>]* selected/g)].length, 1);
      assert.ok(html.includes('Xin chào\n你好 &amp; &lt;script&gt;test&lt;/script&gt;'));
      assert.match(html, /name="volume_percent"[^>]*value="0"/);
      assert.match(html, /name="speed"[^>]*value="0.85"/);
    });
  }

  test(`Unpublished readiness fields cannot silently select or replace a default voice (${locale})`, () => {
    const context = {readiness: {features: {voice_tts: {
      default_voice_genders: ['male'], default_voice_gender: 'male',
    }}}};
    const initial = ui.render(context).select;
    assert.match(initial, /<option value="" selected>/);
    assert.doesNotMatch(initial, /value="(?:female|male)" selected/);
    const restored = ui.render(context, {default_voice_gender: 'female'}).select;
    assert.match(restored, /value="female" selected/);
  });

  test(`Unknown draft gender does not become a supported voice or silently switch to one (${locale})`, () => {
    const {select} = ui.render({}, {default_voice_gender: 'neutral'});
    assert.doesNotMatch(select, /value="neutral"|value="(?:female|male)" selected/);
  });
}
