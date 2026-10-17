import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8'),messages=fs.readFileSync('static/portal/portal-i18n.js','utf8'),noop=()=>{};
function header(locale,{route='/dashboard',signed=true,pwa=false}={}){
 const document={readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],getElementById:()=>null,
 documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
 const window={document,navigator:{language:locale,userAgent:'QA'},location:{pathname:route,search:'',href:'http://127.0.0.1:4178'+route},addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null}};
 const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout,clearTimeout});vm.runInContext(messages,sandbox);
 vm.runInContext(source.replace('  window.TOANAASPortal = Object.freeze({','  window.__UtilityTest={renderHeader,normalizeBootstrap};\n  window.TOANAASPortal = Object.freeze({'),sandbox);
 window.TOANAASI18n.setLocale(locale,{emit:false});const ctx=window.__UtilityTest.normalizeBootstrap({path:route,pwaEnabled:pwa,profile:{locale},session:{authenticated:signed,csrfToken:signed?'qa':''}});
 return window.__UtilityTest.renderHeader(window.TOANAASPortal.resolvePage(route),ctx);
}
for(const [locale,name] of [['vi','Tiện ích'],['en','Utilities'],['zh','工具']]){
 test(`Customer account menu owns a named ${locale} utility group`,()=>{
  const html=header(locale);assert.match(html,new RegExp('role="group" aria-label="'+name+'" data-portal-customer-utilities'));
  const menuStart=html.indexOf('data-portal-user-dropdown hidden'),slot=html.indexOf('data-portal-customer-utilities');assert.ok(slot>menuStart);
 });
}
test('PWA offering has one native install control inside the utility group, not the top toolbar',()=>{
 const html=header('en',{pwa:true}),slot=html.indexOf('data-portal-customer-utilities'),install=html.indexOf('data-portal-install-app');
 assert.equal(html.split('data-portal-install-app').length-1,1);assert.ok(slot>0&&install>slot,'Install control must belong to the utility group');
 const toolbarEnd=html.indexOf('portal-command-trigger');assert.ok(install>toolbarEnd,'Install control must not consume a top-level toolbar position');
});
test('Unsigned customer and Admin headers retain their prior navigation without a customer utility group',()=>{
 for(const options of [{signed:false},{route:'/admin',signed:true}])assert.ok(!header('en',options).includes('data-portal-customer-utilities'));
});
test('Collapsing a previously expanded install hint restores the one supported native menu entry',()=>{
 const native={hidden:true},slot={querySelector:()=>native},removed=[];
 const doc={body:{},querySelector(selector){if(selector==='[data-portal-customer-utilities]')return slot;if(selector.includes('data-portal-app-kind="customer"'))return {};if(selector==='[data-portal-smart-install-banner]')return {remove:()=>removed.push('banner')};return null;}};
 const start=source.indexOf('  function syncSmartInstallBanner() {'),end=source.indexOf('  function dismissSmartInstallBanner()',start);
 const runtime=vm.createContext({document:doc,window:{localStorage:{getItem:()=>null},sessionStorage:{getItem:()=>null}},isStandaloneApp:()=>false,pwaInstallCanBeOffered:()=>true});
 vm.runInContext(source.slice(start,end)+'\nsyncSmartInstallBanner();',runtime);
 assert.equal(native.hidden,false,'The existing ready install entry must be restored on collapse');assert.deepEqual(removed,['banner']);
});
function copilotBinding(){
 const toggle={},close={},input={focuses:0,focus(){this.focuses++}},trigger={attributes:{},focuses:0,setAttribute(k,v){this.attributes[k]=v},focus(){this.focuses++}},menu={hidden:false};
 const container={querySelector(s){return {'#portal-copilot-close-btn':close,'#portal-copilot-text-input':input}[s]||null},querySelectorAll:()=>[]};
 const state={open:false},context={};const runtime=vm.createContext({container,context,copilotState:state,document:{getElementById:()=>toggle,querySelector:s=>s==='[data-portal-user-dropdown]'?menu:trigger},renderCopilotHtml:noop});
 const start=source.indexOf('  function bindCopilotListeners(container, context) {'),end=source.indexOf('  function renderCopilotHtml(container, context) {',start);
 vm.runInContext(source.slice(start,end)+'\nbindCopilotListeners(container,context);',runtime);close.click=()=>close.onclick();
 return {toggle,close,container,state,trigger,menu,input};
}
test('Opening the moved assistant trigger dismisses the account menu and focuses the existing input',()=>{
 const h=copilotBinding();h.toggle.onclick();assert.equal(h.state.open,true);assert.equal(h.menu.hidden,true);assert.equal(h.trigger.attributes['aria-expanded'],'false');assert.equal(h.input.focuses,1);
});
test('Escape in the assistant closes the modeless dialog and restores account-menu trigger focus',()=>{
 const h=copilotBinding();h.state.open=true;let prevented=false,stopped=false;h.container.onkeydown({key:'Escape',preventDefault(){prevented=true},stopPropagation(){stopped=true}});
 assert.equal(h.state.open,false);assert.equal(h.trigger.focuses,1);assert.equal(prevented,true);assert.equal(stopped,true);
});
