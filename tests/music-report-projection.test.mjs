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
function runtime(locale = 'vi') {
  const copy = {
    vi: { title:'Báo cáo xử lý nhạc', pending:'Chưa có báo cáo chi tiết từ máy chủ.', note:'Chỉ hiển thị tín hiệu máy chủ; chưa tự tạo tệp.', status:'Trạng thái', progress:'Tiến độ', output:'Tệp kết quả', outputReady:'Đã có tín hiệu tệp', outputPending:'Chưa có tín hiệu tệp', download:'Tải xuống', downloadReady:'Đủ điều kiện', downloadPending:'Chưa đủ điều kiện', delivery:'Bàn giao', deliveryReady:'Sẵn sàng', deliveryPending:'Chưa sẵn sàng', reason:'Thông tin máy chủ' },
    en: { title:'Music processing report', pending:'No detailed server report yet.', note:'Only server signals are shown; no file is fabricated.', status:'Status', progress:'Progress', output:'Output file', outputReady:'File signal available', outputPending:'No file signal yet', download:'Download', downloadReady:'Eligible', downloadPending:'Not eligible', delivery:'Delivery', deliveryReady:'Ready', deliveryPending:'Not ready', reason:'Server information' },
    zh: { title:'音乐处理报告', pending:'服务器尚无详细报告。', note:'仅显示服务器信号，不会伪造文件。', status:'状态', progress:'进度', output:'输出文件', outputReady:'已有文件信号', outputPending:'尚无文件信号', download:'下载', downloadReady:'符合条件', downloadPending:'尚不符合条件', delivery:'交付', deliveryReady:'已准备', deliveryPending:'未准备', reason:'服务器信息' }
  }[locale];
  const ctx = { safeText: value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])), musicProductText: (key, fallback) => copy[key.split('.').pop()] || fallback, safeVoiceReport: flow => flow.report || null, badge: () => '' };
  vm.createContext(ctx); vm.runInContext(extract('renderMusicCanonicalReport'), ctx); return ctx;
}

for (const locale of ['vi', 'en', 'zh']) {
  test(`Music report keeps known bounded signals and no fake delivery (${locale})`, () => {
    const html = runtime(locale).renderMusicCanonicalReport({ report: { status:'processing', progress:50, outputKnown:true, outputAvailable:false, downloadKnown:true, downloadReady:false, deliveryKnown:true, deliveryReady:false, reason:'QA <script>' } });
    assert.match(html, /data-music-report/); assert.match(html, /50%/); assert.match(html, /QA &lt;script&gt;/);
    assert.doesNotMatch(html, /<audio\b|download=|href=.*https?:|data-music-asset/);
  });
}

test('Music with no report stays pending and does not claim completion', () => {
  const html = runtime('vi').renderMusicCanonicalReport({});
  assert.match(html, /Chưa có báo cáo chi tiết/); assert.doesNotMatch(html, /Đã sẵn sàng bàn giao|<audio\b|download=/);
});
