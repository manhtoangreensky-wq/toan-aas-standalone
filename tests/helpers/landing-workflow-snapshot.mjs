import assert from 'node:assert/strict';

const before={
  vi:'Ứng dụng quản lý nội dung soạn thảo, phiên đăng nhập đã xác thực, quyền sở hữu và nhật ký hoạt động. Trình duyệt không gọi nhà cung cấp dịch vụ, không tự ghi sổ Xu và không tự xác nhận thanh toán.',
  en:'The Web App manages authoring, signed sessions, ownership, and audit. The browser does not call providers, keep a Xu ledger, or finalize payment.',
  zh:'应用管理编辑内容、已验证的登录会话、所有权和操作记录。浏览器不会调用外部服务、保存 Xu 账本或自行确认付款。'
};
const approved={
  vi:'Chọn công cụ, chuẩn bị nội dung, rồi xem lại và lưu khi sẵn sàng.',
  en:'Choose a tool, prepare content, then review and save when ready.',
  zh:'选择工具，准备内容，然后在就绪时检查并保存。'
};

// Preserve the old complete-catalog hashes without ignoring any key or accepting
// arbitrary new copy. Only the three reviewed current literals normalize back.
export function landingWorkflowHistoricalSnapshot(entries,locale){
  assert.ok(['vi','en','zh'].includes(locale));
  return entries.map(([key,value])=>{
    if(key!=='landing.workflow.body')return[key,value];
    assert.equal(value,approved[locale],'Unreviewed landing workflow copy must fail');
    return[key,before[locale]];
  });
}
