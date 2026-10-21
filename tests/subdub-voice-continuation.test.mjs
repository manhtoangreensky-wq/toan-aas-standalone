import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
const source=fs.readFileSync('static/portal/portal.js','utf8');
const fn=name=>{const start=source.indexOf(`  function ${name}(`);assert.ok(start>=0,`missing ${name}`);return source.slice(start,source.indexOf('\n  }',start)+4);};
function harness(){
 let state={path:'/subdub',session:{authenticated:true,csrfToken:'qa-A'}};
 const location={origin:'http://qa.invalid',href:'http://qa.invalid/subdub?mode=subtitle_plus_dubbing&lang=en',pathname:'/subdub',search:'?mode=subtitle_plus_dubbing&lang=en'};
 const moves=[],events=[];
 const controls=[
  {name:'target_language',value:'en'},
  {name:'',value:'0',type:'range',attrs:{'data-subdub-local-volume':'original'}},
  {name:'',value:'200',type:'range',attrs:{'data-subdub-local-volume':'dubbing'}}
 ].map(c=>({...c,type:c.type||'select-one',getAttribute:k=>c.attrs?.[k]??null,hasAttribute:k=>Object.hasOwn(c.attrs||{},k)}));
 const panel={hidden:false,getAttribute:()=> 'SUBTITLE_PLUS_DUBBING',querySelectorAll:()=>controls};
 const root={querySelector:()=>null,querySelectorAll:()=>[panel]};
 const ctx={URL,URLSearchParams,CustomEvent:class{constructor(type){this.type=type;}},
  normalizePath:value=>String(value||'').split('?')[0],resolvePage:value=>({path:value}),getBootstrap:()=>state,
  document:{querySelector:selector=>selector==='.portal-subdub-hub'?root:selector.startsWith('[data-portal-form]')?null:{focus(){}}},
  mountPortal:next=>{state=next;ctx.window.__TOAN_AAS_PORTAL__=state;},
  window:{location,__TOAN_AAS_PORTAL__:state,history:{pushState(_state,_title,url){moves.push(url);const next=new URL(url,location.origin);Object.assign(location,{href:next.href,pathname:next.pathname,search:next.search});}},dispatchEvent:e=>events.push(e.type)}
 };
 vm.createContext(ctx);
 const modeStart=source.indexOf('  const SUBDUB_PRODUCT_MODES'),modeEnd=source.indexOf('  function resolveSubDubJourneyMode',modeStart);
 const langStart=source.indexOf('  const SUBDUB_LANGUAGE_CATALOG'),langEnd=source.indexOf('  function renderSubDubLanguageOptions',langStart);
 const draftStart=source.indexOf('  const SUBDUB_DRAFT_ROUTE'),draftEnd=source.indexOf('  function renderSubDubHub',draftStart);
 vm.runInContext('const transientFormDrafts=new Map();const transientWorkspaceDraftIds=new Map();'+source.slice(modeStart,modeEnd)+source.slice(langStart,langEnd)+source.slice(draftStart,draftEnd)+
  ['clearTransientFormDraft','rememberTransientFormDraft','resolveSubDubJourneyMode','safeSubDubReturnPath','subDubVoiceReturnPath','subDubVoiceCompanionUrl','navigateSubDubVoiceContinuation'].map(fn).join('\n'),ctx);
 ctx.synchronizeSubDubWorkspaceDraftSession(state);
 const event=()=>({button:0,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;}});
 const link=(href,kind='data-subdub-voice-library-link')=>({getAttribute:key=>key==='href'?href:null,hasAttribute:key=>key===kind});
 return{ctx,moves,events,event,link,state:()=>state,location};
}
test('return context accepts exactly the four finite SubDub mode paths',()=>{
 const h=harness();for(const mode of ['subtitle_only','translated_subtitle','dubbing_only','subtitle_plus_dubbing'])assert.equal(h.ctx.safeSubDubReturnPath('/subdub?mode='+mode),'/subdub?mode='+mode);
 for(const bad of ['',null,'//evil.invalid','https://evil.invalid/subdub?mode=dubbing_only','/admin','/subdub?mode=dub','/subdub?mode=dubbing_only#x','/subdub?mode=dubbing_only&x=1','%2Fsubdub%3Fmode%3Ddubbing_only','/subdub\\?mode=dubbing_only','/subdub?mode=dubbing_only\n','/subdub?mode=dubbing_only\r'])assert.equal(h.ctx.safeSubDubReturnPath(bad),'');
});
test('companion links encode only a finite return path, not draft contents',()=>{
 const h=harness();assert.equal(h.ctx.subDubVoiceCompanionUrl('/voice/clone','SUBTITLE_PLUS_DUBBING'),'/voice/clone?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing');
 assert.equal(h.ctx.subDubVoiceCompanionUrl('https://evil.invalid','SUBTITLE_PLUS_DUBBING'),'');
 assert.equal(h.ctx.subDubVoiceCompanionUrl('/voice/clone','constructor'),'/voice/clone');
});
for(const target of ['/voice/saved','/voice/clone'])test(`normal SubDub navigation captures real scalar controls before opening ${target}`,()=>{
 const h=harness(),e=h.event(),href=target+'?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing';
 assert.equal(h.ctx.navigateSubDubVoiceContinuation(e,h.link(href)),true);assert.equal(e.defaultPrevented,true);
 assert.equal(h.state().path,target);assert.equal(new URL(h.location.href).searchParams.get('return_to'),'/subdub?mode=subtitle_plus_dubbing');
 const draft=h.ctx.subDubDraftSnapshot();assert.equal(draft.shared.original_volume,'0');assert.equal(draft.shared.dubbing_volume,'200');assert.equal(draft.shared.target_language,'en');
 assert.equal(h.state().voiceInventoryReadState,'guarded');assert.equal(h.state().voiceProfiles.length,0);
});
test('Voice continuation tabs and return preserve the original SubDub draft',()=>{
 const h=harness(),query='?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing';
 h.ctx.navigateSubDubVoiceContinuation(h.event(),h.link('/voice/saved'+query));
 for(const target of ['/voice/tts','/voice/stt','/voice/clone']){
  assert.equal(h.ctx.navigateSubDubVoiceContinuation(h.event(),h.link(target+query,'data-voice-workspace-mode')),true);assert.equal(h.state().path,target);
 }
 assert.equal(h.ctx.navigateSubDubVoiceContinuation(h.event(),h.link('/subdub?mode=subtitle_plus_dubbing','data-subdub-return')),true);
 assert.equal(h.state().path,'/subdub');assert.equal(new URL(h.location.href).searchParams.get('mode'),'subtitle_plus_dubbing');assert.equal(h.ctx.subDubDraftSnapshot().shared.original_volume,'0');
});
test('activating the current Voice continuation tab does not create duplicate history',()=>{
 const h=harness(),href='/voice/saved?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing';
 h.ctx.navigateSubDubVoiceContinuation(h.event(),h.link(href));const e=h.event();
 assert.equal(h.ctx.navigateSubDubVoiceContinuation(e,h.link(href,'data-voice-workspace-mode')),true);
 assert.equal(e.defaultPrevented,true);assert.equal(h.moves.length,1);
});
test('modified clicks, downloads and alternate targets retain normal browser behavior',()=>{
 for(const variant of [{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true},{button:1},{button:2},{defaultPrevented:true}]){
  const h=harness(),e={...h.event(),...variant};assert.equal(h.ctx.navigateSubDubVoiceContinuation(e,h.link('/voice/saved?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing')),false);assert.equal(h.moves.length,0);
 }
 for(const kind of ['download','target']){
  const h=harness(),e=h.event(),href='/voice/saved?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing';
  const link=kind==='download'?{getAttribute:k=>k==='href'?href:null,hasAttribute:k=>k==='download'||k==='data-subdub-voice-library-link'}:{getAttribute:k=>k==='target'?'_blank':k==='href'?href:null,hasAttribute:k=>k==='data-subdub-voice-library-link'};
  assert.equal(h.ctx.navigateSubDubVoiceContinuation(e,link),false);assert.equal(e.defaultPrevented,false);assert.equal(h.moves.length,0);
 }
});
test('ordinary Voice navigation, unsigned state and forged return contexts do not enter continuation',()=>{
 for(const href of ['https://evil.invalid/voice/saved','//evil.invalid/voice/saved','/voice/saved?return_to=%2Fadmin','/voice/saved?return_to=%2Fsubdub%3Fmode%3Ddubbing_only','/voice/saved?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing&profile_id=1','/voice/saved?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing&return_to=%2Fadmin','/voice/saved']){
  const h=harness();assert.equal(h.ctx.navigateSubDubVoiceContinuation(h.event(),h.link(href)),false,href);assert.equal(h.moves.length,0);
 }
 const h=harness();h.state().session.authenticated=false;assert.equal(h.ctx.navigateSubDubVoiceContinuation(h.event(),h.link('/voice/saved?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing')),false);
});

