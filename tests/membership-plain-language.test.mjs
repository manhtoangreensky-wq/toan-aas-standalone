import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {membershipPlainLanguageHistoricalSnapshot} from './helpers/membership-plain-language-snapshot.mjs';
import {withoutMembershipStaticNotes} from './helpers/membership-static-notes.mjs';

// Catches fixed-copy leaks while preserving technical words in customer data,
// truthful missing information, real offers, controls, and every unrelated byte.
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BASE='1f48b08e753c6b91b1d9b0b7986e80589d413c00';
const HELPER=path.join(ROOT,'tests/helpers/publishing-child-render.mjs');
const {renderChild:renderCurrent}=await import(pathToFileURL(HELPER).href);
const baseSource=file=>execFileSync('git',['show',`${BASE}:${file}`],{cwd:ROOT,encoding:'utf8',maxBuffer:30*1024*1024});
const basePortal=baseSource('static/portal/portal.js'),baseI18n=baseSource('static/portal/portal-i18n.js');
let helper=fs.readFileSync(HELPER,'utf8');
for(const [old,replacement]of [
  ["const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",`const root=${JSON.stringify(ROOT)};`],
  ["const portal=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8');",`const portal=${JSON.stringify(basePortal)};`],
  ["const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');",`const i18n=${JSON.stringify(baseI18n)};`]
]){assert.equal(helper.split(old).length-1,1,'real helper loader must match once');helper=helper.replace(old,replacement);}
const {renderChild:renderBase}=await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'));
const keys=["billingCatalog.page.membership.description","billingCatalog.membership.defaultPlanName","billingCatalog.membership.defaultPlanStatus","billingCatalog.membership.current.description","billingCatalog.membership.label.canonicalCredit","billingCatalog.membership.empty.title","billingCatalog.membership.empty.body","billingCatalog.membership.principle.body","billingCatalog.membership.catalog.title","billingCatalog.membership.catalog.description","billingCatalog.membership.catalog.emptyTitle","billingCatalog.membership.catalog.emptyBody","billingCatalog.membership.action.packages","billingCatalog.membership.action.topup"];
assert.equal(keys.length,14);
const technical=/canonical|authority|metadata|signed[ -]?session|core[ -]?bridge|owner[ -]?scoped|\btier\b|\btrial\b|\breferral\b|\bfeature\b/i;
const escape=value=>String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const CUSTOM={plan:'CUSTOMER canonical metadata plan',status:'CUSTOMER authority signed-session status',month:'CUSTOMER metadata offer',monthNote:'CUSTOMER canonical signed-session benefit',bundle:'CUSTOMER authority bundle',bundleNote:'CUSTOMER Core Bridge referral note'};
const wallet=(balance,vip=false,plan={plan_name:CUSTOM.plan,plan_status:CUSTOM.status})=>({balance_xu:balance,total_spent_xu:0,is_vip:vip,plan});
const unavailable={packageCatalog:{available:false},pricingCatalog:{available:false}};
const fixtures={
  'missing-wallet':{...unavailable,wallet:null,walletReadState:'guarded'},
  'zero-partial-plan':{...unavailable,wallet:wallet(0,false,{}),walletReadState:'ready'},
  VIPnamed:{...unavailable,wallet:wallet(2500,true),walletReadState:'ready'},
  populatedapprovedcatalog:{wallet:wallet(1350),walletReadState:'ready',packageCatalog:{available:true,
    monthly:[{code:'synthetic_month',label:CUSTOM.month,note:CUSTOM.monthNote,manual:false}],
    combos:[{code:'synthetic_bundle',label:CUSTOM.bundle,note:CUSTOM.bundleNote,manual:true}]},
    pricingCatalog:{available:true,image_tiers:[],video_tiers:[],video_combos:[],public_sale_catalog:{available:true,approval_status:'owner_approved',catalog_version:'synthetic_membership_v1',items:[
      {code:'synthetic_month',family:'service',label:CUSTOM.month,sale_price_xu:425},
      {code:'synthetic_bundle',family:'service',label:CUSTOM.bundle,sale_price_xu:875}]}}}
};
const textNodes=html=>html.split(/(<[^>]*>)/g).filter((_,index)=>index%2===0).map(text=>text.trim()).filter(Boolean);
function banner(html){
  const match=/<div class="portal-callout portal-callout--info" style="margin-bottom:16px; padding:16px;[^>]*>/.exec(html);
  assert.ok(match,'retain the original useful pricing banner markup');let depth=0,end=-1;const tags=/<\/?div\b[^>]*>/g;tags.lastIndex=match.index;
  for(let tag;(tag=tags.exec(html));){depth+=tag[0].startsWith('</')?-1:1;if(depth===0){end=tags.lastIndex;break;}}
  assert.ok(end>match.index);const fragment=html.slice(match.index,end),nodes=textNodes(fragment).filter(text=>text!=='💡'&&text!=='.');
  assert.equal(nodes.length,4,'retain four real banner text nodes, not an empty/deleted banner');
  return{start:match.index,end,fragment,nodes};
}
function catalogLabels(html){
  const labels=[];const pattern=/(<article class="portal-module-card portal-billing-catalog-card">[\s\S]*?<span class="portal-module-card-footer"><span>[^<]*<\/span><span>)([^<]*)(<\/span><\/span><\/article>)/g;
  const normalized=html.replace(pattern,(_,before,label,after)=>{labels.push(label.trim());return before+'__MEMBERSHIP_CATALOG_STATUS__'+after;});
  return{html:normalized,labels};
}
function finiteCopyParity(html,messages){
  html=withoutMembershipStaticNotes(html).html;
  // Later fallback-origin coverage checks the real locale; historical parity
  // accepts only these three reviewed family labels, never arbitrary text.
  html=html.replace(/(<span class="portal-billing-catalog-family">)(?:Gói dịch vụ|Service packages|服务套餐)(<\/span>)/g,'$1__MEMBERSHIP_FAMILY__$2');
  const b=banner(html);let index=0;
  const bannerHTML=b.fragment.split(/(<[^>]*>)/g).map((token,position)=>position%2===0&&b.nodes.includes(token.trim())?'__BANNER_'+index+++'__':token).join('');
  assert.equal(index,4);let result=html.slice(0,b.start)+bannerHTML+html.slice(b.end);
  const replacements=new Map(keys.flatMap((key,index)=>[[escape(messages[key]).trim(),'__FIXED_KEY_'+index+'__'],[messages[key].trim(),'__FIXED_KEY_'+index+'__']]));
  result=result.split(/(<[^>]*>)/g).map((token,position)=>position%2===0&&replacements.has(token.trim())?replacements.get(token.trim()):token).join('');
  return catalogLabels(result).html;
}
const controls=html=>[...html.matchAll(/<(?:a|button|form|input|select|option|textarea)\b[^>]*>/g)].map(match=>match[0]);
function language(value,locale){
  if(locale==='vi')return /[À-ỹĐđ]/u.test(value)&&!/\p{Script=Han}/u.test(value);
  if(locale==='zh')return /\p{Script=Han}/u.test(value);
  return !/[À-ỹĐđ]/u.test(value)&&!/\p{Script=Han}/u.test(value)&&/[a-z]/i.test(value);
}
function assertData(result,state,raw){
  assert.ok(result.html.includes('portal-membership-page'));const m=result.messages[raw.profile.locale];
  for(const href of ['/pricing','/packages','/wallet/topup'])assert.ok(result.html.includes(`href="${href}"`),'real '+href+' action retained');
  if(state==='missing-wallet'){assert.equal(result.context.wallet,null);assert.ok(result.html.includes(escape(m['billingCatalog.membership.empty.title'])));}
  else{assert.equal(result.context.wallet.balance_xu,raw.wallet.balance_xu);assert.ok(result.html.includes(raw.wallet.balance_xu+' Xu'),'valid zero/balance stays visible');}
  if(state==='zero-partial-plan')for(const key of ['billingCatalog.membership.defaultPlanName','billingCatalog.membership.defaultPlanStatus'])assert.ok(result.html.includes(escape(m[key])),'missing default remains visible');
  if(state==='VIPnamed'||state==='populatedapprovedcatalog')for(const value of [CUSTOM.plan,CUSTOM.status])assert.ok(result.html.includes(escape(value)),'customer technical words preserved exactly');
  if(state==='populatedapprovedcatalog'){
    for(const value of [CUSTOM.month,CUSTOM.monthNote,CUSTOM.bundle,CUSTOM.bundleNote,'425 Xu','875 Xu'])assert.ok(result.html.includes(escape(value)),'real approved offer/value retained: '+value);
    assert.equal(catalogLabels(result.html).labels.length,2);
  }else assert.ok(result.html.includes(escape(m['billingCatalog.membership.catalog.emptyTitle'])),'real missing catalog remains visible');
}
for(const locale of ['vi','en','zh'])for(const [state,fixture]of Object.entries(fixtures))test(`${locale}/${state}: customer-language membership copy preserves exact real values and finite markup`,()=>{
  const raw={...structuredClone(fixture),profile:{locale,displayName:'SYNTHETIC_MEMBER',accountType:'telegram'},capabilities:{'wallet-view':true,'package-catalog-view':true}};
  const currentRaw=structuredClone(raw),baseRaw=structuredClone(raw),old=renderBase(locale,'/membership',baseRaw),current=renderCurrent(locale,'/membership',currentRaw);
  assert.deepEqual(currentRaw,raw);assert.deepEqual(baseRaw,raw);assert.equal(JSON.stringify(current.context),JSON.stringify(old.context),'normalization/data remain exact');
  assertData(old,state,raw);assertData(current,state,raw);
  const previous=old.messages[locale],messages=current.messages[locale];
  assert.deepEqual(controls(current.html),controls(old.html),'all actual control/href tags unchanged');
  assert.equal(finiteCopyParity(current.html,messages),finiteCopyParity(old.html,previous),'only fourteen finite fixed values, four banner nodes and membership catalog status may differ');
  const violations=keys.filter(key=>!messages[key]||technical.test(messages[key])||!language(messages[key],locale));
  assert.deepEqual(violations,[],'fixed membership copy must be idiomatic selected-language text without internal terminology');
  const b=banner(current.html);for(const value of b.nodes)assert.ok(language(value,locale),'banner node must follow '+locale+': '+value);
  assert.doesNotMatch(b.nodes.join(' '),/\/pricing/,'customer labels must not expose an internal route');
  for(const [index,value]of b.nodes.entries())assert.notEqual(value,banner(renderCurrent(locale==='vi'?'en':'vi','/membership',raw).html).nodes[index],'banner nodes must actually follow locale, not hardcoded Vietnamese');
  const introduced=Object.keys(messages).filter(key=>!Object.hasOwn(previous,key));assert.ok(introduced.length>=4,'localized banner must use real new locale entries');
  for(const key of introduced){assert.ok(language(messages[key],locale),key+' new copy follows locale');assert.equal(technical.test(messages[key]),false,key+' no internal fixed-copy jargon');
    if(state==='populatedapprovedcatalog')assert.ok(current.html.includes(escape(messages[key]))||current.html.includes(messages[key]),key+' new member-only label must actually render');}
  for(const value of b.nodes)assert.ok(introduced.some(key=>escape(messages[key]).trim()===value||messages[key].trim()===value),'each banner text is a real new localized value');
  assert.equal(messages['billingCatalog.catalog.statusCanonical'],previous['billingCatalog.catalog.statusCanonical'],'shared catalog label outside membership must not change');
  if(state==='populatedapprovedcatalog')for(const label of catalogLabels(current.html).labels){assert.equal(technical.test(label),false);assert.ok(language(label,locale));}
  if(state==='zero-partial-plan'){
    const missing=locale==='vi'?/chưa|chờ|đang|không.*(?:gói|thông tin)/i:locale==='en'?/not|no |wait|pending|loading|unavailable|unknown/i:/未|暂无|等待|加载|待|尚|无法/;
    for(const key of ['billingCatalog.membership.defaultPlanName','billingCatalog.membership.defaultPlanStatus'])assert.match(messages[key],missing,'missing information must not become an invented package');
  }
  assert.equal(withoutMembershipStaticNotes(current.html).count,0,'unconditional technical note list must not be rendered');
  const approvedEntries=keys.map(key=>[key,messages[key]]),snapshot=JSON.stringify(approvedEntries);
  assert.deepEqual(membershipPlainLanguageHistoricalSnapshot(approvedEntries,locale),keys.map(key=>[key,previous[key]]));
  assert.equal(JSON.stringify(approvedEntries),snapshot);
  for(const key of [...keys,...introduced])assert.throws(()=>membershipPlainLanguageHistoricalSnapshot([[key,'UNREVIEWED_MUTATION']],locale),/Unreviewed membership copy/);
  assert.deepEqual(membershipPlainLanguageHistoricalSnapshot([['unlisted.key','UNREVIEWED_MUTATION']],locale),[['unlisted.key','UNREVIEWED_MUTATION']]);
});
