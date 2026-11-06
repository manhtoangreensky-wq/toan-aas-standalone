import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const integration=fs.readFileSync(path.join(root,'static/portal/integration.js'),'utf8');
const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');
export const reviewRoute='/content/publish-review';
export function actionReceipt(label='A'){
  const flags=['input_persisted','provider_called','bot_called','job_created','wallet_mutated','payment_started','asset_saved','media_output_created','publish_action_created','delivery_created','fact_checked','rights_verified'];
  return {execution:'web_native_publish_review_text_only',...Object.fromEntries(flags.map(k=>[k,false])),package:{title:'VALUE_'+label,caption:'CAPTION_'+label,hashtags:['#TAG'+label],cta:'CTA_'+label,source_prompt:'SOURCE_'+label,review_checklist:['CHECK_ONE','CHECK_TWO','CHECK_THREE','CHECK_FOUR'],copy_instruction:'COPY_'+label}};
}
export function actionContext(label='A'){
  return {path:reviewRoute,account:{id:label==='A'?'11111111-1111-4111-8111-111111111111':'22222222-2222-4222-8222-222222222222'},session:{authenticated:true,csrfToken:'synthetic-action-'+label},publishReviewPackEnabled:true,capabilities:{'publish-review-pack-compose':true},bridge:{available:false},publishReviewPackResult:actionReceipt('KEPT'),pageStates:{[reviewRoute]:'ready'}};
}
export function reviewActionRuntime(locale='en'){
  let state=actionContext(),button,form;
  const pending=[],listeners=new Map(),toasts=[],networkLog=[];
  const node=(attributes={})=>({attributes:{...attributes},disabled:false,textContent:'',className:'',setAttribute(k,v){this.attributes[k]=String(v);},getAttribute(k){return this.attributes[k]??null;},removeAttribute(k){delete this.attributes[k];},remove(){const i=toasts.indexOf(this);if(i>=0)toasts.splice(i,1);}});
  function resetForm(disabled=false){button=node();button.disabled=disabled;form=node({'data-portal-action':'publish-review-pack-compose','data-portal-route':reviewRoute});form.querySelector=()=>button;}
  resetForm();
  const region={appendChild(n){toasts.push(n);},querySelectorAll(){return toasts;}};
  const noop=()=>{};
  const document={readyState:'loading',visibilityState:'visible',addEventListener:noop,createElement:()=>node(),querySelector:s=>s==='[data-portal-toast]'?region:null,querySelectorAll:s=>['[data-portal-action]','[data-portal-form]'].includes(s)?[form]:[],documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop,toggle:noop}}};
  const window={document,location:{pathname:reviewRoute,search:'',origin:'https://unit.invalid',href:'https://unit.invalid'+reviewRoute,assign:noop},navigator:{language:locale},addEventListener:(k,fn)=>listeners.set(k,fn),dispatchEvent:noop,setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},matchMedia:()=>({matches:false,addEventListener:noop}),crypto:globalThis.crypto};
  Object.defineProperty(window,'__TOAN_AAS_PORTAL__',{get:()=>state,set:value=>{state=value;},configurable:true});
  const fetch=(url,options)=>{
    networkLog.push({url,method:options?.method});
    assert.equal(url,'/api/v1/content-studio/tools/publish-review-pack');
    assert.equal(options.method,'POST');
    assert.equal(options.credentials,'same-origin');
    const payload=JSON.parse(options.body);assert.equal(payload.title,'Nội dung cần rà soát');
    let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});
    pending.push({resolve,reject,payload});return promise;
  };
  const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,Blob,AbortController,Intl,console,fetch,crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop});
  vm.runInContext(i18n,sandbox);window.TOANAASI18n.setLocale(locale,{emit:false});
  const anchor='  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.equal(integration.split(anchor).length,2);
  const injected='  window.__reviewActionTest={advanceSession:()=>{canonicalSessionEpoch+=1;}};\n';
  vm.runInContext(integration.replace(anchor,injected+anchor),sandbox);
  assert.ok(listeners.has('toanaas:portal-action'));
  const fields={title:'Nội dung cần rà soát',caption:'Nội dung rõ ràng dành cho người đọc.',hashtags:'#NoiDung',cta:'Xem thêm thông tin',source_prompt:''};
  function settle(index,kind='valid',label='A',message=''){
    const p=pending[index];assert.ok(p,'request must have reached fetch');
    if(kind==='transport_error'){p.reject(new Error(message || 'network unavailable'));return;}
    const data=actionReceipt(label),guarded=kind.startsWith('guarded');if(guarded)delete data.package;
    if(kind==='unsafe'||kind==='guarded_unsafe')data.provider_called=true;
    if(kind==='wrong_execution')data.execution='provider_output';
    const payload={ok:kind!=='guarded_error',status:guarded?'guarded':'draft',message,data};
    p.resolve({ok:kind!=='guarded_error',status:kind==='guarded_error'?422:200,json:async()=>payload});
  }
  return {pending,toasts,fields,networkLog,run:()=>listeners.get('toanaas:portal-action')({detail:{action:'publish-review-pack-compose',route:reviewRoute,fields:{...fields}}}),settle,get state(){return state;},get button(){return button;},replace(next,{epoch=true,disabled=true}={}){state=next;window.location.pathname=next.path;resetForm(disabled);if(epoch)window.__reviewActionTest.advanceSession();}};
}
