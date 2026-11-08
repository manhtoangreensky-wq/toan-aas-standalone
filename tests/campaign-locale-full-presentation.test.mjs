import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const id='33333333-3333-4333-8333-333333333333';
const routes=['/campaigns','/campaigns/new',`/campaigns/${id}`,'/approvals'];
const expected={
  vi:['Trung tâm kế hoạch','Kế hoạch mới','Chi tiết kế hoạch','Hàng tự rà soát'],
  en:['Campaign Planner','New campaign','Campaign details','Self-review queue'],
  zh:['活动运营看板','新建活动','活动详情','自我审核队列']
};
const genericVi=/\b(?:Campaign|Planner|Self-review|Queue|brief|provider|metadata|signed|owner-scoped|Web-owned|publish|output|payment|server|workspace|workflow|provider)\b/i;
const ownerTitle='OWNER_TITLE Campaign workflow Facebook';
const ownerNote='OWNER_NOTE server provider';

function context(route){
  const plan={id,title:ownerTitle,destination_url:'https://example.com/owner',platform:'facebook',objective:'traffic',scheduled_for:'',approval_status:'review',review_note:ownerNote,revision:1,created_at:'2026-11-07T00:00:00Z',updated_at:'2026-11-07T00:00:00Z'};
  return {account:{id:'11111111-1111-4111-8111-111111111111'},session:{authenticated:true,csrfReady:true,csrfToken:'synthetic'},capabilities:{'campaigns-refresh':true,'campaign-create':true,'campaign-update':true,'campaign-update-status':true},campaignPlans:[plan],campaignPlanDetail:plan,campaignPlannerReadState:'ready',pageStates:{[route]:'ready'}};
}

for(const locale of ['vi','en','zh']) for(const [index,route] of routes.entries()) test(`${locale} ${route} fixed Campaign surface is localized and preserves owner data`,()=>{
  const rendered=renderChild(locale,route,context(route));
  assert.match(rendered.title,new RegExp(expected[locale][index].replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
  if(route==='/campaigns/new') {
    assert.ok(!rendered.text.includes(ownerTitle), 'new form must not show an unrelated existing campaign');
    assert.ok(!rendered.text.includes(ownerNote), 'new form must not show an unrelated existing review note');
  } else {
    assert.ok(rendered.text.includes(ownerTitle), 'existing campaign title must remain unchanged');
    if(route===`/campaigns/${id}`) assert.ok(rendered.text.includes(ownerNote), 'detail review note must remain unchanged');
  }
  const fixedText=rendered.text.replaceAll(ownerTitle,'').replaceAll(ownerNote,'');
  if(locale==='vi') assert.doesNotMatch(fixedText,genericVi,fixedText.slice(0,1000));
  if(route==='/campaigns/new') {
    assert.match(rendered.html,/data-portal-action="campaign-create"/);
    for(const field of ['title','destination_url','platform','objective','scheduled_for']) assert.match(rendered.html,new RegExp(`name="${field}"`));
  }
  if(route==='/approvals') assert.match(rendered.html,/data-portal-action="campaign-update-status"/);
});
