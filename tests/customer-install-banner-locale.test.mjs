import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8'),messages=fs.readFileSync('static/portal/portal-i18n.js','utf8');
const start=source.indexOf('  function syncSmartInstallBanner() {'),end=source.indexOf('  function dismissSmartInstallBanner()',start);
function banner(locale,device='desktop',native=false){
 const attrs={},control={classList:{toggle(){}},setAttribute(k,v){attrs[k]=v},innerHTML:''};
 const parent={appendChild(e){e.parentElement=this}},doc={body:parent,documentElement:{lang:locale,setAttribute(){}},querySelector(){return null},createElement(){return control}};
 const window={document:doc,navigator:{language:locale},dispatchEvent(){},CustomEvent:function(){},localStorage:{getItem:()=>null},sessionStorage:{getItem:k=>k==='toanaas_install_expanded'?'true':null}};
 const runtime=vm.createContext({window,document:doc,navigator:window.navigator,Intl,isStandaloneApp:()=>false,isIosDevice:()=>device==='ios',isAndroidDevice:()=>device==='android',pwaInstallPrompt:native?{prompt(){}}:null,portalIcon:()=>'',ICONS:{download:'download'},safeText:v=>String(v)});
 vm.runInContext(messages,runtime);window.TOANAASI18n.setLocale(locale,{emit:false});runtime.uiText=(key,fallback)=>window.TOANAASI18n.t(key)||fallback;
 vm.runInContext(source.slice(start,end)+'\nsyncSmartInstallBanner();',runtime);
 return {html:control.innerHTML,attrs};
}
const expected={vi:{title:'Ứng dụng TOAN AAS',collapse:'Thu gọn hướng dẫn',dismiss:'Ẩn hướng dẫn cài đặt',desktop:'Hướng dẫn cài đặt',ios:'Cài trên iPhone',android:'Cài trên Android',native:'Cài đặt ứng dụng'},en:{title:'TOAN AAS app',collapse:'Collapse instructions',dismiss:'Hide install instructions',desktop:'Installation guide',ios:'Install on iPhone',android:'Install on Android',native:'Install app'},zh:{title:'TOAN AAS 应用',collapse:'收起说明',dismiss:'隐藏安装说明',desktop:'安装指南',ios:'在 iPhone 上安装',android:'在 Android 上安装',native:'安装应用'}};
const visible=html=>html.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
for(const locale of ['vi','en','zh']){
 test(`Expanded install banner uses ${locale} copy and accessible controls`,()=>{
  const r=banner(locale),e=expected[locale];assert.ok(r.html.includes(e.title));assert.ok(r.html.includes('aria-label="'+e.collapse+'"'));assert.ok(r.html.includes('aria-label="'+e.dismiss+'"'));
  assert.equal(r.attrs['aria-label'],locale==='vi'?'Cài đặt ứng dụng TOAN AAS':locale==='en'?'Install the TOAN AAS app':'安装 TOAN AAS 应用');
  const text=visible(r.html);assert.doesNotMatch(text,/60\s*FPS|60帧|mượt mà|smooth 60/i);if(locale==='en')assert.doesNotMatch(text,/[\u00c0-\u024f\u4e00-\u9fff]/u);
 });
 test(`Install banner selects the real device or readiness action with ${locale} label`,()=>{
  for(const [device,native,key,action] of [['desktop',false,'desktop','pwa-install-prompt'],['ios',false,'ios','pwa-install-ios-guide'],['android',false,'android','pwa-install-prompt'],['desktop',true,'native','pwa-install-prompt']]){
   const r=banner(locale,device,native);assert.ok(r.html.includes(expected[locale][key]));assert.ok(r.html.includes('data-portal-action="'+action+'"'));
  }
 });
}
