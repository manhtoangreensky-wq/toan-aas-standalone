import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const authoring=['IntroKicker','IntroTitle','IntroBody','CountTotal','CountReview','CountReady','CreateKicker','CreateTitle','CreateSubtitle','CreateSafetyHint','CreateSubmit','LibraryKicker','LibraryTitle','LibrarySubtitle','LibraryRefresh','LibraryFilterHint','LibraryApply','EmptyTitle','EmptyBody'].map(k=>'chatRootUi'+k);
const filters=['State','Search','SearchPlaceholder','All','Draft','Review','Ready','Archived'].map(k=>'chatFilterUi'+k);
const documents=['LoadingHeading','LoadingBody','FailedHeading','FailedBody','RetryButton'].map(k=>'docReadUi'+k);
const keys=new Set([...authoring,...filters,...documents]);
const hashes={vi:'f77c8674e5b42f6ef8c49aa5db90fe7aba7514f4ee06d8f14abb59ade4a4a558',en:'ef4985a2153d23c2a3638a2b939d18954251e4452ef7ff3c0862ff6d35de832f',zh:'ad747ac7ecd795522b755d9d9c2104abbe4b6b88c6972fcdfb244413041d9d1e'};
const esc=x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const re=x=>x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');

// Preserve all old catalog golden hashes. Only these exact 32 reviewed entries
// may disappear; a changed/missing value, altered order or unknown key survives
// as a failure rather than being hidden by a prefix filter.
export function chatRootDocReadHistoricalSnapshot(entries,locale){
  assert.ok(hashes[locale]);
  const added=entries.filter(([key])=>keys.has(key));
  if(!added.length)return entries;
  assert.equal(added.length,32,'Unreviewed root/read copy: missing approved keys');
  assert.equal(createHash('sha256').update(JSON.stringify(added)).digest('hex'),hashes[locale],'Unreviewed root/read copy');
  return entries.filter(([key])=>!keys.has(key));
}
export function chatRootDocReadHistoricalMarkup(html,locale,messages){
  chatRootDocReadHistoricalSnapshot(Object.entries(messages),locale);
  const replace=(region,key,before,opening)=>{
    const pattern=new RegExp('('+opening+')'+re(esc(messages[key]))+'(?=<)');
    return region.replace(pattern,(_,start)=>start+before);
  };
  const section=(start,edit)=>{
    const a=html.indexOf(start);if(a<0)return;
    const b=html.indexOf('</section>',a);assert.ok(b>a);
    const old=html.slice(a,b+10);html=html.slice(0,a)+edit(old)+html.slice(b+10);
  };
  if(html.startsWith('<article class="portal-page portal-chat-workspace">')){
    section('<section class="portal-chat-workspace-intro">',s=>{
      for(const [key,before,tag]of [
        ['IntroKicker','Web-native conversation vault','<span class="portal-section-kicker">'],
        ['IntroTitle','Giữ bối cảnh rõ ràng trước khi bất kỳ engine nào được cấp riêng.','<h2>'],
        ['IntroBody','Soạn thread, context card, prompt và quyết định bằng signed Web account. Mọi nội dung là private authoring, không phải output AI.','<p>'],
        ['CountTotal','Threads','<dd>'],['CountReview','Đang review','<dd>'],['CountReady','Sẵn sàng handoff','<dd>']
      ])s=replace(s,'chatRootUi'+key,before,re(tag));return s;
    });
    section('<section class="portal-card portal-card-pad portal-chat-workspace-create">',s=>{
      for(const [key,before,tag]of [
        ['CreateKicker','New conversation','<span class="portal-section-kicker">'],
        ['CreateTitle','Tạo thread riêng tư','<h2 class="portal-card-title">'],
        ['CreateSubtitle','Server kiểm tra session, CSRF, owner reference, idempotency và revision. Lưu thread không gọi AI hoặc trừ Xu.','<p class="portal-card-subtitle">'],
        ['CreateSafetyHint','Không nhập URL/path/blob, secret, OTP/CVV, payment reference, Bot/provider/job handle.','<span class="portal-form-note">'],
        ['CreateSubmit','Tạo thread','<button class="portal-button portal-button--primary" type="submit"[^>]*>']
      ])s=replace(s,'chatRootUi'+key,before,key==='CreateSubmit'?tag:re(tag));return s;
    });
    section('<section class="portal-card portal-card-pad"><div class="portal-card-header">',s=>{
      for(const [key,before,tag]of [
        ['LibraryKicker','Conversation library','<span class="portal-section-kicker">'],
        ['LibraryTitle','Threads của bạn','<h2 class="portal-card-title">'],
        ['LibrarySubtitle','Danh sách chỉ có metadata/excerpt thuộc signed Web account. Tìm, lọc hoặc chuyển trang để mở mọi thread trong giới hạn lưu trữ của account.','<p class="portal-card-subtitle">'],
        ['LibraryRefresh','Làm mới','<button[^>]+data-portal-action="chat-workspace-refresh"[^>]*>'],
        ['LibraryFilterHint','Tìm kiếm không lưu vào browser, không nhận URL/path/secret hoặc handle external.','<span class="portal-form-note">'],
        ['LibraryApply','Áp dụng bộ lọc','<button class="portal-button portal-button--quiet" type="submit"[^>]*>']
      ])s=replace(s,'chatRootUi'+key,before,/Refresh|Apply/.test(key)?tag:re(tag));
      const start=s.indexOf('<form class="portal-form portal-chat-workspace-filters"'),end=s.indexOf('</form>',start);
      if(start>=0&&end>start){
        const original=s.slice(start,end+7);let form=original;
        for(const [key,before]of [['State','Trạng thái'],['Search','Tìm trong thread']])form=replace(form,'chatFilterUi'+key,before,'<label\\b[^>]*>');
        form=form.replace('placeholder="'+esc(messages.chatFilterUiSearchPlaceholder)+'"','placeholder="Tìm theo tên, mục tiêu hoặc tag"');
        for(const [key,value,before]of [['All','all','Tất cả trạng thái'],['Draft','draft','Bản nháp'],['Review','review','Đang self-review'],['Ready','ready','Sẵn sàng handoff'],['Archived','archived','Đã archive']])form=replace(form,'chatFilterUi'+key,before,'<option value="'+value+'"[^>]*>');
        s=s.replace(original,form);
      }
      if(s.includes('<div class="portal-empty"')){
        s=replace(s,'chatRootUiEmptyTitle','Chưa có hội thoại','<h3>');
        s=replace(s,'chatRootUiEmptyBody','Tạo thread đầu tiên để gom mục tiêu, context và các ghi chú do bạn tự soạn. Workspace không tạo câu trả lời AI thay bạn.','<p>');
      }
      return s;
    });
  }
  if(html.startsWith('<article class="portal-page portal-document-hub">')){
    for(const [key,before,tag]of [
      ['LoadingHeading','Đang xác minh lịch sử tài liệu private','<h2>'],
      ['LoadingBody','Web Workspace đang tải metadata Document Operations thuộc signed account hiện tại. Không hiển thị route trước, PWA cache, Asset Vault hay danh sách Bot trong khi chờ dữ liệu owner-scoped.','<p>'],
      ['FailedHeading','Chưa thể tải lịch sử tài liệu private','<h2>'],
      ['FailedBody','Projection owner-scoped chưa trả dữ liệu an toàn. Web đã xóa dữ liệu cũ và không thay bằng Asset Vault, Bot, provider, file preview hay URL công khai.','<p>'],
      ['RetryButton','Thử lại dữ liệu private','<button[^>]+data-portal-action="document-operation-refresh"[^>]*>']
    ])html=replace(html,'docReadUi'+key,before,key==='RetryButton'?tag:re(tag));
  }
  return html;
}
