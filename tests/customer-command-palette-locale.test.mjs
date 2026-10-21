import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const messages=fs.readFileSync('static/portal/portal-i18n.js','utf8');
const registry=fs.readFileSync('copyfast_registry.py','utf8');
const catalog=Array.from(registry.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"/g)).map(([,key,title,group,route])=>({key,title,group,route}));
const noop=()=>{};
function runtime(locale){
  const document={readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],getElementById:()=>null,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
  const window={document,navigator:{language:locale,userAgent:'QA'},location:{pathname:'/dashboard',search:'',href:'http://127.0.0.1:4178/dashboard'},addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null}};
  const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout,clearTimeout});
  vm.runInContext(messages,sandbox);
  vm.runInContext(source.replace('  window.TOANAASPortal = Object.freeze({','  window.__PaletteTest = { commandPaletteItems, renderCommandPalette, normalizeBootstrap, manifest, fallbackCatalogGroup };\n  window.TOANAASPortal = Object.freeze({'),sandbox);
  window.TOANAASI18n.setLocale(locale,{emit:false});
  const helpers=window.__PaletteTest,state=helpers.normalizeBootstrap({path:'/dashboard',title:'TOAN AAS',profile:{locale},session:{authenticated:true,csrfToken:'qa'},catalog});
  const page=window.TOANAASPortal.resolvePage('/dashboard');
  return {window,helpers,state,page,items:()=>helpers.commandPaletteItems(state,page),render:()=>helpers.renderCommandPalette(page,state)};
}
const expected={
 vi:{'/music/song':'Bài hát có lời','/content/caption':'Chú thích nội dung','/projects/new':'Tạo dự án','/image-studio/new':'Bảng thiết kế mới','/voice/stt':'Giọng nói thành văn bản'},
 en:{'/music/song':'Song with lyrics','/content/caption':'Caption','/projects/new':'Create a project','/image-studio/new':'New artboard','/voice/stt':'Speech to text'},
 zh:{'/music/song':'带歌词歌曲','/content/caption':'内容配文','/projects/new':'创建项目','/image-studio/new':'新建画板','/voice/stt':'语音转文字'}
};
const mixedVi=/\b(?:workflow|workspace|content|caption|hook|studio|library|prompt|voice|image|music|project|lead|brief|review|direction|transcript|audio|media|template|planner|blueprint|readiness|artboard|campaign|autoPost|item)\b/i;
const allowedZhLatin=new Set(['AI','PDF','OCR','SRT','VTT','XU','CRM','SFX','ASR','MFA','TTS','FFMPEG','TELEGRAM','TOAN','AAS','USD','CNY','VND','VIP','PAYOS','TIKTOK','FACEBOOK','YOUTUBE']);

for(const locale of ['vi','en','zh']){
 test(`Quick-switch uses reviewed catalogue and route copy in ${locale}`,()=>{
  const r=runtime(locale),items=r.items();
  for(const [route,title] of Object.entries(expected[locale]))assert.equal(items.find(item=>item.path===route)?.title,title,route);
 });
 test(`All 152 non-Video quick-switch destinations and sections have clean ${locale} copy`,()=>{
  const r=runtime(locale),items=r.items().filter(item=>{const entry=catalog.find(e=>e.route===item.path);return entry?.group!=='video'&&r.helpers.fallbackCatalogGroup(item.path)!=='video'});
  assert.equal(items.length,152,'Every current non-Video destination must be retained, including Voice STT');
  for(const item of items){const text=item.title+' '+item.section;if(locale==='vi')assert.doesNotMatch(text,mixedVi,item.path);if(locale==='en')assert.doesNotMatch(text,/[\u00c0-\u024f]/u,item.path);if(locale==='zh')assert.deepEqual((text.match(/[a-z][a-z0-9-]*/gi)||[]).filter(word=>!allowedZhLatin.has(word.toUpperCase())),[],item.path);}
 });
}

test('Translated labels retain source-language search terms and exact routes',()=>{
 const r=runtime('vi'),item=r.items().find(item=>item.path==='/content/caption');
 assert.match(item.sourceSearchText||'',/Caption/);
 const markup=r.render();const entry=markup.match(/<a class="portal-command-item" href="\/content\/caption"[\s\S]*?<\/a>/)?.[0];
 assert.ok(entry);assert.match(entry,/data-command-search="[^"]*caption/);assert.match(entry,/<strong>Chú thích nội dung<\/strong>/);
});

test('Video labels and server navigation authority stay outside the copy projection',()=>{
 const r=runtime('vi');r.helpers.manifest['/video/palette-fixture']={path:'/video/palette-fixture',title:'Deferred video fixture',section:'AI Studio',access:'member'};
 r.helpers.manifest['/admin/palette-fixture']={path:'/admin/palette-fixture',title:'Private admin fixture',section:'Quản trị',access:'admin'};
 r.state.catalog.push({key:'music_song',route:'/video/palette-fixture',group:'video'});
 r.state.session.role='admin';const items=r.items();assert.equal(items.find(item=>item.path==='/video/palette-fixture').title,'Deferred video fixture');assert.ok(!items.some(item=>item.path==='/admin/palette-fixture'),'Browser role must not grant an unissued Admin destination');
});

test('Unreviewed catalogue keys cannot invent a destination or overwrite a known page label',()=>{
 const r=runtime('vi');r.state.catalog.push({key:'not_reviewed_key',route:'/not-a-manifest-route',title:'Invented route',group:'content'});
 assert.ok(!r.items().some(item=>item.path==='/not-a-manifest-route'));
});

test('A destination fallback cannot inherit the current document title',()=>{
 const r=runtime('en');r.state.title='Unrelated current-page title';r.helpers.manifest['/qa/palette-destination']={path:'/qa/palette-destination',title:'Known destination',section:'Customer',access:'member'};
 assert.equal(r.items().find(item=>item.path==='/qa/palette-destination').title,'Known destination');
});
