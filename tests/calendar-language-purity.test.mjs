import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild,calendarContext} from './helpers/publishing-child-render.mjs';

for(const locale of ['vi','en','zh']){
  for(const state of ['guarded','loading','failed','empty','ready']){
    test(`${locale}: calendar ${state} titles, notices, summary and overflow follow the interface language`,()=>{
      const r=renderChild(locale,'/calendar',calendarContext(state));
      assert.ok(r.title.includes({vi:'Lịch nội dung',en:'Content calendar',zh:'内容日历'}[locale]),r.title);
      if(locale==='vi')assert.doesNotMatch(r.text.replace(/\btrang web\b/gi,''),/\b(?:Web|owned|canonical|automation|Content Calendar|URL|provider)\b/i);
      else assert.doesNotMatch(r.text,/[À-ỹĐđ]/);
      if(locale==='zh')assert.doesNotMatch(r.text,/\b(?:Web|URL|Bot|Content Calendar)\b/i);
      assert.doesNotMatch(r.text,/\b0\s*\+0\b/);
      if(state==='ready'){
        assert.ok(r.text.includes({vi:'6 mốc phù hợp',en:'6 matching dates',zh:'6 个匹配日期'}[locale]));
        assert.doesNotMatch(r.text,/\b6\s*\+6\b/);
        assert.ok(r.text.includes({vi:'+1 mốc đã tải',en:'+1 loaded dates',zh:'+1 个已加载日期'}[locale]));
        for(let i=0;i<4;i++)assert.ok(r.text.includes(`CUSTOMER_CALENDAR_${i}`));
        assert.equal((r.html.match(/class="portal-calendar-event"/g)||[]).length,3);
        assert.equal((r.html.match(/class="portal-calendar-agenda-item"/g)||[]).length,4);
      }
    });
  }
  test(`${locale}: calendar keeps month navigation, controls and owner-scoped record links unchanged`,()=>{
    const r=renderChild(locale,'/calendar',calendarContext());
    for(const value of ['2026-10','2026-12'])assert.ok(r.html.includes(`data-campaign-calendar-month="${value}"`));
    for(const name of ['month','status','platform'])assert.ok(r.html.includes(`name="${name}"`));
    assert.match(r.html,/value="2026-11" required/);
    assert.match(r.html,/data-portal-no-transient/);
    assert.match(r.html,/data-portal-action="campaign-calendar-filter"/);
    assert.match(r.html,/href="\/campaigns\/22222222-2222-4222-8222-222222222220"/);
  });
  test(`${locale}: missing calendar titles use a localized fallback in both grid and agenda`,()=>{
    const raw=calendarContext();raw.campaignCalendar.items[0].title='';
    const r=renderChild(locale,'/calendar',raw);
    const expected={vi:'Kế hoạch chưa đặt tên',en:'Untitled campaign',zh:'未命名活动'}[locale];
    assert.equal(r.text.split(expected).length-1,2,r.text);
    assert.equal(raw.campaignCalendar.items[0].title,'');
  });
  test(`${locale}: a customer title containing ordinary English or brand names is never translated`,()=>{
    const raw=calendarContext();raw.campaignCalendar.items[0].title='Customer Media Studio Facebook TikTok';
    const r=renderChild(locale,'/calendar',raw);
    assert.equal(r.text.split('Customer Media Studio Facebook TikTok').length-1,2);
    assert.equal(raw.campaignCalendar.items[0].title,'Customer Media Studio Facebook TikTok');
  });
}
