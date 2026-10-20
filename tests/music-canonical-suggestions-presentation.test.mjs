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
  const copy = {
    vi: { 'suggestion.kicker':'GỢI Ý ÂM NHẠC', 'suggestion.title':'Ba phương án để so sánh', 'suggestion.description':'Chọn một hướng để tiếp tục.', 'suggestion.empty':'Chưa có đủ phương án từ máy chủ.', 'suggestion.option':'Phương án {number}', 'suggestion.copy':'Sao chép mô tả', 'suggestion.apply':'Dùng trong biểu mẫu', 'suggestion.meta.mood':'Cảm xúc', 'suggestion.meta.tempo':'Nhịp độ', 'suggestion.meta.instrument':'Nhạc cụ', 'suggestion.meta.duration':'Thời lượng', 'suggestion.meta.vocal':'Giọng hát', 'suggestion.meta.useCase':'Mục đích' },
    en: { 'suggestion.kicker':'MUSIC SUGGESTIONS', 'suggestion.title':'Three options to compare', 'suggestion.description':'Choose one direction to continue.', 'suggestion.empty':'The server has not returned enough options.', 'suggestion.option':'Option {number}', 'suggestion.copy':'Copy description', 'suggestion.apply':'Use in form', 'suggestion.meta.mood':'Mood', 'suggestion.meta.tempo':'Tempo', 'suggestion.meta.instrument':'Instrument', 'suggestion.meta.duration':'Duration', 'suggestion.meta.vocal':'Vocal', 'suggestion.meta.useCase':'Use case' },
    zh: { 'suggestion.kicker':'音乐方案', 'suggestion.title':'比较三个方案', 'suggestion.description':'选择一个方向继续。', 'suggestion.empty':'服务器尚未返回足够的方案。', 'suggestion.option':'方案 {number}', 'suggestion.copy':'复制描述', 'suggestion.apply':'用于表单', 'suggestion.meta.mood':'情绪', 'suggestion.meta.tempo':'节奏', 'suggestion.meta.instrument':'乐器', 'suggestion.meta.duration':'时长', 'suggestion.meta.vocal':'演唱', 'suggestion.meta.useCase':'用途' }
  }[locale];
  const ctx = { safeText: htmlEscape, canonicalDraftText: value => typeof value === 'string' && value.trim() && value.length <= 2000 ? value.trim() : '', musicProductText: (key, fallback, params) => (copy[key] || fallback).replace('{number}', String(params?.number || '')), canonicalDraftActions: (text, route, field, label) => `<div data-copy="${htmlEscape(text)}" data-route="${route}" data-field="${field}">${htmlEscape(label)}</div>` };
  vm.createContext(ctx);
  vm.runInContext(extract('renderMusicCanonicalSuggestions'), ctx);
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
    assert.match(html, /Nền bình minh/); assert.match(html, /data-copy=/);
    assert.doesNotMatch(html, /canonical planning|provider|asset|job|Engine|server/i);
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
  assert.match(html, /&lt;script&gt;/); assert.match(html, /data-route="\/music\/song"/); assert.match(html, /data-field="brief"/);
});
