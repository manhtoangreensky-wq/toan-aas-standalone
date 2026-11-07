import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const integration=fs.readFileSync(path.join(root,'static/portal/integration.js'),'utf8');
const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');
export const calendarRoute='/calendar';
export const calendarActions=['campaign-calendar-filter','campaign-calendar-month','campaign-calendar-refresh'];
export function calendarWindow(month='2026-11',label='A',status='all',platform='all'){
 return {month,filters:{status,platform},items:[{id:'33333333-3333-4333-8333-333333333333',title:'OWNER_CALENDAR_'+label,platform:platform==='all'?'tiktok':platform,objective:'traffic',scheduled_for:month+'-06T10:00',approval_status:status==='all'?'draft':status,updated_at:'2026-11-01T00:00:00Z'}],summary:{total:1,returned:1,has_more:false,limit:200}};
}
export function calendarActionContext(label='A'){
 return {path:calendarRoute,account:{id:label==='A'?'11111111-1111-4111-8111-111111111111':'22222222-2222-4222-8222-222222222222'},session:{authenticated:true,csrfReady:true,csrfToken:'synthetic-calendar-'+label},capabilities:{'campaign-calendar-view':true,'campaign-calendar-refresh':true},bridge:{available:false},campaignCalendar:calendarWindow('2026-11','KEPT_'+label),campaignCalendarReadState:'read_only',pageStates:{[calendarRoute]:'read_only'}};
}
export function calendarActionRuntime(locale='en',action='campaign-calendar-refresh'){
 assert(calendarActions.includes(action));let state=calendarActionContext(),button,form;
 const pending=[],listeners=new Map(),toasts=[],networkLog=[];
 const node=(attributes={})=>({attributes:{...attributes},disabled:false,textContent:'',className:'',setAttribute(k,v){this.attributes[k]=String(v);},getAttribute(k){return this.attributes[k]??null;},removeAttribute(k){delete this.attributes[k];},remove(){const i=toasts.indexOf(this);if(i>=0)toasts.splice(i,1);}});
 function resetControls(disabled=false){button=node({'data-portal-action':action,'data-portal-route':state.path});button.disabled=disabled;form=node({'data-portal-action':action,'data-portal-route':state.path});form.querySelector=()=>button;}
 resetControls();const region={appendChild(n){toasts.push(n);},querySelectorAll(){return toasts;}};const noop=()=>{};
 const document={readyState:'loading',visibilityState:'visible',addEventListener:noop,createElement:()=>node(),querySelector:s=>s==='[data-portal-toast]'?region:null,querySelectorAll:s=>s==='[data-portal-action]'?[button]:s==='[data-portal-form]'?[form]:[],documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop,toggle:noop}}};
 const window={document,location:{pathname:calendarRoute,search:'',origin:'https://unit.invalid',href:'https://unit.invalid'+calendarRoute,assign:noop},navigator:{language:locale},addEventListener:(k,fn)=>listeners.set(k,fn),dispatchEvent:noop,setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},matchMedia:()=>({matches:false,addEventListener:noop}),crypto:globalThis.crypto};
 Object.defineProperty(window,'__TOAN_AAS_PORTAL__',{get:()=>state,set:value=>{state=value;},configurable:true});
 const fetch=(url,options)=>{const parsed=new URL(url,'https://unit.invalid');assert.equal(parsed.pathname,'/api/v1/campaign-calendar/window');assert.equal(options.method||'GET','GET');assert.equal(options.credentials,'same-origin');assert.equal(options.cache,'no-store');assert.equal(options.body,undefined);networkLog.push({url,method:options.method||'GET',month:parsed.searchParams.get('month'),status:parsed.searchParams.get('status'),platform:parsed.searchParams.get('platform')});let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});pending.push({resolve,reject,query:parsed.searchParams});return promise;};
 const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,Blob,AbortController,Intl,console,fetch,crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop});
 vm.runInContext(i18n,sandbox);window.TOANAASI18n.setLocale(locale,{emit:false});
 const anchor='  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';assert.equal(integration.split(anchor).length,2);
 vm.runInContext(integration.replace(anchor,'  window.__calendarActionTest={advanceSession:()=>{campaignSessionEpoch+=1;canonicalSessionEpoch+=1;}};\n'+anchor),sandbox);assert(listeners.has('toanaas:portal-action'));
 const fields=action==='campaign-calendar-filter'?{month:'2026-11',status:'draft',platform:'tiktok'}:action==='campaign-calendar-month'?{__campaignCalendarMonth:'2026-12'}:{};
 function settle(index,kind='valid',label='A',message=''){
  const p=pending[index];assert(p,'request must have reached fake fetch');
  if(kind==='transport_error'){p.reject(new Error(message||'network unavailable'));return;}
  const guarded=kind==='guarded',failed=kind==='error';
  const payload={ok:!guarded&&!failed,status:guarded?'guarded':failed?'error':'read_only',message,data:calendarWindow(p.query.get('month'),label,p.query.get('status'),p.query.get('platform'))};
  p.resolve({ok:!guarded&&!failed,status:guarded?403:failed?422:200,json:async()=>payload});
 }
 return {pending,toasts,fields,networkLog,settle,run:(overrideFields)=>listeners.get('toanaas:portal-action')({detail:{action,route:calendarRoute,fields:overrideFields===undefined?{...fields}:overrideFields}}),get state(){return state;},get button(){return button;},replace(next,{epoch=true,disabled=true}={}){state=next;window.location.pathname=next.path;resetControls(disabled);if(epoch)window.__calendarActionTest.advanceSession();}};
}
