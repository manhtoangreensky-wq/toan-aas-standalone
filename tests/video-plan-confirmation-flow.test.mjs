import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath, pathToFileURL} from 'node:url';
import test from 'node:test';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = process.env.WEBAPP_SOURCE_ROOT || path.resolve(here, '..');
const integrationPath = process.env.WEBAPP_INTEGRATION_SOURCE || path.join(root, 'static/portal/integration.js');
const integration = fs.readFileSync(integrationPath, 'utf8');
const portal = fs.readFileSync(path.join(root, 'static/portal/portal.js'), 'utf8');
const i18n = fs.readFileSync(path.join(root, 'static/portal/portal-i18n.js'), 'utf8');
const {renderChild} = await import(pathToFileURL(path.join(root, 'tests/helpers/publishing-child-render.mjs')));
const route = '/video-studio/long-form-planner';
const action = 'long-form-roadmap-save-plan';
const id = '11111111-1111-4111-8111-111111111111';
const planPath = '/video-studio/' + id;
const clone = value => JSON.parse(JSON.stringify(value));
const sourceFixture = {"capabilities":{"long-form-roadmap-compose":true,"long-form-roadmap-save-plan":true,"video-plan-create":true},"longFormRoadmapResult":{"roadmap":{"title":"ROADMAP_TITLE CUSTOMER Studio media Facebook TikTok & tên riêng","topic_category":"education","topic":"TOPIC CUSTOMER Studio media Facebook TikTok & tên riêng","audience":"AUDIENCE CUSTOMER Studio media Facebook TikTok & tên riêng","duration_minutes":3,"target_duration_seconds":180,"style":"professional","style_label":"STYLE CUSTOMER Studio media Facebook TikTok & tên riêng","structure_mode":"chapters","structure":"STRUCTURE CUSTOMER Studio media Facebook TikTok & tên riêng","platform":"facebook","aspect_ratio":"16:9","language":"en","chapter_count":3,"outline":["OUTLINE_0 CUSTOMER Studio media Facebook TikTok & tên riêng","OUTLINE_1 CUSTOMER Studio media Facebook TikTok & tên riêng","OUTLINE_2 CUSTOMER Studio media Facebook TikTok & tên riêng","OUTLINE_3 CUSTOMER Studio media Facebook TikTok & tên riêng"],"character_bible":["CHARACTER_0 CUSTOMER Studio media Facebook TikTok & tên riêng","CHARACTER_1 CUSTOMER Studio media Facebook TikTok & tên riêng","CHARACTER_2 CUSTOMER Studio media Facebook TikTok & tên riêng","CHARACTER_3 CUSTOMER Studio media Facebook TikTok & tên riêng"],"chapters":[{"index":1,"start_seconds":0,"end_seconds":60,"title":"CHAPTER_TITLE_0 CUSTOMER Studio media Facebook TikTok & tên riêng","objective":"OBJECTIVE_0 CUSTOMER Studio media Facebook TikTok & tên riêng","hook":"HOOK_0 CUSTOMER Studio media Facebook TikTok & tên riêng","script_beat":"SCRIPT_0 CUSTOMER Studio media Facebook TikTok & tên riêng","visual_direction":"VISUAL_0 CUSTOMER Studio media Facebook TikTok & tên riêng","image_prompt":"IMAGE_0 CUSTOMER Studio media Facebook TikTok & tên riêng","video_prompt":"VIDEO_0 CUSTOMER Studio media Facebook TikTok & tên riêng","voice_direction":"VOICE_0 CUSTOMER Studio media Facebook TikTok & tên riêng","music_sfx_direction":"MUSIC_0 CUSTOMER Studio media Facebook TikTok & tên riêng","transition":"TRANSITION_0 CUSTOMER Studio media Facebook TikTok & tên riêng"},{"index":2,"start_seconds":60,"end_seconds":120,"title":"CHAPTER_TITLE_1 CUSTOMER Studio media Facebook TikTok & tên riêng","objective":"OBJECTIVE_1 CUSTOMER Studio media Facebook TikTok & tên riêng","hook":"HOOK_1 CUSTOMER Studio media Facebook TikTok & tên riêng","script_beat":"SCRIPT_1 CUSTOMER Studio media Facebook TikTok & tên riêng","visual_direction":"VISUAL_1 CUSTOMER Studio media Facebook TikTok & tên riêng","image_prompt":"IMAGE_1 CUSTOMER Studio media Facebook TikTok & tên riêng","video_prompt":"VIDEO_1 CUSTOMER Studio media Facebook TikTok & tên riêng","voice_direction":"VOICE_1 CUSTOMER Studio media Facebook TikTok & tên riêng","music_sfx_direction":"MUSIC_1 CUSTOMER Studio media Facebook TikTok & tên riêng","transition":"TRANSITION_1 CUSTOMER Studio media Facebook TikTok & tên riêng"},{"index":3,"start_seconds":120,"end_seconds":180,"title":"CHAPTER_TITLE_2 CUSTOMER Studio media Facebook TikTok & tên riêng","objective":"OBJECTIVE_2 CUSTOMER Studio media Facebook TikTok & tên riêng","hook":"HOOK_2 CUSTOMER Studio media Facebook TikTok & tên riêng","script_beat":"SCRIPT_2 CUSTOMER Studio media Facebook TikTok & tên riêng","visual_direction":"VISUAL_2 CUSTOMER Studio media Facebook TikTok & tên riêng","image_prompt":"IMAGE_2 CUSTOMER Studio media Facebook TikTok & tên riêng","video_prompt":"VIDEO_2 CUSTOMER Studio media Facebook TikTok & tên riêng","voice_direction":"VOICE_2 CUSTOMER Studio media Facebook TikTok & tên riêng","music_sfx_direction":"MUSIC_2 CUSTOMER Studio media Facebook TikTok & tên riêng","transition":"TRANSITION_2 CUSTOMER Studio media Facebook TikTok & tên riêng"}],"audio_direction":"AUDIO CUSTOMER Studio media Facebook TikTok & tên riêng","caption":"CAPTION CUSTOMER Studio media Facebook TikTok & tên riêng","cta":"CTA CUSTOMER Studio media Facebook TikTok & tên riêng","review_before_use":["REVIEW_1 CUSTOMER Studio media Facebook TikTok & tên riêng","REVIEW_2 CUSTOMER Studio media Facebook TikTok & tên riêng"]},"execution":"web_native_deterministic_long_form_roadmap_only","input_persisted":false,"telegram_state_changed":false,"bot_called":false,"bridge_called":false,"source_media_inspected":false,"provider_called":false,"image_created":false,"video_created":false,"audio_created":false,"preview_created":false,"output_created":false,"job_created":false,"payment_started":false,"wallet_mutated":false,"asset_saved":false,"publish_action_created":false,"fact_checked":false,"rights_verified":false},"longFormRoadmapSaveSource":{"topic_category":"education","topic":"TOPIC CUSTOMER Studio media Facebook TikTok & tên riêng","audience":"AUDIENCE CUSTOMER Studio media Facebook TikTok & tên riêng","duration_minutes":3,"style":"professional","custom_style":"","structure_mode":"chapters","custom_structure":"","platform":"facebook","language":"en"}};
const receiptFixture = {"destination":"video_plan","plan":{"id":"11111111-1111-4111-8111-111111111111","revision":1,"state":"draft"},"scene_count":3,"execution":"web_native_video_plan_server_recomputed","draft_recomputed_on_server":true,"web_video_plan_persisted":true,"browser_result_persisted":false,"pending_bot_save_created":false,"telegram_state_changed":false,"bot_called":false,"bridge_called":false,"source_media_inspected":false,"media_uploads":false,"provider_called":false,"image_created":false,"video_created":false,"audio_created":false,"preview_created":false,"output_created":false,"job_created":false,"wallet_mutated":false,"payment_started":false,"asset_saved":false,"publish_action_created":false,"delivery_created":false,"approval_created":false,"plan_approved":false,"plan_locked":false,"generation_started":false,"fact_checked":false,"rights_verified":false};
const titles = {vi:'Đã lưu bản nháp kế hoạch video dài', en:'Long-form video plan draft saved', zh:'已保存长视频计划草稿'};

