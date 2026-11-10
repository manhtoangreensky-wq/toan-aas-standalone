import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const fixtures=JSON.parse(fs.readFileSync(new URL('./fixtures/video-inner-composer-samples.json',import.meta.url),'utf8'));
const actions={
  'prompt-planner':['video-prompt-plan','video-prompt-plan-save'],
  'idea-planner':['video-idea-planner-compose','video-idea-planner-save-plan'],
  'self-shot-planner':['self-shot-scene-planner-compose','self-shot-scene-planner-save-plan']
};
const saved='/video-studio/11111111-1111-4111-8111-111111111111';
function render(row,kind='valid'){
  const result=structuredClone(row.result),source=structuredClone(row.source),receipt=structuredClone(row.receipt);
  // The amended prompt receipt contract must echo its validated language.
  // The separate Python regression proves the real composer produces this field.
  if(row.route==='prompt-planner')result.planner.language=source.language;
  if(kind==='malformed')result.provider_called=true;
  if(kind==='mismatch'){
    if(row.route==='prompt-planner')source.brief='Different current customer brief';
    else if(row.route==='idea-planner')source.topic='Different current customer topic';
    else source.subject_description='Different current customer subject';
  }
  if(kind==='forgedReceipt')receipt.plan.id='not-a-plan-id';
  const caps=Object.fromEntries([...actions[row.route],'video-plan-create'].map(k=>[k,true]));
  if(kind==='noSave')caps[actions[row.route][1]]=false;
  return renderChild('vi','/video-studio/'+row.route,{
    capabilities:caps,[row.key+'Enabled']:true,[row.key+'Result']:result,
    [row.key+'SaveSource']:source,[row.key+'SaveReceipt']:receipt
  });
}
for(const row of fixtures){
  test(row.route+': a valid boundary-normalized result remains visible without a second transport parse',()=>{
    const r=render(row);assert.ok(r.context[row.key+'Result'].planner,'actual full boundary accepted');
    assert.ok(r.html.includes(row.result.planner.title),'server title is rendered unchanged');
  });
  test(row.route+': matching current selections expose the explicit save action',()=>{
    assert.ok(render(row).html.includes('data-portal-action="'+actions[row.route][1]+'"'));
  });
  test(row.route+': changed current customer selections cannot save the old result',()=>{
    assert.ok(!render(row,'mismatch').html.includes('data-portal-action="'+actions[row.route][1]+'"'));
  });
  test(row.route+': absent save capability keeps the current save control disabled',()=>{
    const html=render(row,'noSave').html;
    const button=[...html.matchAll(/<button\b[^>]*>/g)].find(m=>m[0].includes('data-portal-action="'+actions[row.route][1]+'"'));
    assert.ok(button,'matching source still has a truthful disabled control');assert.match(button[0],/\sdisabled(?:\s|>)/);
  });
  test(row.route+': a validated content-free save receipt opens the exact private plan',()=>{
    assert.ok(render(row).html.includes('href="'+saved+'"'));
  });
  test(row.route+': unsafe execution boundary never displays the supplied planner',()=>{
    const r=render(row,'malformed');assert.ok(!r.context[row.key+'Result'].planner);
    assert.ok(!r.html.includes(row.result.planner.title));
  });
  test(row.route+': malformed plan identity cannot create a saved-plan link',()=>{
    assert.ok(!render(row,'forgedReceipt').html.includes('href="/video-studio/not-a-plan-id"'));
  });
}
