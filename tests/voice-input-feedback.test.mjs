import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  const end = source.indexOf('\n  }', start) + 4;
  assert.ok(start >= 0 && end > start, `missing ${name}`);
  return source.slice(start, end);
}

test('Voice content counts preserve Unicode and do not confuse a blank volume with silence', () => {
  const ctx = {};
  vm.createContext(ctx);
  vm.runInContext(fn('voiceFeedbackMetrics'), ctx);
  const value = ctx.voiceFeedbackMetrics({ script: 'Xin chào\nViệt Nam 😀', volume_percent: '0' });
  assert.equal(value.words, 5);
  assert.equal(value.characters, 19);
  assert.equal(value.muted, true);
  for (const volume of ['', '100', '200', undefined]) {
    assert.equal(ctx.voiceFeedbackMetrics({ script: '', volume_percent: volume }).muted, false);
  }
  assert.equal(ctx.voiceFeedbackMetrics({ script: '  \n\t' }).words, 0);
});

for (const locale of ['vi', 'en', 'zh']) {
  test(`Voice content count and mute warning render from current input in ${locale}`, () => {
    const ctx = {};
    vm.createContext(ctx);
    vm.runInContext(catalogue, ctx);
    ctx.voiceUiText = (key, fallback, params) => ctx.TOANAASI18n.t(`voiceUi.${key}`, params, locale) || fallback;
    vm.runInContext(fn('safeText') + '\n' + fn('voiceFeedbackMetrics') + '\n' + fn('renderVoiceFormFeedback'), ctx);
    const html = ctx.renderVoiceFormFeedback({ script: 'Xin chào', volume_percent: '0' });
    assert.match(html, /data-voice-text-count/);
    assert.match(html, /2/);
    assert.match(html, /8/);
    assert.doesNotMatch(html, /data-voice-muted-warning[^>]* hidden/);
    assert.match(html, locale === 'vi' ? /Âm lượng đang ở 0%/ : locale === 'en' ? /Volume is set to 0%/ : /音量设为 0%/);
    assert.match(ctx.renderVoiceFormFeedback({ script: '', volume_percent: '100' }), /data-voice-muted-warning[^>]* hidden/);
    assert.doesNotMatch(html, /<audio\b|https?:\/\/|\{words\}|\{characters\}/);
    if (locale === 'vi') assert.doesNotMatch(html, /capability|workflow|provider|canonical/);
    if (locale === 'en') assert.doesNotMatch(html, /[À-ỹ]/);
  });
}
