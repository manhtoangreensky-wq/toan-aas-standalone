import assert from 'node:assert/strict';
import test from 'node:test';
import {calendarActions,calendarActionRuntime} from './helpers/calendar-action-runtime.mjs';
const expected={
 vi:{success:['Đã áp dụng bộ lọc lịch.','Đã chuyển tháng của lịch.','Đã làm mới lịch.'],failed:'Không thể tải lịch. Hãy làm mới trang.',route:'Chỉ thực hiện thao tác này trên trang Lịch nội dung.',view:'Phiên hiện tại chưa có quyền xem lịch.',refresh:'Phiên hiện tại chưa có quyền làm mới lịch.',unconfirmed:'Yêu cầu chưa được xác nhận.'},
 en:{success:['Calendar filters applied.','Calendar month changed.','Calendar refreshed.'],failed:'The calendar could not be loaded. Refresh the page.',route:'Use this action on the Content calendar page.',view:'This session does not have calendar access.',refresh:'This session cannot refresh the calendar.',unconfirmed:'The request was not confirmed.'},
 zh:{success:['已应用日历筛选条件。','已切换日历月份。','已刷新日历。'],failed:'无法加载日历。请刷新页面。',route:'请在内容日历页面执行此操作。',view:'当前会话无权查看日历。',refresh:'当前会话无权刷新日历。',unconfirmed:'请求尚未得到确认。'}
};
for(const locale of ['vi','en','zh']){
 for(const [index,action] of calendarActions.entries()){
  test(`${locale}: ${action} success feedback follows the interface language`,async()=>{
   const h=calendarActionRuntime(locale,action),task=h.run();assert.equal(h.pending.length,1);h.settle(0);await task;
   assert.equal(h.state.campaignCalendarReadState,'read_only');assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,expected[locale].success[index]);
  });
  test(`${locale}: ${action} failed read is localized and never announced as success`,async()=>{
   const h=calendarActionRuntime(locale,action),task=h.run();h.settle(0,'error');await task;
   assert.equal(h.state.campaignCalendarReadState,'failed');assert.equal(h.state.campaignCalendar.items.length,0);assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].getAttribute('role'),'alert');assert.equal(h.toasts[0].textContent,expected[locale].failed);
  });
 }
 for(const reason of ['route','view','refresh'])test(`${locale}: Calendar ${reason} entry feedback is localized without a request`,async()=>{
  const h=calendarActionRuntime(locale,'campaign-calendar-refresh');
  if(reason==='route')h.replace({...h.state,path:'/projects'},{epoch:false});
  if(reason==='view')h.state.capabilities['campaign-calendar-view']=false;
  if(reason==='refresh')h.state.capabilities['campaign-calendar-refresh']=false;
  await h.run();assert.equal(h.pending.length,0);assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,expected[locale][reason]);
 });
 for(const message of ['PRIVATE_NOTICE_317 — keep the original text.','constructor','toString','__proto__'])test(`${locale}: unknown Calendar preparation error ${message} retains its content`,async()=>{
  const h=calendarActionRuntime(locale,'campaign-calendar-filter'),fields={status:'all',platform:'all'};
  Object.defineProperty(fields,'month',{get(){throw new Error(message);}});
  await h.run(fields);assert.equal(h.pending.length,0);assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,message);
 });
 test(`${locale}: an empty preparation error uses the localized existing generic fallback`,async()=>{
  const h=calendarActionRuntime(locale,'campaign-calendar-filter'),fields={};Object.defineProperty(fields,'month',{get(){throw new Error('');}});
  await h.run(fields);assert.equal(h.pending.length,0);assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,expected[locale].unconfirmed);
 });
}
