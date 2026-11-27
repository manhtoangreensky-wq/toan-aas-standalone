import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Run the complete production bundle; only external browser boundaries are doubles.
const integration = fs.readFileSync(new URL('../static/portal/integration.js', import.meta.url), 'utf8');
const i18n = fs.readFileSync(new URL('../static/portal/portal-i18n.js', import.meta.url), 'utf8');
const route = '/free-prompt-gallery', id = 'caption_cta_food_cafe_1';
const native = {
  vi: {category:'Chú thích và lời mời', industry:'Quán cà phê', title:'Mời khách thưởng thức cà phê', prompt:'Viết lời mời thưởng thức cà phê.\nGiữ nguyên {tên_quán} và 25%.'},
  en: {category:'Captions and invitations', industry:'Coffee shops', title:'Invite guests to enjoy coffee', prompt:'Write an invitation to enjoy coffee.\nKeep {tên_quán} and 25% unchanged.'},
  zh: {category:'配文与邀请', industry:'咖啡店', title:'邀请顾客品尝咖啡', prompt:'撰写邀请顾客品尝咖啡的文案。\n保留 {tên_quán} 和 25%。'}
};
const boundaries = {execution:'web_native_static_prompt_gallery',snapshot_read_only:true,gallery_request_persisted:false,provider_called:false,bot_called:false,bridge_called:false,job_created:false,wallet_mutated:false,payment_started:false,asset_saved:false,publish_action_created:false,delivery_created:false};
const item = (lang, suffix='') => ({id,category_id:'caption_cta',category_title:native[lang].category,industry_id:'food_cafe',industry:native[lang].industry,title:native[lang].title+suffix,prompt:native[lang].prompt+suffix,goals:['conversion'],platforms:['facebook']});
const catalog = lang => ({snapshot_version:'2026-07-15.1',description:native[lang].category,total_items:1,categories:[{id:'caption_cta',title:native[lang].category,goals:['conversion'],platforms:['facebook'],item_count:1}],industries:[{id:'food_cafe',title:native[lang].industry,item_count:1}],boundaries:{...boundaries}});
const listing = (lang, query=new URLSearchParams()) => ({snapshot_version:'2026-07-15.1',filters:Object.fromEntries(['category_id','industry_id','goal','platform','q'].map(k=>[k,query.get(k)||''])),pagination:{page:1,page_size:20,total_items:1,total_pages:1,has_next:false,has_previous:false},items:[item(lang)],boundaries:{...boundaries}});
const detail = (lang,suffix='') => ({snapshot_version:'2026-07-15.1',item:item(lang,suffix),copy_instruction:native[lang].title,boundaries:{...boundaries}});
const receipt = () => ({note:{id:'11111111-1111-4111-8111-111111111111',category:'Gallery',priority:'normal',state:'active',revision:1},gallery:{prompt_id:id,snapshot_version:'2026-07-15.1'},boundaries:{execution:'web_native_memory_gallery_save',source_snapshot_read_only:true,memory_note_persisted:true,gallery_state_persisted:false,pending_bot_save_created:false,telegram_state_changed:false,provider_called:false,bot_called:false,bridge_called:false,job_created:false,wallet_mutated:false,payment_started:false,asset_saved:false,publish_action_created:false,delivery_created:false}});
const actions = ['filter','refresh','page','detail','copy','save'];
const tick = async () => { for(let n=0;n<16;n++) await Promise.resolve(); };

