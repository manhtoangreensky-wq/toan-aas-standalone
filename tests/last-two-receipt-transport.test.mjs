import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const fixtures=JSON.parse(fs.readFileSync(new URL('./fixtures/last-two-planner-results.json',import.meta.url),'utf8')).rows;
const source=fs.readFileSync(new URL('../static/portal/integration.js',import.meta.url),'utf8');
const names={imageMotionPlanner:'imageMotionPlanSaveReceipt',referenceFormatPlanner:'referenceFormatPlanSaveReceipt'};
const noop=()=>{};
const document={readyState:'loading',visibilityState:'visible',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],documentElement:{lang:'vi',setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop,toggle:noop}}};
const window={document,TOANAASPortal:{mount:noop},navigator:{language:'vi'},location:{pathname:'/video-studio/script-to-screen-planner',search:'',origin:'https://unit.invalid',href:'https://unit.invalid/video-studio/script-to-screen-planner'},addEventListener:noop,dispatchEvent:noop,setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},matchMedia:()=>({matches:false,addEventListener:noop}),crypto:globalThis.crypto};
const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,Blob,AbortController,Intl,console,crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop,fetch:()=>{throw Error('Network forbidden');}});
const end=source.lastIndexOf('}());');assert.ok(end>0);
vm.runInContext(source.slice(0,end)+'window.__remainingReceipts={imageMotionPlanSaveReceipt,referenceFormatPlanSaveReceipt,imageMotionPlannerResultIsSafe,referenceFormatPlannerResultIsSafe};\n'+source.slice(end),sandbox);
for(const row of fixtures){
 const parse=raw=>window.__remainingReceipts[names[row.key]](structuredClone(raw));
 test(row.route+': actual owned deterministic server result is accepted by its real integration boundary validator',()=>{
  const name={imageMotionPlanner:'imageMotionPlannerResultIsSafe',referenceFormatPlanner:'referenceFormatPlannerResultIsSafe'}[row.key];
  assert.equal(window.__remainingReceipts[name](structuredClone(row.result)),true);
 });
 test(row.route+': strict integration validator retains its verified bounded transport envelope',()=>assert.deepEqual(JSON.parse(JSON.stringify(parse(row.receipt))),row.receipt));
 test(row.route+': real integration receipt survives Portal bootstrap and renderer',()=>{
  const receipt=parse(row.receipt),view=renderChild('vi','/video-studio/'+row.route,{[row.key+'SaveReceipt']:receipt});
  assert.equal(view.context[row.key+'SaveReceipt'].plan?.id,row.receipt.plan.id);
 });
 test(row.route+': every false safety flag stays rejected if changed or omitted',()=>{
  for(const[key,value]of Object.entries(row.receipt))if(value===false){
   assert.equal(parse({...row.receipt,[key]:true}),null,key+' must remain false');
   const missing=structuredClone(row.receipt);delete missing[key];assert.equal(parse(missing),null,key+' must remain present');
  }
 });
 test(row.route+': unknown fields or forged identity never pass',()=>{
  assert.equal(parse({...row.receipt,unexpected:'private data'}),null);
  assert.equal(parse({...row.receipt,plan:{...row.receipt.plan,id:'forged'}}),null);
  assert.equal(parse({...row.receipt,plan:{...row.receipt.plan,unexpected:'private data'}}),null);
 });
}
