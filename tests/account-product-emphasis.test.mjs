import assert from 'node:assert/strict';
import test from 'node:test';
import './membership-static-clutter.test.mjs';
import {renderChild} from './helpers/publishing-child-render.mjs';
const wallets={missing:undefined,unlinked:{status_name:'unlinked'},zero:{balance_xu:0,total_spent_xu:0,is_vip:false,plan:{plan_name:'CUSTOMER_PLAN'}},standard:{balance_xu:1250,total_spent_xu:50,is_vip:false,plan:{plan_name:'CUSTOMER_PLAN'}},vip:{balance_xu:2500,total_spent_xu:50,is_vip:true,plan:{plan_name:'CUSTOMER_VIP_PLAN'}}};
function card(result,locale){const title=result.messages[locale]['accountCenter.membership.title'],index=result.html.indexOf(title),a=result.html.lastIndexOf('<section',index),b=result.html.indexOf('</section>',index)+10;assert.ok(a>=0&&b>a,'Actualmembershipsectionfound');return result.html.slice(a,b);}
for(const locale of ['vi','en','zh'])test(locale+': account keeps security/profile actions without implementation-only paragraphs',()=>{
 const result=renderChild(locale,'/account',{});
 for(const key of ['overviewBody','sessionSecurityBody']){
  const text=result.messages[locale]['accountCenter.profile.'+key];assert.ok(text);assert.equal(result.html.includes(text),false,key+'notshownasfiller');
 }
 for(const action of ['update-profile','auth-logout','select-avatar-preset'])assert.ok(result.html.includes('data-portal-action="'+action+'"'));
 assert.ok(result.html.includes('href="/account/security"'));
});
for(const locale of ['vi','en','zh'])for(const [state,wallet]of Object.entries(wallets)){
 const raw={wallet},snapshot=JSON.stringify(raw),result=renderChild(locale,'/account',raw),html=card(result,locale),messages=result.messages[locale];
 test(locale+':'+state+': tier is an explicit second line, no vague or duplicate verification filler',()=>{
  assert.match(html,/<h2\b[^>]*>[\s\S]*?<span class="portal-membership-tier">[\s\S]*?<\/span><\/h2>/);
  for(const key of ['unavailable','canonicalVerified','verifiedBody','appliedBody']){const text=messages['accountCenter.membership.'+key];if(text)assert.equal(html.includes(text),false,key+'removedonlyfrommembershipcard');}
  assert.equal(html.includes(messages['accountCenter.membership.benefitLabel']+':'),false,'Tiernotduplicatedasbenefit');
  assert.ok(html.includes(state==='vip'?messages['accountCenter.membership.tierVip']:messages['accountCenter.membership.tierStandard']));
 });
 test(locale+':'+state+': missing balance has no empty box, valid zero and custom package stay truthful',()=>{
  const known=wallet&&Number.isSafeInteger(wallet.balance_xu),balanceLabel=messages['accountCenter.membership.balanceLabel'];
  assert.equal(html.includes(balanceLabel),Boolean(known));
  if(known){assert.ok(html.includes(wallet.balance_xu.toLocaleString('vi-VN')+' Xu'));assert.ok(html.includes(wallet.plan.plan_name));}
  assert.ok(html.includes('href="/pricing"'));assert.ok(html.includes('href="/wallet/topup"'));
  assert.equal(JSON.stringify(raw),snapshot);
  if(known)assert.equal(JSON.stringify(result.context.wallet),JSON.stringify(wallet));
 });
}
