import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath, pathToFileURL} from 'node:url';
import test from 'node:test';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=process.env.WEBAPP_SOURCE_ROOT||path.resolve(here,'..');
const integration=fs.readFileSync(process.env.WEBAPP_INTEGRATION_SOURCE||path.join(root,'static/portal/integration.js'),'utf8');
const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');
const {renderChild}=await import(pathToFileURL(path.join(root,'tests/helpers/publishing-child-render.mjs')));
const route='/video-studio/long-form-planner';
const canonicalGuard='Guard: chỉ dùng người, thương hiệu, giọng nói và nguồn tham chiếu có quyền; không mô phỏng người được nhận diện.';
const unsafe='mô phỏng người được nhận diện';
const clone=value=>JSON.parse(JSON.stringify(value));
const baseFields={
  topic_category:'education',topic:'Quy trình kiểm tra đơn hàng',audience:'Chủ cửa hàng nhỏ',
  duration_minutes:3,style:'professional',custom_style:'',structure_mode:'chapters',
  custom_structure:'',platform:'youtube',language:'vi'
};
const falseFields=[
  'input_persisted','telegram_state_changed','bot_called','bridge_called',
  'source_media_inspected','provider_called','image_created','video_created',
  'audio_created','preview_created','output_created','job_created','payment_started',
  'wallet_mutated','asset_saved','publish_action_created','fact_checked','rights_verified'
];
function responseData(withGuard=true){
  return {
    roadmap:{
      title:'Kế hoạch kiểm tra đơn hàng',topic_category:baseFields.topic_category,
      topic:baseFields.topic,audience:baseFields.audience,duration_minutes:3,target_duration_seconds:180,
      style:baseFields.style,style_label:'Chuyên nghiệp',structure_mode:baseFields.structure_mode,
      structure:'Ba chương rõ ràng',platform:baseFields.platform,aspect_ratio:'16:9',language:'vi',
      chapter_count:3,
      outline:['Mở đầu rõ ràng','Giải thích bối cảnh','Các bước kiểm tra','Tổng kết nội dung'],
      character_bible:[
        'Chủ thể xuyên suốt cùng một điểm nhìn.','Trang phục và bảng màu nhất quán.',
        'Cử chỉ tự nhiên và nhịp trình bày vừa phải.','Giọng đọc rõ và đều.',
        ...(withGuard?[canonicalGuard]:[])
      ],
      chapters:[0,1,2].map(index=>({
        index:index+1,start_seconds:index*60,end_seconds:(index+1)*60,
        title:'Chương kiểm tra '+(index+1),objective:'Làm rõ bước kiểm tra.',
        hook:'Vì sao cần kiểm tra đơn hàng?',script_beat:'Giải thích một bước bằng ví dụ.',
        visual_direction:'Bố cục gọn và không gian rõ ràng.',
        image_prompt:'Hình minh họa quy trình kiểm tra.',
        video_prompt:'Chuyển cảnh nhẹ giữa các bước.',
        voice_direction:'Giọng rõ và nhịp vừa phải.',
        music_sfx_direction:'Nhạc nền nhẹ để hỗ trợ nội dung.',
        transition:'Chuyển sang bước tiếp theo.'
      })),
      audio_direction:'Giọng đọc rõ và khoảng nghỉ phù hợp.',
      caption:'Các bước kiểm tra đơn hàng theo trình tự.',
      cta:'Xem lại từng bước khi cần.',
      review_before_use:['Kiểm tra nội dung trước khi dùng.','Chỉ dùng tư liệu có quyền sử dụng.']
    },
    execution:'web_native_deterministic_long_form_roadmap_only',
    ...Object.fromEntries(falseFields.map(key=>[key,false]))
  };
}

