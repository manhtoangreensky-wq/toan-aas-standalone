import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
function fn(name){const start=source.indexOf(`  function ${name}(`);assert.ok(start>=0,name);return source.slice(start,source.indexOf('\n  }',start)+4);}
function harness(){
 let state={path:'/music/create',session:{authenticated:true,csrfToken:'qa-session-a'}};
 let values={brief:'Mô tả âm nhạc 🎵',tier:'premium',duration_seconds:'30'};
 const history=[],focused=[];
 const form={getAttribute:name=>name==='data-portal-route'?state.path:'feature-estimate',hasAttribute:()=>false,querySelectorAll:()=>Object.entries(values).map(([name,value])=>({name,value,type:'text'}))};
 const ctx={MUSIC_PRODUCT_ROUTES:['/music/create','/music/song'],URL,
  normalizePath:path=>String(path),resolvePage:path=>({path}),getBootstrap:()=>state,
  document:{querySelector:selector=>selector.includes('data-portal-form')?form:{focus:()=>focused.push(state.path)}},
  window:{__TOAN_AAS_PORTAL__:state,location:{origin:'https://qa.invalid',href:'https://qa.invalid/music/create?lang=zh&theme=dark'},history:{pushState:(_data,_title,url)=>history.push(url)}},
  mountPortal:next=>{state=next;ctx.window.__TOAN_AAS_PORTAL__=next;}
 };
 vm.createContext(ctx);
 vm.runInContext('let musicWorkspaceDraftSession=""; const transientFormDrafts=new Map(); const transientWorkspaceDraftIds=new Map();\n'+['rememberTransientFormDraft','transientFormValues','clearTransientFormDraft','synchronizeMusicWorkspaceDraftSession','navigateMusicWorkspace'].map(fn).join('\n'),ctx);
 ctx.synchronizeMusicWorkspaceDraftSession(state);
 const event=(overrides={})=>({button:0,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;},...overrides});
 const link=(href,attributes={})=>({getAttribute:name=>name==='href'?href:attributes[name]||null,hasAttribute:name=>Boolean(attributes[name])});
 return{ctx,history,focused,event,link,state:()=>state,setValues:next=>{values=next;}};
}
test('Music mode switches retain independent drafts, known locale/theme and actual routes',()=>{
 const h=harness();
 assert.equal(h.ctx.navigateMusicWorkspace(h.event(),h.link('/music/song')),true);
 assert.equal(h.state().path,'/music/song');
 assert.equal(h.ctx.transientFormValues('/music/create').brief,'Mô tả âm nhạc 🎵');
 assert.equal(h.history[0],'/music/song?lang=zh&theme=dark');
 h.setValues({brief:'Mô tả bài hát',lyrics:'Dòng một\nDòng hai',vocal_mode:'duet',song_length_mode:'full'});
 assert.equal(h.ctx.navigateMusicWorkspace(h.event(),h.link('/music/create')),true);
 assert.equal(h.ctx.transientFormValues('/music/song').lyrics,'Dòng một\nDòng hai');
 assert.equal(h.ctx.transientFormValues('/music/song').vocal_mode,'duet');
 assert.equal(h.ctx.transientFormValues('/music/create').tier,'premium');
 assert.equal(h.focused.length,2);
});
test('Music modified clicks and destinations outside the two creation modes remain native links',()=>{
 const h=harness();
 for(const change of [{button:1},{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true},{defaultPrevented:true}]) assert.equal(h.ctx.navigateMusicWorkspace(h.event(change),h.link('/music/song')),false);
 for(const target of ['/music/library','/music/sfx','https://external.invalid','/music/song?other=1']) assert.equal(h.ctx.navigateMusicWorkspace(h.event(),h.link(target)),false);
 assert.equal(h.ctx.navigateMusicWorkspace(h.event(),h.link('/music/song',{target:'_blank'})),false);
 assert.equal(h.ctx.navigateMusicWorkspace(h.event(),h.link('/music/song',{download:true})),false);
 assert.equal(h.history.length,0);
});
test('Current Music mode does not duplicate history and unsigned navigation stays guarded',()=>{
 const h=harness(),event=h.event();
 assert.equal(h.ctx.navigateMusicWorkspace(event,h.link('/music/create')),true);assert.equal(event.defaultPrevented,true);assert.equal(h.history.length,0);
 h.state().session={authenticated:false};
 assert.equal(h.ctx.navigateMusicWorkspace(h.event(),h.link('/music/song')),false);
});
test('Music session cleanup clears only Music drafts on replacement or sign-out',()=>{
 const h=harness();
 h.ctx.navigateMusicWorkspace(h.event(),h.link('/music/song'));
 vm.runInContext('transientFormDrafts.set("/voice/tts",{script:"Voice preserved"});',h.ctx);
 h.ctx.synchronizeMusicWorkspaceDraftSession(h.state());
 assert.equal(h.ctx.transientFormValues('/music/create').tier,'premium');
 h.ctx.synchronizeMusicWorkspaceDraftSession({session:{authenticated:true,csrfToken:'qa-session-b'}});
 assert.equal(h.ctx.transientFormValues('/music/create').tier,undefined);
 assert.equal(h.ctx.transientFormValues('/voice/tts').script,'Voice preserved');
 vm.runInContext('transientFormDrafts.set("/music/song",{lyrics:"Private draft"});',h.ctx);
 h.ctx.synchronizeMusicWorkspaceDraftSession({session:{authenticated:false}});
 assert.equal(h.ctx.transientFormValues('/music/song').lyrics,undefined);
 assert.equal(h.ctx.transientFormValues('/voice/tts').script,'Voice preserved');
});
