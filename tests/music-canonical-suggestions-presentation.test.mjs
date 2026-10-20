import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
function extract(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, `${name} must exist`);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}
function htmlEscape(value) {
  return String(value).replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
}
function runtime(locale) {
  const ctx = {safeText:htmlEscape, MUSIC_PRODUCT_ROUTES:['/music/create','/music/song'], normalizePath:value=>value};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync('static/portal/portal-i18n.js','utf8'),ctx);
  ctx.TOANAASI18n.setLocale(locale,{emit:false});
  ctx.musicProductText=(key,fallback,params)=>ctx.TOANAASI18n.has('musicProduct.'+key)?ctx.TOANAASI18n.t('musicProduct.'+key,params):fallback;
  vm.runInContext(extract('canonicalDraftText')+'\n'+extract('renderMusicCanonicalSuggestions'),ctx);
  return ctx;
}
const fixture = [
  { name: 'Nền bình minh', prompt: 'Nhạc nền nhẹ cho video giới thiệu.', mood: 'Ấm áp', tempo: '92 BPM', instrument: 'Piano', duration: '30 giây', vocal: 'Không lời', use_case: 'Video sản phẩm' },
  { name: 'Năng lượng mới', prompt: 'Nhịp điện tử sáng, mở đầu nhanh.', mood: 'Tươi sáng', tempo: '118 BPM', instrument: 'Synth', duration: '45 giây', vocal: 'Không lời', use_case: 'Video ngắn' },
  { name: 'Chiều sâu thương hiệu', prompt: 'Âm thanh rộng, nhấn vào thông điệp chính.', mood: 'Tin cậy', tempo: '80 BPM', instrument: 'Strings', duration: '60 giây', vocal: 'Không lời', use_case: 'Thương hiệu' }
];

for (const locale of ['vi', 'en', 'zh']) {
  test(`Music renders exactly three real suggestions with localized chrome (${locale})`, () => {
    const html = runtime(locale).renderMusicCanonicalSuggestions(fixture, '/music/create', 'brief');
    assert.equal((html.match(/data-music-suggestion-card=/g) || []).length, 3);
    assert.match(html, /Nền bình minh/); assert.match(html, /data-canonical-text=/);
    assert.doesNotMatch(html, /canonical planning|provider|asset|job|Engine/i);
    assert.doesNotMatch(html, /<audio\b|download|feature-confirm/);
  });
}

test('Music never pads missing or malformed suggestions', () => {
  const ctx = runtime('vi');
  for (const values of [[], [{prompt:'Một'}], [{prompt:'Một'}, {prompt:'Hai'}], [{prompt:''}, null, 'bad', {name:'Thiếu prompt'}]]) {
    const html = ctx.renderMusicCanonicalSuggestions(values, '/music/song', 'brief');
    assert.ok((html.match(/data-music-suggestion-card=/g) || []).length <= 2);
    assert.doesNotMatch(html, /Phương án 3/);
  }
});

test('Music escapes suggestion content and keeps copy/apply route-bound', () => {
  const html = runtime('vi').renderMusicCanonicalSuggestions([{name:'<script>alert(1)</script>',prompt:'<img src=x onerror=alert(1)>',mood:'<b>x</b>'}], '/music/song', 'brief');
  assert.doesNotMatch(html, /<(script|img)\b/i);
  assert.match(html, /&lt;script&gt;/); assert.match(html, /data-canonical-route="\/music\/song"/); assert.match(html, /data-canonical-field="brief"/);
});
