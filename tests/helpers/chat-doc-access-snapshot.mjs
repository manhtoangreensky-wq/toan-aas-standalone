import assert from 'node:assert/strict';
import {chatRootDocReadHistoricalSnapshot} from './chat-root-doc-read-snapshot.mjs';
import {usableCopyHistoricalSnapshot} from './chat-document-usable-snapshot.mjs';

const rows={
  chatAccessUiHeading:['Khu vực trò chuyện hiện chưa thể mở','Conversation area cannot currently be opened','当前无法打开对话区域'],
  chatAccessUiEnabledBody:['Đăng nhập để xem các cuộc trò chuyện thuộc tài khoản hiện tại.','Sign in to view conversations belonging to the current account.','登录以查看属于当前账户的对话。'],
  chatAccessUiUnavailableBody:['Tính năng trò chuyện chưa được bật cho phiên này.','Conversation feature has not been enabled for this session.','当前会话尚未启用对话功能。'],
  documentAccessUiHeading:['Tài liệu hiện chưa thể mở','Documents cannot currently be opened','当前无法打开文档'],
  documentAccessUiBody:['Tài khoản hoặc phiên làm việc hiện chưa được phép xem công cụ và lịch sử tài liệu.','The account or session is not yet allowed to view document tools and history.','当前账户或会话暂未获准查看文档工具与历史记录。']
};
const rootLabels={
  vi:{chat:['Nội dung & trò chuyện','Mở không gian trò chuyện và ngữ cảnh do ứng dụng quản lý, tách biệt với Telegram.'],documents:['Không gian tài liệu','Chọn công cụ phù hợp cho tài liệu; từng thao tác có giới hạn, kiểm tra quyền sở hữu và điều kiện bàn giao riêng.']},
  en:{chat:['Content & Chat','Open a conversation workspace and Web-owned context, separate from Telegram.'],documents:['Document Workspace','Choose a document tool; each operation has its own limits, ownership checks and delivery conditions.']},
  zh:{chat:['内容与聊天','打开独立于 Telegram 的聊天空间和应用内资料。'],documents:['文档工作台','选择合适的文档工具；每项操作都有各自的限制、所有权检查和交付条件。']}
};
const oldLabels={
  chat:['AI Chat Workspace','Tổ chức hội thoại, context card, ghi chú và lịch sử revision trong không gian riêng tư của Web account.'],
  documents:['Document Studio','Không gian xử lý PDF riêng tư: chọn workflow có contract rõ ràng thay vì một form generic hoặc output mô phỏng.']
};
const esc=x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const value=(key,locale)=>rows[key][['vi','en','zh'].indexOf(locale)];
// Original full-catalog hashes remain strict: remove only five exact reviewed
// additions. Any mutated value, unknown key or existing value still fails.
export function chatDocAccessHistoricalSnapshot(entries,locale){
  assert.ok(rootLabels[locale]);
  entries=chatRootDocReadHistoricalSnapshot(usableCopyHistoricalSnapshot(entries,locale),locale);
  return entries.flatMap(([key,text])=>{
    if(!Object.hasOwn(rows,key))return[[key,text]];
    assert.equal(text,value(key,locale),'Unreviewed access copy must fail: '+key);
    return[];
  });
}
// Restore only finite root-hero/guard and /chat|/documents module-card labels
// for older HTML comparators. Never rewrite arbitrary/customer text nodes.
export function chatDocHistoricalMarkup(html,locale){
  assert.ok(rootLabels[locale]);
  for(const kind of ['chat','documents']){
    const [title,description]=rootLabels[locale][kind],old=oldLabels[kind];
    const className=kind==='chat'?'portal-chat-workspace':'portal-document-hub';
    if(html.startsWith('<article class="portal-page '+className+'">')&&html.includes('<h1 class="portal-title">'+esc(title)+'</h1>')){
      html=html.replace('<h1 class="portal-title">'+esc(title)+'</h1>','<h1 class="portal-title">'+esc(old[0])+'</h1>');
      html=html.replace('<p class="portal-description">'+esc(description)+'</p>','<p class="portal-description">'+esc(old[1])+'</p>');
    }
    const pattern=new RegExp('<a class="portal-module-card" href="/'+kind+'">[\\s\\S]*?</a>','g');
    html=html.replace(pattern,card=>card.replace('<h3>'+esc(title)+'</h3><p>'+esc(description)+'</p>','<h3>'+esc(old[0])+'</h3><p>'+esc(old[1])+'</p>'));
  }
  if(html.startsWith('<article class="portal-page portal-chat-workspace">')){
    const heading=esc(value('chatAccessUiHeading',locale));
    for(const [key,before]of [
      ['chatAccessUiEnabledBody','Đăng nhập bằng signed session để xem thread thuộc Web account hiện tại.'],
      ['chatAccessUiUnavailableBody','AI Chat Workspace đang được server giữ ở chế độ guarded. Web không gọi model hoặc bridge thay thế.']
    ])html=html.replace('<h3>'+heading+'</h3><p>'+esc(value(key,locale))+'</p>','<h3>AI Chat Workspace đang được bảo vệ</h3><p>'+before+'</p>');
  }
  if(html.startsWith('<article class="portal-page portal-document-hub">')){
    html=html.replace('<h2>'+esc(value('documentAccessUiHeading',locale))+'</h2><p>'+esc(value('documentAccessUiBody',locale))+'</p>',
      '<h2>Document Operations đang ở chế độ an toàn</h2><p>Document Studio chỉ hiển thị lịch sử khi signed session, Asset Vault và storage Document Operations được máy chủ xác minh. Web không thay thế bằng Asset Vault, Bot job, provider hay output mô phỏng.</p><div class="portal-state-meta"><span>Signed session</span><span>Owner-scoped</span><span>Không có output giả</span></div>');
  }
  return html;
}
