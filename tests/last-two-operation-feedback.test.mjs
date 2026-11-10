import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source=fs.readFileSync(new URL('../static/portal/integration.js',import.meta.url),'utf8');
const catalog=fs.readFileSync(new URL('../static/portal/portal-i18n.js',import.meta.url),'utf8');
const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/last-two-operation-messages.json',import.meta.url),'utf8'));
const a=source.indexOf('  function toast(message, type) {'),b=source.indexOf('\n  }',a)+4;
function runtime(locale){
 const nodes=[],timers=[],noop=()=>{},region={querySelectorAll:()=>nodes,appendChild:node=>nodes.push(node)};
 const document={readyState:'loading',addEventListener:noop,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop}},querySelector:()=>region,createElement:()=>({className:'',textContent:'',attributes:{},setAttribute(k,v){this.attributes[k]=v;},remove(){const i=nodes.indexOf(this);if(i>=0)nodes.splice(i,1);}})};
 const window={document,navigator:{language:locale},location:{pathname:'/video-studio/image-motion-planner',search:''},localStorage:{getItem:()=>null,setItem:noop},addEventListener:noop,dispatchEvent:noop,setTimeout:(fn,ms)=>timers.push({fn,ms})};
 const ctx=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console});
 vm.runInContext(catalog,ctx);window.TOANAASI18n.setLocale(locale,{emit:false});
 return{toast:vm.runInContext('('+source.slice(a,b)+')',ctx),nodes,timers};
}
for(const locale of['vi','en','zh']){
 for(const[text,category]of Object.entries(fixture.map))test(locale+': exact last-two '+category+' feedback remains meaningful and localized: '+text,()=>{
  const r=runtime(locale);r.toast(text,'error');assert.equal(r.nodes.length,1);
  assert.equal(r.nodes[0].textContent,fixture.copy[category][locale]);
  assert.equal(r.nodes[0].attributes.role,'alert');assert.match(r.nodes[0].className,/warning/);assert.equal(r.timers[0].ms,6500);
 });
 for(const text of['Customer message <b>original</b>','__proto__','constructor','toString'])test(locale+': unknown operation message is not hidden or relabeled: '+text,()=>{
  const r=runtime(locale);r.toast(text);assert.equal(r.nodes[0].textContent,text);assert.equal(r.nodes[0].attributes.role,'status');
 });
 test(locale+': same operation feedback remains deduplicated and dismissible',()=>{
  const r=runtime(locale),text=Object.keys(fixture.map)[0];r.toast(text);r.toast(text);assert.equal(r.nodes.length,1);assert.equal(r.timers.length,1);r.timers[0].fn();assert.equal(r.nodes.length,0);
 });
}
