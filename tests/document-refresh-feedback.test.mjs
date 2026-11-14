import test from 'node:test';
import assert from 'node:assert/strict';
import {documentRefreshRuntime} from './helpers/document-refresh-action-runtime.mjs';

const expected={
  vi:{success:'Đã cập nhật lịch sử tài liệu.',failed:'Chưa tải được lịch sử tài liệu. Vui lòng thử lại.',permission:'Chưa thể làm mới tài liệu từ tài khoản này.',route:'Hãy mở trang tài liệu cần làm mới rồi thử lại.'},
  en:{success:'Document history updated.',failed:'Could not load document history. Please try again.',permission:'Cannot refresh documents from this account yet.',route:'Please open the document page to refresh and try again.'},
  zh:{success:'已更新文档历史记录。',failed:'无法加载文档历史记录，请重试。',permission:'此账户暂无法刷新文档。',route:'请打开需要刷新的文档页面后再试。'}
};
for(const locale of ['vi','en','zh'])for(const route of ['/documents','/documents/split'])for(const scenario of ['success','failure','stale-route','stale-session','stale-request','stale-logout']){
  test(`${locale}${route}/${scenario}: real read outcome controls feedback without extra requests`,async()=>{
    const r=documentRefreshRuntime(locale,route),job=r.run();
    assert.equal(r.pending.length,route==='/documents'?1:2);
    if(scenario.startsWith('stale-'))r.mutate(scenario.slice(6));
    for(let i=0;i<r.pending.length;i++)r.settle(i,{failed:scenario==='failure'||scenario==='stale-session'});
    await job;
    assert.equal(r.network.filter(x=>x.path==='/api/v1/document-operations').length,1);
    assert.equal(r.network.filter(x=>x.path==='/api/v1/asset-vault').length,route==='/documents'?0:1);
    if(scenario.startsWith('stale-'))assert.equal(r.toasts.length,0,'stale reads must stay silent');
    else{
      assert.equal(r.toasts.length,1);assert.equal(r.toasts[0].textContent,expected[locale][scenario==='failure'?'failed':'success']);
      assert.equal(r.toasts[0].attributes.role,scenario==='failure'?'alert':'status');
      assert.equal(r.state.documentOperationsReadState,scenario==='failure'?'failed':'ready');
      assert.deepEqual(Array.from(r.state.documentOperations),[]);
    }
  });
}
for(const locale of ['vi','en','zh'])for(const guard of ['permission','route'])test(`${locale}/${guard}: existing guard denies before any request, plain localized error`,async()=>{
  const r=documentRefreshRuntime(locale);if(guard==='permission')r.mutate('permission');
  await r.run(guard==='route'?'/documents/split':'/documents');
  assert.equal(r.network.length,0);assert.equal(r.toasts.length,1);
  assert.equal(r.toasts[0].textContent,expected[locale][guard]);assert.equal(r.toasts[0].attributes.role,'alert');
});
