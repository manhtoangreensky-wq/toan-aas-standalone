import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath,pathToFileURL} from 'node:url';
import test from 'node:test';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=process.env.WEBAPP_SOURCE_ROOT||path.resolve(here,'..');
const integration=fs.readFileSync(path.join(root,'static/portal/integration.js'),'utf8');
const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');
const {renderChild}=await import(pathToFileURL(path.join(root,'tests/helpers/publishing-child-render.mjs')));
const route='/video-studio/motion-guide';
const actorA='A';
const actorB='B';
const clone=value=>JSON.parse(JSON.stringify(value));
const defaultFields={topic_kind:'product',custom_topic:'',language:'vi',suggestion_set:'1',selected_suggestion:'0',style:'cinematic'};
const guideFixture={"guide":{"title":"GUIDE_TITLE CUSTOMER Studio media Facebook TikTok & tên riêng","topic_kind":"custom","topic":"TOPIC CUSTOMER Studio media Facebook TikTok & tên riêng","language":"en","style":{"id":"cinematic","label":"STYLE CUSTOMER Studio media Facebook TikTok & tên riêng"},"suggestion_set":0,"selected_suggestion":null,"idea_15_seconds":"IDEA_15 CUSTOMER Studio media Facebook TikTok & tên riêng","idea_30_seconds":"IDEA_30 CUSTOMER Studio media Facebook TikTok & tên riêng","timeline":[{"index":1,"start_seconds":0,"end_seconds":7,"direction":"TIMELINE_0 CUSTOMER Studio media Facebook TikTok & tên riêng"},{"index":2,"start_seconds":7,"end_seconds":14,"direction":"TIMELINE_1 CUSTOMER Studio media Facebook TikTok & tên riêng"},{"index":3,"start_seconds":14,"end_seconds":21,"direction":"TIMELINE_2 CUSTOMER Studio media Facebook TikTok & tên riêng"},{"index":4,"start_seconds":21,"end_seconds":30,"direction":"TIMELINE_3 CUSTOMER Studio media Facebook TikTok & tên riêng"}],"camera_motions":["CAMERA_0 CUSTOMER Studio media Facebook TikTok & tên riêng","CAMERA_1 CUSTOMER Studio media Facebook TikTok & tên riêng","CAMERA_2 CUSTOMER Studio media Facebook TikTok & tên riêng","CAMERA_3 CUSTOMER Studio media Facebook TikTok & tên riêng","CAMERA_4 CUSTOMER Studio media Facebook TikTok & tên riêng","CAMERA_5 CUSTOMER Studio media Facebook TikTok & tên riêng"],"image_prompt":"IMAGE_PROMPT CUSTOMER Studio media Facebook TikTok & tên riêng","video_motion_prompt":"VIDEO_PROMPT CUSTOMER Studio media Facebook TikTok & tên riêng","overlay_lines":["OVERLAY_0 CUSTOMER Studio media Facebook TikTok & tên riêng","OVERLAY_1 CUSTOMER Studio media Facebook TikTok & tên riêng","OVERLAY_2 CUSTOMER Studio media Facebook TikTok & tên riêng","OVERLAY_3 CUSTOMER Studio media Facebook TikTok & tên riêng"],"voiceover":"VOICEOVER CUSTOMER Studio media Facebook TikTok & tên riêng","cta":"CTA CUSTOMER Studio media Facebook TikTok & tên riêng","cautions":["CAUTION_1 CUSTOMER Studio media Facebook TikTok & tên riêng","CAUTION_2 CUSTOMER Studio media Facebook TikTok & tên riêng"],"review_before_use":["REVIEW_1 CUSTOMER Studio media Facebook TikTok & tên riêng","REVIEW_2 CUSTOMER Studio media Facebook TikTok & tên riêng"]},"execution":"web_native_deterministic_creative_motion_guide_only","input_persisted":false,"telegram_state_changed":false,"bot_called":false,"bridge_called":false,"source_media_inspected":false,"media_uploads":false,"provider_called":false,"image_created":false,"video_created":false,"audio_created":false,"preview_created":false,"output_created":false,"job_created":false,"wallet_mutated":false,"payment_started":false,"asset_saved":false,"publish_action_created":false,"delivery_created":false,"fact_checked":false,"rights_verified":false};
const falseFlags=['input_persisted','telegram_state_changed','bot_called','bridge_called','source_media_inspected','media_uploads','provider_called','image_created','video_created','audio_created','preview_created','output_created','job_created','wallet_mutated','payment_started','asset_saved','publish_action_created','delivery_created','fact_checked','rights_verified'];
function suggestions(){
  return {
    suggestions:{
      topic_kind:'product',topic_label:'Sản phẩm',language:'vi',suggestion_set:1,
      suggestions:[1,2,3].map(index=>({index,title:'Hướng sản phẩm '+index,
        video_prompt:'Mô tả sản phẩm '+index,motion:'Chuyển động nhẹ '+index,
        audio_direction:'Âm thanh nhẹ '+index}))
    },
    execution:'web_native_deterministic_creative_motion_guide_only',
    ...Object.fromEntries(falseFlags.map(key=>[key,false]))
  };
}
// browser_account_payload deliberately exposes presentation metadata, not id.
// Session fixtures are child-only synthetic values and differ across accounts.
function account(label=actorA){return {
  email:'actor-'+label.toLowerCase()+'@example.invalid',display_name:'Người dùng '+label,
  role:'user',telegram_linked:false,
  profile:{locale:'vi',timezone:'Asia/Ho_Chi_Minh',avatar_style:'gradient'},
  login_methods:{email:true,telegram_oidc:false,telegram:false,google:false,github:false,apple:false},
  oauth_only:false,account_type:'standard'
};}
function runtime({actor=actorA,sessionToken=true,signed=true,enabled=true,pathname=route}={}){
  const noop=()=>{},listeners=new Map(),toasts=[],post=[],authPending=[],requests=[];
  let fields=clone(defaultFields),readDeferred=false;
  let currentActor=actor;
  let meAccount=signed?account(actor):null;
  let featureEnabled=enabled;
  let state={path:pathname,profile:{locale:'vi'},session:{authenticated:false,csrfToken:''},
    creativeMotionGuideEnabled:false,creativeMotionGuideDraft:{},
    capabilities:{},bridge:{available:false},pageStates:{[pathname]:'guarded'}};
  let rendered=renderChild('vi',pathname,state);
  class NativeForm {
    constructor(){this.dataset={};}
    getAttribute(name){return name==='data-portal-action'?'creative-motion-guide-compose':name==='data-portal-route'?route:null;}
    setAttribute(){ }
    querySelector(){return null;}
    querySelectorAll(){return Object.entries(fields).map(([name,value])=>({name,value,type:'text',disabled:false}));}
  }
  const form=new NativeForm();
  const node=()=>({attributes:{},textContent:'',className:'',setAttribute(k,v){this.attributes[k]=String(v);},getAttribute(k){return this.attributes[k]??null;},remove(){const index=toasts.indexOf(this);if(index>=0)toasts.splice(index,1);}});
  const region={appendChild(n){toasts.push(n);},querySelectorAll:()=>toasts};
  const document={
    readyState:'loading',visibilityState:'visible',addEventListener:noop,createElement:node,
    querySelector(selector){if(selector==='[data-portal-toast]')return region;if(selector==='form[data-creative-motion-guide-form]'&&window.location.pathname===route)return form;return null;},
    querySelectorAll:()=>[],getElementById:()=>null,
    documentElement:{lang:'vi',setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop,toggle:noop}}
  };
  const window={
    document,navigator:{language:'vi'},location:{pathname,search:'',origin:'https://unit.invalid',href:'https://unit.invalid'+pathname,assign:noop,replace:noop},
    addEventListener:(name,handler)=>listeners.set(name,handler),dispatchEvent:noop,
    setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,
    localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},
    matchMedia:()=>({matches:false,addEventListener:noop}),crypto:globalThis.crypto
  };
  Object.defineProperty(window,'__TOAN_AAS_PORTAL__',{get:()=>state,set:value=>{state=value;}});
  window.TOANAASPortal={mount(raw){
    rendered=renderChild('vi',raw.path||window.location.pathname,raw);
    if(raw.creativeMotionGuideDraft&&Object.keys(raw.creativeMotionGuideDraft).length)fields={...fields,...raw.creativeMotionGuideDraft};
  },clearTransientFormDraft:noop};
  const response=data=>({ok:true,status:200,json:async()=>data});
  const fetch=(url,options={})=>{
    requests.push({url,method:options.method||'GET'});
    if(options.method==='POST'){
      let resolve;const promise=new Promise(done=>{resolve=done;});
      post.push({url,options,payload:JSON.parse(options.body),resolve});return promise;
    }
    if(url==='/api/v1/auth/me'){
      const payload={ok:true,data:{account:clone(meAccount),csrf_token:meAccount&&sessionToken?'synthetic-motion-session-'+currentActor:''}};
      if(readDeferred){let resolve;const promise=new Promise(done=>{resolve=done;});authPending.push({resolve,payload});return promise;}
      return Promise.resolve(response(payload));
    }
    if(url==='/api/v1/core/status')return Promise.resolve(response({ok:true,data:{flags:{video_studio_enabled:featureEnabled}}}));
    if(url==='/api/v1/catalog')return Promise.resolve(response({ok:true,data:{features:[]}}));
    if(url==='/api/v1/auth/providers')return Promise.resolve(response({ok:true,data:{providers:{}}}));
    if(url==='/api/v1/auth/telegram/connection/status')return Promise.resolve(response({ok:true,data:{}}));
    return Promise.resolve({ok:false,status:403,json:async()=>({ok:false,status:'guarded',data:{}})});
  };
  const CustomEvent=function(type,options){this.type=type;this.detail=options?.detail;};window.CustomEvent=CustomEvent;
  const sandbox=vm.createContext({window,document,navigator:window.navigator,HTMLFormElement:NativeForm,
    URL,URLSearchParams,Headers,FormData,Blob,AbortController,Intl,console,fetch,CustomEvent,
    crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop});
  vm.runInContext(i18n,sandbox);
  const anchor='  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", startInitialHydration, { once: true });';
  assert.ok(integration.includes(anchor));
  vm.runInContext(integration.replace(anchor,
    '  window.__actorTest={hydrate,readActor:()=>typeof creativeMotionGuideSessionToken==="string"?creativeMotionGuideSessionToken:""};\n'+anchor),sandbox);
  return {
    hydrate:()=>window.__actorTest.hydrate(),actor:()=>window.__actorTest.readActor(),
    run(action='creative-motion-guide-suggest',nextFields=clone(defaultFields)){
      fields={...nextFields};
      return listeners.get('toanaas:portal-action')({detail:{action,route,fields:{...fields}}});
    },
    settle(index=0,data=suggestions()){const entry=post[index];assert.ok(entry,'The actual action must issue a POST');entry.resolve(response({ok:true,status:'draft',data}));},
    holdReads(){readDeferred=true;},releaseRead(index=0){const pending=authPending[index];assert.ok(pending);pending.resolve(response(pending.payload));},
    switchAccount(next){currentActor=next;meAccount=next===null?null:account(next);},
    move(next){window.location.pathname=next;window.location.href='https://unit.invalid'+next;state={...state,path:next};},
    post,requests,authPending,toasts,get state(){return state;},get view(){return rendered;}
  };
}
function assertNoGlobalAccount(app){assert.equal(Object.hasOwn(app.state,'account'),false,'Signed hydration must not project a global account object to solve a route-private snapshot');}
function postCount(app){return app.post.filter(item=>item.url.startsWith('/api/v1/video-studio/tools/creative-motion-guide')).length;}

