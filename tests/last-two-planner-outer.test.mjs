import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';
const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/last-two-outer-controls.json',import.meta.url),'utf8'));
const fingerprint=html=>crypto.createHash('sha256').update([...html.matchAll(/<(?:form|input|select|textarea|option|button)\b[^>]*>/g)].map(m=>m[0].replace(/\s(?:placeholder|aria-label|title)="[^"]*"/g,'')).join('\n')).digest('hex');
const patterns={vi:/\b(?:brief|media|studio|prompt|plan|review|runtime|asset|bot|web|native|format|social|follow|lead|inbox|online|cinematic|orbit|hero|metadata|provider|execution|source|scene|browser|owner|direction)\b/gi,en:/[À-ỹ\u3400-\u9fff]/g,zh:/[À-ỹ]|\b(?:metadata|brief|media|studio|prompt|plan|review|runtime|asset|web|native|format|follow|lead|inbox|online|cinematic|provider|execution|source|browser|owner|direction)\b/gi};
for(const d of fixture.definitions)for(const locale of['vi','en','zh'])for(const state of['loading','empty','ready','guarded']){
 const raw={capabilities:{[d.route+'-compose']:state!=='guarded',[d.route+'-save-plan']:true,'video-plan-create':true},[d.key+'Enabled']:true,[d.key+'ReadState']:state==='empty'?'ready':state,[d.key+'References']:['ready','guarded'].includes(state)?[d.reference]:[]},snapshot=JSON.stringify(raw),view=renderChild(locale,'/video-studio/'+d.route,raw),form=view.html.match(new RegExp('<form\\b[^>]*data-portal-action="'+d.route+'-compose"[\\s\\S]*?<\\/form>'))?.[0]||'';
 test(locale+':'+d.route+':'+state+' real controls and source records stay exact',()=>{
  assert.equal(JSON.stringify(raw),snapshot);assert.equal([...form.matchAll(/\bname="[^"]*"/g)].length,d.count);
  assert.equal(fingerprint(form),fixture.hashes[d.route+':'+state]);assert.match(form,/data-portal-no-transient/);
 });
 test(locale+':'+d.route+':'+state+' fixed form copy is localized and decorative panels are absent',()=>{
  let text=form.replace(/<[^>]+>/g,' ');for(const value of Object.values(d.reference))if(typeof value==='string')text=text.split(value).join(' ');
  const attributes=[...form.matchAll(/\b(?:placeholder|aria-label|title)="([^"]*)"/g)].map(m=>m[1]).join(' ');
  assert.deepEqual([...new Set((text+' '+attributes).match(patterns[locale])||[])],[]);
  assert.doesNotMatch(form,/lastTwoPlannerUi\./);assert.doesNotMatch(view.html,/portal-cinematic-concept-(?:intro|boundary|layout)/);
 });
}
for(const locale of['vi','en','zh']){
 const messages=renderChild(locale,'/studio',{}).messages[locale];
 test(locale+': all 10349 released catalog entries remain unchanged',()=>{
  const entries=Object.entries(messages).filter(([k])=>!k.startsWith('lastTwoPlannerUi.')).sort(([a],[b])=>a<b?-1:a>b?1:0);
  assert.equal(entries.length,fixture.oldCatalogCount);assert.equal(crypto.createHash('sha256').update(JSON.stringify(entries)).digest('hex'),fixture.catalog[locale]);
 });
 test(locale+': new last-two catalog contains only the 75 used keys',()=>assert.equal(Object.keys(messages).filter(k=>k.startsWith('lastTwoPlannerUi.')).length,fixture.newCatalogCount));
}
