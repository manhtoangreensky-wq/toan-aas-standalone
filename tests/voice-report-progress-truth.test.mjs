import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalog = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, name);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}
function runtime(locale = 'vi') {
  const ctx = { ALLOWED_STATES: new Set(['processing','completed']), FEATURE_TRACKING_JOB_STATES:new Set(['processing','completed']),
    canonicalPreferredText:() => '', featureDraftTarget:() => '', safeFeatureTracking:() => null,
    flowHasFreshEstimate:() => false, voiceQuoteAmount:() => null };
  vm.createContext(ctx); vm.runInContext(catalog,ctx);
  ctx.voiceUiText = (key,fallback) => ctx.TOANAASI18n.has(`voiceUi.${key}`) ? ctx.TOANAASI18n.t(`voiceUi.${key}`,null,locale) : fallback;
  vm.runInContext(['safeText','safeVoiceReport','renderVoiceFlowState'].map(fn).join('\n'),ctx);
  return ctx;
}
const flow = (report) => ({phase:'confirm',feature:'voice_tts',status:'processing',data:{report:{status:'processing',...report}}});

test('Voice report rejects non-numeric progress instead of fabricating zero', () => {
  const ctx = runtime();
  for (const value of [undefined,null,'','   ',false,true,'0','50',[],[50],{},NaN,Infinity,-Infinity,-1,101]) {
    assert.equal(ctx.safeVoiceReport(flow({progress_percent:value})).progress,null,`invalid ${String(value)}`);
  }
});
test('Voice report preserves actual zero, decimal rounding, full progress and key priority', () => {
  const ctx = runtime();
  for (const [value,expected] of [[0,0],[0.4,0],[49.6,50],[100,100]]) {
    assert.equal(ctx.safeVoiceReport(flow({progress_percent:value})).progress,expected);
  }
  assert.equal(ctx.safeVoiceReport(flow({progress_percentage:35})).progress,35);
  assert.equal(ctx.safeVoiceReport(flow({progress:65})).progress,65);
  assert.equal(ctx.safeVoiceReport(flow({progress_percent:0,progress_percentage:30,progress:70})).progress,0);
  assert.equal(ctx.safeVoiceReport(flow({progress_percent:false,progress:70})).progress,null);
});
for (const locale of ['vi','en','zh']) {
  test(`Voice report renders known progress only and retains truthful delivery state (${locale})`, () => {
    const ctx = runtime(locale);
    const render = (value) => ctx.renderVoiceFlowState(flow({progress_percent:value,output_available:true,download_ready:false,delivery_ready:false,status_reason:'QA_REASON <script>'}),'/voice/tts');
    for (const value of ['',false,'   ',[],{}]) {
      const html = render(value);
      assert.doesNotMatch(html,/<dd>\d+%<\/dd>/);
      assert.match(html,/data-voice-report-state="available"/);
      assert.match(html,/QA_REASON &lt;script&gt;/);
      assert.doesNotMatch(html,/<audio\b|<script\b|data-voice-report-download/);
      assert.ok(html.includes(ctx.voiceUiText('flow.report.downloadPending','')));
    }
    for (const value of [0,50,100]) assert.ok(render(value).includes(`<dd>${value}%</dd>`));
  });
}
