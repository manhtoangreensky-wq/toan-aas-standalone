import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const source=fs.readFileSync(new URL('../static/portal/integration.js',import.meta.url),'utf8');
const fixtures=JSON.parse(fs.readFileSync(new URL('./fixtures/video-inner-composer-samples.json',import.meta.url),'utf8'));
const noop=()=>{};
const document={readyState:'loading',visibilityState:'visible',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],documentElement:{lang:'vi',setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop,toggle:noop}}};
const window={document,TOANAASPortal:{mount:noop},navigator:{language:'vi'},location:{pathname:'/video-studio/prompt-planner',search:'',origin:'https://unit.invalid',href:'https://unit.invalid/video-studio/prompt-planner'},addEventListener:noop,dispatchEvent:noop,setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},matchMedia:()=>({matches:false,addEventListener:noop}),crypto:globalThis.crypto};
const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,Blob,AbortController,Intl,console,crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop,fetch:()=>{throw Error('Network forbidden');}});
const end=source.lastIndexOf('}());');assert.ok(end>0);
vm.runInContext(source.slice(0,end)+'window.__innerReceipt={videoPromptPlannerPlanSaveReceipt,videoIdeaPlanSaveReceipt,selfShotScenePlanSaveReceipt};\n'+source.slice(end),sandbox);
const names={'prompt-planner':'videoPromptPlannerPlanSaveReceipt','idea-planner':'videoIdeaPlanSaveReceipt','self-shot-planner':'selfShotScenePlanSaveReceipt'};
for(const row of fixtures){
  const parse=raw=>window.__innerReceipt[names[row.route]](structuredClone(raw));
  test(row.route+': validated receipt keeps its exact bounded transport until Portal normalization',()=>{
    assert.deepEqual(JSON.parse(JSON.stringify(parse(row.receipt))),row.receipt);
  });
  test(row.route+': integration receipt survives real Portal normalizeBootstrap',()=>{
    const r=renderChild('vi','/video-studio/'+row.route,{[row.key+'SaveReceipt']:parse(row.receipt)});
    assert.equal(r.context[row.key+'SaveReceipt'].plan?.id,row.receipt.plan.id);
  });
  for(const flag of ['provider_called','wallet_mutated','bot_called'])test(row.route+': true '+flag+' remains rejected',()=>assert.equal(parse({...row.receipt,[flag]:true}),null));
  test(row.route+': extra receipt field remains rejected',()=>assert.equal(parse({...row.receipt,unknown:'not allowed'}),null));
  test(row.route+': malformed plan ID remains rejected',()=>assert.equal(parse({...row.receipt,plan:{...row.receipt.plan,id:'forged'}}),null));
}
