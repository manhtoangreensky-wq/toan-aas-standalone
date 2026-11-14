import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const integration=fs.readFileSync(new URL('../../static/portal/integration.js',import.meta.url),'utf8');
const i18n=fs.readFileSync(new URL('../../static/portal/portal-i18n.js',import.meta.url),'utf8');

// Real handler + real read hydrators, with only fetch and DOM boundaries owned.
export function documentRefreshRuntime(locale='vi',route='/documents'){
  let state={path:route,session:{authenticated:true,csrfToken:'synthetic-owned-only'},capabilities:{'document-operation-refresh':true},documentOperationsReadState:'ready',documentOperations:[],pageStates:{[route]:'ready'},bridge:{available:false}};
  const listeners=new Map(),pending=[],toasts=[],network=[],noop=()=>{};
  const node=()=>({className:'',textContent:'',attributes:{},setAttribute(k,v){this.attributes[k]=v;},getAttribute(k){return this.attributes[k]??null;},remove(){const i=toasts.indexOf(this);if(i>=0)toasts.splice(i,1);}});
  const region={appendChild:n=>toasts.push(n),querySelectorAll:()=>toasts};
  const document={readyState:'loading',visibilityState:'visible',addEventListener:noop,createElement:node,querySelector:s=>s==='[data-portal-toast]'?region:null,querySelectorAll:()=>[],documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop,toggle:noop}}};
  const window={document,navigator:{language:locale},location:{pathname:route,search:'',origin:'https://unit.invalid',href:'https://unit.invalid'+route,assign:noop},addEventListener:(name,fn)=>listeners.set(name,fn),dispatchEvent:noop,setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},crypto:globalThis.crypto};
  Object.defineProperty(window,'__TOAN_AAS_PORTAL__',{get:()=>state,set:x=>{state=x;}});
  const fetch=(url,options)=>{
    const parsed=new URL(url,'https://unit.invalid');assert.equal(parsed.origin,'https://unit.invalid');
    assert.ok(['/api/v1/document-operations','/api/v1/asset-vault'].includes(parsed.pathname),parsed.pathname);
    assert.equal(options.method||'GET','GET');assert.equal(options.body,undefined);assert.equal(options.credentials,'same-origin');assert.equal(options.cache,'no-store');
    network.push({path:parsed.pathname,method:options.method||'GET',kind:parsed.searchParams.get('kind')});let resolve,reject;
    const promise=new Promise((a,b)=>{resolve=a;reject=b;});pending.push({resolve,reject,path:parsed.pathname});return promise;
  };
  const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,Blob,AbortController,Intl,console,fetch,crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop});
  vm.runInContext(i18n,sandbox);window.TOANAASI18n.setLocale(locale,{emit:false});
  const anchor='  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';assert.equal(integration.split(anchor).length-1,1);
  vm.runInContext(integration.replace(anchor,'  window.__docRefreshTest={session:()=>{operationHistorySessionEpoch+=1;},request:()=>{documentOperationHistoryHydrationEpoch+=1;}};\n'+anchor),sandbox);
  return{pending,toasts,network,messages:window.TOANAASI18n.messages,run(eventRoute=route){return listeners.get('toanaas:portal-action')({detail:{action:'document-operation-refresh',route:eventRoute,fields:{}}});},
    get state(){return state;},
    settle(index,{failed=false}={}){
      const p=pending[index];assert.ok(p);
      const isError=failed&&p.path==='/api/v1/document-operations';
      p.resolve({ok:!isError,status:isError?422:200,json:async()=>({ok:!isError,status:isError?'error':'read_only',message:isError?'SOURCE_FAILURE':'',data:{items:[],pagination:{total:0,limit:20,offset:0,returned:0,has_more:false,next_offset:null,previous_offset:null}}})});
    },
    mutate(kind){
      if(kind==='route'){state={...state,path:'/dashboard'};window.location.pathname='/dashboard';}
      if(kind==='session')window.__docRefreshTest.session();
      if(kind==='request')window.__docRefreshTest.request();
      if(kind==='logout')state={...state,session:{authenticated:false}};
      if(kind==='permission')state={...state,capabilities:{'document-operation-refresh':false}};
    }};
}
