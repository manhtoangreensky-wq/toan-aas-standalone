import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {requestPanelSources} from './chat-request-panel-runtime.mjs';
const copy=JSON.parse(fs.readFileSync(new URL('../fixtures/chat-request-panel-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(copy.vi)),hash=value=>createHash('sha256').update(value).digest('hex');
const hashes={vi:'b7c7339ccb4b40142e33bff3d4d479a531c57aa5d96e12eefe0a93ce63bf594b',en:'66e4178b42e68c8aa840afcb5b9f7e72059e8669ae54ce8f4e5d94f26b8e7bf7',zh:'1af4b4a115ab3ce91f02af0b12b1c464a38871b92f606684616e9bca49d12d2a'};
assert.equal(keys.size,29);
export function requestPanelHistoricalSnapshot(entries,locale){
  assert.ok(hashes[locale]);
  const reserved=entries.filter(([key])=>/^(?:chatExecutionUi|chatRunTimelineUi)/.test(key));
  if(!reserved.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));
  assert.equal(reserved.length,added.length,'Unreviewed Chat request copy: unknown key');
  assert.equal(added.length,29,'Unreviewed Chat request copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat request copy: value/order');
  return entries.filter(([key])=>!keys.has(key));
}
export const requestPanelSpans=[
  ['chatRunBadge','  function chatRunBadge(value) {','\n  function chatExecutionProjection(context) {','7bdaf5eb9c31eb86fb1ca9c86e7dd1b2128b66d2445045d438b0e4cc27e796b0','2df50453da2bf48ddf9d565cacfccb9f48935245435454d03435ebf858a3995f'],
  ['renderChatRunTimeline','  function renderChatRunTimeline(context) {','\n  function renderChatExecutionPanel(thread, context, route) {','e5a6d1ba20b957157ec4e13f1d488f16e126550e4c14f55555e24cb33b5a4761','90b91f820bcce8a856ca0aa56cb25016bf3cc371c03d5d583099e58c9df10716'],
  ['renderChatExecutionPanel','  function renderChatExecutionPanel(thread, context, route) {','\n  function renderChatWorkspaceBoundary(context) {','a6f303ef04e551064f0aad0d29a67d7e90170286374c6b41c5f5cbc260099ac4','5a3878c36d3025b9a2fb8588c64abf5b9dd85400b53dd58a6bb0bf2de2700972']
];
function part(source,spec){
  const [,start,end]=spec;
  assert.equal(source.split(start).length-1,1,'Unreviewed Chat request source boundary');
  const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a,'Unreviewed Chat request source boundary');
  return {a,b,text:source.slice(a,b)};
}
// This deliberately blocks before Git when root has not filled the release SHA.
const original=requestPanelSources(true).portal;
const oldParts=requestPanelSpans.map(spec=>{
  const value=part(original,spec).text;assert.equal(hash(value),spec[3],'History release has a different protected request baseline');return value;
});
export function requestPanelHistoricalPortalSource(value){
  let source=value.replace(/\r\n/g,'\n');
  const spans=requestPanelSpans.map(spec=>part(source,spec)),states=spans.map((p,k)=>hash(p.text)===requestPanelSpans[k][3]?'old':hash(p.text)===requestPanelSpans[k][4]?'new':'unknown');
  if(states.every(state=>state==='old'))return source;
  assert.ok(states.every(state=>state==='new'),'Unreviewed Chat request source: changed or partial function set');
  for(let k=requestPanelSpans.length-1;k>=0;k--)source=source.slice(0,spans[k].a)+oldParts[k]+source.slice(spans[k].b);
  return source;
}
export const requestPanelCssOld='.portal-chat-execution-status { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 9px; }';
export const requestPanelCssNew='.portal-chat-execution-status { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }';
export const requestStatusWrapRules=[
  ['.portal-chat-execution-status strong { overflow: hidden; color: #ddf9f4; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }',
   '.portal-chat-execution-status strong { overflow: visible; color: #ddf9f4; font-size: 10px; text-overflow: clip; white-space: normal; overflow-wrap: anywhere; }'],
  ['.portal-chat-execution-status em:not(:empty) { max-width: 86px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }',
   '.portal-chat-execution-status em:not(:empty) { max-width: 55%; overflow: visible; text-overflow: clip; white-space: normal; overflow-wrap: anywhere; }']
];
export function requestPanelHistoricalCss(value){
  let source=value.replace(/\r\n/g,'\n');
  const states=requestStatusWrapRules.map(([old,next])=>{
    const a=source.split(old).length-1,b=source.split(next).length-1;
    assert.ok((a===1&&b===0)||(a===0&&b===1),'Unreviewed Chat request CSS: status wrap rule count');
    return b?'new':'old';
  });
  assert.ok(states.every(state=>state===states[0]),'Unreviewed Chat request CSS: partial status wrap');
  for(const[old,next]of requestStatusWrapRules)if(states[0]==='new')source=source.replace(next,old);
  const oldCount=source.split(requestPanelCssOld).length-1,newCount=source.split(requestPanelCssNew).length-1;
  assert.ok((oldCount===1&&newCount===0)||(oldCount===0&&newCount===1),'Unreviewed Chat request CSS: exact desktop rule count');
  return newCount?source.replace(requestPanelCssNew,requestPanelCssOld):source;
}
