import assert from 'node:assert/strict';
import test from 'node:test';
import {reviewActionRuntime} from './helpers/publish-review-action-runtime.mjs';

const known=[
  ['valid','Đã tạo gói review text; chưa có post hoặc publish action.',{vi:'Đã tạo gói văn bản để rà soát; chưa có thao tác đăng bài.',en:'Review text created; no publishing action was made.',zh:'已创建审核文字包；未执行发布操作。'}],
  ['guarded','Nội dung cần được điều chỉnh trước khi tạo gói review.',{vi:'Nội dung cần được điều chỉnh trước khi tạo gói rà soát.',en:'Adjust the content before creating a review package.',zh:'请调整内容后再创建审核包。'}],
  ['transport_error','Yêu cầu chưa được xác nhận.',{vi:'Yêu cầu chưa được xác nhận.',en:'The request was not confirmed.',zh:'请求尚未得到确认。'}],
  ['guarded_unsafe','',{vi:'Máy chủ chưa trả thông tin xác nhận gói rà soát an toàn.',en:'The server did not return a safe review-package boundary.',zh:'服务器未返回安全的审核包边界。'}],
  ['unsafe','',{vi:'Máy chủ chưa trả gói rà soát an toàn.',en:'The server did not return a safe Web-native review package.',zh:'服务器未返回安全的网页审核包。'}],
  ['valid','Đã chuẩn bị gói review text. Web không kết nối social, không tạo lịch, job, thanh toán hoặc publish action.',{vi:'Đã chuẩn bị gói văn bản để rà soát. Ứng dụng không kết nối mạng xã hội, không tạo lịch, tác vụ, thanh toán hoặc thao tác đăng bài.',en:'Review text is prepared. The app does not connect social accounts or create schedules, jobs, payments or publishing actions.',zh:'已准备审核文字包。应用不会连接社交账户，也不会创建日程、任务、付款或发布操作。'}],
  ['guarded_error','Nội dung cần được viết lại theo hướng nguyên bản, không mô phỏng tác giả, nghệ sĩ, bài hát hoặc phong cách cụ thể.',{vi:'Nội dung cần được viết lại theo hướng nguyên bản, không mô phỏng tác giả, nghệ sĩ, bài hát hoặc phong cách cụ thể.',en:'Rewrite the content in an original direction without imitating a specific author, artist, song or style.',zh:'请以原创方向改写内容，不模仿特定作者、艺术家、歌曲或风格。'}]
];
for(const locale of ['vi','en','zh']){
  for(const [kind,message,expected]of known){
    test(`${locale}: known ${kind} feedback remains localized`,async()=>{
      const h=reviewActionRuntime(locale),task=h.run();h.settle(0,kind,'CURRENT',message);await task;
      assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,expected[locale]);assert.equal(h.button.disabled,false);
    });
  }
  for(const kind of ['valid','guarded','guarded_error','transport_error']){
    test(`${locale}: unknown ${kind} feedback retains its actual message`,async()=>{
      const message='REMOTE_NOTE_317 — nội dung riêng cần giữ nguyên.';
      const h=reviewActionRuntime(locale),task=h.run();h.settle(0,kind,'CURRENT',message);await task;
      assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,message);assert.equal(h.button.disabled,false);
    });
  }
  for(const message of ['constructor','toString','__proto__']){
    test(`${locale}: prototype-like feedback ${message} is not interpreted as a catalog key`,async()=>{
      const h=reviewActionRuntime(locale),task=h.run();h.settle(0,'valid','CURRENT',message);await task;
      assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,message);
    });
  }
}