function runtime(locale = 'vi', options = {}) {
  const listeners = new Map(), pending = [], transport = [], toasts = [];
  let state = {
    ...clone(sourceFixture), path: route,
    account:{id:'22222222-2222-4222-8222-222222222222'},
    profile:{locale}, interfaceLocale:locale,
    session:{authenticated:true,csrfToken:'synthetic-confirmation-only'},
    longFormRoadmapEnabled:true,
    longFormRoadmapSaveReceipt:{},
    pageStates:{[route]:'ready'}
  };
  if (options.deny) state.capabilities[options.deny] = false;
  if (options.mismatch) state.longFormRoadmapSaveSource.topic = 'Different original brief';
  const noop=()=>{};
  const node=(attrs={})=>({
    attributes:{...attrs},textContent:'',className:'',disabled:false,
    setAttribute(key,value){this.attributes[key]=String(value);},
    getAttribute(key){return this.attributes[key]??null;},
    removeAttribute(key){delete this.attributes[key];},
    remove(){const offset=toasts.indexOf(this);if(offset>=0)toasts.splice(offset,1);}
  });
  const region={appendChild(value){toasts.push(value);},querySelectorAll:()=>toasts};
  const document={
    readyState:'loading',visibilityState:'visible',addEventListener:noop,
    createElement:()=>node(),querySelector:selector=>selector==='[data-portal-toast]'?region:null,
    querySelectorAll:()=>[],
    documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},
    body:{classList:{add:noop,remove:noop,toggle:noop}}
  };
  const window={
    document,navigator:{language:locale},
    location:{pathname:route,search:'',origin:'https://unit.invalid',href:'https://unit.invalid'+route,assign:()=>{throw Error('Unexpected navigation');}},
    addEventListener:(name,handler)=>listeners.set(name,handler),dispatchEvent:noop,
    setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,
    localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},
    sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},
    matchMedia:()=>({matches:false,addEventListener:noop}),crypto:globalThis.crypto
  };
  Object.defineProperty(window,'__TOAN_AAS_PORTAL__',{get:()=>state,set:value=>{state=value;}});
  // The real action/merge executes unchanged. Its mount boundary is connected
  // to the existing real Portal normalizeBootstrap -> renderPage harness.
  let rendered=renderChild(locale,route,state);
  window.TOANAASPortal={mount(raw){rendered=renderChild(locale,route,raw);}};
  const fetch=(url,request)=>{
    const payload=JSON.parse(request.body);
    transport.push({url,request,payload});
    let resolve,reject;
    const response=new Promise((a,b)=>{resolve=a;reject=b;});
    pending.push({resolve,reject});
    return response;
  };
  const sandbox=vm.createContext({
    window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,
    Blob,AbortController,Intl,console,fetch,crypto:globalThis.crypto,
    setTimeout:window.setTimeout,clearTimeout:noop
  });
  vm.runInContext(i18n,sandbox);
  window.TOANAASI18n.setLocale(locale,{emit:false});
  vm.runInContext(integration,sandbox);
  assert.ok(listeners.has('toanaas:portal-action'),'The real integration action listener must be registered');
  return {
    run:()=>listeners.get('toanaas:portal-action')({detail:{action,route,fields:{}}}),
    settle(...args){
      const data=args.length?args[0]:clone(receiptFixture),status=args.length>1?args[1]:'draft';
      const entry=pending.find(item=>!item.done);
      assert.ok(entry,'Action must reach the controlled API boundary');
      entry.done=true;
      entry.resolve({ok:true,status:200,json:async()=>({ok:true,status,message:'',data})});
    },
    get state(){return state;},get view(){return rendered;},transport,toasts
  };
}

