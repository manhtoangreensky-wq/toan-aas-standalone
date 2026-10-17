import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8'),messages=fs.readFileSync('static/portal/portal-i18n.js','utf8'),noop=()=>{};
function render(locale){
 const document={readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],getElementById:()=>null,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
 const window={document,navigator:{language:locale,userAgent:'QA'},location:{pathname:'/dashboard',search:'',href:'http://127.0.0.1:4178/dashboard'},addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null}};
 const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout,clearTimeout});vm.runInContext(messages,sandbox);
 vm.runInContext(source.replace('  window.TOANAASPortal = Object.freeze({','  window.__LayoutTest={renderCopilotHtml,copilotState};\n  window.TOANAASPortal = Object.freeze({'),sandbox);window.TOANAASI18n.setLocale(locale,{emit:false});
 const container={innerHTML:'',querySelector:()=>null,querySelectorAll:()=>[],contains:()=>false};window.__LayoutTest.renderCopilotHtml(container,{});return container.innerHTML;
}
for(const [locale,label] of [['vi','Gợi ý nhanh'],['en','Quick suggestions'],['zh','快捷建议']]){
 test(`Assistant offers all eleven suggestions behind a named native ${locale} disclosure`,()=>{
  const html=render(locale),details=html.match(/<details class="portal-copilot-suggestions"[^>]*>([\s\S]*?)<\/details>/)?.[1];assert.ok(details,'Suggestion choices need a native collapsible group rather than a horizontal strip');assert.match(details,new RegExp('<summary>'+label+'<\\/summary>'));assert.equal((details.match(/data-copilot-query=/g)||[]).length,11);
 });
}
test('The initial greeting starts at the top instead of scrolling past its instructions',()=>{
 const from=source.indexOf('  function bindCopilotListeners(container, context) {'),to=source.indexOf('  function renderCopilotHtml(container, context) {',from);
 const list={scrollTop:0,scrollHeight:700},container={querySelector:s=>s==='#portal-copilot-msgs-list'?list:null,querySelectorAll:()=>[]};
 const context=vm.createContext({container,copilotState:{messages:[{role:'assistant',copyKey:'welcome'}]},document:{getElementById:()=>null}});vm.runInContext(source.slice(from,to)+'\nbindCopilotListeners(container,{});',context);assert.equal(list.scrollTop,0,'A new user must see the greeting before the long vertical action list');
});
test('Later assistant replies retain the existing auto-scroll to the newest message',()=>{
 const from=source.indexOf('  function bindCopilotListeners(container, context) {'),to=source.indexOf('  function renderCopilotHtml(container, context) {',from);
 const list={scrollTop:0,scrollHeight:700},container={querySelector:s=>s==='#portal-copilot-msgs-list'?list:null,querySelectorAll:()=>[]};
 const context=vm.createContext({container,copilotState:{messages:[{role:'assistant'},{role:'user'},{role:'assistant'}]},document:{getElementById:()=>null}});vm.runInContext(source.slice(from,to)+'\nbindCopilotListeners(container,{});',context);assert.equal(list.scrollTop,700);
});
