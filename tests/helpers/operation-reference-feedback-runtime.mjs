import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {operationReferenceStaleFeedbackHistoricalIntegrationSource} from "./operation-reference-stale-feedback-snapshot.mjs";
import {imageResizeGuidanceHistoricalI18nSource} from "./image-resize-guidance-snapshot.mjs";
import {pdfSplitMetaHistoricalPortalSource} from "./pdf-split-meta-snapshot.mjs";
import {resizePolishHistoricalThemeSource} from "./image-resize-polish-snapshot.mjs";
const files={integration:"static/portal/integration.js",i18n:"static/portal/portal-i18n.js",portal:"static/portal/portal.js",theme:"static/portal/portal-theme.css"};
export const REFERENCE_CUSTOMER='CUSTOMER Bot provider media CSRF Facebook TikTok <img src=x onerror="alert(1)">&';
export const REFERENCE_IDS=Object.freeze(["11111111-1111-4111-8111-111111111111","22222222-2222-4222-8222-222222222222","33333333-3333-4333-8333-333333333333"]);
export function operationReferenceFeedbackSources(base){
  if(base!==undefined)assert.match(base,/^[a-f0-9]{40}$/,"Bind actual delivered full 40-hex reference-feedback BASE before git");
  const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
  return Object.fromEntries(Object.entries(files).map(([key,file])=>{
    const value=(base===undefined
    ?fs.readFileSync(path.join(root,file),"utf8")
    :execFileSync("git",["show",base+":"+file],{cwd:root,encoding:"utf8",maxBuffer:30e6})).replace(/\r\n/g,"\n");
    return [key,key==="integration"?operationReferenceStaleFeedbackHistoricalIntegrationSource(value):key==="i18n"?imageResizeGuidanceHistoricalI18nSource(value):key==="portal"?pdfSplitMetaHistoricalPortalSource(value):resizePolishHistoricalThemeSource(value)];
  }));
}
const metadata=(id,kind)=>({id,display_name:REFERENCE_CUSTOMER,original_filename:REFERENCE_CUSTOMER+(kind==="pdf"?".pdf":".png"),
  extension:kind==="pdf"?".pdf":".png",content_type:kind==="pdf"?"application/pdf":"image/png",state:"active",byte_size:1024,updated_at:"2026-11-16T16:00:00Z"});
