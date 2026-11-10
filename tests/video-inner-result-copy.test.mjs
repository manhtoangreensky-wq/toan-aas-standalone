import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const rows=JSON.parse(fs.readFileSync(new URL('./fixtures/video-inner-composer-samples.json',import.meta.url),'utf8'));
const actions={'prompt-planner':['video-prompt-plan','video-prompt-plan-save'],'idea-planner':['video-idea-planner-compose','video-idea-planner-save-plan'],'self-shot-planner':['self-shot-scene-planner-compose','self-shot-scene-planner-save-plan']};
const escape=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const decode=s=>String(s).replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
function dataStrings(value){return typeof value==='string'?[value]:Array.isArray(value)?value.flatMap(dataStrings):value&&typeof value==='object'?Object.values(value).flatMap(dataStrings):[];}
const patterns={vi:/\b(?:brief|media|studio|prompt|style|action|audio|scene|shots?|plan|planning|review|runtime|consent|asset|bot|web|native|provider|engine|concept|creative|direction|workflow|claim|identity|lock|owner|server|browser|off|template|preview|render|upload|output|publish|delivery|metadata|scope|cue|camera|voice|host|social|online|demo|CSRF|SaaS|ASMR|UGC|AI)\b/gi,en:/[À-ỹ\u3400-\u9fff]/g,zh:/[À-ỹ]|\b(?:brief|media|studio|prompt|style|action|audio|scene|plan|planning|review|consent|asset|bot|web|provider|concept|direction|server|browser|off|preview|render|CSRF|SaaS|ASMR|UGC|AI)\b/gi};
for(const locale of['vi','en','zh'])for(const row of rows){
 const result=structuredClone(row.result);if(row.route==='prompt-planner')result.planner.language=row.source.language;
 const caps=Object.fromEntries([...actions[row.route],'video-plan-create'].map(k=>[k,true]));
 const raw={capabilities:caps,[row.key+'Enabled']:true,[row.key+'Result']:result,[row.key+'SaveSource']:row.source,[row.key+'SaveReceipt']:row.receipt};
 const view=renderChild(locale,'/video-studio/'+row.route,raw);
 test(locale+':'+row.route+' keeps accepted server content while localizing only fixed result labels',()=>{
  assert.ok(view.html.includes(escape(row.result.planner.title)),'the real server result must remain visible');
  const prompt=row.result.planner.prompt||row.result.planner.video_prompt||row.result.planner.scenes?.[0]?.video_prompt;
  assert.ok(prompt&&view.html.includes(escape(prompt)),'full server prompt must be retained without translation or substitution');
  let html=view.html;
  for(const value of [...new Set(dataStrings(row.result.planner).filter(s=>s.length>=4))].sort((a,b)=>b.length-a.length))html=html.split(escape(value)).join(' ');
  html=html.replace(/<code\b[^>]*>[\s\S]*?<\/code>/g,'').replace(/<svg\b[\s\S]*?<\/svg>/g,'');
  const attributes=[...html.matchAll(/\b(?:placeholder|aria-label|title|data-portal-confirm)="([^"]*)"/g)].map(m=>m[1]).join(' ');
  const fixed=decode(html.replace(/<[^>]+>/g,' '))+' '+decode(attributes);
  assert.deepEqual([...new Set((fixed.match(patterns[locale])||[]).map(s=>s.toLowerCase()))],[],'fixed UI must not leak another language; raw result strings are excluded, not translated');
 });
 test(locale+':'+row.route+' keeps a truthful localized explicit save confirmation',()=>{
  const button=[...view.html.matchAll(/<button\b[^>]*>/g)].find(m=>m[0].includes('data-portal-action="'+actions[row.route][1]+'"'));
  assert.ok(button,'matching current source exposes the save control');
  const confirmation=decode(button[0].match(/data-portal-confirm="([^"]*)"/)?.[1]||'');
  assert.ok(confirmation.length>80,'retain meaningful privacy/execution boundary explanation');
  assert.doesNotMatch(button[0],/\sdisabled(?:\s|>)/,'known permitted source is not falsely disabled');
 });
}