for (const locale of ['vi','en','zh']) {
  test(locale+': actual save action retains validated transport through merge and Portal normalization',async()=>{
    const app=runtime(locale),before=JSON.stringify(receiptFixture),completion=app.run();
    assert.equal(app.transport.length,1);
    const {url,request,payload}=app.transport[0];
    assert.equal(url,'/api/v1/video-studio/tools/long-form-roadmap/save');
    assert.equal(request.method,'POST');
    assert.equal(request.credentials,'same-origin');
    assert.equal(request.headers.get('X-CSRF-Token'),'synthetic-confirmation-only');
    const {idempotency_key,...body}=payload;
    assert.match(idempotency_key,/^video-studio:long-form-roadmap:save-plan-[a-f0-9]{32}$/);
    assert.deepEqual(body,{...sourceFixture.longFormRoadmapSaveSource,destination:'video_plan'});
    app.settle();await completion;
    assert.equal(JSON.stringify(receiptFixture),before);
    assert.equal(JSON.stringify(app.view.context.longFormRoadmapSaveReceipt),JSON.stringify({
      destination:'video_plan',plan:{id,revision:1,state:'draft'},scene_count:3
    }),'The actual integration result must survive strict Portal normalization');
    assert.ok(app.view.html.includes('href="'+planPath+'"'),'The saved draft must expose its own plan link');
    assert.ok(app.view.html.includes(titles[locale]),'The real rendered confirmation must follow the interface locale');
    assert.equal(app.toasts.some(item=>item.getAttribute('role')==='alert'),false);
  });
  test(locale+': duplicate pending save does not create a second write',async()=>{
    const app=runtime(locale),first=app.run(),duplicate=app.run();
    await duplicate;
    assert.equal(app.transport.length,1);
    app.settle();await first;
    assert.ok(app.view.html.includes('href="'+planPath+'"'));
    const acknowledgedKey=app.transport[0].payload.idempotency_key;
    const intentionalNext=app.run();
    assert.equal(app.transport.length,2);
    assert.notEqual(app.transport[1].payload.idempotency_key,acknowledgedKey,
      'After acknowledgment, a new deliberate save must use a fresh intent');
    app.settle();await intentionalNext;
    assert.ok(app.view.html.includes(titles[locale]));
  });
  for (const capability of ['long-form-roadmap-compose','long-form-roadmap-save-plan','video-plan-create']) {
    test(locale+': missing '+capability+' blocks save without output',async()=>{
      const app=runtime(locale,{deny:capability});await app.run();
      assert.equal(app.transport.length,0);
      assert.equal(app.view.html.includes(planPath),false);
      assert.ok(app.toasts.some(item=>item.getAttribute('role')==='alert'));
    });
  }
  test(locale+': mismatched original brief cannot be saved',async()=>{
    const app=runtime(locale,{mismatch:true});await app.run();
    assert.equal(app.transport.length,0);
    assert.equal(app.view.html.includes(planPath),false);
    assert.ok(app.toasts.some(item=>item.getAttribute('role')==='alert'));
  });
}

