import assert from 'node:assert/strict';
import test from 'node:test';
import {calendarActions,calendarActionContext,calendarActionRuntime,calendarWindow} from './helpers/calendar-action-runtime.mjs';
for(const action of calendarActions)test(`current ${action} accepts its isolated read response without a Bot bridge`,async()=>{
 const h=calendarActionRuntime('en',action),task=h.run();
 assert.equal(h.pending.length,1,'positive control must reach the actual action GET');
 assert.equal(h.networkLog[0].month,action==='campaign-calendar-month'?'2026-12':'2026-11');
 assert.equal(h.networkLog[0].status,action==='campaign-calendar-filter'?'draft':'all');
 assert.equal(h.button.disabled,true);h.settle(0);await task;
 assert.equal(h.state.campaignCalendarReadState,'read_only');assert.equal(h.state.campaignCalendar.items[0].title,'OWNER_CALENDAR_A');
 assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].className,'portal-toast');assert.equal(h.button.disabled,false);
});
for(const action of calendarActions)for(const change of ['route','session','account','logout','selection'])for(const kind of ['valid','error','guarded']){
 test(`${action}: a ${kind} read cannot affect feedback or controls after ${change} changes`,async()=>{
  const h=calendarActionRuntime('en',action),task=h.run();assert.equal(h.pending.length,1);
  const next=calendarActionContext(change==='account'?'B':'A');next.campaignCalendarReadState='guarded';
  if(change==='route')next.path='/projects';
  if(change==='logout'){next.account=null;next.session={authenticated:false};next.capabilities={};}
  if(change==='selection')next.campaignCalendar=calendarWindow('2027-01','NEW_SELECTION');
  h.replace(next,{epoch:['session','account','logout'].includes(change),disabled:true});
  const snapshot=JSON.stringify(h.state);h.settle(0,kind,'OLD');await task;
  assert.equal(JSON.stringify(h.state),snapshot,'stale window must not alter the current projection');
  assert.equal(h.toasts.length,0,'a stale read must not announce success or failure in the new context');
  assert.equal(h.button.disabled,true,'a stale read must not enable controls in the new context');
 });
}
for(const action of calendarActions)for(const kind of ['valid','error','guarded']){
 test(`${action}: an older ${kind} completion cannot end the newer pending action`,async()=>{
  const h=calendarActionRuntime('en',action),first=h.run(),second=h.run();assert.equal(h.pending.length,2);
  h.settle(0,kind,'OLD');await first;
  const oldEffects={toasts:h.toasts.length,disabled:h.button.disabled};
  h.settle(1,'valid','NEW');await second;
  assert.equal(oldEffects.toasts,0);assert.equal(oldEffects.disabled,true);
  assert.equal(h.state.campaignCalendar.items[0].title,'OWNER_CALENDAR_NEW');assert.equal(h.toasts.length,1);assert.equal(h.button.disabled,false);
 });
 test(`${action}: an older ${kind} completion after a newer success cannot replace its projection`,async()=>{
  const h=calendarActionRuntime('en',action),first=h.run(),second=h.run();assert.equal(h.pending.length,2);
  h.settle(1,'valid','NEW');await second;const snapshot=JSON.stringify(h.state),feedback=h.toasts[0].textContent;
  h.settle(0,kind,'OLD');await first;
  assert.equal(JSON.stringify(h.state),snapshot);assert.equal(h.toasts.length,1);assert.equal(h.toasts[0].textContent,feedback);assert.equal(h.button.disabled,false);
 });
}
