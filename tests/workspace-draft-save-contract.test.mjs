import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/integration.js', 'utf8');
const catalogue = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
function fn(name) {
  const start = source.indexOf(`  function ${name}(`);
  assert.ok(start >= 0, name);
  return source.slice(start, source.indexOf('\n  }', start) + 4);
}
function runtime(locale = 'vi', options = {}) {
  const calls = [], toasts = [], busy = [], released = [];
  const context = { window: {}, document: { querySelector: () => ({ textContent: {vi:'Sáng tác bài hát', en:'Write a song', zh:'创作歌曲'}[locale] }) },
    workspaceDraftFeatureForRoute: () => ({ key: 'music_song', title: 'Tên VI không được rò vào EN' }),
    validWorkspaceDraftId: () => true, acquireSubmission: () => options.pending ? null : { key: 'qa-idempotency' },
    releaseSubmission: value => released.push(value), setActionBusy: (...value) => busy.push(value),
    refreshWorkspaceDraftLibraryAfterMutation: async () => {}, toast: (...value) => toasts.push(value),
    api: async (path, request) => { calls.push({path, request}); if(options.fail) throw Object.assign(new Error('Nội dung lỗi máy chủ'), {status:options.fail}); return {ok:true,message:'Thông báo VI từ máy chủ'}; }
  };
  vm.createContext(context); vm.runInContext(catalogue, context);
  context.window.TOANAASI18n.setLocale(locale, {emit:false});
  if(source.includes('  function workspaceDraftText(')) vm.runInContext(fn('workspaceDraftText'), context);
  vm.runInContext(fn('workspaceDraftInput'), context);
  const start = source.indexOf('      if (action === "workspace-draft-save" || action === "workspace-draft-update") {');
  const end = source.indexOf('      if (action === "workspace-draft-resume") {', start);
  vm.runInContext(`async function save(action, fields, detail = {}) { const route = '/music/song'; ${source.slice(start,end)} }`, context);
  return {context,calls,toasts,busy,released};
}

test('Native draft keeps product text and zero volume, excludes file/profile/receipt values', () => {
  const {context} = runtime();
  const input = {lyrics:'Lời 🎵\n第二行', vocal_mode:'duet', default_voice_gender:'female', volume_percent:'0', source_language:'auto', upload_ids:'x',voice_profile_id:'x',consent:'true',file:'x',web_quote_receipt:'x',notes:''};
  assert.deepEqual(JSON.parse(JSON.stringify(context.workspaceDraftInput(input))), {lyrics:'Lời 🎵\n第二行',vocal_mode:'duet',default_voice_gender:'female',volume_percent:'0',source_language:'auto'});
});

for(const locale of ['vi','en','zh']) {
  test(`Native draft rejects long input before any request, preserves source text (${locale})`, async () => {
    const h=runtime(locale), fields={brief:'Giữ nguyên',lyrics:'🎵'.repeat(4001)}, snapshot={...fields};
    await assert.rejects(h.context.save('workspace-draft-save', fields), /4[.,]?000/);
    assert.deepEqual(fields,snapshot); assert.equal(h.calls.length,0); assert.equal(h.busy.length,0);
    assert.equal(h.context.workspaceDraftInput({lyrics:'🎵'.repeat(4000)}).lyrics,'🎵'.repeat(4000));
  });
  test(`Native save/update uses locale copy, keeps payload and releases submission (${locale})`, async () => {
    const h=runtime(locale);
    for(const action of ['workspace-draft-save','workspace-draft-update']) await h.context.save(action,{lyrics:'Lời gốc',vocal_mode:'duet'},{workspaceDraftId:'qa-draft'});
    assert.equal(h.calls[0].request.method,'POST'); assert.equal(h.calls[1].request.method,'PATCH');
    const payload=JSON.parse(h.calls[0].request.body);
    assert.deepEqual(payload.input,{lyrics:'Lời gốc',vocal_mode:'duet'}); assert.equal(payload.idempotency_key,'qa-idempotency');
    assert.equal(payload.feature_key,'music_song'); assert.ok(payload.title.includes({vi:'Sáng tác bài hát',en:'Write a song',zh:'创作歌曲'}[locale]));
    assert.equal(h.released.length,2); assert.equal(h.busy.at(-1)[2],false);
    assert.ok(h.toasts[0][0].includes({vi:'Đã lưu',en:'saved',zh:'已保存'}[locale]));
    assert.doesNotMatch(h.toasts.flat().join(' '),/Thông báo VI từ máy chủ/);
  });
  test(`Native duplicate and API failure stay localized and never claim saved (${locale})`, async () => {
    const pending=runtime(locale,{pending:true}); await pending.context.save('workspace-draft-save',{brief:'QA'});
    assert.equal(pending.calls.length,0); assert.equal(pending.toasts[0][1],'error');
    const failed=runtime(locale,{fail:422});
    await assert.rejects(failed.context.save('workspace-draft-save',{brief:'QA'}), error => !/Nội dung lỗi máy chủ/.test(error.message) && Boolean(error.message));
    assert.equal(failed.toasts.length,0); assert.equal(failed.released.length,1); assert.equal(failed.busy.at(-1)[2],false);
    if(locale!=='vi') assert.doesNotMatch(pending.toasts[0][0],/[À-ỹĐđ]/);
  });
}
