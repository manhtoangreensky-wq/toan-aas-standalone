import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync(process.env.R175_SOURCE_FIXTURE||'static/portal/portal.js','utf8'),messages=fs.readFileSync('static/portal/portal-i18n.js','utf8');
const start=source.indexOf('  function openUniversalInstallGuideModal(activeTab) {'),end=source.indexOf('  function openIosInstallGuideModal()',start);
function guide(locale,{device='desktop',inApp=false,activeTab}={}){
 const modal={attrs:{},innerHTML:'',setAttribute(k,v){this.attrs[k]=v},querySelector:()=>null},doc={body:{appendChild(){}},documentElement:{lang:locale,setAttribute(){}},querySelector:()=>null,createElement:()=>modal,activeElement:{id:'qa-trigger'}};
 const window={document:doc,navigator:{language:locale},dispatchEvent(){},CustomEvent:function(){},requestAnimationFrame(){}};
 const runtime=vm.createContext({window,document:doc,navigator:window.navigator,Intl,isIosDevice:()=>device==='ios',isAndroidDevice:()=>device==='android',isInAppBrowser:()=>inApp,closeInstallGuideModal(){},installModalFocusables:()=>[],safeText:v=>String(v??''),portalIcon:()=>''});
 vm.runInContext(messages,runtime);window.TOANAASI18n.setLocale(locale,{emit:false});runtime.uiText=(key,fallback)=>window.TOANAASI18n.t(key)||fallback;
 vm.runInContext(source.slice(start,end)+'\nglobalThis.openGuide=openUniversalInstallGuideModal;',runtime);runtime.openGuide(activeTab);return modal.innerHTML;
}
const text=html=>html.replace(/<[^>]+>/g,' ').replace(/&amp;/g,'&').replace(/\s+/g,' ').trim();
const expected={vi:{title:'Cài ứng dụng TOAN AAS',close:'Đóng hướng dẫn cài đặt',desktop:'Máy tính',done:'Đã hiểu',inApp:'Đang mở trong một ứng dụng khác'},en:{title:'Install the TOAN AAS app',close:'Close install instructions',desktop:'Computer',done:'Got it',inApp:'Opened inside another app'},zh:{title:'安装 TOAN AAS 应用',close:'关闭安装说明',desktop:'电脑',done:'知道了',inApp:'当前在其他应用内打开'}};
for(const locale of ['vi','en','zh']){
 test(`Universal install guide has clean ${locale} copy across all three device panels`,()=>{
  const html=guide(locale),want=expected[locale],t=text(html);assert.ok(t.includes(want.title));assert.ok(t.includes(want.desktop));assert.ok(t.includes(want.done));assert.ok(html.includes('aria-label="'+want.close+'"'));assert.doesNotMatch(t,/60\s*fps|60帧|chạy mượt|toàn màn hình không có thanh URL/i);
  if(locale==='vi')assert.doesNotMatch(t,/\b(?:App|Add|Home Screen|Share|Desktop|Taskbar|Install App|link|file)\b/i);
  if(locale==='en')assert.doesNotMatch(t,/[\u00c0-\u024f\u4e00-\u9fff]/u);
  if(locale==='zh'){const allowed=new Set(['TOAN','AAS','CHROME','SAFARI','EDGE','ANDROID','IPHONE','IPAD','URL','PWA','MAC','WINDOWS']);assert.deepEqual((t.match(/[a-z][a-z0-9]*/gi)||[]).filter(w=>!allowed.has(w.toUpperCase())),[])}
 });
 test(`In-app install warning uses cautious ${locale} guidance instead of claiming a confirmed block`,()=>{
  const t=text(guide(locale,{device:'ios',inApp:true}));assert.ok(t.includes(expected[locale].inApp));assert.doesNotMatch(t,/đang chặn quyền|blocked your permission|已阻止安装权限/i);
 });
 test(`Changing default install tab in ${locale} preserves tab values and explicit copy/download action names`,()=>{
  for(const device of ['desktop','ios','android']){const html=guide(locale,{device});assert.match(html,new RegExp('class="portal-install-panel is-active"[^>]*data-portal-install-panel="'+device+'"'));assert.deepEqual(Array.from(html.matchAll(/data-portal-install-tab="([^"]+)"/g),m=>m[1]),['android','ios','desktop']);assert.ok(html.includes('data-portal-action="pwa-copy-link"'));assert.ok(html.includes('data-portal-action="pwa-download-shortcut"'));assert.ok(html.includes('data-portal-action="pwa-try-prompt"'));}
 });
}
test('Unsupported install requests open instructions without silently downloading a shortcut',async()=>{
 const from=source.indexOf('  async function requestPwaInstall() {'),to=source.indexOf('  function bindPwaInstallEvents()',from);let guides=0,downloads=0;
 const runtime=vm.createContext({pwaInstallCanBeOffered:()=>false,pwaInstallInFlight:false,isIosDevice:()=>false,downloadAppLauncherShortcut:()=>{downloads++},openUniversalInstallGuideModal:()=>{guides++},syncPwaInstallControl(){}});
 vm.runInContext(source.slice(from,to)+'\nglobalThis.requestInstall=requestPwaInstall;',runtime);await runtime.requestInstall();assert.equal(guides,1);assert.equal(downloads,0,'Opening install guidance must not imply consent to download a .url file');
});
for(const locale of ['vi','en','zh']){
 test(`Install request acceptance is localized ${locale} and is not reported as completed installation`,async()=>{
  const doc={documentElement:{lang:locale,setAttribute(){}},querySelector:()=>null},window={document:doc,navigator:{language:locale},dispatchEvent(){},CustomEvent:function(){}};let toast='',prompts=0;
  const context=vm.createContext({window,document:doc,navigator:window.navigator,Intl,pwaInstallCanBeOffered:()=>true,pwaInstallInFlight:false,pwaInstallPrompt:{async prompt(){prompts++},userChoice:Promise.resolve({outcome:'accepted'})},showToast:t=>{toast=t},syncPwaInstallControl(){},dismissSmartInstallBanner(){},isIosDevice:()=>false,openUniversalInstallGuideModal(){}});
  vm.runInContext(messages,context);window.TOANAASI18n.setLocale(locale,{emit:false});context.uiText=(key,fallback)=>window.TOANAASI18n.t(key)||fallback;
  const from=source.indexOf('  async function requestPwaInstall() {'),to=source.indexOf('  function bindPwaInstallEvents()',from);vm.runInContext(source.slice(from,to)+'\nglobalThis.requestInstall=requestPwaInstall;',context);await context.requestInstall();
  assert.equal(prompts,1);assert.ok(toast.includes({vi:'đã nhận yêu cầu',en:'received the install request',zh:'已收到安装请求'}[locale]));assert.doesNotMatch(toast,/đã được cài đặt|installed successfully|安装完成|sẽ hoàn tất cài đặt/i);if(locale==='en')assert.doesNotMatch(toast,/[\u00c0-\u024f\u4e00-\u9fff]/u);
 });
}