for(const locale of ['vi','en','zh'])test(`Voice return link uses the real ${locale} catalogue and rejects unsafe contexts`,()=>{
 const h=harness();vm.runInContext(fs.readFileSync('static/portal/portal-i18n.js','utf8'),h.ctx);
 h.ctx.window.TOANAASI18n.setLocale(locale,{emit:false});
 vm.runInContext(['portalI18n','uiText','safeText','voiceUiText','renderVoiceWorkspaceNav'].map(fn).join('\n'),h.ctx);
 h.location.search='?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing';
 const html=h.ctx.renderVoiceWorkspaceNav('/voice/saved');
 assert.match(html,/data-subdub-return href="\/subdub\?mode=subtitle_plus_dubbing"/);
 assert.match(html,new RegExp({vi:'Quay lại SubDub',en:'Back to SubDub',zh:'返回 SubDub'}[locale]));
 assert.equal((html.match(/href="\/voice\/(?:tts|stt|saved|clone)\?return_to=/g)||[]).length,4);
 for(const bad of ['%2Fadmin','https%3A%2F%2Fevil.invalid','%2Fsubdub%3Fmode%3Ddubbing_only%26profile_id%3D1']){
  h.location.search='?return_to='+bad;assert.doesNotMatch(h.ctx.renderVoiceWorkspaceNav('/voice/saved'),/data-subdub-return|evil\.invalid|profile_id/);
 }
 h.location.search='?return_to=%2Fsubdub%3Fmode%3Ddubbing_only&return_to=%2Fadmin';assert.doesNotMatch(h.ctx.renderVoiceWorkspaceNav('/voice/saved'),/data-subdub-return/);
});
