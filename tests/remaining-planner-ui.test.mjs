import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const rows=JSON.parse(fs.readFileSync(new URL('./fixtures/remaining-planner-composer-samples.json',import.meta.url),'utf8'));
const catalog={vi:'7667d86df605f48206d6520f7e205ff2587adaae712a162fdc31e7be1bd61fcf',en:'be08f1c6a87c32093eceddc007d6502b578616331277e2b620cbd0e3a9d2ad13',zh:'5450fabd9be5f77c51764b35a53645c6e15c76955b974f242446d650028bb85d'};
const escape=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const decode=s=>String(s).replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
const strings=v=>typeof v==='string'?[v]:v&&typeof v==='object'?Object.values(v).flatMap(strings):[];
const patterns={vi:/\b(?:brief|media|studio|prompt|style|action|audio|scene|shots?|plan|planning|review|runtime|consent|asset|bot|web|native|provider|engine|concept|creative|direction|workflow|claim|identity|lock|owner|server|browser|off|template|preview|render|upload|output|publish|delivery|metadata|scope|cue|camera|voice|host|social|online|demo|beta|placeholder|URL|token|OTP|CSRF|CTA|UGC|ASMR|SaaS|logo|piano)\b/gi,en:/[À-ỹ\u3400-\u9fff]/g,zh:/[À-ỹ]|\b(?:brief|media|studio|prompt|style|action|audio|scene|shots?|plan|planning|review|consent|asset|bot|web|provider|engine|concept|creative|direction|workflow|claim|identity|lock|owner|server|browser|off|template|preview|render|upload|output|publish|delivery|metadata|scope|cue|camera|voice|URL|token|OTP|CSRF|CTA|UGC|ASMR|SaaS)\b/gi};
function rawFor(row,mode){
 const source=structuredClone(row.source),result=structuredClone(row.result),receipt=structuredClone(row.receipt);
 if(mode==='mismatch')source[row.route==='script-to-screen-planner'?'brief':row.route==='cinematic-concept'?'product':'topic']='Different current customer input';
 if(mode==='unsafeResult')result.provider_called=true;
 if(mode==='unsafeReceipt')receipt.provider_called=true;
 const enabled=mode!=='guarded';
 return{capabilities:{[row.route+'-compose']:enabled,[row.route+'-save-plan']:enabled&&mode!=='noSave','video-plan-create':enabled},[row.key+'Enabled']:enabled,[row.key+'Result']:['empty','guarded'].includes(mode)?{}:result,[row.key+'SaveSource']:['empty','guarded'].includes(mode)?{}:source,[row.key+'SaveReceipt']:['saved','unsafeReceipt'].includes(mode)?receipt:{}};
}
for(const locale of['vi','en','zh'])for(const row of rows)for(const mode of['empty','guarded','result','saved','mismatch','noSave','unsafeResult','unsafeReceipt']){
 const raw=rawFor(row,mode),snapshot=JSON.stringify(raw),view=renderChild(locale,'/video-studio/'+row.route,raw);
 test(locale+':'+row.route+':'+mode+' fixed UI uses only its chosen language',()=>{
  let html=view.html;
  for(const value of[...new Set([...strings(raw[row.key+'Result']),...strings(raw[row.key+'SaveSource'])].filter(s=>s.length>=4))].sort((a,b)=>b.length-a.length))html=html.split(escape(value)).join(' ');
  for(const value of[...new Set([...strings(raw[row.key+'Result']),...strings(raw[row.key+'SaveSource'])].filter(s=>s.length>0&&s.length<4))]){
   const escaped=escape(value).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
   html=html.replace(new RegExp('(?<![\\p{L}\\p{N}_])'+escaped+'(?![\\p{L}\\p{N}_])','gu'),' ');
  }
  html=html.replace(/<code\b[^>]*>[\s\S]*?<\/code>/g,'').replace(/<svg\b[\s\S]*?<\/svg>/g,'');
  const attrs=[...html.matchAll(/\b(?:placeholder|aria-label|title|data-portal-confirm)="([^"]*)"/g)].map(m=>m[1]).join(' ');
  const text=(decode(html.replace(/<[^>]+>/g,' '))+' '+decode(attrs)).replace(/Meta AI/g,'');
  assert.deepEqual([...new Set((text.match(patterns[locale])||[]).map(s=>s.toLowerCase()))],[]);
  assert.doesNotMatch(text,/videoNextFieldsUi\.|remainingPlannerUi\.|\{(?:count|index|revision|number)\}/,'no unresolved key/parameter is shown as content');
 });
 test(locale+':'+row.route+':'+mode+' retains real controls, data and save safety',()=>{
  assert.equal(JSON.stringify(raw),snapshot,'no customer/server mutation');
  const form=view.html.match(new RegExp('<form\\b[^>]*data-portal-action="'+row.route+'-compose"[\\s\\S]*?<\\/form>'))?.[0];
  assert.ok(form);assert.equal([...form.matchAll(/\bname="[^"]*"/g)].length,row.route==='script-to-screen-planner'?16:10);
  assert.ok(form.includes('data-portal-no-transient'));
  const savedHref='href="/video-studio/'+row.receipt.plan.id+'"',save=[...view.html.matchAll(/<button\b[^>]*>/g)].find(m=>m[0].includes('data-portal-action="'+row.route+'-save-plan"'));
  if(['empty','guarded','unsafeResult'].includes(mode))assert.ok(!view.html.includes(escape(row.result[row.resultKey].title)));
  else assert.ok(view.html.includes(escape(row.result[row.resultKey].title)),'accepted server result remains visible');
  if(mode==='saved'){assert.ok(view.html.includes(savedHref));assert.equal(!!save,false,'terminal receipt cannot recreate save');}
  if(['result','noSave'].includes(mode)){assert.ok(save,'matching source keeps explicit save control');assert.equal(/\sdisabled(?:\s|>)/.test(save[0]),mode==='noSave');}
  if(['mismatch','unsafeResult'].includes(mode))assert.equal(!!save,false);
  if(mode==='unsafeReceipt')assert.ok(!view.html.includes(savedHref));
  assert.ok(!view.html.includes('class="portal-video-prompt-planner-layout"')&&!view.html.includes('class="portal-cinematic-concept-layout"')&&!view.html.includes('class="portal-storyboard-composer-layout"'));
  assert.ok(!view.html.includes('portal-video-prompt-planner-intro')&&!view.html.includes('portal-cinematic-concept-intro')&&!view.html.includes('portal-storyboard-composer-intro'));
 });
}
for(const locale of['vi','en','zh']){
 const messages=renderChild(locale,'/studio',{}).messages[locale];
 test(locale+': all 9951 previously released catalog entries remain unchanged',()=>{
  const entries=Object.entries(messages).filter(([k])=>!k.startsWith('videoNextFieldsUi.')&&!k.startsWith('remainingPlannerUi.')&&!k.startsWith('lastTwoPlannerUi.')).sort(([a],[b])=>a.localeCompare(b));
  assert.equal(entries.length,9951);assert.equal(crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex'),catalog[locale]);
 });
 test(locale+': new scoped catalog has every actual worker field/result key',()=>assert.equal(Object.keys(messages).filter(k=>k.startsWith('videoNextFieldsUi.')||k.startsWith('remainingPlannerUi.')).length,398));
}
