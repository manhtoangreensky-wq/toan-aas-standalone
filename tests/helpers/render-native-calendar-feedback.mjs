import assert from 'node:assert/strict';
import {calendarActions,calendarActionRuntime} from './calendar-action-runtime.mjs';
let input='';for await(const chunk of process.stdin)input+=chunk;
const envelopes=JSON.parse(input),receiptOnly=process.argv.includes('--receipt-only');
const expected={vi:['Đã áp dụng bộ lọc lịch.','Đã chuyển tháng của lịch.','Đã làm mới lịch.'],en:['Calendar filters applied.','Calendar month changed.','Calendar refreshed.'],zh:['已应用日历筛选条件。','已切换日历月份。','已刷新日历。']};
let completed=0;
for(const locale of ['vi','en','zh'])for(const [index,action]of calendarActions.entries()){
 const envelope=envelopes[action];assert.equal(envelope.ok,true);assert.equal(envelope.status,'read_only');
 const h=calendarActionRuntime(locale,action),task=h.run();assert.equal(h.pending.length,1);
 h.pending[0].resolve({ok:true,status:200,json:async()=>envelope});await task;
 assert.equal(h.state.campaignCalendarReadState,'read_only');assert.deepEqual(JSON.parse(JSON.stringify(h.state.campaignCalendar)),envelope.data);
 assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].className,'portal-toast');assert.equal(h.button.disabled,false);
 if(!receiptOnly)assert.equal(h.toasts[0].textContent,expected[locale][index]);completed++;
}
console.log((receiptOnly?'NATIVE_CALENDAR_API_TO_INTEGRATION_CONTROLS=':'NATIVE_CALENDAR_API_TO_LOCALIZED_FEEDBACK=')+completed+'/9; projection retained; no external network');
