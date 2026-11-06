import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild,calendarContext} from './helpers/publishing-child-render.mjs';

const words={
 vi:{boundary:'Lịch không tạo hàng đợi đăng bài',undated:'Kế hoạch chưa có mốc lịch',loading:'Đang tải lịch',loadingBody:'Đang lấy các mốc trong tháng đã chọn.',failed:'Chưa thể tải lịch an toàn',guarded:'Chưa có quyền xem lịch',guardedBody:'Làm mới trang để cập nhật quyền truy cập lịch của tài khoản.',count:n=>`${n} mốc phù hợp`},
 en:{boundary:'Calendar does not create a publishing queue',undated:'Campaigns without dates',loading:'Loading calendar',loadingBody:'Retrieving dates for the selected month.',failed:'Calendar could not load safely',guarded:'Calendar access is unavailable',guardedBody:'Refresh the page to update calendar access for this account.',count:n=>`${n} matching dates`},
 zh:{boundary:'日历不会创建发布队列',undated:'没有日期的活动',loading:'正在加载日历',loadingBody:'正在获取所选月份的日期。',failed:'无法安全加载日历',guarded:'暂时无法访问日历',guardedBody:'请刷新页面以更新此账户的日历访问权限。',count:n=>`${n} 个匹配日期`}
};
for(const locale of ['vi','en','zh'])for(const state of ['guarded','loading','failed','empty','ready']){
 test(`${locale}: calendar ${state} prioritizes controls and real counts without tutorial panels`,()=>{
  const r=renderChild(locale,'/calendar',calendarContext(state));
  assert.ok(!r.text.includes(words[locale].boundary),'Static boundary tutorial must not displace calendar controls');
  assert.ok(!r.text.includes(words[locale].undated),'Do not imply undated records exist when the calendar API supplies none');
  for(const href of ['/campaigns','/approvals'])assert.ok(r.html.includes(`href="${href}"`));
  for(const name of ['month','status','platform'])assert.ok(r.html.includes(`name="${name}"`));
  const count=words[locale].count(state==='ready'?6:0);
  const markup=`<span class="portal-badge">${count}</span>`;
  if(['ready','empty'].includes(state))assert.ok(r.html.includes(markup),'Only a completed read may show its matching count');
  else assert.ok(!r.html.includes(markup),'Unknown loading/failed/guarded counts must not be presented as zero');
  if(state==='loading'){
    assert.ok(r.text.includes(words[locale].loading),'Retain the meaningful loading feedback');
    assert.ok(r.text.includes(words[locale].loadingBody),'Do not suggest that a pending read is an empty result');
  }
  if(state==='failed')assert.ok(r.text.includes(words[locale].failed),'A failed read is not an empty calendar');
  if(state==='guarded'){
    assert.ok(r.text.includes(words[locale].guarded),'A guarded read is not an empty calendar');
    assert.ok(r.text.includes(words[locale].guardedBody));
  }
  assert.equal((r.html.match(/class="portal-calendar-event"/g)||[]).length,state==='ready'?3:0);
  assert.equal((r.html.match(/class="portal-calendar-agenda-item"/g)||[]).length,state==='ready'?4:0);
 });
}
