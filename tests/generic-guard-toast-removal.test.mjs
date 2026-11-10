import assert from 'node:assert/strict';
import fs from 'node:fs';

import vm from 'node:vm';
import test from 'node:test';

const source=fs.readFileSync(new URL('../static/portal/integration.js',import.meta.url),'utf8'),catalog=fs.readFileSync(new URL('../static/portal/portal-i18n.js',import.meta.url),'utf8'),a=source.indexOf('  function toast(message, type) {'),b=source.indexOf('\n  }',a)+4;
const suppressed=['Khả năng này đang được Core Bridge bảo vệ.','Không thể thực hiện thao tác này lúc này.','Cannot perform this action right now.','当前无法执行此操作。'];
function runtime(locale){
 const nodes=[],timers=[],noop=()=>{},region={querySelectorAll:()=>nodes,appendChild:node=>nodes.push(node)};
 const document={readyState:'loading',addEventListener:noop,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop}},querySelector:()=>region,createElement:()=>({className:'',textContent:'',attributes:{},setAttribute(k,v){this.attributes[k]=v;},remove(){const i=nodes.indexOf(this);if(i>=0)nodes.splice(i,1);}})};
 const window={document,navigator:{language:locale},location:{pathname:'/studio',search:''},localStorage:{getItem:()=>null,setItem:noop},addEventListener:noop,dispatchEvent:noop,setTimeout:(fn,ms)=>timers.push({fn,ms})};
 const ctx=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console});vm.runInContext(catalog,ctx);window.TOANAASI18n.setLocale(locale,{emit:false});return{toast:vm.runInContext('('+source.slice(a,b)+')',ctx),nodes,timers};
}
for(const locale of['vi','en','zh']){
 for(const message of suppressed)test(locale+': exact generic notice creates no visible toast or timer: '+message,()=>{const r=runtime(locale);r.toast(message,'error');assert.equal(r.nodes.length,0);assert.equal(r.timers.length,0);});
 for(const message of['Bạn cần đăng nhập để tiếp tục.','Thông tin nhập không hợp lệ.','Không thể tải dữ liệu. Vui lòng thử lại.','CUSTOMER_ERROR <b>exact</b>','__proto__','constructor',suppressed[1]+' Hãy kiểm tra quyền.', 'Chi tiết: '+suppressed[1]])test(locale+': actionable/unknown/lookalike error stays visible: '+message,()=>{const r=runtime(locale);r.toast(message,'error');assert.equal(r.nodes.length,1);assert.equal(r.nodes[0].textContent,message);assert.equal(r.nodes[0].attributes.role,'alert');assert.equal(r.timers[0].ms,6500);});
 test(locale+': specific duplicate errors keep deduplication and dismissal',()=>{const r=runtime(locale),text='Không thể tải dữ liệu. Vui lòng thử lại.';r.toast(text,'error');r.toast(text,'error');assert.equal(r.nodes.length,1);assert.equal(r.timers.length,1);r.timers[0].fn();assert.equal(r.nodes.length,0);});
}
