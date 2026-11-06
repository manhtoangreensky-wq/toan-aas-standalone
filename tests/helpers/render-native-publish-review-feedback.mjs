import assert from 'node:assert/strict';
import {reviewActionRuntime} from './publish-review-action-runtime.mjs';
let input='';for await(const chunk of process.stdin)input+=chunk;
const envelope=JSON.parse(input);
assert.equal(envelope.ok,true);assert.equal(envelope.status,'draft');
const expected={
  vi:'Đã chuẩn bị gói văn bản để rà soát. Ứng dụng không kết nối mạng xã hội, không tạo lịch, tác vụ, thanh toán hoặc thao tác đăng bài.',
  en:'Review text is prepared. The app does not connect social accounts or create schedules, jobs, payments or publishing actions.',
  zh:'已准备审核文字包。应用不会连接社交账户，也不会创建日程、任务、付款或发布操作。'
};
for(const locale of ['vi','en','zh']){
  const h=reviewActionRuntime(locale),task=h.run();assert.equal(h.pending.length,1);
  h.pending[0].resolve({ok:true,status:200,json:async()=>envelope});await task;
  assert.equal(h.state.publishReviewPackResult.package.title,envelope.data.package.title);
  assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,expected[locale]);assert.equal(h.button.disabled,false);
}
console.log('NATIVE_API_TO_INTEGRATION_FEEDBACK=3/3; customer receipt retained; no external network');