function runtime(lang='vi') {
  const noop=()=>{}, requests=[], clipboard=[], toasts=[], mounts=[], listeners=new Map();
  let controls=[], deferredClipboard=false;
  class Element {
    constructor(attributes={}) {this.attributes={...attributes};this.disabled=false;this.textContent='';this.className='';this.dataset={};this.style={};}
    getAttribute(k){return this.attributes[k]??null;} setAttribute(k,v){this.attributes[k]=String(v);} removeAttribute(k){delete this.attributes[k];}
    remove(){const i=toasts.indexOf(this);if(i>=0)toasts.splice(i,1);} addEventListener(){} querySelector(){return null;} querySelectorAll(){return [];}
  }
  const region={appendChild:n=>toasts.push(n),querySelectorAll:()=>toasts};
  const document={readyState:'loading',visibilityState:'visible',title:'',addEventListener:noop,createElement:()=>new Element(),
    querySelector:s=>s==='[data-portal-toast]'?region:null,querySelectorAll:s=>s==='[data-portal-action]'?controls:[],
    documentElement:{lang,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},body:{appendChild:noop,classList:{add:noop,remove:noop,toggle:noop}}};
  const window={document,isSecureContext:true,navigator:{language:lang,clipboard:{writeText:text=>{
    let resolve;const promise=deferredClipboard?new Promise(r=>{resolve=r;}):Promise.resolve();clipboard.push({text,resolve});return promise;}}},
    location:{pathname:route,search:'',origin:'https://unit.invalid',href:'https://unit.invalid'+route,assign:noop},
    TOANAASPortal:{mount:state=>mounts.push(JSON.parse(JSON.stringify(state)))},
    addEventListener:(k,fn)=>{const l=listeners.get(k)||[];l.push(fn);listeners.set(k,l);},
    dispatchEvent:e=>{for(const fn of listeners.get(e.type)||[])fn(e);return true;},
    setTimeout:()=>0,clearTimeout:noop,setInterval:()=>0,clearInterval:noop,
    localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},sessionStorage:{getItem:()=>null,setItem:noop,removeItem:noop},
    matchMedia:()=>({matches:false,addEventListener:noop}),crypto:globalThis.crypto};
  const initial=()=>({path:route,account:{id:'22222222-2222-4222-8222-222222222222',role:'user'},session:{authenticated:true,csrfToken:'synthetic-gallery-session-a'},
    capabilities:{'free-prompt-gallery-view':true,'free-prompt-gallery-save':true},freePromptGalleryEnabled:true,memoryCenterEnabled:true,
    freePromptGalleryCatalog:{},freePromptGalleryListing:{},freePromptGalleryDetail:{},freePromptGallerySaveResult:{},
    freePromptGalleryReadState:'loading',pageStates:{[route]:'processing'}});
  window.__TOAN_AAS_PORTAL__=initial();
  const fetch=(url,options={})=>new Promise((resolve,reject)=>{
    const parsed=new URL(url,window.location.origin);
    assert.ok(parsed.pathname.startsWith('/api/v1/free-prompt-gallery/')||parsed.pathname===`/api/v1/memory/gallery-items/${id}/save`,'Unexpected endpoint '+parsed.pathname);
    assert.equal(options.credentials,'same-origin');assert.equal(options.cache,'no-store');
    requests.push({url:parsed,options,resolve,reject,settled:false});
  });
  const context=vm.createContext({window,document,navigator:window.navigator,console,Intl,URL,URLSearchParams,Headers,Response,Blob,AbortController,FormData,
    HTMLElement:Element,HTMLFormElement:class extends Element{},HTMLInputElement:class extends Element{},HTMLSelectElement:class extends Element{},HTMLTextAreaElement:class extends Element{},
    crypto:globalThis.crypto,CustomEvent:class{constructor(type,init={}){this.type=type;this.detail=init.detail;}},fetch,setTimeout:window.setTimeout,clearTimeout:noop});
  vm.runInContext(i18n,context);window.TOANAASI18n.setLocale(lang,{emit:false});
  const end=integration.lastIndexOf('}());');assert.ok(end>0,'Complete bundle closure');
  vm.runInContext(integration.slice(0,end)+'window.__galleryQA={handleAction,hydrateFreePromptGallery,hydrateFreePromptGalleryDetail,freePromptGalleryCatalogIsSafe,freePromptGalleryItemIsSafe,freePromptGalleryListingIsSafe,freePromptGalleryDetailIsSafe,freePromptGallerySaveResultIsSafe,advanceSession(){++freePromptGallerySessionEpoch;}};\n'+integration.slice(end),context);
  const qa=window.__galleryQA;
  function replaceControls(disabled=false){controls=actions.map(action=>Object.assign(new Element({'data-portal-action':'free-prompt-gallery-'+action,'data-portal-route':route}),{disabled}));}
  replaceControls();
  const r={window,qa,requests,clipboard,toasts,mounts,
    get state(){return window.__TOAN_AAS_PORTAL__;},get controls(){return controls;},
    locale:value=>window.TOANAASI18n.setLocale(value,{emit:false}),replaceControls,
    action:(action,fields={},targetId=id)=>qa.handleAction({detail:{action:'free-prompt-gallery-'+action,route,fields,copyText:targetId}}),
    list:()=>qa.hydrateFreePromptGallery(),select:()=>qa.hydrateFreePromptGalleryDetail(id),
    deferClipboard(){deferredClipboard=true;},
    snapshot(){return JSON.stringify({state:r.state,toasts:toasts.map(n=>({text:n.textContent,className:n.className})),controls:controls.map(n=>({disabled:n.disabled,attributes:n.attributes})),mounts:mounts.length,clipboard:clipboard.map(n=>n.text)});},
    respond(index,locale='vi',outcome='success',suffix=''){
      const p=requests[index];assert.ok(p&&!p.settled,'Unsettled request '+index);p.settled=true;
      if(outcome==='transport'){p.reject(new TypeError('Synthetic lost acknowledgement'));return;}
      const failed=outcome==='error';let data;
      if(p.url.pathname.endsWith('/catalog'))data=catalog(locale);
      else if(p.url.pathname.endsWith('/items'))data=listing(locale,p.url.searchParams);
      else if(p.url.pathname.endsWith('/save'))data=receipt();
      else {
        data=detail(locale,suffix);
        if(p.url.pathname.endsWith('/caption_cta_affiliate_1')){
          data.item={...data.item,id:'caption_cta_affiliate_1',industry_id:'affiliate',industry:'Native affiliate industry',title:'Native second sample',prompt:'Native second sample prompt'};
        }
      }
      p.resolve(new Response(JSON.stringify({ok:!failed,status:failed?'error':'ready',message:failed?'ARBITRARY_SERVER_FAILURE':'',data}),{status:failed?422:200,headers:{'Content-Type':'application/json'}}));
    },
    async finish(task,locale='vi',outcome='success'){
      let done=false,error;task.then(()=>{done=true;},e=>{error=e;done=true;});
      for(let n=0;n<12&&!done;n++){await tick();for(let i=0;i<requests.length;i++)if(!requests[i].settled)r.respond(i,locale,outcome);await tick();}
      assert.equal(done,true,'All explicitly settled requests must complete without real timers');return error;
    },
    async load(locale=window.TOANAASI18n.getLocale()){const error=await r.finish(r.list(),locale);assert.equal(error,undefined);},
    async selected(locale=window.TOANAASI18n.getLocale()){await r.load(locale);assert.equal(await r.finish(r.select(),locale),undefined);},
    change(kind){
      if(kind==='locale')r.locale('en');
      if(kind==='route'){window.location.pathname='/memory';window.__TOAN_AAS_PORTAL__={...r.state,path:'/memory'};}
      if(kind==='session'){qa.advanceSession();window.__TOAN_AAS_PORTAL__={...r.state,account:{id:'33333333-3333-4333-8333-333333333333'},session:{authenticated:true,csrfToken:'synthetic-gallery-session-b'}};}
      if(kind==='logout')window.__TOAN_AAS_PORTAL__={...r.state,session:{authenticated:false,csrfToken:''}};
      if(kind==='disabled')window.__TOAN_AAS_PORTAL__={...r.state,freePromptGalleryEnabled:false};
    },
    restore(){window.location.pathname=route;r.locale('vi');window.__TOAN_AAS_PORTAL__=initial();}
  };return r;
}
function feedback(r,lang,operation){
  assert.equal(r.toasts.length,1,'Exactly one truthful current success');
  const n=r.toasts[0];assert.equal(n.className,'portal-toast');
  const words={vi:{copy:/sao chép/i,save:/lưu/i,refresh:/mới/i,filter:/lọc|toàn bộ/i,detail:/chi tiết/i},en:{copy:/cop/i,save:/sav/i,refresh:/refresh/i,filter:/filter|all/i,detail:/detail/i},zh:{copy:/复制/,save:/保存/,refresh:/刷新/,filter:/筛选|全部/,detail:/详情/}};
  assert.match(n.textContent,words[lang][operation]);
  assert.doesNotMatch(n.textContent,/\b(?:snapshot|signed|execution|provider|receipt|canonical)\b/i,'Customer feedback must not expose internal runtime jargon');
}

