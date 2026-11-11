import assert from 'node:assert/strict';
import {accountPlainLanguageHistoricalSnapshot} from './helpers/account-plain-language-snapshot.mjs';
import crypto from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';
const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/last-two-planner-results.json',import.meta.url),'utf8'));
const escape=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'),strings=v=>typeof v==='string'?[v]:v&&typeof v==='object'?Object.values(v).flatMap(strings):[];
const patterns={vi:/\b(?:brief|media|studio|prompt|style|action|audio|scene|shots?|plan|planning|review|runtime|consent|asset|bot|web|native|provider|engine|concept|creative|direction|workflow|claim|identity|lock|owner|server|browser|off|template|preview|render|upload|output|publish|delivery|metadata|scope|cue|camera|voice|host|social|online|demo|beta|placeholder|URL|token|OTP|CSRF|CTA)\b/gi,en:/[À-ỹ\u3400-\u9fff]/g,zh:/[À-ỹ]|\b(?:brief|media|studio|prompt|style|action|audio|scene|plan|review|asset|bot|web|provider|engine|direction|workflow|owner|server|browser|template|preview|render|upload|output|publish|delivery|metadata|camera|voice)\b/gi};
for(const locale of['vi','en','zh'])for(const f of fixture.rows)for(const mode of['empty','result','saved','mismatch','noSave','unsafeResult','unsafeReceipt']){
 const source=structuredClone(f.source),result=structuredClone(f.result),receipt=structuredClone(f.receipt);if(mode==='mismatch')source[f.part==='image'?'direction_id':'topic']=f.part==='image'?'22222222-2222-4222-8222-222222222222':'Changed current topic';if(mode==='unsafeResult')result.provider_called=true;if(mode==='unsafeReceipt')receipt.provider_called=true;
 const raw={capabilities:{[f.route+'-compose']:true,[f.route+'-save-plan']:mode!=='noSave','video-plan-create':true},[f.key+'Enabled']:true,[f.key+'ReadState']:'ready',[f.key+'References']:[f.result.planner.reference],[f.key+'Result']:mode==='empty'?{}:result,[f.key+'SaveSource']:mode==='empty'?{}:source,[f.key+'SaveReceipt']:['saved','unsafeReceipt'].includes(mode)?receipt:{}},snapshot=JSON.stringify(raw),view=renderChild(locale,'/video-studio/'+f.route,raw);
 test(locale+':'+f.part+':'+mode+' fixed result UI is localized without empty placeholder cards',()=>{
  let html=view.html;for(const text of[...new Set([...strings(result),...strings(source)])].filter(s=>s.length>=4).sort((a,b)=>b.length-a.length))html=html.split(escape(text)).join(' ');
  html=html.replace(/<svg\b[\s\S]*?<\/svg>/g,'').replace(/<code\b[\s\S]*?<\/code>/g,'');const attrs=[...html.matchAll(/\b(?:placeholder|aria-label|title|data-portal-confirm)="([^"]*)"/g)].map(m=>m[1]).join(' '),text=html.replace(/<[^>]+>/g,' ')+' '+attrs;
  assert.deepEqual([...new Set(text.match(patterns[locale])||[])],[]);assert.doesNotMatch(text,/lastTwo(?:Result|Save)Ui\./);
  if(['empty','unsafeResult'].includes(mode))assert.doesNotMatch(view.html,/Reviewable planning receipt|Chưa có Image Motion Plan|Chưa có Reference Format Plan/);
 });
 test(locale+':'+f.part+':'+mode+' keeps raw data, strict save guards and terminal receipt',()=>{
  assert.equal(JSON.stringify(raw),snapshot);const button=[...view.html.matchAll(/<button\b[^>]*>/g)].find(m=>m[0].includes('data-portal-action="'+f.route+'-save-plan"'))?.[0],href='href="/video-studio/'+f.receipt.plan.id+'"';
  if(mode==='saved'){assert.ok(view.html.includes(href));assert.equal(button,undefined);assert.doesNotMatch(view.html,/data-portal-confirm=/);}
  if(['mismatch','unsafeResult','empty'].includes(mode))assert.equal(button,undefined);
  if(mode==='unsafeReceipt')assert.ok(!view.html.includes(href));
  if(mode==='result'||mode==='noSave'){assert.ok(button);assert.equal(/\sdisabled(?:\s|>)/.test(button),mode==='noSave');}
  if(f.part==='image'){
   assert.equal(view.html.includes('data-image-motion-planner-rendered-result'),!['empty','unsafeResult'].includes(mode),'freshness helper sees only an actually valid result region');
   assert.equal(view.html.includes('data-image-motion-planner-saved-receipt'),mode==='saved','only a valid terminal receipt exposes its semantic region');
  }
 });
}
for(const locale of['vi','en','zh']){
 const messages=renderChild(locale,'/studio',{}).messages[locale],isNew=k=>['lastTwoResultUi.','lastTwoSaveUi.','lastTwoFeedbackUi.','lastTwoOperationFeedbackUi.'].some(p=>k.startsWith(p));
 test(locale+': all 10424 released catalog values remain unchanged',()=>{const entries=accountPlainLanguageHistoricalSnapshot(Object.entries(messages),locale).filter(([k])=>!isNew(k)).sort(([a],[b])=>a<b?-1:a>b?1:0);assert.equal(entries.length,10424);assert.equal(crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex'),fixture.catalog[locale]);});
 test(locale+': result and save catalog has exactly 60 used keys',()=>assert.equal(Object.keys(messages).filter(k=>k.startsWith('lastTwoResultUi.')||k.startsWith('lastTwoSaveUi.')).length,60));
}
