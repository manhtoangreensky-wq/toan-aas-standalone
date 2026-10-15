import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8'),messages=fs.readFileSync('static/portal/portal-i18n.js','utf8'),noop=()=>{};
function runtime(){
 let root=null,storageWrites=0;
 const document={readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],activeElement:null,
  documentElement:{lang:'vi',setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},
  body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop,appendChild(e){root=e}},
  getElementById(id){if(id==='portal-copilot-root')return root;if(id==='portal-copilot-toggle-btn')return root?._toggle||null;return null},
  createElement(){const container={id:'',_input:null,_toggle:null,_close:null,remove(){root=null},contains(e){return e===this._input||e===this._toggle},querySelector(s){return {'#portal-copilot-text-input':this._input,'#portal-copilot-toggle-btn':this._toggle,'#portal-copilot-close-btn':this._close}[s]||null},querySelectorAll:()=>[]};
   Object.defineProperty(container,'innerHTML',{get(){return this._html||''},set(html){this._html=html;this._input=html?{value:'',selectionStart:0,selectionEnd:0,focus(){document.activeElement=this},setSelectionRange(a,b){this.selectionStart=a;this.selectionEnd=b}}:null;this._toggle=html?{remove:noop}:null;this._close=html?{}:null}});return container}
 };
 const window={document,navigator:{language:'vi',userAgent:'QA'},location:{pathname:'/dashboard',search:'',href:'http://127.0.0.1:4178/dashboard'},addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null,setItem(){storageWrites++}},sessionStorage:{setItem(){storageWrites++}}};
 const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout,clearTimeout});vm.runInContext(messages,sandbox);
 vm.runInContext(source.replace('  window.TOANAASPortal = Object.freeze({','  window.__DraftTest={copilotState,mountPortalAiCopilot,renderCopilotHtml};\n  window.TOANAASPortal = Object.freeze({'),sandbox);
 const api=window.__DraftTest,session={path:'/dashboard',session:{authenticated:true,csrfToken:'qa-session-a'}};
 api.mountPortalAiCopilot(session);api.copilotState.open=true;
 return {api,document,session,mount:ctx=>api.mountPortalAiCopilot(ctx||session),render:()=>api.renderCopilotHtml(root,session),input:()=>root?._input,root:()=>root,storageWrites:()=>storageWrites};
}
test('Closing and reopening the assistant preserves exactly the unsent text in tab memory',()=>{
 const r=runtime();r.input().value='<QA text> & tiếng Việt';r.api.copilotState.open=false;r.render();r.api.copilotState.open=true;r.render();assert.equal(r.input().value,'<QA text> & tiếng Việt');assert.equal(r.storageWrites(),0);
});
test('Same-session hydration preserves assistant input, selection and its active focus',()=>{
 const r=runtime();r.input().value='QA unsent text';r.input().setSelectionRange(3,9);r.input().focus();r.mount();assert.equal(r.input().value,'QA unsent text');assert.equal(r.input().selectionStart,3);assert.equal(r.input().selectionEnd,9);assert.equal(r.document.activeElement,r.input());
});
test('Signing out clears the unsent draft before the same tab may sign in again',()=>{
 const r=runtime();r.input().value='Private account A draft';r.mount({path:'/dashboard',session:{authenticated:false,csrfToken:''}});assert.equal(r.root(),null);r.mount();assert.equal(r.input().value,'');assert.equal(r.api.copilotState.open,false);
});
test('Account-session replacement clears draft and prior assistant conversation rather than inheriting it',()=>{
 const r=runtime();r.input().value='Private account A draft';r.api.copilotState.messages.push({role:'user',text:'Private A conversation'});r.mount({path:'/dashboard',session:{authenticated:true,csrfToken:'qa-session-b'}});assert.equal(r.input().value,'');assert.equal(r.api.copilotState.messages.length,1);assert.equal(r.api.copilotState.open,false);
});
test('A signed bootstrap without a known session token cannot retain a prior account draft',()=>{
 const r=runtime();r.input().value='Unknown session owner';r.mount({path:'/dashboard',session:{authenticated:true,csrfToken:''}});assert.equal(r.input().value,'');assert.equal(r.api.copilotState.open,false);
});
