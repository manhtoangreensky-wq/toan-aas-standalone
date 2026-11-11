import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../../static/portal/integration.js',import.meta.url),'utf8');
const sample=JSON.parse(fs.readFileSync(new URL('../fixtures/last-two-planner-results.json',import.meta.url),'utf8')).rows.find(row=>row.part==='reference');
export const route='/video-studio/reference-format-planner';
export const original=()=>structuredClone(sample);
export function resultFor(fields, title='OWNED_RESULT'){
  const data=structuredClone(sample.result),p=data.planner;
  p.topic=fields.topic;p.audience=fields.audience;p.language=fields.language;p.title=title;
  for(const key of ['direction','platform','goal','tone'])p[key]={...p[key],id:fields[key]};
  return data;
}
export function createReferenceRuntime(options={}){
  const integrationSource=options.integrationSource||source;
  const noop=()=>{},listeners=new Map(),documentListeners=new Map(),requests=[],bootstrapRequests=[],bootstrapErrors=[],mounts=[],toasts=[],timers=[];
  class Element{
    constructor(attributes={}){this.attributes={...attributes};this.dataset={};this.disabled=false;this.className='';this.textContent='';}
    getAttribute(key){return Object.hasOwn(this.attributes,key)?this.attributes[key]:null;}
    setAttribute(key,value){this.attributes[key]=String(value);}
    removeAttribute(key){delete this.attributes[key];}
    toggleAttribute(key,value){if(value)this.setAttribute(key,'');else this.removeAttribute(key);}
    closest(selector){return selector.includes('form')?form:null;}
    addEventListener(){}
    remove(){const i=toasts.indexOf(this);if(i>=0)toasts.splice(i,1);}
  }
  class Input extends Element{};class Select extends Element{};class Textarea extends Element{};
  let fields=structuredClone(sample.source);
  const fieldControls=new Map();
  let compose=new Element({'data-portal-action':'reference-format-planner-compose','data-portal-route':route});
  let save=new Element({'data-portal-action':'reference-format-planner-save-plan','data-portal-route':route});
  class Form extends Element{
    constructor(){super({'data-portal-action':'reference-format-planner-compose','data-portal-route':route,'data-portal-form':''});}
    querySelector(selector){if(selector.includes('button'))return compose;if(selector.includes('stale-note'))return note;const name=selector.match(/name="([^"]+)"/)?.[1];return name?nativeFields().find(item=>item.name===name)||null:null;}
    querySelectorAll(selector){return selector.includes('input')||selector.includes('select')||selector.includes('textarea')?nativeFields():[];}
    contains(node){return node===this||node===compose||node===save||nativeFields().includes(node);}
    get elements(){const list=nativeFields();list.namedItem=name=>list.find(field=>field.name===name)||null;return list;}
  }
  let form=new Form();const note=new Element();note.hidden=true;
  function nativeFields(){return Object.entries(fields).map(([name,value])=>{
    if(!fieldControls.has(name))fieldControls.set(name,Object.assign(new Select(),{name,form}));
    return Object.assign(fieldControls.get(name),{value:String(value),form});
  });}
  class FormData{
    constructor(input){assert.equal(input,form,'Only the actual current form may be read');this.entries=Object.entries(fields).filter(([name])=>!nativeFields().find(field=>field.name===name)?.disabled);}
    forEach(callback){this.entries.forEach(([key,value])=>callback(String(value),key));}
    get(key){return fields[key]??null;}
  }
  const region={children:toasts,querySelectorAll:()=>toasts,appendChild:node=>toasts.push(node)};
  const document={readyState:'loading',visibilityState:'visible',title:'',
    addEventListener:(name,fn)=>{const list=documentListeners.get(name)||[];list.push(fn);documentListeners.set(name,list);},
    querySelector:selector=>selector==='[data-portal-toast]'?region:selector.includes('form')?form:null,
    querySelectorAll:selector=>selector==='[data-portal-action]'?[compose,save]:selector==='[data-portal-form]'?[form]:selector.includes('reference-format-planner-save-plan')?[save]:selector.includes('form')&&selector.includes('reference-format-planner-compose')?[form]:[],
    createElement:()=>new Element(),documentElement:{lang:'vi',setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},
    body:{appendChild:noop,classList:{add:noop,remove:noop,toggle:noop}}};
  const initial={path:route,account:{role:'user'},session:{authenticated:true,csrfToken:'synthetic-reference-session-a'},
    capabilities:{'reference-format-planner-view':true,'reference-format-planner-compose':true,'reference-format-planner-save-plan':true,'video-plan-create':true},
    videoStudioEnabled:true,referenceFormatPlannerEnabled:true,referenceFormatPlannerReadState:'ready',
    referenceFormatPlannerReferences:[structuredClone(sample.result.planner.reference)],referenceFormatPlannerResult:structuredClone(sample.result),
    referenceFormatPlannerSaveSource:structuredClone(sample.source),referenceFormatPlannerSaveReceipt:{},pageStates:{[route]:'ready'}};
  const window={__TOAN_AAS_PORTAL__:initial,document,navigator:{language:'vi'},
    location:{pathname:route,search:'',origin:'https://unit.invalid',href:'https://unit.invalid'+route,assign:noop},
    TOANAASPortal:{mount:state=>mounts.push(JSON.parse(JSON.stringify(state)))},
    addEventListener:(name,fn)=>{const list=listeners.get(name)||[];list.push(fn);listeners.set(name,list);},
    dispatchEvent:event=>{for(const fn of listeners.get(event.type)||[])fn(event);return true;},
    setTimeout:(fn,ms)=>{timers.push({fn,ms});return timers.length;},clearTimeout:noop,setInterval:()=>0,clearInterval:noop,
    localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},matchMedia:()=>({matches:false,addEventListener:noop})};
  const fetch=(url,options={})=>new Promise((resolve,reject)=>{
    if(!options.method||options.method==='GET'){bootstrapRequests.push({url:String(url)});return;}
    assert.equal(options.method,'POST','Witness only performs explicit planner POSTs');
    assert.ok([route.replace('/video-studio/','/api/v1/video-studio/tools/'),'/api/v1/video-studio/tools/reference-format-planner/save'].some(path=>String(url).endsWith(path)),'Unexpected endpoint '+url);
    requests.push({url:String(url),options,payload:JSON.parse(options.body),resolve,reject});
  });
  const sandbox=vm.createContext({window,document,navigator:window.navigator,console,Intl,URL,URLSearchParams,Headers,Response,Blob,AbortController,FormData,
    HTMLFormElement:Form,HTMLElement:Element,HTMLInputElement:Input,HTMLSelectElement:Select,HTMLTextAreaElement:Textarea,
    crypto:globalThis.crypto,CustomEvent:class{constructor(type,init={}){this.type=type;this.detail=init.detail;}},Event:class{constructor(type){this.type=type;}},
    setTimeout:window.setTimeout,clearTimeout:noop,fetch});
  const end=integrationSource.lastIndexOf('}());');assert.ok(end>0);
  vm.runInContext(integrationSource.slice(0,end)+'window.__referenceTest={handleAction,hydrate,referenceFormatPlannerResultIsSafe,referenceFormatPlanSaveReceipt,seedOwnership(value){if(typeof referenceFormatPlannerSessionToken!=="undefined")referenceFormatPlannerSessionToken=value;}};\n'+integrationSource.slice(end),sandbox);
  window.__referenceTest.seedOwnership(initial.session.csrfToken);
  assert.equal(window.__referenceTest.referenceFormatPlannerResultIsSafe(structuredClone(sample.result)),true,'Genuine public envelope accepted by actual validator');
  const api={
    window,document,requests,bootstrapRequests,bootstrapErrors,mounts,toasts,timers,
    get state(){return window.__TOAN_AAS_PORTAL__;},get fields(){return fields;},get compose(){return compose;},get save(){return save;},get nativeFields(){return nativeFields();},
    action(kind,values=fields){return window.__referenceTest.handleAction({detail:{action:'reference-format-planner-'+kind,route,fields:structuredClone(values)}});},
    success(index,data,status='ready',message=''){requests[index].resolve(new Response(JSON.stringify({ok:true,status,message,data}),{status:200,headers:{'Content-Type':'application/json'}}));},
    fail(index,status=503,message='OWNED_CURRENT_ERROR'){requests[index].resolve(new Response(JSON.stringify({ok:false,message}),{status,headers:{'Content-Type':'application/json'}}));},
    transportFail(index){requests[index].reject(new TypeError('Owned response lost'));},
    edit(next){fields={...fields,...next};for(const name of ['input','change'])for(const fn of documentListeners.get(name)||[])fn({target:Object.assign(new Select(),{name:Object.keys(next)[0],form})});
      window.dispatchEvent({type:'toanaas:reference-format-planner-draft-edited'});},
    navigate(path){window.location.pathname=path;window.__TOAN_AAS_PORTAL__={...api.state,path};},
    newSession(){window.__TOAN_AAS_PORTAL__={...api.state,account:{role:'user'},session:{authenticated:true,csrfToken:'synthetic-reference-session-b'},referenceFormatPlannerResult:{newer:'NEW_ACCOUNT_RESULT'},referenceFormatPlannerSaveSource:{newer:'NEW_ACCOUNT_SOURCE'},referenceFormatPlannerSaveReceipt:{newer:'NEW_ACCOUNT_RECEIPT'}};},
    unsigned(){window.__TOAN_AAS_PORTAL__={...api.state,session:{authenticated:false,csrfToken:''}};},
    clear(){void window.__referenceTest.hydrate().catch(error=>bootstrapErrors.push(error.message));},
    replaceControls(busy=true){compose=new Element({'data-portal-action':'reference-format-planner-compose','data-portal-route':route});save=new Element({'data-portal-action':'reference-format-planner-save-plan','data-portal-route':route});form=new Form();compose.disabled=busy;save.disabled=busy;},
    snapshot(){return JSON.stringify({result:api.state.referenceFormatPlannerResult,source:api.state.referenceFormatPlannerSaveSource,receipt:api.state.referenceFormatPlannerSaveReceipt});}
  };return api;
}