test('DTO witness: actual validators accept complete public item/catalogue/list/detail/receipt in all locales',()=>{
  const r=runtime();for(const lang of ['vi','en','zh']){
    assert.equal(r.qa.freePromptGalleryItemIsSafe(item(lang)),true);
    assert.equal(r.qa.freePromptGalleryCatalogIsSafe(catalog(lang)),true);
    assert.equal(r.qa.freePromptGalleryListingIsSafe(listing(lang),catalog(lang)),true);
    assert.equal(r.qa.freePromptGalleryDetailIsSafe(detail(lang),catalog(lang)),true);
    assert.equal(r.qa.freePromptGallerySaveResultIsSafe(receipt(),id),true);
  }
});
for(const lang of ['vi','en','zh'])test(`transport-${lang}: current native reads carry captured locale and preserve native DTOs`,async()=>{
  const r=runtime(lang);await r.selected(lang);
  assert.deepEqual(r.requests.map(p=>p.url.searchParams.get('lang')),[lang,lang,lang]);
  assert.deepEqual(JSON.parse(JSON.stringify(r.state.freePromptGalleryCatalog)),catalog(lang));
  assert.equal(r.state.freePromptGalleryListing.items[0].title,native[lang].title);
  assert.equal(r.state.freePromptGalleryDetail.item.prompt,native[lang].prompt);
});
for(const [before,after] of [['vi','en'],['en','zh']])test(`cache-${before}-${after}: emit:false locale change invalidates every old projection before await`,async()=>{
  const r=runtime(before);await r.selected(before);r.window.__TOAN_AAS_PORTAL__={...r.state,freePromptGallerySaveResult:{note:{id:'old-receipt'}}};
  r.locale(after);const start=r.requests.length,task=r.list(),early=structuredClone(r.state);
  await r.finish(task,after);
  for(const key of ['freePromptGalleryCatalog','freePromptGalleryListing','freePromptGalleryDetail','freePromptGallerySaveResult'])assert.deepEqual(early[key],{},key+' leaked previous-language data while loading');
  assert.equal(early.freePromptGalleryReadState,'loading');
  assert.equal(r.requests[start].url.pathname,'/api/v1/free-prompt-gallery/catalog');
  assert.equal(r.requests[start].url.searchParams.get('lang'),after);
  assert.equal(r.state.freePromptGalleryCatalog.categories[0].title,native[after].category);
});
const readRaces=[
  ['catalog','locale'],['catalog','route'],['catalog','session'],['catalog','logout'],
  ['list','locale'],['list','route'],['list','session'],['list','request'],['list','disabled'],
  ['detail','locale'],['detail','route'],['detail','session'],['detail','logout'],['detail','request'],
  ['catalog','locale','error'],['list','session','error'],['detail','locale','error']
];
for(const [stage,change,outcome='success'] of readRaces)test(`read-${stage}-${change}-${outcome}: obsolete response cannot paint, clear, toast, or unlock current view`,async()=>{
  const r=runtime();if(stage!=='catalog')await r.selected();
  const old=stage==='detail'?r.select():r.list();await tick();
  if(change==='request'){const newer=stage==='detail'?r.select():r.list();const newest=r.requests.length-1;r.respond(newest,'vi','success',' NEW_SELECTION');await newer;}
  else r.change(change);
  r.replaceControls(true);const before=r.snapshot();await r.finish(old,'vi',outcome);
  assert.ok(r.snapshot()===before,'Obsolete read changed complete protected state, toast, controls, mount count, or clipboard');
});
for(const lang of ['vi','en','zh'])test(`copy-${lang}: current action writes exact localized bytes and localized truthful feedback`,async()=>{
  const r=runtime(lang);await r.selected(lang);await r.action('copy');
  assert.deepEqual(r.clipboard.map(n=>n.text),[native[lang].prompt]);feedback(r,lang,'copy');
});
test('copy-null-stale: older hydrate returning null cannot erase newer same-ID selection or call clipboard',async()=>{
  const r=runtime();await r.load();const old=r.action('copy');await tick();
  const newer=r.select();r.respond(r.requests.length-1,'vi','success',' NEW_SELECTION');await newer;
  r.replaceControls(true);const before=r.snapshot();await r.finish(old);
  assert.ok(r.snapshot()===before,'Stale copy hydrate changed newer selection/feedback/controls');assert.equal(r.clipboard.length,0);
});
test('copy-clipboard-await: locale switch after write starts suppresses stale completion feedback and unlock',async()=>{
  const r=runtime();await r.selected();r.deferClipboard();const task=r.action('copy');await tick();
  assert.equal(r.clipboard.length,1);r.locale('en');r.replaceControls(true);const before=r.snapshot();
  r.clipboard[0].resolve();await task;assert.ok(r.snapshot()===before,'Stale clipboard completion changed protected UI');
});
test('copy-clipboard-selection: newer same-ID detail generation owns controls while old clipboard finishes',async()=>{
  const r=runtime();await r.selected();r.deferClipboard();const task=r.action('copy');await tick();
  assert.equal(r.clipboard.length,1);const newer=r.select();
  r.respond(r.requests.length-1,'vi','success',' NEW_SELECTION');await newer;
  r.replaceControls(true);const before=r.snapshot();r.clipboard[0].resolve();await task;
  assert.ok(r.snapshot()===before,'Old clipboard completion must not unlock newer same-ID selection');
});
test('copy-denied-current: current browser denial reports a native error and releases its own busy control',async()=>{
  const r=runtime();await r.selected();r.window.navigator.clipboard=undefined;await r.action('copy');
  assert.equal(r.clipboard.length,0);assert.equal(r.toasts.length,1);assert.equal(r.toasts[0].className,'portal-toast portal-toast--warning');
  assert.match(r.toasts[0].textContent,/sao chép/);
  assert.equal(r.controls.find(n=>n.getAttribute('data-portal-action')==='free-prompt-gallery-copy').disabled,false);
});
test('cached-reselection: viewing cached A invalidates an older pending Copy B across action names',async()=>{
  const r=runtime();await r.selected();
  const catalogue=r.state.freePromptGalleryCatalog;
  catalogue.total_items=2;catalogue.categories[0].item_count=2;
  catalogue.industries.push({id:'affiliate',title:'Native affiliate industry',item_count:1});
  const old=r.action('copy',{},'caption_cta_affiliate_1');await tick();
  assert.equal(r.requests.at(-1).url.pathname,'/api/v1/free-prompt-gallery/items/caption_cta_affiliate_1');
  await r.action('detail',{},id);
  assert.equal(r.state.freePromptGalleryDetail.item.id,id);
  assert.equal(r.controls.find(n=>n.getAttribute('data-portal-action')==='free-prompt-gallery-copy').disabled,false,
    'New explicit cached selection must own copy controls rather than leave an obsolete copy busy');
  r.replaceControls(true);const before=r.snapshot();await r.finish(old);
  assert.ok(r.snapshot()===before,'Older Copy B cannot overwrite/copy/announce/unlock after newer cached A selection');
  assert.equal(r.clipboard.length,0);
});
test('cached-copy: copying cached A supersedes a pending Detail B without leaving detail controls busy',async()=>{
  const r=runtime();await r.selected();const catalogue=r.state.freePromptGalleryCatalog;
  catalogue.total_items=2;catalogue.categories[0].item_count=2;
  catalogue.industries.push({id:'affiliate',title:'Native affiliate industry',item_count:1});
  const old=r.action('detail',{},'caption_cta_affiliate_1');await tick();await r.action('copy',{},id);
  assert.equal(r.state.freePromptGalleryDetail.item.id,id);assert.deepEqual(r.clipboard.map(n=>n.text),[native.vi.prompt]);
  assert.equal(r.controls.find(n=>n.getAttribute('data-portal-action')==='free-prompt-gallery-detail').disabled,false,
    'Current cached copy owns detail controls after superseding older detail read');
  r.replaceControls(true);const before=r.snapshot();await r.finish(old);
  assert.ok(r.snapshot()===before,'Superseded detail cannot affect current copy/selection');
});
test('cached-selection-save: selecting cached A supersedes old save feedback without stranding save controls',async()=>{
  const r=runtime();await r.selected();const old=r.action('save');await tick();await r.action('detail',{},id);
  assert.equal(r.controls.find(n=>n.getAttribute('data-portal-action')==='free-prompt-gallery-save').disabled,false,
    'New explicit cached selection owns save controls; old acknowledged intent still cleans up separately');
  r.replaceControls(true);const before=r.snapshot();await r.finish(old);
  assert.ok(r.snapshot()===before,'Superseded save receipt cannot affect the new cached selection');
});
test('cached-selection-capability: taking ownership of sibling controls never enables a forbidden save action',async()=>{
  const r=runtime();await r.selected();r.state.capabilities['free-prompt-gallery-save']=false;
  const save=r.controls.find(n=>n.getAttribute('data-portal-action')==='free-prompt-gallery-save');save.disabled=true;
  const catalogue=r.state.freePromptGalleryCatalog;catalogue.total_items=2;catalogue.categories[0].item_count=2;
  catalogue.industries.push({id:'affiliate',title:'Native affiliate industry',item_count:1});
  const old=r.action('copy',{},'caption_cta_affiliate_1');await tick();await r.action('detail',{},id);
  assert.equal(save.disabled,true,'A disabled-by-capability save control is not an obsolete busy control');
  const before=r.snapshot();await r.finish(old);assert.ok(r.snapshot()===before,'Old copy cannot unlock forbidden save');
});
for(const change of ['locale','route','session','logout','selection'])for(const outcome of ['success','error'])test(`save-${change}-${outcome}: late acknowledgement preserves newer UI and releases intent`,async()=>{
  const r=runtime();await r.selected();const task=r.action('save'),oldIndex=r.requests.length-1;
  const oldKey=JSON.parse(r.requests[oldIndex].options.body).idempotency_key;
  if(change==='selection'){const newer=r.select();r.respond(r.requests.length-1,'vi','success',' NEW_SELECTION');await newer;}
  else r.change(change);
  r.replaceControls(true);const before=r.snapshot();r.respond(oldIndex,'vi',outcome);await task;
  assert.ok(r.snapshot()===before,'Stale save must be silent and cannot clear/merge/unlock');
  r.restore();await r.selected();const retry=r.action('save'),next=r.requests.length-1;
  assert.notEqual(JSON.parse(r.requests[next].options.body).idempotency_key,oldKey,'Acknowledged intent must be discarded, not retained or locked');
  await r.finish(retry);
});
test('save-vi-en-vi: uncertain locale-owned intents preserve VI key across EN without fingerprint eviction',async()=>{
  const r=runtime();await r.selected();const a=r.action('save'),ai=r.requests.length-1;r.respond(ai,'vi','transport');await a;
  const viKey=JSON.parse(r.requests[ai].options.body).idempotency_key;
  r.locale('en');await r.selected('en');const b=r.action('save'),bi=r.requests.length-1;r.respond(bi,'en','transport');await b;
  const enKey=JSON.parse(r.requests[bi].options.body).idempotency_key;
  r.locale('vi');await r.selected('vi');const c=r.action('save'),ci=r.requests.length-1;await r.finish(c);
  assert.notEqual(enKey,viKey);assert.equal(JSON.parse(r.requests[ci].options.body).idempotency_key,viKey);
  assert.equal(r.requests[bi].url.searchParams.get('lang'),'en');
  assert.equal(r.requests[ci].url.searchParams.get('lang'),'vi');
});
for(const lang of ['vi','en','zh'])test(`save-current-${lang}: bounded signed request produces safe content-free receipt and native feedback`,async()=>{
  const r=runtime(lang);await r.selected(lang);const task=r.action('save'),p=r.requests.at(-1);
  const payload=JSON.parse(p.options.body);assert.deepEqual(Object.keys(payload),['idempotency_key']);
  assert.match(payload.idempotency_key,/^[A-Za-z0-9._:-]{12,160}$/);assert.equal(p.options.headers.get('X-CSRF-Token'),'synthetic-gallery-session-a');
  await r.finish(task,lang);assert.equal(p.url.searchParams.get('lang'),lang);
  assert.deepEqual(JSON.parse(JSON.stringify(r.state.freePromptGallerySaveResult)),{note:receipt().note,gallery:receipt().gallery});
  feedback(r,lang,'save');assert.equal(r.controls.find(n=>n.getAttribute('data-portal-action').endsWith('-save')).disabled,false);
});
for(const lang of ['vi','en','zh'])test(`actions-current-${lang}: filter, refresh, and detail announce only confirmed current native results`,async()=>{
  const r=runtime(lang);await r.load(lang);
  for(const action of ['filter','refresh','detail']){
    r.toasts.splice(0);await r.finish(r.action(action,{q:'coffee'}),lang);
    feedback(r,lang,action);assert.equal(r.state.freePromptGalleryCatalog.categories[0].title,native[lang].category);
    if(action==='detail')assert.equal(r.state.freePromptGalleryDetail.item.prompt,native[lang].prompt);
  }
});
for(const action of ['filter','refresh'])for(const outcome of ['error','stale'])test(`action-${action}-${outcome}: failed or obsolete load never reports success`,async()=>{
  const r=runtime('en');await r.selected('en');const task=r.action(action,{q:'coffee'});await tick();
  if(outcome==='stale'){r.change('route');r.replaceControls(true);}
  const before=r.snapshot();await r.finish(task,'en',outcome==='error'?'error':'success');
  if(outcome==='stale')assert.ok(r.snapshot()===before,'Obsolete action changed protected state/toasts/controls');
  else {assert.equal(r.toasts.filter(n=>n.className==='portal-toast').length,0);assert.equal(r.state.freePromptGalleryReadState,'failed');}
});
