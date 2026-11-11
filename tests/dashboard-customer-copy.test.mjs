import assert from 'node:assert/strict';
import test from 'node:test';
import {renderPlainLanguage,sectionWith} from './helpers/account-plain-language-render.mjs';
const labels={vi:{standard:'Tài khoản ứng dụng',telegram:'Telegram',oauth_only:'Đăng nhập qua tài khoản liên kết'},en:{standard:'App account',telegram:'Telegram',oauth_only:'Linked-account sign-in'},zh:{standard:'应用账户',telegram:'Telegram',oauth_only:'关联账户登录'}};
const wallet={balance_xu:0,total_spent_xu:0,is_vip:false,plan:{plan_name:'CUSTOMER_PLAN',plan_status:'active'}};
const escape=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
for(const locale of ['vi','en','zh']){
 for(const route of ['/dashboard','/membership','/pricing'])for(const code of ['standard','telegram','oauth_only','CUSTOMER_TYPE <img onerror=alert(1)>'])test(`${locale}:${route}:${code}: account type is a label, never a tier or new authority`,()=>{
  const raw={profile:{accountType:code,displayName:'CUSTOMER_NAME',locale},wallet:structuredClone(wallet)},snapshot=JSON.stringify(raw);
  const {html,context}=renderPlainLanguage(locale,route,raw);
  const expected=labels[locale][code]||code;
  assert.ok(html.includes(escape(expected)),'Actual account-type consumer shows localized known type/escaped unknown');
  if(labels[locale][code])assert.doesNotMatch(html,new RegExp('>\\s*'+code+'\\s*<'));
  assert.equal(JSON.stringify(raw),snapshot);assert.equal(context.profile.accountType,code);
  assert.equal(context.wallet.balance_xu,0);assert.equal(context.wallet.plan.plan_name,'CUSTOMER_PLAN');
 });
 for(const state of ['loading','failed','guarded','ready'])test(`${locale}:${state}: Dashboard removes repeated headers and preserves real read states`,()=>{
  const raw={dashboardReadState:state,workspaceDraftReadState:state,projectCenterReadState:state,workspaceDrafts:[],projects:[],capabilities:{'dashboard-refresh':true}};
  const {html,messages}=renderPlainLanguage(locale,'/dashboard',raw);
  assert.equal(html.includes('<p class="portal-card-subtitle">'+messages['dashboard.drafts.body']+'</p>'),false);
  assert.equal(html.includes('<p class="portal-card-subtitle">'+messages['dashboard.projects.body']+'</p>'),false);
  const drafts=sectionWith(html,messages['dashboard.drafts.title']),projects=sectionWith(html,messages['dashboard.projects.title']);
  const technical=/canonical|owner-scoped|signed account|projection|server|browser|nguồn chuẩn|quyền chủ sở hữu|kết quả giả|siêu dữ liệu|元数据|权威数据|所有者权限/i;
  for(const area of [drafts,projects])assert.doesNotMatch(area.replace(/<[^>]+>/g,' '),technical);
  assert.match(html,new RegExp('data-state="'+state+'"'));
  if(state==='failed'){assert.ok(html.includes(messages['dashboard.canonical.failedBody']));assert.match(html,/data-portal-action="dashboard-refresh"/);}
  if(state==='loading')assert.match(html,/aria-busy="true"/);
  if(state==='ready'){assert.ok(drafts.includes(messages['dashboard.drafts.emptyBody']));assert.ok(projects.includes(messages['dashboard.projects.emptyBody']));}
  if(state==='guarded'||state==='failed')assert.ok(drafts.includes(messages['dashboard.drafts.unavailableBody']));
 });
 test(locale+': loading/failed/ready account descriptions are plain but never hide actionable errors',()=>{
  for(const state of ['loading','failed','ready']){
   const {html,messages}=renderPlainLanguage(locale,'/dashboard',{dashboardReadState:state,capabilities:{'dashboard-refresh':true}});
   const value=messages['dashboard.canonical.'+(state==='failed'?'failedBody':state==='loading'?'loadingBody':'readyBody')];
   assert.ok(html.includes(value));assert.doesNotMatch(value,/canonical|Core Bridge|signed|server|browser|dữ liệu chuẩn|máy chủ|trình duyệt|nhà cung cấp|权威|签名会话|服务器|供应商/i);
  }
 });
}
