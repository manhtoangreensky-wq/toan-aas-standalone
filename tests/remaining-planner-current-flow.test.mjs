import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const rows=JSON.parse(fs.readFileSync(new URL('./fixtures/remaining-planner-composer-samples.json',import.meta.url),'utf8'));
const id='11111111-1111-4111-8111-111111111111';
const escape=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
function render(row,mode='new'){
 const result=structuredClone(row.result),source=structuredClone(row.source),receipt=structuredClone(row.receipt);
 if(mode==='unsafeResult'){
  if(row.route==='script-to-screen-planner')result.provider_called=true;
  else result.provider_called=true;
 }
 if(mode==='mismatch'){
  if(row.route==='script-to-screen-planner')source.brief='Different current customer brief';
  else if(row.route==='cinematic-concept')source.product='Different current customer product';
  else source.topic='Different current customer topic';
 }
 if(mode==='unsafeReceipt')receipt.provider_called=true;
 const action=row.route;
 const capabilities={[action+'-compose']:true,[action+'-save-plan']:mode!=='noSave','video-plan-create':true};
 return renderChild('vi','/video-studio/'+row.route,{capabilities,[row.key+'Enabled']:true,[row.key+'Result']:result,[row.key+'SaveSource']:source,[row.key+'SaveReceipt']:['saved','unsafeReceipt'].includes(mode)?receipt:{}});
}
for(const row of rows){
 test(row.route+': actual accepted composer content survives full Portal normalization and renderer checks',()=>{
  const view=render(row);assert.ok(view.context[row.key+'Result']?.[row.resultKey]);
  assert.ok(view.html.includes(escape(row.result[row.resultKey].title)),'real server title remains visible');
 });
 test(row.route+': matching permitted current choices expose the explicit save action',()=>assert.ok(render(row).html.includes('data-portal-action="'+row.route+'-save-plan"')));
 test(row.route+': changed current choices do not save an older result',()=>assert.ok(!render(row,'mismatch').html.includes('data-portal-action="'+row.route+'-save-plan"')));
 test(row.route+': missing save capability leaves the matching control disabled',()=>{
  const button=[...render(row,'noSave').html.matchAll(/<button\b[^>]*>/g)].find(m=>m[0].includes('data-portal-action="'+row.route+'-save-plan"'));
  assert.ok(button);assert.match(button[0],/\sdisabled(?:\s|>)/);
 });
 test(row.route+': valid saved receipt opens the exact private saved plan',()=>assert.ok(render(row,'saved').html.includes('href="/video-studio/'+id+'"')));
 test(row.route+': saved current result does not restore a second active save button',()=>assert.ok(!render(row,'saved').html.includes('data-portal-action="'+row.route+'-save-plan"')));
 test(row.route+': unsafe execution result remains rejected',()=>{
  const view=render(row,'unsafeResult');assert.ok(!view.context[row.key+'Result']?.[row.resultKey]);assert.ok(!view.html.includes(escape(row.result[row.resultKey].title)));
 });
 test(row.route+': unsafe receipt cannot produce a saved-plan link',()=>assert.ok(!render(row,'unsafeReceipt').html.includes('href="/video-studio/'+id+'"')));
}