export function operationReferenceFeedbackRuntime(locale="vi",route="/documents/split",overrides){
  // Explicit overrides perform no fixture/default-source reads: this entry is importable from an artifact folder.
  const sources=overrides===undefined?operationReferenceFeedbackSources():overrides;
  assert.equal(typeof sources.integration,"string");assert.equal(typeof sources.i18n,"string");
  const isDocument=route.startsWith("/documents/"),kind=isDocument?"pdf":"image",prefix=isDocument?"document":"image-operation";
  const selected=metadata(REFERENCE_IDS[0],kind),pinned=metadata(REFERENCE_IDS[1],kind),received=metadata(REFERENCE_IDS[2],kind);
  const listing={kind,filters:{q:"OLD CUSTOMER"},pagination:{limit:50,offset:0,returned:1,has_more:false,next_offset:null,previous_offset:null}};
  let state={path:route,session:{authenticated:true,csrfToken:"synthetic-owned-only"},capabilities:{"document-operation-view":true,"image-operation-view":true},
    assetVaultEnabled:true,assetVaultReadState:"ready",documentAssetReferenceReadState:"ready",imageOperationAssetReferenceReadState:"ready",
    documentAssetReferences:{pdf:kind==="pdf"?[selected]:[],image:[],pinned_pdf:kind==="pdf"?[pinned]:[],pinned_image:[],pdf_listing:listing},
    imageOperationAssetReferences:{items:kind==="image"?[selected]:[],pinned:kind==="image"?[pinned]:[],listing},pageStates:{[route]:"ready"},bridge:{available:false}};
  const listeners=new Map(),pending=[],toasts=[],network=[],noop=()=>{};
  const node=()=>({className:"",textContent:"",attributes:{},get innerHTML(){return "";},set innerHTML(_){throw Error("Toast must use plain textContent, not HTML");},
    setAttribute(key,value){this.attributes[key]=value;},getAttribute(key){return this.attributes[key]??null;},remove(){const index=toasts.indexOf(this);if(index>=0)toasts.splice(index,1);}});
  const region={appendChild:value=>toasts.push(value),querySelectorAll:()=>toasts};
  const document={readyState:"loading",visibilityState:"visible",addEventListener:noop,createElement:tag=>{assert.equal(tag,"div");return node();},
    querySelector:selector=>selector==="[data-portal-toast]"?region:null,querySelectorAll:()=>[],documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop,toggle:noop}}};
  const window={document,navigator:{language:locale},location:{pathname:route,search:"",origin:"https://unit.invalid",href:"https://unit.invalid"+route,assign:noop},
    addEventListener:(name,fn)=>listeners.set(name,fn),dispatchEvent:noop,setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,
    matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},crypto:globalThis.crypto};
  Object.defineProperty(window,"__TOAN_AAS_PORTAL__",{get:()=>state,set:value=>{state=value;}});
  const fetch=(url,options={})=>{
    const parsed=new URL(url,"https://unit.invalid");assert.equal(parsed.origin,"https://unit.invalid");assert.equal(parsed.pathname,"/api/v1/asset-vault");
    assert.equal(options.method||"GET","GET");assert.equal(options.body,undefined);assert.equal(options.credentials,"same-origin");assert.equal(options.cache,"no-store");
    assert.equal(options.headers.get("Accept"),"application/json");
    assert.ok([...parsed.searchParams.keys()].every(key=>["reference_kind","limit","offset","q"].includes(key)));
    const entry={path:parsed.pathname,method:"GET",query:Object.fromEntries(parsed.searchParams)};network.push(entry);
    let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});pending.push({resolve,reject,entry,settled:false});return promise;
  };
  const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,Blob,AbortController,Intl,console,fetch,
    crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop});
  vm.runInContext(sources.i18n,sandbox);const normalI18n=window.TOANAASI18n;normalI18n.setLocale(locale,{emit:false});
  // Keep the real frozen catalogue/export intact; vary only the owned integration window boundary.
  let integrationI18n=normalI18n;
  const integrationWindow=Object.create(window);Object.defineProperty(integrationWindow,"TOANAASI18n",{get:()=>integrationI18n});
  sandbox.window=integrationWindow;
  const anchor='  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.equal(sources.integration.split(anchor).length-1,1,"Unique initial-hydration exposure anchor");
  const exposure='  window.__operationReferenceProbe={session:()=>{assetVaultSessionEpoch+=1;},documentRequest:kind=>{documentAssetReferenceHydrationEpoch[kind]+=1;},imageRequest:()=>{imageOperationAssetReferenceHydrationEpoch+=1;}};\n';
  vm.runInContext(sources.integration.replace(anchor,exposure+anchor),sandbox);
  assert.equal(network.length,0,"DOMContentLoaded hydration remains suppressed");
  return {pending,toasts,network,messages:normalI18n.messages,selected,pinned,received,
    get state(){return state;},
    run(action="filter",fields={},eventRoute=route){
      const suffix=action==="clear"?"filter-clear":action;
      return listeners.get("toanaas:portal-action")({detail:{action:prefix+"-asset-reference-"+suffix,route:eventRoute,fields}});
    },
    settle(index,{failed=false,data}={}){
      const entry=pending[index];assert.ok(entry);assert.equal(entry.settled,false);entry.settled=true;
      const offset=Number(entry.entry.query.offset),q=entry.entry.query.q||"";
      const responseData=data??{items:[received],has_more:true,next_offset:offset+50,filters:{q},pagination:{limit:50,offset,returned:1,has_more:true,next_offset:offset+50,previous_offset:offset>=50?offset-50:null}};
      entry.resolve({ok:!failed,status:failed?422:200,json:async()=>({ok:!failed,status:failed?"error":"read_only",message:failed?"SYNTHETIC_READ_FAILURE":"",data:failed?{}:responseData})});
    },
    mutate(type,value){
      if(type==="route"){state={...state,path:value||"/dashboard"};window.location.pathname=value||"/dashboard";}
      else if(type==="session")integrationWindow.__operationReferenceProbe.session();
      else if(type==="request"){if(isDocument)integrationWindow.__operationReferenceProbe.documentRequest(kind);else integrationWindow.__operationReferenceProbe.imageRequest();}
      else if(type==="logout")state={...state,session:{authenticated:false}};
      else if(type==="permission")state={...state,capabilities:{...state.capabilities,[isDocument?"document-operation-view":"image-operation-view"]:value}};
      else throw Error("Unknown controlled boundary mutation");
    },
    setLocale:value=>normalI18n.setLocale(value,{emit:false}),
    translation(mode,value){
      if(mode==="missing")integrationI18n=undefined;
      else if(mode==="empty")integrationI18n={t:()=>""};
      else if(mode==="hostile")integrationI18n={...normalI18n,t:key=>key.startsWith("operationReferenceFeedback.")?value:normalI18n.t(key)};
      else if(mode==="normal")integrationI18n=normalI18n;
      else throw Error("Unknown translation boundary mode");
    },
    observe(){return {network:JSON.parse(JSON.stringify(network)),state:JSON.parse(JSON.stringify(state)),toasts:toasts.map(value=>({text:value.textContent,role:value.attributes.role}))};}
  };
}