const invalid=[];
function reject(name,mutate){const value=clone(receiptFixture);mutate(value);invalid.push({name,value});}
reject('missing boundary',v=>{delete v.provider_called;});
reject('extra transport field',v=>{v.extra='not-allowed';});
reject('provider side effect',v=>{v.provider_called=true;});
reject('wallet side effect',v=>{v.wallet_mutated=true;});
reject('unconfirmed persistence',v=>{v.web_video_plan_persisted=false;});
reject('not recomputed',v=>{v.draft_recomputed_on_server=false;});
reject('wrong destination',v=>{v.destination='asset';});
reject('wrong execution',v=>{v.execution='provider_output';});
reject('unsafe id',v=>{v.plan.id='../../other-account';});
reject('extra plan field',v=>{v.plan.owner_id='other-account';});
reject('wrong revision',v=>{v.plan.revision=2;});
reject('wrong state',v=>{v.plan.state='approved';});
reject('too few chapters',v=>{v.scene_count=2;});
invalid.push({name:'missing receipt',value:undefined},{name:'null receipt',value:null},{name:'empty receipt',value:{}},
  {name:'compact raw receipt',value:{destination:receiptFixture.destination,plan:receiptFixture.plan,scene_count:3}});
for (const locale of ['vi','en','zh']) for (const variant of invalid) {
  test(locale+': actual save action rejects '+variant.name+' before confirmation',async()=>{
    const app=runtime(locale),completion=app.run();
    app.settle(variant.value===undefined?undefined:clone(variant.value));await completion;
    assert.equal(app.transport.length,1);
    assert.equal(JSON.stringify(app.view.context.longFormRoadmapSaveReceipt),'{}');
    assert.equal(app.view.html.includes(planPath),false);
    for (const title of Object.values(titles)) assert.equal(app.view.html.includes(title),false);
    assert.ok(app.toasts.some(item=>item.getAttribute('role')==='alert'));
  });
}

function optionsRenderer(locale) {
  const noop=()=>{};
  const document={
    readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],
    getElementById:()=>null,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},
    body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}
  };
  const window={
    document,navigator:{language:locale},location:{pathname:'/video-studio/motion-guide',search:'',href:'https://unit.invalid/video-studio/motion-guide',origin:'https://unit.invalid'},
    addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},
    matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null,setItem:noop}
  };
  const context=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout:noop,clearTimeout:noop,fetch:()=>{throw Error('Network forbidden');}});
  vm.runInContext(i18n,context);
  const anchor='  window.TOANAASPortal = Object.freeze({';
  assert.ok(portal.includes(anchor));
  vm.runInContext(portal.replace(anchor,'  window.__optionsForTest=creativeMotionGuideOptions;\n'+anchor),context);
  window.TOANAASI18n.setLocale(locale,{emit:false});
  return window.__optionsForTest;
}
const fallbackCases=[
  ['constructor','constructor'],['toString','toString'],['__proto__','__proto__'],
  ['CUSTOMER Studio media & label','CUSTOMER Studio media &amp; label'],
  ['<img src=x onerror=alert(1)>','&lt;img src=x onerror=alert(1)&gt;']
];
for (const locale of ['vi','en','zh']) {
  const render=optionsRenderer(locale);
  for (const [label,escaped] of fallbackCases) {
    test(locale+': unexpected option '+label+' keeps escaped fallback text and selected scalar',()=>{
      assert.equal(render([['unexpected',label]],'unexpected'),'<option value="unexpected" selected>'+escaped+'</option>');
    });
  }
}