test('real signed hydration without base.account enables a finite suggestions request and renders three cards',async()=>{
  const app=runtime();assertNoGlobalAccount(app);await app.hydrate();assertNoGlobalAccount(app);
  assert.equal(app.state.session.authenticated,true);
  assert.equal(app.state.capabilities['creative-motion-guide-suggest'],true);
  const beforeOther=JSON.stringify([app.state.longFormRoadmapResult,app.state.imageMotionPlannerResult]);
  const done=app.run();
  assert.equal(postCount(app),1,'A hydrated signed actor must not fail closed because base.account is absent');
  assert.equal(app.post[0].url,'/api/v1/video-studio/tools/creative-motion-guide/suggestions');
  assert.equal(app.post[0].options.headers.get('X-CSRF-Token'),'synthetic-motion-session-'+actorA);
  app.settle();await done;
  assert.equal(app.view.context.creativeMotionGuideSuggestions.suggestions.suggestions.length,3);
  assert.equal((app.view.html.match(/data-creative-motion-guide-choice="/g)||[]).length,3);
  assertNoGlobalAccount(app);
  assert.equal(JSON.stringify([app.state.longFormRoadmapResult,app.state.imageMotionPlannerResult]),beforeOther);
});

test('real signed hydration also enables custom compose with no provider or wallet effects',async()=>{
  const app=runtime();await app.hydrate();
  const data=clone(guideFixture),guide=data.guide;
  const fields={topic_kind:'custom',custom_topic:guide.topic,language:guide.language,suggestion_set:'0',selected_suggestion:'0',style:guide.style.id};
  const done=app.run('creative-motion-guide-compose',fields);
  assert.equal(postCount(app),1);
  assert.equal(app.post[0].url,'/api/v1/video-studio/tools/creative-motion-guide');
  app.settle(0,data);await done;
  assert.equal(app.view.context.creativeMotionGuideResult.guide.title,guide.title);
  assert.equal(data.provider_called,false);assert.equal(data.wallet_mutated,false);assertNoGlobalAccount(app);
});

for(const [name,options] of [
  ['missing session token',{sessionToken:false}],['unsigned response',{signed:false}],
  ['disabled feature',{enabled:false}],['another route',{pathname:'/login'}]
]){
  test(name+' still blocks motion requests after real hydration',async()=>{
    const app=runtime(options);await app.hydrate();await app.run();assert.equal(postCount(app),0);assertNoGlobalAccount(app);
  });
}

test('a new pending hydration clears the private snapshot before its account response resolves',async()=>{
  const app=runtime();await app.hydrate();
  app.holdReads();const pending=app.hydrate();
  assert.equal(app.actor(),'');
  await app.run();assert.equal(postCount(app),0);
  app.releaseRead();await pending;assertNoGlobalAccount(app);
});

test('an old action response cannot merge after a new account hydration takes ownership',async()=>{
  const app=runtime();await app.hydrate();const old=app.run();
  assert.equal(postCount(app),1);
  app.switchAccount(actorB);await app.hydrate();app.settle();await old;
  assert.equal(JSON.stringify(app.view.context.creativeMotionGuideSuggestions),'{}');assertNoGlobalAccount(app);
});

test('a late response from the motion route cannot merge into a different current route',async()=>{
  const app=runtime();await app.hydrate();const old=app.run();
  assert.equal(postCount(app),1);app.move('/login');app.settle();await old;
  assert.equal(JSON.stringify(app.state.creativeMotionGuideSuggestions),'{}');assertNoGlobalAccount(app);
});