function runtime(locale='vi'){
  const noop=()=>{},listeners=new Map(),pending=[],requests=[],toasts=[];
  let state={
    path:route,account:{id:'22222222-2222-4222-8222-222222222222'},profile:{locale},
    interfaceLocale:locale,session:{authenticated:true,csrfToken:'synthetic-compose-only'},
    longFormRoadmapEnabled:true,capabilities:{
      'long-form-roadmap-compose':true,'long-form-roadmap-save-plan':true,'video-plan-create':true
    },longFormRoadmapResult:{},longFormRoadmapSaveSource:{},longFormRoadmapSaveReceipt:{},
    pageStates:{[route]:'ready'}
  };
  const node=()=>({
    attributes:{},className:'',textContent:'',
    setAttribute(k,v){this.attributes[k]=String(v);},getAttribute(k){return this.attributes[k]??null;},
    remove(){const n=toasts.indexOf(this);if(n>=0)toasts.splice(n,1);}
  });
  const region={appendChild(n){toasts.push(n);},querySelectorAll:()=>toasts};
  const document={
    readyState:'loading',visibilityState:'visible',addEventListener:noop,createElement:node,
    querySelector:s=>s==='[data-portal-toast]'?region:null,querySelectorAll:()=>[],
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
  let rendered=renderChild(locale,route,state);
  window.TOANAASPortal={mount(raw){rendered=renderChild(locale,route,raw);}};
  const fetch=(url,options)=>{
    requests.push({url,options,payload:JSON.parse(options.body)});
    let resolve;const promise=new Promise(done=>{resolve=done;});pending.push({resolve});return promise;
  };
  const sandbox=vm.createContext({
    window,document,navigator:window.navigator,URL,URLSearchParams,Headers,FormData,Blob,
    AbortController,Intl,console,fetch,crypto:globalThis.crypto,setTimeout:window.setTimeout,clearTimeout:noop
  });
  vm.runInContext(i18n,sandbox);window.TOANAASI18n.setLocale(locale,{emit:false});
  vm.runInContext(integration,sandbox);
  assert.ok(listeners.has('toanaas:portal-action'));
  return {
    run:(fields=clone(baseFields))=>listeners.get('toanaas:portal-action')({detail:{action:'long-form-roadmap-compose',route,fields}}),
    settle(data){assert.equal(pending.length,1);pending[0].resolve({ok:true,status:200,json:async()=>({ok:true,status:'draft',message:'',data})});},
    requests,toasts,get view(){return rendered;},get state(){return state;}
  };
}
async function composed(locale,data){
  const app=runtime(locale),before=JSON.stringify(data),done=app.run();
  assert.equal(app.requests.length,1,'The actual compose action must reach the controlled API boundary');
  assert.equal(app.requests[0].url,'/api/v1/video-studio/tools/long-form-roadmap');
  assert.equal(app.requests[0].options.method,'POST');
  assert.equal(app.requests[0].options.headers.get('X-CSRF-Token'),'synthetic-compose-only');
  assert.deepEqual(app.requests[0].payload,baseFields);
  app.settle(data);await done;
  assert.equal(JSON.stringify(data),before,'Validation and rendering must preserve server text');
  return app;
}
function assertRejected(app){
  assert.equal(JSON.stringify(app.view.context.longFormRoadmapResult),'{}');
  assert.equal(JSON.stringify(app.view.context.longFormRoadmapSaveSource),'{}');
  assert.equal(app.view.html.includes('data-portal-action="long-form-roadmap-save-plan"'),false);
  assert.ok(app.toasts.some(item=>item.getAttribute('role')==='alert'),'Actual action must expose rejection, not a false success');
}

for(const locale of ['vi','en','zh']){
  test(locale+': safe compose control without the canonical fixed guard is accepted',async()=>{
    const data=responseData(false),app=await composed(locale,data);
    assert.equal(JSON.stringify(app.view.context.longFormRoadmapResult.roadmap),JSON.stringify(data.roadmap));
    assert.equal(app.toasts.some(item=>item.getAttribute('role')==='alert'),false);
  });
  test(locale+': actual compose accepts the exact canonical negative guard only as server result text',async()=>{
    const data=responseData(),app=await composed(locale,data);
    assert.equal(JSON.stringify(app.view.context.longFormRoadmapResult.roadmap),JSON.stringify(data.roadmap),
      'The known fixed prohibition must not invalidate a safe complete planning result');
    assert.ok(app.view.html.includes(canonicalGuard),'The canonical prohibition remains visible and unchanged');
    assert.equal(JSON.stringify(app.view.context.longFormRoadmapSaveSource),JSON.stringify(baseFields));
    const save=app.view.html.match(/<button\b[^>]*data-portal-action="long-form-roadmap-save-plan"[^>]*>/)?.[0];
    assert.ok(save,'Validated compose result and original source must still match for save');
    assert.equal(/\bdisabled\b/.test(save),false);
    assert.equal(app.toasts.some(item=>item.getAttribute('role')==='alert'),false);
  });
  for(const [name,value] of [
    ['appended canonical guard',canonicalGuard+' '+unsafe],
    ['negation removed',canonicalGuard.replace('không mô phỏng','mô phỏng')],
    ['changed canonical guard',canonicalGuard.replace('có quyền','được cấp quyền')]
  ]){
    test(locale+': '+name+' remains subject to the safety scan',async()=>{
      const data=responseData();data.roadmap.character_bible[4]=value;
      assertRejected(await composed(locale,data));
    });
  }
  const locations=[
    ...['title','topic','audience','style_label','structure','audio_direction','caption','cta'].map(key=>[key,d=>{d.roadmap[key]=unsafe;}]),
    ['outline',d=>{d.roadmap.outline[0]=unsafe;}],
    ['another character item',d=>{d.roadmap.character_bible[0]=unsafe;}],
    ['review',d=>{d.roadmap.review_before_use[0]=unsafe;}],
    ...['title','objective','hook','script_beat','visual_direction','image_prompt','video_prompt','voice_direction','music_sfx_direction','transition'].map(key=>['chapter.'+key,d=>{d.roadmap.chapters[0][key]=unsafe;}])
  ];
  for(const [name,mutate] of locations){
    test(locale+': unsafe '+name+' is rejected even when the exact fixed guard is present',async()=>{
      const data=responseData();mutate(data);assertRejected(await composed(locale,data));
    });
  }
  for(const [name,mutate] of [
    ['provider side effect',d=>{d.provider_called=true;}],
    ['wallet side effect',d=>{d.wallet_mutated=true;}],
    ['wrong execution',d=>{d.execution='provider_output';}],
    ['extra envelope key',d=>{d.extra='not-allowed';}]
  ]){
    test(locale+': canonical guard does not override '+name,async()=>{
      const data=responseData();mutate(data);assertRejected(await composed(locale,data));
    });
  }
  for(const field of ['topic','audience','custom_style','custom_structure']){
    test(locale+': unsafe input '+field+' still blocks the API call',async()=>{
      const app=runtime(locale),fields=clone(baseFields);fields[field]=unsafe;
      if(field==='custom_style')fields.style='custom';
      if(field==='custom_structure')fields.structure_mode='custom';
      await app.run(fields);
      assert.equal(app.requests.length,0);assertRejected(app);
    });
  }
  test(locale+': canonical result guard is not exempted when entered as a customer topic',async()=>{
    const app=runtime(locale),fields={...baseFields,topic:canonicalGuard};await app.run(fields);
    assert.equal(app.requests.length,0);assertRejected(app);
  });
  test(locale+': the exact canonical guard is not exempted in a different result field',async()=>{
    const data=responseData();data.roadmap.caption=canonicalGuard;
    assertRejected(await composed(locale,data));
  });
}
