import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const source = readFileSync('static/portal/portal.js', 'utf8');
const start = source.indexOf('  const SUBDUB_PRODUCT_MODES');
const block = source.slice(start, source.indexOf('\n  function renderDocumentHub', start));
const companionStart = source.indexOf('  function subDubVoiceCompanionUrl(');
const companion = source.slice(companionStart, source.indexOf('\n  }', companionStart) + 4);
const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');

function harness({ mode = 'subtitle_only', locale = 'vi', shared = {}, modes = {}, wallet = null } = {}) {
  const drafts = new Map([['/subdub', { shared, modes }]]);
  const browserWindow = { location: { search: '?mode=' + mode } };
  const api = new Function('window', 'interfaceLocaleFor', 'safeText', 'badge', 'renderHero', 'transientFormDrafts',
    companion + '\n' + block + '\nreturn {renderSubDubHub, captureSubDubDraft, subDubDraftSnapshot};')(
    browserWindow, context => context.locale, escape, () => '', () => '', drafts);
  return { html: api.renderSubDubHub({}, { locale, wallet }), api };
}

function summary(html) {
  return html.match(/data-subdub-stage="3"[\s\S]*?<\/section>/)?.[0] || '';
}

function rows(html) {
  return Object.fromEntries([...summary(html).matchAll(/data-subdub-setting="([^"]+)"[^>]*>([^<]*)</g)]
    .map(([, key, value]) => [key, value]));
}

test('review shows the selected subtitle settings and keeps unverified input unknown', () => {
  const { html } = harness({ shared: { source_subtitle_state: 'with_subtitles', subtitle_position: 'top_left' },
    modes: { SUBTITLE_ONLY: { 'subdub-source-output-format': 'txt', subtitle_format: 'short' } } });
  const values = rows(html);
  assert.equal(values.source_subtitle_state, 'Đã có phụ đề');
  assert.equal(values.source_file, 'Chưa xác minh');
  assert.equal(values.source_language, 'Chưa xác minh');
  assert.equal(values.output_format, 'TXT (Văn bản phân đoạn)');
  assert.equal(values.subtitle_position, 'Trên · trái');
  assert.equal(values.subtitle_format, 'Ngắn gọn cho video ngắn (Tối đa 25 ký tự/dòng, 1 dòng)');
  assert.equal(values.target_language, undefined);
  assert.equal(values.voice_lane, undefined);
});

test('dubbing review retains zero and two-hundred and omits hidden subtitle controls', () => {
  const { html } = harness({ mode: 'dubbing_only', shared: { target_language: 'en', target_language_custom: 'pt-BR',
    voice_lane: 'smart_multi', original_volume: '0', dubbing_volume: '200', subtitle_position: 'top_left' } });
  const values = rows(html);
  assert.equal(values.target_language, 'Tiếng Anh');
  assert.equal(values.target_language_custom, 'pt-BR');
  assert.equal(values.voice_lane, 'Smart Multi · phân bổ nhiều giọng thông minh');
  assert.equal(values.original_volume, '0%');
  assert.equal(values.dubbing_volume, '200%');
  assert.equal(values.subtitle_position, undefined);
  assert.equal(values.output_format, undefined);
  assert.equal(values.sub_display_type, undefined);
  assert.match(summary(html), /disabled data-status="guarded"/);
  assert.doesNotMatch(summary(html), /<audio|<video|download=/);
});

test('translated and combo reviews use their own formats and display defaults', () => {
  const translated = rows(harness({ mode: 'translated_subtitle', modes: {
    TRANSLATED_SUBTITLE: { 'subdub-translated-output-format': 'vtt' },
    SUBTITLE_PLUS_DUBBING: { 'subdub-combined-output-format': 'srt' }
  } }).html);
  assert.equal(translated.output_format, 'VTT (Trình duyệt web)');
  assert.equal(translated.sub_display_type, 'Phụ đề đơn ngữ (Chỉ bản dịch)');
  assert.equal(translated.voice_lane, undefined);
  assert.equal(translated.subtitle_format, undefined);
  const combo = rows(harness({ mode: 'subtitle_plus_dubbing', shared: { voice_lane: 'default_male' }, modes: {
    TRANSLATED_SUBTITLE: { 'subdub-translated-output-format': 'vtt' },
    SUBTITLE_PLUS_DUBBING: { 'subdub-combined-output-format': 'srt' }
  } }).html);
  assert.equal(combo.output_format, 'SRT (Tiêu chuẩn)');
  assert.equal(combo.sub_display_type, 'Phụ đề song ngữ (Gốc + Dịch)');
  assert.equal(combo.voice_lane, 'Giọng nam mặc định');
});

test('review localizes values, escapes custom user text and never invents a price or balance', () => {
  for (const [locale, unknown, language] of [['en', 'Not verified', 'English'], ['zh', '尚未确认', '英语']]) {
    const { html } = harness({ mode: 'subtitle_plus_dubbing', locale, shared: {
      target_language: 'en', target_language_custom: '<img src=x onerror=alert(1)>'
    } });
    const values = rows(html);
    assert.equal(values.source_file, unknown);
    assert.equal(values.target_language, language);
    assert.match(values.target_language_custom, /^&lt;img/);
    assert.doesNotMatch(summary(html), /<img|onerror="|>0 Xu</);
    assert.match(summary(html), />—</);
  }
  const { html } = harness({ wallet: { balance_xu: 0 } });
  assert.match(summary(html), />0 Xu</);
});

test('both dubbing panels provide precise number inputs and muted voice acknowledgement', () => {
  const { html } = harness({ mode: 'subtitle_plus_dubbing', shared: { original_volume: '0', dubbing_volume: '0' } });
  for (const suffix of ['dub', 'combo']) {
    const panel = html.match(new RegExp('data-subdub-mode-panel="' + (suffix === 'dub' ? 'DUBBING_ONLY' : 'SUBTITLE_PLUS_DUBBING') + '"[\\s\\S]*?</section>'))?.[0] || '';
    for (const [kind, max] of [['original', '100'], ['dubbing', '200']]) {
      const input = panel.match(new RegExp('<input[^>]*id="subdub-' + kind + '-volume-number-' + suffix + '"[^>]*>'))?.[0] || '';
      assert.match(input, /type="number"/);
      assert.match(input, /step="1"/);
      assert.match(input, /min="0"/);
      assert.ok(input.includes('max="' + max + '"'));
      assert.match(input, /value="0"/);
      assert.match(input, /aria-describedby=/);
      assert.ok(panel.includes('for="subdub-' + kind + '-volume-number-' + suffix + '"'));
    }
    assert.match(panel, /type="checkbox"[^>]*data-subdub-mute-ack/);
    assert.match(panel, /Giọng lồng tiếng đang tắt trong cấu hình/);
    assert.doesNotMatch(panel, /type="checkbox"[^>]*data-subdub-mute-ack[^>]*checked/);
  }
});
