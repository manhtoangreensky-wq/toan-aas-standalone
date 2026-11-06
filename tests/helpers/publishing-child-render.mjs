import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const portal=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8');
const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');
export const strategyId='11111111-1111-4111-8111-111111111111';
export function customerProfile(state='active'){
  return {id:strategyId,revision:2,state,channel_name:'CUSTOMER_CHANNEL',platform:'tiktok',channel_url:'https://example.invalid/customer',niche:'CUSTOMER_NICHE',target_audience:'CUSTOMER_AUDIENCE',content_style:'CUSTOMER_STYLE',tone:'CUSTOMER_TONE',language:'en',allowed_topics:['CUSTOMER_TOPIC'],blocked_topics:['CUSTOMER_BLOCK'],brand_keywords:['CUSTOMER_BRAND'],cta_default:'CUSTOMER_CTA',affiliate_allowed:true,product_categories:['CUSTOMER_PRODUCT'],posting_frequency:'CUSTOMER_FREQUENCY',preferred_aspect_ratio:'9:16',preferred_duration_seconds:18,primary_goal:'follow',notes:'CUSTOMER_NOTE'};
}
export function strategyContext(state='library'){
  const profile=customerProfile(state==='archived'?'archived':'active');
  const capabilities=Object.fromEntries(['view','create','filter','update','archive','restore','preview'].map(a=>['channel-strategy-'+a,true]));
  if(state==='guarded')capabilities['channel-strategy-view']=false;
  return {capabilities,channelStrategyEnabled:true,channelStrategyReadState:'ready',channelStrategySummary:{active:1,archived:0,total:1},channelStrategyProfiles:state==='empty'?[]:[profile],channelStrategyListing:{filters:{q:'',state:'all'},pagination:{offset:0,has_more:true,next_offset:20,previous_offset:null}},channelStrategyProfileDetail:state==='missing'?{}:{profile,versions:[{...profile,revision:1}],events:['profile_created','profile_updated','profile_archived','profile_restored','strategy_previewed','unknown_event'].map(action=>({action,revision:2,created_at:'2026-11-01T00:00:00Z'}))},channelStrategyPreview:{strategy:{title:'CUSTOMER_PREVIEW',summary:'CUSTOMER_SUMMARY',content_pillars:[],guardrails:[],review_before_use:[],next_workflows:[]}}};
}
export function publishReceipt(){
  const names=['input_persisted','provider_called','bot_called','job_created','wallet_mutated','payment_started','asset_saved','media_output_created','publish_action_created','delivery_created','fact_checked','rights_verified'];
  return {execution:'web_native_publish_review_text_only',...Object.fromEntries(names.map(n=>[n,false])),package:{title:'CUSTOMER_TITLE',caption:'CUSTOMER_CAPTION',hashtags:['#CUSTOMER_TAG'],cta:'CUSTOMER_CTA',source_prompt:'CUSTOMER_PROMPT',review_checklist:['CUSTOMER_CHECK_1','CUSTOMER_CHECK_2','CUSTOMER_CHECK_3','CUSTOMER_CHECK_4'],copy_instruction:'CUSTOMER_COPY'}};
}
export function calendarContext(state='ready'){
  const ready=state==='ready';
  const items=ready?Array.from({length:4},(_,i)=>({id:`22222222-2222-4222-8222-22222222222${i}`,title:`CUSTOMER_CALENDAR_${i}`,platform:'facebook',objective:'content',approval_status:'scheduled',scheduled_for:`2026-11-06T${String(10+i).padStart(2,'0')}:00`,updated_at:'2026-11-01T00:00:00Z'})):[];
  return {capabilities:{'campaign-calendar-view':state!=='guarded','campaign-calendar-refresh':state!=='guarded'},campaignCalendarReadState:['loading','failed','guarded'].includes(state)?state:'read_only',campaignCalendar:{month:'2026-11',filters:{status:'all',platform:'all'},items,summary:{total:ready?6:0,returned:items.length,limit:200,has_more:ready}}};
}
export function plain(html){
  return String(html).replace(/<svg\b[\s\S]*?<\/svg>/g,' ').replace(/<[^>]+>/g,' ').replace(/&(?:amp|quot|lt|gt|#39);/g,' ').replace(/\s+/g,' ').trim();
}
export function renderChild(locale,route,raw={}){
  const noop=()=>{};
  const document={readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],getElementById:()=>null,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
  const window={document,navigator:{language:locale,userAgent:'Publishing child locale QA'},location:{pathname:route,search:'',href:'https://unit.invalid'+route,origin:'https://unit.invalid'},addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null,setItem:noop}};
  const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout:noop,clearTimeout:noop,fetch:()=>{throw Error('Network forbidden in locale renderer test');}});
  vm.runInContext(i18n,sandbox);
  const anchor='  window.TOANAASPortal = Object.freeze({';
  assert.ok(portal.includes(anchor));
  vm.runInContext(portal.replace(anchor,'  window.__childLocale={renderPage,normalizeBootstrap,documentTitle,channelStrategyFields,channelStrategyProfileValues,validChannelStrategyRevision,normalizePublishReviewPackResult,customerMobileNavGroupForPath};\n'+anchor),sandbox);
  window.TOANAASI18n.setLocale(locale,{emit:false});
  const context=window.__childLocale.normalizeBootstrap({path:route,interfaceLocale:locale,profile:{locale,displayName:'QA'},session:{authenticated:true,csrfToken:'synthetic-local-only'},...raw});
  const snapshot=JSON.stringify(raw);
  const page=window.TOANAASPortal.resolvePage(route);
  const html=window.__childLocale.renderPage(page,context);
  assert.equal(JSON.stringify(raw),snapshot,'render must not translate or mutate raw records');
  const attributes=[...html.matchAll(/\b(?:placeholder|aria-label|title|data-portal-confirm)="([^"]*)"/g)].map(m=>m[1]).join(' ');
  const fields=route.startsWith('/content/channel-strategy')?window.__childLocale.channelStrategyFields():[];
  return {html,text:plain(html),attributes,fields,title:window.__childLocale.documentTitle(page,context),context,messages:window.TOANAASI18n.messages,validateStrategyRevision:window.__childLocale.validChannelStrategyRevision,normalizeReviewReceipt:window.__childLocale.normalizePublishReviewPackResult,mobileGroupForPath:window.__childLocale.customerMobileNavGroupForPath};
}
